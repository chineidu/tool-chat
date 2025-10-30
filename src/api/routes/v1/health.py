from fastapi import APIRouter, status

from src import create_logger
from src.config import app_config
from src.logic.graph import build_graph
from src.schemas import HealthStatusSchema

logger = create_logger(name="status_route")

router = APIRouter(tags=["health"])
graph = build_graph()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> HealthStatusSchema:
    """
    Simple health check endpoint to verify API is operational.

    Returns:
        HealthCheck: Status of the API
    """
    logger.info("Health check requested")
    return HealthStatusSchema(
        status=app_config.api_config.status, version=app_config.api_config.version
    )
