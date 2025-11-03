from fastapi import APIRouter, Request, status

from src import create_logger
from src.api.core.rate_limit import limiter
from src.config import app_config
from src.schemas import HealthStatusSchema

logger = create_logger(name="status_route")

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def health_check(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
) -> HealthStatusSchema:
    """
    Simple health check endpoint to verify API is operational.

    Rate Limited to 60 requests per minute.

    Parameters
    ----------
        request:
            FastAPI request object
        limiter:
            Rate limiter dependency


    Returns
    -------
        HealthCheck: Status of the API
    """

    logger.info("Health check requested")
    return HealthStatusSchema(
        status=app_config.api_config.status, version=app_config.api_config.version
    )
