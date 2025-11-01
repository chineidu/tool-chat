"""
Test configuration and fixtures for the application.
"""

from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.pool import StaticPool

from src.db.crud import create_role
from src.db.models import Base
from src.schemas import RoleSchema
from src.schemas.types import RoleType


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
