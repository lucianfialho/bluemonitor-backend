"""Redis cache configuration for FastAPI."""
from typing import Optional

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings

# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None


def get_redis_pool() -> ConnectionPool:
    """Get or create a Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        # Build connection parameters
        connection_params = {
            "host": settings.REDIS_HOST,
            "port": settings.REDIS_PORT,
            "db": settings.REDIS_DB,
            "password": settings.REDIS_PASSWORD or None,
            "socket_connect_timeout": settings.REDIS_TIMEOUT,
            "socket_timeout": settings.REDIS_TIMEOUT,
            "retry_on_timeout": True,
            "max_connections": 20,
        }
        
        # Only add ssl parameter if explicitly set to True
        if settings.REDIS_SSL:
            connection_params["ssl"] = True
            # Use rediss:// protocol for SSL/TLS
            url = f"rediss://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        else:
            url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            
        _redis_pool = ConnectionPool.from_url(
            url,
            **{k: v for k, v in connection_params.items() if v is not None}
        )
    return _redis_pool


def get_redis() -> Redis:
    """Get a Redis client from the connection pool."""
    return Redis(connection_pool=get_redis_pool())


async def init_cache() -> None:
    """Initialize the FastAPI cache with Redis backend."""
    redis = get_redis()
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


# Re-export the cache decorator with default settings
cache = cache  # pylint: disable=invalid-name
