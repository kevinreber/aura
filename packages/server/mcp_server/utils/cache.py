"""Caching utilities for external API responses."""

import asyncio
import json
import time
from typing import Any, Optional, Dict, Union, Callable
import hashlib
from functools import wraps
import redis.asyncio as aioredis
from .logging import get_logger
from ..config import get_settings

logger = get_logger("cache")


class CacheService:
    """Cache service with Redis backend and in-memory fallback."""
    
    def __init__(self):
        self.settings = get_settings()
        self._redis_client: Optional[aioredis.Redis] = None
        self._in_memory_cache: Dict[str, Dict[str, Any]] = {}
        self._connected = False
        
    async def initialize(self) -> bool:
        """Initialize Redis connection if available."""
        if not self.settings.redis_url:
            logger.info("No Redis URL configured, using in-memory cache only")
            return False
            
        try:
            self._redis_client = aioredis.from_url(
                self.settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self._redis_client.ping()
            self._connected = True
            logger.info("Redis cache initialized successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory cache: {e}")
            self._redis_client = None
            self._connected = False
            return False
    
    def _is_event_loop_closed(self) -> bool:
        """Check if the current event loop is closed or unavailable."""
        try:
            loop = asyncio.get_running_loop()
            return loop.is_closed()
        except RuntimeError:
            # No running event loop
            return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            # Try Redis first (only if properly connected and event loop is active)
            if self._connected and self._redis_client and not self._is_event_loop_closed():
                try:
                    value = await self._redis_client.get(key)
                    if value:
                        data = json.loads(value)
                        # Check if expired
                        if data.get('expires_at', 0) > time.time():
                            logger.debug(f"Cache hit (Redis): {key}")
                            return data['value']
                        else:
                            # Remove expired key
                            await self._redis_client.delete(key)
                except Exception as e:
                    logger.warning(f"Redis get error: {e}")
                    # Mark as disconnected if it's a connection-related error
                    if "Event loop is closed" in str(e) or "Connection closed" in str(e):
                        self._connected = False
                    
            # Fallback to in-memory cache
            if key in self._in_memory_cache:
                data = self._in_memory_cache[key]
                if data.get('expires_at', 0) > time.time():
                    logger.debug(f"Cache hit (memory): {key}")
                    return data['value']
                else:
                    # Remove expired key
                    del self._in_memory_cache[key]
                    
            logger.debug(f"Cache miss: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            if ttl is None:
                ttl = self.settings.cache_ttl
                
            expires_at = time.time() + ttl
            cache_data = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            # Try Redis first (only if properly connected and event loop is active)
            if self._connected and self._redis_client and not self._is_event_loop_closed():
                try:
                    await self._redis_client.setex(
                        key, 
                        ttl, 
                        json.dumps(cache_data, default=str)
                    )
                    logger.debug(f"Cache set (Redis): {key} (TTL: {ttl}s)")
                    return True
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
                    # Mark as disconnected if it's a connection-related error
                    if "Event loop is closed" in str(e) or "Connection closed" in str(e):
                        self._connected = False
                    
            # Fallback to in-memory cache
            self._in_memory_cache[key] = cache_data
            logger.debug(f"Cache set (memory): {key} (TTL: {ttl}s)")
            
            # Clean up expired in-memory entries periodically
            await self._cleanup_memory_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            deleted = False
            
            # Delete from Redis
            if self._connected and self._redis_client:
                try:
                    result = await self._redis_client.delete(key)
                    deleted = result > 0
                except Exception as e:
                    logger.warning(f"Redis delete error: {e}")
            
            # Delete from in-memory cache
            if key in self._in_memory_cache:
                del self._in_memory_cache[key]
                deleted = True
                
            if deleted:
                logger.debug(f"Cache delete: {key}")
                
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            # Clear Redis
            if self._connected and self._redis_client:
                try:
                    await self._redis_client.flushdb()
                except Exception as e:
                    logger.warning(f"Redis clear error: {e}")
            
            # Clear in-memory cache
            self._in_memory_cache.clear()
            
            logger.info("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def _cleanup_memory_cache(self):
        """Remove expired entries from in-memory cache."""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._in_memory_cache.items()
            if data.get('expires_at', 0) <= current_time
        ]
        
        for key in expired_keys:
            del self._in_memory_cache[key]
            
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'redis_connected': self._connected,
            'memory_cache_size': len(self._in_memory_cache),
            'redis_size': 0
        }
        
        if self._connected and self._redis_client:
            try:
                info = await self._redis_client.info()
                stats['redis_size'] = info.get('db0', {}).get('keys', 0)
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
                
        return stats


# Global cache instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
    return _cache_service


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from prefix and parameters."""
    # Create a consistent string representation
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        key_parts.append(str(arg))
    
    # Add keyword arguments (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    # Join and hash to handle long keys
    key_string = "|".join(key_parts)
    
    # If key is too long, hash it but keep prefix for readability
    if len(key_string) > 200:
        hash_suffix = hashlib.md5(key_string.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_suffix}"
    
    return key_string.replace(" ", "_").replace(":", "_")


def cached(prefix: str, ttl: int = None, key_func: Optional[Callable] = None):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await get_cache_service()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Use function name and arguments for key
                cache_key = generate_cache_key(
                    f"{prefix}:{func.__name__}",
                    *args,
                    **kwargs
                )
            
            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Only cache successful results (not None or empty)
            if result is not None:
                await cache.set(cache_key, result, ttl)
            
            return result
            
        return wrapper
    return decorator


# Cache TTL constants for different data types
class CacheTTL:
    """Cache TTL constants for different types of data."""
    
    # Weather data (changes every few hours)
    WEATHER_GEOCODING = 7 * 24 * 3600  # 7 days (coordinates don't change)
    WEATHER_FORECAST = 1800  # 30 minutes
    
    # Financial data (changes during market hours)
    FINANCIAL_STOCKS = 300  # 5 minutes during market hours
    FINANCIAL_CRYPTO = 120  # 2 minutes (crypto is more volatile)
    
    # Mobility data (changes with traffic)
    MOBILITY_DIRECTIONS = 900  # 15 minutes
    
    # Calendar data (events don't change frequently)
    CALENDAR_EVENTS = 600  # 10 minutes
    CALENDAR_FREE_TIME = 300  # 5 minutes
    
    # Default fallback
    DEFAULT = 300  # 5 minutes
