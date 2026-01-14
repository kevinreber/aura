"""Per-API rate limiting implementation."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from collections import deque
from .logging import get_logger

logger = get_logger("rate_limiter")


@dataclass
class RateLimitConfig:
    """Configuration for a rate limiter."""
    requests_per_minute: int = 60
    requests_per_day: int = 1000
    burst_limit: int = 10  # Max requests in a short burst


@dataclass
class RateLimitState:
    """State tracking for rate limiting."""
    minute_requests: deque = field(default_factory=deque)
    day_requests: deque = field(default_factory=deque)
    last_request_time: float = 0.0


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Tracks requests per minute and per day for each API.

    Usage:
        limiter = RateLimiter("google_maps", requests_per_minute=60)

        if await limiter.acquire():
            # Make API call
        else:
            # Rate limited
    """

    _instances: Dict[str, 'RateLimiter'] = {}

    def __init__(
        self,
        name: str,
        requests_per_minute: int = 60,
        requests_per_day: int = 1000,
        burst_limit: int = 10
    ):
        self.name = name
        self.config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_day=requests_per_day,
            burst_limit=burst_limit
        )
        self.state = RateLimitState()
        self._lock = asyncio.Lock()

        # Register this instance
        RateLimiter._instances[name] = self

    @classmethod
    def get(cls, name: str) -> Optional['RateLimiter']:
        """Get a rate limiter by name."""
        return cls._instances.get(name)

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict]:
        """Get stats for all rate limiters."""
        return {
            name: limiter.get_stats()
            for name, limiter in cls._instances.items()
        }

    def get_stats(self) -> Dict:
        """Get current rate limiter statistics."""
        self._cleanup_old_requests()
        return {
            "name": self.name,
            "requests_last_minute": len(self.state.minute_requests),
            "requests_today": len(self.state.day_requests),
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_day": self.config.requests_per_day,
                "burst_limit": self.config.burst_limit
            },
            "remaining": {
                "minute": max(0, self.config.requests_per_minute - len(self.state.minute_requests)),
                "day": max(0, self.config.requests_per_day - len(self.state.day_requests))
            }
        }

    def _cleanup_old_requests(self):
        """Remove expired request timestamps."""
        current_time = time.time()
        minute_ago = current_time - 60
        day_ago = current_time - 86400

        # Clean minute window
        while self.state.minute_requests and self.state.minute_requests[0] < minute_ago:
            self.state.minute_requests.popleft()

        # Clean day window
        while self.state.day_requests and self.state.day_requests[0] < day_ago:
            self.state.day_requests.popleft()

    async def acquire(self) -> bool:
        """
        Try to acquire a rate limit token.

        Returns True if request is allowed, False if rate limited.
        """
        async with self._lock:
            self._cleanup_old_requests()
            current_time = time.time()

            # Check minute limit
            if len(self.state.minute_requests) >= self.config.requests_per_minute:
                logger.warning(
                    f"Rate limiter '{self.name}': minute limit exceeded "
                    f"({len(self.state.minute_requests)}/{self.config.requests_per_minute})"
                )
                return False

            # Check day limit
            if len(self.state.day_requests) >= self.config.requests_per_day:
                logger.warning(
                    f"Rate limiter '{self.name}': daily limit exceeded "
                    f"({len(self.state.day_requests)}/{self.config.requests_per_day})"
                )
                return False

            # Check burst limit (requests in last second)
            recent_requests = sum(
                1 for t in self.state.minute_requests
                if current_time - t < 1.0
            )
            if recent_requests >= self.config.burst_limit:
                logger.debug(
                    f"Rate limiter '{self.name}': burst limit hit, adding small delay"
                )
                await asyncio.sleep(0.1)  # Small delay for burst protection

            # Record request
            self.state.minute_requests.append(current_time)
            self.state.day_requests.append(current_time)
            self.state.last_request_time = current_time

            return True

    async def wait_and_acquire(self, max_wait: float = 60.0) -> bool:
        """
        Wait for rate limit to clear, then acquire.

        Returns True if acquired within max_wait, False if timed out.
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if await self.acquire():
                return True
            await asyncio.sleep(1.0)

        return False

    def get_wait_time(self) -> float:
        """Get estimated wait time until next request is allowed."""
        self._cleanup_old_requests()

        if len(self.state.minute_requests) < self.config.requests_per_minute:
            return 0.0

        if self.state.minute_requests:
            oldest_in_minute = self.state.minute_requests[0]
            wait_time = 60 - (time.time() - oldest_in_minute)
            return max(0.0, wait_time)

        return 0.0


def rate_limited(limiter: RateLimiter):
    """Decorator to apply rate limiting to an async function."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not await limiter.acquire():
                raise RateLimitExceededError(
                    f"Rate limit exceeded for '{limiter.name}'"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    pass


# Pre-configured rate limiters for external APIs
# Based on documented API limits

google_maps_limiter = RateLimiter(
    name="google_maps",
    requests_per_minute=60,  # Google allows higher, but be conservative
    requests_per_day=2500,
    burst_limit=10
)

google_calendar_limiter = RateLimiter(
    name="google_calendar",
    requests_per_minute=100,
    requests_per_day=10000,
    burst_limit=20
)

openweathermap_limiter = RateLimiter(
    name="openweathermap",
    requests_per_minute=60,  # Free tier limit
    requests_per_day=1000,
    burst_limit=10
)

todoist_limiter = RateLimiter(
    name="todoist",
    requests_per_minute=50,
    requests_per_day=5000,
    burst_limit=10
)

alpha_vantage_limiter = RateLimiter(
    name="alpha_vantage",
    requests_per_minute=5,  # Free tier: 5 calls/minute
    requests_per_day=500,   # Free tier: 500 calls/day
    burst_limit=2
)

coingecko_limiter = RateLimiter(
    name="coingecko",
    requests_per_minute=50,  # Free tier: 10-50 calls/minute
    requests_per_day=5000,
    burst_limit=10
)
