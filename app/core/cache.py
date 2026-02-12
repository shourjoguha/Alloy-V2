"""Advanced caching layer with query result caching support."""
import hashlib
import json
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.metrics import cache_hits, cache_misses

settings = get_settings()

P = ParamSpec('P')
T = TypeVar('T')


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    Generate a consistent cache key from function arguments.

    Args:
        prefix: Cache key prefix (e.g., function name)
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hash-based cache key string
    """
    key_data = {
        "args": args,
        "kwargs": {k: v for k, v in sorted(kwargs.items()) if v is not None},
    }
    key_hash = hashlib.sha256(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
    return f"{prefix}:{key_hash}"


async def get_cached(key: str) -> Any | None:
    """Get value from cache and track metrics."""
    r = await get_redis()
    value = await r.get(key)
    if value:
        cache_hits.inc()
        return json.loads(value)
    cache_misses.inc()
    return None


async def set_cached(key: str, value: Any, ttl: int = 300) -> None:
    """Set value in cache with TTL."""
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value))


async def invalidate_cache(key: str) -> None:
    """Invalidate cache entry."""
    r = await get_redis()
    await r.delete(key)


async def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate all cache entries matching a pattern."""
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        await r.delete(*keys)


def cache_result(ttl: int = 300, key_prefix: str | None = None):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds (default: 300)
        key_prefix: Custom key prefix (default: function name)

    Usage:
        @cache_result(ttl=600)
        async def get_user(user_id: int):
            return await db.get(User, user_id)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            prefix = key_prefix or func.__name__
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            cached = await get_cached(cache_key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            await set_cached(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


class QueryCache:
    """
    Caching decorator for SQLAlchemy query results.

    Provides intelligent caching for database queries with:
    - Automatic cache invalidation on writes
    - Key generation based on query parameters
    - Support for different cache strategies
    """

    def __init__(
        self,
        ttl: int = 300,
        prefix: str = "query",
        invalidate_on_write: bool = True,
    ):
        self.ttl = ttl
        self.prefix = prefix
        self.invalidate_on_write = invalidate_on_write

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache_key = self._generate_key(func.__name__, args, kwargs)
            cached = await get_cached(cache_key)
            if cached is not None:
                return cached

            result = await func(*args, **kwargs)
            await set_cached(cache_key, result, self.ttl)
            return result

        wrapper.cache_key_prefix = f"{self.prefix}:{func.__name__}"
        wrapper.invalidate_on_write = self.invalidate_on_write
        return wrapper

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key for query."""
        key_data = {"args": args, "kwargs": {k: v for k, v in sorted(kwargs.items()) if v is not None}}
        key_hash = hashlib.sha256(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
        return f"{self.prefix}:{func_name}:{key_hash}"


async def cache_query_result(
    session: AsyncSession,
    cache_key: str,
    query: str,
    params: dict | None = None,
    ttl: int = 300,
) -> list[Any] | None:
    """
    Cache SQLAlchemy query results.

    Args:
        session: Database session
        cache_key: Cache key for storing results
        query: SQL query string
        params: Query parameters
        ttl: Cache TTL in seconds

    Returns:
        Cached results or None if cache miss
    """
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    result = await session.execute(text(query), params or {})
    rows = result.fetchall()
    results = [dict(row._mapping) for row in rows]

    await set_cached(cache_key, results, ttl)
    return results


class CacheInvalidator:
    """
    Helper class for cache invalidation strategies.
    """

    @staticmethod
    async def invalidate_by_id(prefix: str, entity_id: int):
        """Invalidate cache entries by entity ID."""
        pattern = f"{prefix}:*{entity_id}*"
        await invalidate_cache_pattern(pattern)

    @staticmethod
    async def invalidate_by_user(prefix: str, user_id: int):
        """Invalidate cache entries by user ID."""
        pattern = f"{prefix}:*user_id={user_id}*"
        await invalidate_cache_pattern(pattern)

    @staticmethod
    async def invalidate_by_program(prefix: str, program_id: int):
        """Invalidate cache entries by program ID."""
        pattern = f"{prefix}:*program_id={program_id}*"
        await invalidate_cache_pattern(pattern)

    @staticmethod
    async def invalidate_all(prefix: str):
        """Invalidate all cache entries with a prefix."""
        pattern = f"{prefix}:*"
        await invalidate_cache_pattern(pattern)


async def warm_cache(keys: dict[str, Any], ttl: int = 300):
    """
    Pre-warm cache with data.

    Args:
        keys: Dictionary of cache keys to values
        ttl: TTL for all cache entries
    """
    r = await get_redis()
    for key, value in keys.items():
        await r.setex(key, ttl, json.dumps(value))


async def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache hit rate, memory usage, etc.
    """
    r = await get_redis()
    info = await r.info("stats")

    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0

    memory_info = await r.info("memory")
    used_memory = memory_info.get("used_memory_human", "unknown")

    return {
        "hits": hits,
        "misses": misses,
        "hit_rate": round(hit_rate, 2),
        "total_requests": total,
        "used_memory": used_memory,
    }
