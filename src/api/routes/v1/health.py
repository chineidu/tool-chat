from aiocache import Cache
from fastapi import APIRouter, Depends, HTTPException, Request, status

from src import create_logger
from src.api import get_cache
from src.api.core.cache import cached
from src.api.core.rate_limit import limiter
from src.config import app_config
from src.schemas import HealthStatusSchema

logger = create_logger(name="status_route")

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
@cached(ttl=300, key_prefix="health")  # type: ignore
async def health_check(
    request: Request,  # Required by SlowAPI  # noqa: ARG001
    cache: Cache = Depends(get_cache),  # noqa: ARG001
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
    --------
        HealthStatusSchema: Status of the API
    """

    logger.info("Health check requested")
    try:
        return HealthStatusSchema(
            status=app_config.api_config.status,
            version=app_config.api_config.version,
        ).model_dump()
    except Exception as e:
        logger.warning(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed",
        ) from e
