"""Tests for the rate limiter utility."""

import pytest
import asyncio
import time

from mcp_server.utils.rate_limiter import (
    RateLimiter, RateLimitExceededError, rate_limited
)


class TestRateLimiter:
    """Test the RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create a test rate limiter."""
        return RateLimiter(
            name="test_limiter",
            requests_per_minute=5,
            requests_per_day=100,
            burst_limit=3
        )

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self, limiter):
        """Test that requests under the limit are allowed."""
        for _ in range(3):
            allowed = await limiter.acquire()
            assert allowed is True

    @pytest.mark.asyncio
    async def test_blocks_when_minute_limit_exceeded(self, limiter):
        """Test that requests are blocked when minute limit is exceeded."""
        # Use up all requests
        for _ in range(5):
            await limiter.acquire()

        # Next request should be blocked
        allowed = await limiter.acquire()
        assert allowed is False

    @pytest.mark.asyncio
    async def test_cleanup_old_requests(self, limiter):
        """Test that old requests are cleaned up."""
        # Add some fake old timestamps
        limiter.state.minute_requests.append(time.time() - 120)  # 2 minutes ago
        limiter.state.day_requests.append(time.time() - 100000)  # More than a day ago

        limiter._cleanup_old_requests()

        assert len(limiter.state.minute_requests) == 0
        assert len(limiter.state.day_requests) == 0

    def test_get_stats(self, limiter):
        """Test getting rate limiter statistics."""
        stats = limiter.get_stats()

        assert stats["name"] == "test_limiter"
        assert stats["requests_last_minute"] == 0
        assert "config" in stats
        assert "remaining" in stats

    @pytest.mark.asyncio
    async def test_get_wait_time_when_available(self, limiter):
        """Test wait time when requests are available."""
        wait_time = limiter.get_wait_time()
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_get_wait_time_when_limited(self, limiter):
        """Test wait time when rate limited."""
        # Fill up the minute bucket
        for _ in range(5):
            await limiter.acquire()

        wait_time = limiter.get_wait_time()
        assert wait_time > 0.0
        assert wait_time <= 60.0

    @pytest.mark.asyncio
    async def test_wait_and_acquire_timeout(self, limiter):
        """Test wait_and_acquire with timeout."""
        # Fill up the bucket
        for _ in range(5):
            await limiter.acquire()

        # Should timeout waiting
        acquired = await limiter.wait_and_acquire(max_wait=0.1)
        assert acquired is False


class TestRateLimitedDecorator:
    """Test the @rate_limited decorator."""

    @pytest.mark.asyncio
    async def test_decorator_allows_requests(self):
        """Test that decorated function works when under limit."""
        limiter = RateLimiter(
            name="decorator_test",
            requests_per_minute=10
        )

        @rate_limited(limiter)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_raises_when_limited(self):
        """Test that decorator raises when rate limited."""
        limiter = RateLimiter(
            name="decorator_limit_test",
            requests_per_minute=1
        )

        @rate_limited(limiter)
        async def test_func():
            return "success"

        # First call should succeed
        await test_func()

        # Second call should raise
        with pytest.raises(RateLimitExceededError):
            await test_func()


class TestRateLimiterRegistry:
    """Test the rate limiter registry."""

    def test_get_limiter_by_name(self):
        """Test getting a limiter by name."""
        limiter = RateLimiter(name="registry_test_rl")

        retrieved = RateLimiter.get("registry_test_rl")
        assert retrieved is limiter

    def test_get_nonexistent_limiter(self):
        """Test getting a non-existent limiter."""
        retrieved = RateLimiter.get("nonexistent_rl")
        assert retrieved is None

    def test_get_all_stats(self):
        """Test getting stats for all limiters."""
        RateLimiter(name="rl_stats_test_1")
        RateLimiter(name="rl_stats_test_2")

        all_stats = RateLimiter.get_all_stats()

        assert "rl_stats_test_1" in all_stats
        assert "rl_stats_test_2" in all_stats
