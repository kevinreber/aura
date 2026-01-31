"""Utility modules for the MCP server."""

from .logging import get_logger, setup_logging, log_tool_call
from .cache import (
    CacheService, get_cache_service, generate_cache_key,
    cached, CacheTTL
)
from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerOpenError, CircuitState,
    google_maps_breaker, google_calendar_breaker, openweathermap_breaker,
    todoist_breaker, alpha_vantage_breaker, coingecko_breaker
)
from .rate_limiter import (
    RateLimiter, RateLimitExceededError, rate_limited,
    google_maps_limiter, google_calendar_limiter, openweathermap_limiter,
    todoist_limiter, alpha_vantage_limiter, coingecko_limiter
)
from .audit import audit_log, AuditTrail

__all__ = [
    # Logging
    'get_logger', 'setup_logging', 'log_tool_call',
    # Cache
    'CacheService', 'get_cache_service', 'generate_cache_key', 'cached', 'CacheTTL',
    # Circuit Breaker
    'CircuitBreaker', 'CircuitBreakerOpenError', 'CircuitState',
    'google_maps_breaker', 'google_calendar_breaker', 'openweathermap_breaker',
    'todoist_breaker', 'alpha_vantage_breaker', 'coingecko_breaker',
    # Rate Limiter
    'RateLimiter', 'RateLimitExceededError', 'rate_limited',
    'google_maps_limiter', 'google_calendar_limiter', 'openweathermap_limiter',
    'todoist_limiter', 'alpha_vantage_limiter', 'coingecko_limiter',
    # Audit
    'audit_log', 'AuditTrail'
]
