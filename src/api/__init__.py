import asyncio
import os
import time
import warnings
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status

from src import create_logger
from src.logic.graph import GraphManager

warnings.filterwarnings("ignore")
logger = create_logger(name="api_utilities")


MAX_WORKERS: int = os.cpu_count() - 1  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Initialize and cleanup FastAPI application lifecycle.

    This context manager handles the initialization of model components during startup
    and cleanup during shutdown.
    """
    try:
        start_time: float = time.perf_counter()
        logger.info("Starting up application and loading model...")

        # ===================================================
        # ================= Load model here =================
        # ===================================================

        # Initialize GraphManager with Postgres checkpointer for LangGraph
        app.state.graph_manager = GraphManager()
        await app.state.graph_manager.initialize_checkpointer()

        await asyncio.sleep(1)  # Simulate async model loading
        app.state.my_model = {"dummy": "model"}  # Placeholder for model instance

        logger.info(
            f"Application startup completed in {time.perf_counter() - start_time:.2f} seconds"
        )

        # Yield control to the application
        yield

    except Exception as e:
        logger.error(f"Failed to load model during startup: {e}")
        raise

    finally:
        # Cleanup on shutdown
        if hasattr(app.state, "my_model"):
            try:
                app.state.my_model = None
                logger.info("Model unloaded during shutdown")

            except Exception as e:
                logger.error(f"Error during shutdown cleanup: {e}")

        # Cleanup Postgres checkpointer
        if hasattr(app.state, "graph_manager"):
            try:
                await app.state.graph_manager.cleanup_checkpointer()
                logger.info("Postgres checkpointer cleaned up during shutdown")
            except Exception as e:
                logger.error(f"Error cleaning up checkpointer: {e}")


def get_model_manager(request: Request) -> dict[str, Any]:
    """Get the prediction service from the app state."""
    if not hasattr(request.app.state, "my_model") or request.app.state.my_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediction service not loaded. Please try again later.",
        )
    return request.app.state.my_model


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
