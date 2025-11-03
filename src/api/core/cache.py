"""
Caching utilities for FastAPI endpoints using aiocache with Redis backend.
"""

import hashlib
import json
import warnings
from functools import wraps
from types import CoroutineType
from typing import Any, Callable

from aiocache import Cache
from aiocache.serializers import JsonSerializer
from fastapi import Request

from src import create_logger
from src.config import app_settings

logger = create_logger(name="cache_utilities")
type CacheDecorator = Callable[..., Callable[..., CoroutineType[Any, Any, Any]]]


def setup_cache() -> Cache:
    """
    Initialize Redis cache (call once at startup).

    Connects to Redis using the REDIS_URL environment variable.
    Falls back to in-memory cache if Redis is not available.

    Returns:
        Cache: Configured cache instance (Redis or MEMORY fallback)
    """
    redis_url: str = app_settings.redis_url

    password = app_settings.REDIS_PASSWORD.get_secret_value()
    db: int = app_settings.REDIS_DB

    try:
        # Try to create Redis cache
        cache_kwargs: dict[str, Any] = {
            "endpoint": app_settings.REDIS_HOST,
            "port": app_settings.REDIS_PORT,
            "serializer": JsonSerializer(),
            "namespace": "main",
        }
        if password:
            cache_kwargs["password"] = password
        if db != 0:
            cache_kwargs["db"] = db

        return Cache(Cache.REDIS, **cache_kwargs)

    except Exception as e:
        warnings.warn(
            f"Failed to connect to Redis ({redis_url}): {e}. Falling back to MEMORY cache.",
            stacklevel=2,
        )
        # Fallback to in-memory cache
        return Cache(Cache.MEMORY, serializer=JsonSerializer(), namespace="main")


def cached(
    ttl: int = 300, key_prefix: str = ""
) -> Callable[[CacheDecorator], CacheDecorator]:
    """
    Decorator for caching endpoint responses.

    Args:
        ttl: Time to live in seconds (default 5 minutes)
        key_prefix: Prefix for cache key (useful for namespacing)

    Usage:
        @cached(ttl=60, key_prefix="products")
        async def get_products():
            ...
    """

    def decorator(func: CacheDecorator) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:  # noqa: ANN002, ANN003
            # Extract request and cache from kwargs
            request: Request | None = kwargs.get("request")
            cache: Cache | None = kwargs.get("cache")

            if not cache:
                # If no cache available, just call the function
                return await func(*args, **kwargs)  # type: ignore

            # Generate cache key from endpoint path and query params
            if request is None:
                raise ValueError("Request object is required for caching")
            cache_key = generate_cache_key(
                request.url.path, dict(request.query_params), key_prefix
            )

            # Try to get from cache
            cached_response = await cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Cache miss - call the actual function
            response = await func(*args, **kwargs)  # type: ignore

            # Store in cache
            await cache.set(cache_key, response, ttl=ttl)

            return response

        return wrapper

    return decorator


def generate_cache_key(path: str, params: dict[str, Any], prefix: str = "") -> str:
    """
    Generate a unique cache key from path and parameters.
    """
    # Create a deterministic string from params
    params_str = json.dumps(params, sort_keys=True)
    key_content = f"{path}:{params_str}"

    # Hash for shorter keys
    key_hash = hashlib.md5(key_content.encode()).hexdigest()

    if prefix:
        return f"{prefix}:{key_hash}"
    return key_hash


async def invalidate_cache(cache: Cache, pattern: str | None = None) -> None:
    """
    Invalidate cache entries. Use after data updates.

    Args:
        cache: Cache instance
        pattern: Pattern to match keys (None = clear all)
    """
    try:
        if pattern:
            await cache.clear(namespace=pattern.rstrip("*"))  # type: ignore
        else:
            await cache.clear()  # type: ignore
    except AttributeError:
        logger.warning(
            "Cache backend does not support clear operation for the given pattern."
        )
