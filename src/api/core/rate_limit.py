import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import redis.asyncio as redis
from fastapi import HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from src import create_logger
from src.config import app_settings

logger = create_logger(name="rate_limit")

# Create a global limiter instance
limiter = Limiter(key_func=get_remote_address)


def setup_rate_limiter() -> Limiter:
    """
    Initialize rate limiter (call once at startup).
    Uses client IP address as the key for rate limiting.
    """
    return Limiter(key_func=get_remote_address)


# Initialize Redis client for concurrent stream limiting
redis_client = redis.from_url(app_settings.redis_url)
CONCURRENT_STREAM_KEY: str = app_settings.CONCURRENT_STREAM_KEY
MAX_CONCURRENT: int = app_settings.MAX_CONCURRENT
TTL: int = app_settings.TTL

# Fallback in-memory counter for when Redis is unavailable
_concurrent_counter = 0
_concurrent_lock = asyncio.Lock()


async def check_concurrent_limit() -> None:
    """Check and increment concurrent stream counter."""
    global _concurrent_counter

    try:
        # Try Redis-based limiting first
        current = await redis_client.incr(CONCURRENT_STREAM_KEY)
        if current > MAX_CONCURRENT:
            await redis_client.decr(CONCURRENT_STREAM_KEY)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many concurrent streams (max {MAX_CONCURRENT})",
            ) from None
    except Exception:
        # Redis not available, use in-memory fallback
        async with _concurrent_lock:
            _concurrent_counter += 1
            if _concurrent_counter > MAX_CONCURRENT:
                _concurrent_counter -= 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"Too many concurrent streams (max {MAX_CONCURRENT})",
                ) from None


async def decrement_concurrent_count() -> None:
    """Decrement concurrent stream counter."""
    global _concurrent_counter

    try:
        # Try Redis-based decrement first
        await redis_client.decr(CONCURRENT_STREAM_KEY)
        # Optional: TTL to clean up stale increments
        await redis_client.expire(CONCURRENT_STREAM_KEY, TTL)
    except Exception:
        # Redis not available, use in-memory fallback
        async with _concurrent_lock:
            _concurrent_counter = max(0, _concurrent_counter - 1)


@asynccontextmanager
async def limit_concurrent_streams() -> AsyncGenerator[None, Any]:
    """Context manager to limit concurrent streaming responses."""
    global _concurrent_counter

    try:
        # Try Redis-based limiting first
        current = await redis_client.incr(CONCURRENT_STREAM_KEY)
        redis_available = True
    except Exception:
        # Redis not available, use in-memory fallback
        async with _concurrent_lock:
            _concurrent_counter += 1
            current = _concurrent_counter
        redis_available = False

    try:
        if current > MAX_CONCURRENT:
            if redis_available:
                await redis_client.decr(CONCURRENT_STREAM_KEY)
            else:
                async with _concurrent_lock:
                    _concurrent_counter -= 1
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Too many concurrent streams (max {MAX_CONCURRENT})",
            )

        try:
            yield
        finally:
            if redis_available:
                await redis_client.decr(CONCURRENT_STREAM_KEY)
                # Optional: TTL to clean up stale increments
                await redis_client.expire(CONCURRENT_STREAM_KEY, TTL)
            else:
                async with _concurrent_lock:
                    _concurrent_counter -= 1
    except Exception:
        # If something goes wrong, allow the request (fail open)
        yield
