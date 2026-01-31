"""Tests for the circuit breaker utility."""

import pytest
import asyncio
from unittest.mock import AsyncMock

from mcp_server.utils.circuit_breaker import (
    CircuitBreaker, CircuitBreakerOpenError, CircuitState
)


class TestCircuitBreaker:
    """Test the CircuitBreaker class."""

    @pytest.fixture
    def breaker(self):
        """Create a test circuit breaker."""
        return CircuitBreaker(
            name="test_breaker",
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for tests
            success_threshold=2,
            timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, breaker):
        """Test that circuit breaker starts in closed state."""
        assert breaker.state.state == CircuitState.CLOSED
        assert breaker.state.failure_count == 0

    @pytest.mark.asyncio
    async def test_successful_call_passes(self, breaker):
        """Test that successful calls pass through."""
        @breaker
        async def successful_call():
            return "success"

        result = await successful_call()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_failure_increments_count(self, breaker):
        """Test that failures increment the failure count."""
        @breaker
        async def failing_call():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await failing_call()

        assert breaker.state.failure_count == 1

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, breaker):
        """Test that circuit opens after failure threshold."""
        @breaker
        async def failing_call():
            raise ValueError("test error")

        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await failing_call()

        assert breaker.state.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_rejects_when_open(self, breaker):
        """Test that requests are rejected when circuit is open."""
        # Manually open the circuit
        breaker.state.state = CircuitState.OPEN
        breaker.state.last_failure_time = asyncio.get_event_loop().time()

        @breaker
        async def test_call():
            return "success"

        with pytest.raises(CircuitBreakerOpenError):
            await test_call()

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self, breaker):
        """Test transition to half-open after recovery timeout."""
        # Open the circuit with old failure time
        breaker.state.state = CircuitState.OPEN
        breaker.state.last_failure_time = asyncio.get_event_loop().time() - 2.0  # 2 seconds ago

        # Should transition to half-open
        allowed = await breaker._check_state()
        assert allowed is True
        assert breaker.state.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self, breaker):
        """Test that circuit closes after successes in half-open state."""
        breaker.state.state = CircuitState.HALF_OPEN

        @breaker
        async def successful_call():
            return "success"

        # First success
        await successful_call()
        assert breaker.state.success_count == 1

        # Second success should close the circuit
        await successful_call()
        assert breaker.state.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self, breaker):
        """Test that circuit reopens on failure in half-open state."""
        breaker.state.state = CircuitState.HALF_OPEN

        @breaker
        async def failing_call():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await failing_call()

        assert breaker.state.state == CircuitState.OPEN

    def test_get_stats(self, breaker):
        """Test getting circuit breaker statistics."""
        stats = breaker.get_stats()

        assert stats["name"] == "test_breaker"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert "config" in stats

    @pytest.mark.asyncio
    async def test_timeout_triggers_failure(self, breaker):
        """Test that timeout triggers a failure."""
        breaker.config.timeout = 0.1  # 100ms timeout

        @breaker
        async def slow_call():
            await asyncio.sleep(1.0)  # Takes 1 second
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await slow_call()

        assert breaker.state.failure_count == 1


class TestCircuitBreakerRegistry:
    """Test the circuit breaker registry."""

    def test_get_breaker_by_name(self):
        """Test getting a breaker by name."""
        breaker = CircuitBreaker(name="registry_test")

        retrieved = CircuitBreaker.get("registry_test")
        assert retrieved is breaker

    def test_get_nonexistent_breaker(self):
        """Test getting a non-existent breaker."""
        retrieved = CircuitBreaker.get("nonexistent")
        assert retrieved is None

    def test_get_all_stats(self):
        """Test getting stats for all breakers."""
        CircuitBreaker(name="stats_test_1")
        CircuitBreaker(name="stats_test_2")

        all_stats = CircuitBreaker.get_all_stats()

        assert "stats_test_1" in all_stats
        assert "stats_test_2" in all_stats
