"""Circuit breaker pattern implementation for external API resilience."""

import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from functools import wraps
from dataclasses import dataclass, field
from .logging import get_logger

logger = get_logger("circuit_breaker")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 30.0  # Seconds before trying half-open
    success_threshold: int = 2  # Successes needed to close from half-open
    timeout: float = 10.0  # Request timeout in seconds


@dataclass
class CircuitBreakerState:
    """State tracking for a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Usage:
        breaker = CircuitBreaker("google_maps")

        @breaker
        async def call_google_maps():
            ...
    """

    _instances: Dict[str, 'CircuitBreaker'] = {}

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        timeout: float = 10.0
    ):
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout
        )
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()

        # Register this instance
        CircuitBreaker._instances[name] = self

    @classmethod
    def get(cls, name: str) -> Optional['CircuitBreaker']:
        """Get a circuit breaker by name."""
        return cls._instances.get(name)

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuit breakers."""
        return {
            name: breaker.get_stats()
            for name, breaker in cls._instances.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "last_failure": self.state.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold
            }
        }

    async def _check_state(self) -> bool:
        """Check if request should be allowed. Returns True if allowed."""
        async with self._lock:
            current_time = time.time()

            if self.state.state == CircuitState.CLOSED:
                return True

            elif self.state.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                time_since_failure = current_time - self.state.last_failure_time
                if time_since_failure >= self.config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    return True
                return False

            elif self.state.state == CircuitState.HALF_OPEN:
                # Allow limited requests in half-open state
                return True

            return False

    async def _record_success(self):
        """Record a successful call."""
        async with self._lock:
            self.state.success_count += 1

            if self.state.state == CircuitState.HALF_OPEN:
                if self.state.success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    logger.info(f"Circuit breaker '{self.name}' recovered, transitioning to CLOSED")

    async def _record_failure(self, error: Exception):
        """Record a failed call."""
        async with self._lock:
            self.state.failure_count += 1
            self.state.last_failure_time = time.time()
            self.state.success_count = 0  # Reset success count on failure

            if self.state.state == CircuitState.HALF_OPEN:
                # Immediately open on failure in half-open state
                self._transition_to(CircuitState.OPEN)
                logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN, returning to OPEN")

            elif self.state.state == CircuitState.CLOSED:
                if self.state.failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"Circuit breaker '{self.name}' opened after {self.state.failure_count} failures"
                    )

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        self.state.state = new_state
        self.state.last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            self.state.failure_count = 0
            self.state.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.state.success_count = 0

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap async functions with circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not await self._check_state():
                logger.warning(f"Circuit breaker '{self.name}' is OPEN, rejecting request")
                raise CircuitBreakerOpenError(
                    f"Service '{self.name}' is currently unavailable"
                )

            try:
                # Apply timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
                await self._record_success()
                return result

            except asyncio.TimeoutError as e:
                await self._record_failure(e)
                logger.error(f"Circuit breaker '{self.name}': request timed out")
                raise

            except Exception as e:
                await self._record_failure(e)
                logger.error(f"Circuit breaker '{self.name}': request failed: {e}")
                raise

        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""
    pass


# Pre-configured circuit breakers for external APIs
google_maps_breaker = CircuitBreaker(
    name="google_maps",
    failure_threshold=5,
    recovery_timeout=60.0,
    timeout=15.0
)

google_calendar_breaker = CircuitBreaker(
    name="google_calendar",
    failure_threshold=5,
    recovery_timeout=60.0,
    timeout=15.0
)

openweathermap_breaker = CircuitBreaker(
    name="openweathermap",
    failure_threshold=5,
    recovery_timeout=30.0,
    timeout=10.0
)

todoist_breaker = CircuitBreaker(
    name="todoist",
    failure_threshold=5,
    recovery_timeout=30.0,
    timeout=10.0
)

alpha_vantage_breaker = CircuitBreaker(
    name="alpha_vantage",
    failure_threshold=3,
    recovery_timeout=60.0,
    timeout=15.0
)

coingecko_breaker = CircuitBreaker(
    name="coingecko",
    failure_threshold=5,
    recovery_timeout=30.0,
    timeout=10.0
)
