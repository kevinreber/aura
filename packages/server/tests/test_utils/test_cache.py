"""Tests for the cache utility."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import time

from mcp_server.utils.cache import (
    CacheService, get_cache_service, generate_cache_key,
    cached, CacheTTL
)


class TestCacheService:
    """Test the CacheService class."""

    @pytest.fixture
    def cache_service(self):
        """Create a CacheService instance (in-memory only for tests)."""
        service = CacheService()
        return service

    @pytest.mark.asyncio
    async def test_cache_initialize_no_redis(self, cache_service):
        """Test initialization without Redis."""
        result = await cache_service.initialize()

        # Without Redis URL, should fall back to in-memory
        assert result is False
        assert cache_service._connected is False

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_service):
        """Test setting and getting a value."""
        await cache_service.initialize()

        # Set a value
        result = await cache_service.set("test_key", {"data": "value"}, ttl=60)
        assert result is True

        # Get the value
        value = await cache_service.get("test_key")
        assert value == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self, cache_service):
        """Test getting a non-existent key."""
        await cache_service.initialize()

        value = await cache_service.get("nonexistent_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_service):
        """Test deleting a cached value."""
        await cache_service.initialize()

        # Set a value
        await cache_service.set("delete_test", "value")

        # Delete it
        result = await cache_service.delete("delete_test")
        assert result is True

        # Verify it's gone
        value = await cache_service.get("delete_test")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_service):
        """Test clearing all cached values."""
        await cache_service.initialize()

        # Set multiple values
        await cache_service.set("key1", "value1")
        await cache_service.set("key2", "value2")

        # Clear cache
        result = await cache_service.clear()
        assert result is True

        # Verify all keys are gone
        assert await cache_service.get("key1") is None
        assert await cache_service.get("key2") is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self, cache_service):
        """Test that cached values expire."""
        await cache_service.initialize()

        # Set a value with very short TTL
        await cache_service.set("expiring_key", "value", ttl=1)

        # Should exist immediately
        value = await cache_service.get("expiring_key")
        assert value == "value"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be gone now
        value = await cache_service.get("expiring_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service):
        """Test getting cache statistics."""
        await cache_service.initialize()

        # Add some data
        await cache_service.set("stats_key", "value")

        stats = await cache_service.get_cache_stats()

        assert "redis_connected" in stats
        assert "memory_cache_size" in stats
        assert stats["memory_cache_size"] >= 1

    @pytest.mark.asyncio
    async def test_cache_complex_data_types(self, cache_service):
        """Test caching complex data types."""
        await cache_service.initialize()

        # Test list
        await cache_service.set("list_key", [1, 2, 3, "four"])
        value = await cache_service.get("list_key")
        assert value == [1, 2, 3, "four"]

        # Test nested dict
        nested = {"outer": {"inner": {"deep": "value"}}}
        await cache_service.set("nested_key", nested)
        value = await cache_service.get("nested_key")
        assert value == nested


class TestGenerateCacheKey:
    """Test the generate_cache_key function."""

    def test_generate_simple_key(self):
        """Test generating a simple cache key."""
        key = generate_cache_key("prefix", "arg1", "arg2")

        assert "prefix" in key
        assert "arg1" in key or len(key) < 200  # Either contains arg or is hashed

    def test_generate_key_with_kwargs(self):
        """Test generating a key with keyword arguments."""
        key = generate_cache_key("prefix", param1="value1", param2="value2")

        assert "prefix" in key

    def test_generate_key_consistency(self):
        """Test that same inputs produce same key."""
        key1 = generate_cache_key("test", "a", "b", x=1, y=2)
        key2 = generate_cache_key("test", "a", "b", x=1, y=2)

        assert key1 == key2

    def test_generate_key_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = generate_cache_key("test", "a")
        key2 = generate_cache_key("test", "b")

        assert key1 != key2

    def test_generate_key_long_input(self):
        """Test that long inputs are hashed."""
        long_args = ["x" * 50 for _ in range(10)]
        key = generate_cache_key("prefix", *long_args)

        # Should be hashed to a shorter key
        assert len(key) < 250

    def test_generate_key_special_characters(self):
        """Test handling of special characters."""
        key = generate_cache_key("prefix", "with space", "with:colon")

        # Spaces and colons should be replaced
        assert " " not in key


class TestCachedDecorator:
    """Test the @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        call_count = 0

        @cached("test_prefix", ttl=60)
        async def expensive_operation(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call should execute function
        result1 = await expensive_operation(5)
        assert result1 == 10
        assert call_count == 1

        # Second call should use cache
        result2 = await expensive_operation(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, used cache

    @pytest.mark.asyncio
    async def test_cached_decorator_different_args(self):
        """Test that different args get different cache entries."""
        call_count = 0

        @cached("test_prefix", ttl=60)
        async def operation(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        await operation(1)
        await operation(2)
        await operation(1)  # Should be cached

        assert call_count == 2  # Called for 1 and 2, third was cached


class TestCacheTTL:
    """Test the CacheTTL constants."""

    def test_weather_ttl(self):
        """Test weather-related TTL values."""
        assert CacheTTL.WEATHER_GEOCODING == 7 * 24 * 3600  # 7 days
        assert CacheTTL.WEATHER_FORECAST == 1800  # 30 minutes

    def test_financial_ttl(self):
        """Test financial TTL values."""
        assert CacheTTL.FINANCIAL_STOCKS == 300  # 5 minutes
        assert CacheTTL.FINANCIAL_CRYPTO == 120  # 2 minutes
        assert CacheTTL.FINANCIAL_CRYPTO < CacheTTL.FINANCIAL_STOCKS

    def test_mobility_ttl(self):
        """Test mobility TTL values."""
        assert CacheTTL.MOBILITY_DIRECTIONS == 900  # 15 minutes

    def test_calendar_ttl(self):
        """Test calendar TTL values."""
        assert CacheTTL.CALENDAR_EVENTS == 600  # 10 minutes
        assert CacheTTL.CALENDAR_FREE_TIME == 300  # 5 minutes

    def test_default_ttl(self):
        """Test default TTL value."""
        assert CacheTTL.DEFAULT == 300  # 5 minutes
