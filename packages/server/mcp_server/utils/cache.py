"""Cache service for Aura, backed by asyncresil.

Wraps ``asyncresil.MemoryCache`` and ``asyncresil.RedisCache`` while preserving
the historical ``CacheService`` API that Aura's tool and client code depends on:

- ``CacheService`` with ``initialize``/``get``/``set``/``delete``/``clear``/``get_cache_stats``
- ``get_cache_service`` global singleton getter
- ``generate_cache_key`` helper
- ``cached`` decorator
- ``CacheTTL`` constants

Reads prefer Redis (if connected) and fall back to memory. Writes go to both
so a Redis blip doesn't cause silent cache misses; memory acts as a
write-through replica.

Backwards-compat: if Redis holds entries in this module's previous wrapped
format (``{"value": ..., "expires_at": ..., "created_at": ...}``), ``get``
unwraps them. New writes use asyncresil's native format (raw value JSON).
Old entries phase out as their TTLs expire.
"""

import hashlib
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

import redis.asyncio as aioredis
from asyncresil import MemoryCache, RedisCache

from ..config import get_settings
from .logging import get_logger

logger = get_logger("cache")


class CacheService:
    """Cache facade backed by asyncresil.MemoryCache + (optional) RedisCache."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._memory = MemoryCache()
        self._redis: Optional[RedisCache] = None
        self._redis_client: Optional[aioredis.Redis] = None
        self._connected = False

    async def initialize(self) -> bool:
        """Connect the Redis backend if a URL is configured."""
        if not self.settings.redis_url:
            logger.info("No Redis URL configured, using in-memory cache only")
            return False

        try:
            self._redis_client = aioredis.from_url(
                self.settings.redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self._redis_client.ping()
            self._redis = RedisCache(redis_client=self._redis_client)
            self._connected = True
            logger.info("Redis cache initialized successfully")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory cache: {e}")
            self._redis = None
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get a value. Tries Redis first (if connected), falls back to memory."""
        if self._redis is not None and self._connected:
            try:
                value = await self._redis.get(key)
                if value is not None:
                    # Backwards-compat: unwrap pre-asyncresil format.
                    if (
                        isinstance(value, dict)
                        and "value" in value
                        and "expires_at" in value
                        and "created_at" in value
                    ):
                        if value.get("expires_at", 0) > time.time():
                            logger.debug(f"Cache hit (Redis, legacy format): {key}")
                            return value["value"]
                        # Expired legacy entry; treat as miss
                    else:
                        logger.debug(f"Cache hit (Redis): {key}")
                        return value
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                if "Event loop is closed" in str(e) or "Connection closed" in str(e):
                    self._connected = False

        value = await self._memory.get(key)
        if value is not None:
            logger.debug(f"Cache hit (memory): {key}")
            return value

        logger.debug(f"Cache miss: {key}")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in both backends with TTL. ttl=None uses settings default."""
        if ttl is None:
            ttl = self.settings.cache_ttl

        ttl_f: Optional[float] = float(ttl) if ttl and ttl > 0 else None

        try:
            if self._redis is not None and self._connected:
                try:
                    await self._redis.set(key, value, ttl_f)
                    logger.debug(f"Cache set (Redis): {key} (TTL: {ttl}s)")
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
                    if "Event loop is closed" in str(e) or "Connection closed" in str(e):
                        self._connected = False

            await self._memory.set(key, value, ttl_f)
            logger.debug(f"Cache set (memory): {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        deleted = False
        if self._redis is not None and self._connected:
            try:
                await self._redis.delete(key)
                deleted = True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")

        await self._memory.delete(key)
        deleted = True

        if deleted:
            logger.debug(f"Cache delete: {key}")
        return deleted

    async def clear(self) -> bool:
        """Clear both backends. Useful for tests; rarely called in production."""
        try:
            if self._redis_client is not None and self._connected:
                try:
                    await self._redis_client.flushdb()
                except Exception as e:
                    logger.warning(f"Redis clear error: {e}")

            # Reach into MemoryCache internals — acceptable since this module
            # owns the lifecycle of that instance.
            self._memory._store.clear()  # type: ignore[attr-defined]

            logger.info("Cache cleared")
            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "redis_connected": self._connected,
            "memory_cache_size": len(self._memory._store),  # type: ignore[attr-defined]
            "redis_size": 0,
        }

        if self._redis_client is not None and self._connected:
            try:
                info = await self._redis_client.info()
                stats["redis_size"] = info.get("db0", {}).get("keys", 0)
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")

        return stats


# Global cache instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get the global cache service instance, initializing on first call."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
    return _cache_service


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from prefix + positional + keyword arguments."""
    key_parts = [prefix]

    for arg in args:
        key_parts.append(str(arg))

    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")

    key_string = "|".join(key_parts)

    if len(key_string) > 200:
        hash_suffix = hashlib.md5(key_string.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_suffix}"

    return key_string.replace(" ", "_").replace(":", "_")


def cached(prefix: str, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator: cache an async function's result under (prefix, args, kwargs)."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache_service()

            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = generate_cache_key(
                    f"{prefix}:{func.__name__}", *args, **kwargs
                )

            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)

            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


class CacheTTL:
    """Cache TTL constants for different data types."""

    # Weather data
    WEATHER_GEOCODING = 7 * 24 * 3600  # 7 days
    WEATHER_FORECAST = 1800  # 30 minutes

    # Financial data
    FINANCIAL_STOCKS = 300  # 5 minutes
    FINANCIAL_CRYPTO = 120  # 2 minutes

    # Mobility
    MOBILITY_DIRECTIONS = 900  # 15 minutes

    # Calendar
    CALENDAR_EVENTS = 600  # 10 minutes
    CALENDAR_FREE_TIME = 300  # 5 minutes

    # Weekend
    WEEKEND_TRAILS = 24 * 3600  # 24 hours
    WEEKEND_CONCERTS = 3600  # 1 hour
    WEEKEND_POIS = 12 * 3600  # 12 hours

    # Default
    DEFAULT = 300  # 5 minutes
