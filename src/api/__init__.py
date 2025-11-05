import os
import time
import warnings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiocache import Cache
from fastapi import FastAPI, HTTPException, Request, status
from langfuse.langchain import CallbackHandler

from src import create_logger
from src.api.core.cache import setup_cache
from src.api.core.rate_limit import limiter
from src.db.init import init_db
from src.logic.graph import GraphManager

warnings.filterwarnings("ignore")
logger = create_logger(name="api_utilities")


MAX_WORKERS: int = os.cpu_count() - 1  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Initialize and cleanup FastAPI application lifecycle.

    This context manager handles the initialization of required resources
    during startup and cleanup during shutdown.
    """
    try:
        start_time: float = time.perf_counter()
        logger.info("Starting up application and loading model...")

        # Initialize database
        init_db()

        # ====================================================
        # ================= Load Dependencies ================
        # ====================================================

        # Initialize GraphManager with Postgres checkpointer for LangGraph
        app.state.graph_manager = GraphManager()
        await app.state.graph_manager.initialize_checkpointer()
        logger.info("GraphManager initialized with Postgres checkpointer")

        # Initialize Langfuse callback handler
        app.state.langfuse_handler = CallbackHandler()

        # Initialize cache
        app.state.cache = setup_cache()
        logger.info("Cache initialized")

        # Initialize rate limiter
        app.state.limiter = limiter
        logger.info("Rate limiter initialized")

        logger.info(
            f"Application startup completed in {time.perf_counter() - start_time:.2f} seconds"
        )

        # Yield control to the application
        yield

    # Cleanup and shutdown
    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}")
        raise

    finally:
        logger.info("Shutting down application...")
        # Cleanup Postgres checkpointer
        if hasattr(app.state, "graph_manager"):
            try:
                await app.state.graph_manager.cleanup_checkpointer()
                logger.info("Postgres checkpointer cleaned up during shutdown")
            except Exception as e:
                logger.error(f"Error cleaning up checkpointer: {e}")

            try:
                await app.state.graph_manager.cleanup_long_term_memory()
                logger.info("Long-term memory store cleaned up during shutdown")
            except Exception as e:
                logger.error(f"Error cleaning up long-term memory: {e}")

        # Cleanup Langfuse handler
        if hasattr(app.state, "langfuse_handler"):
            try:
                app.state.langfuse_handler = None  # type: ignore
                logger.info("Langfuse handler closed during shutdown")
            except Exception as e:
                logger.error(f"Error closing Langfuse handler: {e}")

        if hasattr(app.state, "cache"):
            # Cache will be automatically garbage collected
            try:
                await app.state.cache.clear()  # type: ignore
            except Exception as e:
                logger.warning(f"Error clearing cache during shutdown: {e}")
            logger.info("Cache shutdown initiated")


# ======================================================
# =============== Dependency Injection =================
# ======================================================
def get_graph_manager(request: Request) -> GraphManager:
    """Get the GraphManager from the app state."""
    if (
        not hasattr(request.app.state, "graph_manager")
        or request.app.state.graph_manager is None
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph manager not loaded. Please try again later.",
        )
    return request.app.state.graph_manager


async def get_cache(request: Request) -> Cache:
    """Dependency to inject cache into endpoints."""
    return request.app.state.cache


def get_langfuse_handler(request: Request) -> CallbackHandler:
    """Get the Langfuse CallbackHandler from the app state."""
    if (
        not hasattr(request.app.state, "langfuse_handler")
        or request.app.state.langfuse_handler is None
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse handler not loaded. Please try again later.",
        )
    return request.app.state.langfuse_handler
