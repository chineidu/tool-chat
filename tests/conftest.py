"""
Test configuration and fixtures for the application.
"""

from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.pool import StaticPool

from src.api.app import app
from src.db.crud import create_role
from src.db.models import Base
from src.logic.graph import GraphManager
from src.schemas import RoleSchema
from src.schemas.types import RoleType

if TYPE_CHECKING:
    from fastapi import FastAPI


# ==========================================================
# ======================== CLIENT  =========================
# ==========================================================
@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Create a TestClient for FastAPI app."""
    # Import here to avoid circular imports
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from src.api.routes import feedback, health, history, streamer
    from src.config import app_config

    # Create a test app without lifespan to avoid database connections
    prefix = app_config.api_config.prefix
    test_app = FastAPI(
        title="Test API",
        description="API for testing",
        version="1.0.0",
        docs_url=None,  # Disable docs for tests
        redoc_url=None,
        lifespan=None,  # No lifespan for tests
    )

    # Configure CORS middleware (same as production)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.api_config.middleware.cors.allow_origins,
        allow_credentials=app_config.api_config.middleware.cors.allow_credentials,
        allow_methods=app_config.api_config.middleware.cors.allow_methods,
        allow_headers=app_config.api_config.middleware.cors.allow_headers,
    )

    # Include routers
    test_app.include_router(feedback.router, prefix=prefix)
    test_app.include_router(health.router, prefix=prefix)
    test_app.include_router(streamer.router, prefix=prefix)
    test_app.include_router(history.router, prefix=prefix)

    with TestClient(test_app) as test_client:
        yield test_client


# ==========================================================
# ==================== CRUD Operations =====================
# ==========================================================
@pytest.fixture(
    # Created ONCE for the entire test session
    scope="session",
)
def engine() -> Generator[Engine, None, None]:
    """Create a test database engine using SQLite."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            # Allow usage of the same connection in different threads
            "check_same_thread": False,
        },
        poolclass=StaticPool,
        echo=False,
    )
    yield test_engine


@pytest.fixture(scope="session")
def tables(engine: Engine) -> Generator[None, None, None]:
    """Create all database tables.

    It uses the engine fixture to get the test database engine.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def initialized_db(engine: Engine, tables: None) -> Generator[None, None, None]:  # noqa: ARG001
    """Initialize the test database with default roles.

    It uses the tables fixture to ensure tables are created.
    """
    # Create default roles if they do not exist
    description: list[str] = [
        "Administrator with full access",
        "Standard user with limited access",
        "Guest user with read-only access",
    ]

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with TestingSessionLocal() as session:
        try:
            for role, desc in zip(RoleType, description):
                create_role(db=session, role=RoleSchema(name=role, description=desc))

        except Exception:  # noqa: S110
            pass
    yield


@pytest.fixture
def db_session(engine: Engine, initialized_db: None) -> Generator[Session, None, None]:  # noqa: ARG001
    """Create a test database session with transaction rollback.

    It uses the initialized_db fixture to ensure the database is set up.

    Notes
    -----
    - Uses the same SQLite database (created once)
    - Has all tables created
    - Contains default roles
    - Automatically rolls back all changes

    Dependency Chain
    ----------------
    engine (session) → tables (session) → initialized_db (session) → db_session (function)
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    session.begin()  # Start a transaction
    try:
        yield session
    finally:
        session.rollback()  # Rollback all changes after test
        session.close()


# ==========================================================
# ===================== LLM Operations =====================
# ==========================================================
type EventStreamFactory = Callable[..., AsyncGenerator[AIMessageChunk, None]]


@pytest.fixture
def mock_astream_events() -> type[EventStreamFactory]:  # type: ignore
    """Create a mock async event stream generator for AIMessageChunk events."""

    def _builder(events: list[AIMessageChunk]) -> type[EventStreamFactory]:  # type: ignore
        async def _astream_events(
            *args: Any, **kwargs: Any
        ) -> AsyncGenerator[AIMessageChunk, None]:  # noqa: ARG001
            for event in events:
                yield event

        return _astream_events

    return _builder


# Mock GraphManager fixture
@pytest.fixture
def mock_graph_manager() -> Generator[
    Callable[[list[dict[str, Any]], FastAPI | None], None], None, None
]:  # noqa: ANN001
    """Create a mock GraphManager with astream_events method."""

    overridden_apps: list["FastAPI"] = []

    def _create(
        events: list[dict[str, Any]], target_app: FastAPI | None = None
    ) -> None:
        async def astream_events(
            *args: Any, **kwargs: Any
        ) -> AsyncGenerator[dict[str, Any], None]:  # noqa: ARG001
            for event in events:
                yield event

        # Build mock graph
        _graph = MagicMock()
        _graph.astream_events = astream_events

        # Build mock GraphManager
        graph_manager = MagicMock(spec=GraphManager)
        graph_manager.build_graph = AsyncMock(return_value=_graph)
        # Override dependency
        from src.api import get_graph_manager

        app_to_override = target_app or app
        app_to_override.dependency_overrides[get_graph_manager] = lambda: graph_manager
        overridden_apps.append(app_to_override)

    yield _create
    from src.api import get_graph_manager

    for overridden_app in overridden_apps:
        overridden_app.dependency_overrides.pop(get_graph_manager, None)


@pytest.fixture
def parse_sse_event() -> Callable[[str], list[dict[str, Any]]]:
    """Fixture to parse Server-Sent Events (SSE) from streaming response content."""
    from src.frontend.app import parse_sse_event as _parse_sse_event

    def _parse_response(content: str) -> list[dict[str, Any]]:
        """Parse all SSE events from response content string."""
        events: list[dict[str, Any]] = []
        for line in content.splitlines():
            event: dict[str, Any] | None = _parse_sse_event(line)
            if event:
                events.append(event)
        return events

    return _parse_response
