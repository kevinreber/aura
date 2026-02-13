"""Security middleware for the MCP server.

Provides API key authentication, security headers, and request size limiting.
"""

import hmac
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .config import get_settings
from .utils.logging import get_logger

logger = get_logger("security")

# Endpoints that bypass API key authentication
AUTH_EXEMPT_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Prefixes that bypass authentication (MCP SSE needs open access for protocol clients)
AUTH_EXEMPT_PREFIXES = (
    "/mcp/",
)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates API key on incoming requests.

    When an API key is configured (API_KEY env var), all requests must
    include a matching X-API-Key header. Health, docs, and MCP protocol
    endpoints are exempt.

    When no API key is configured (development mode), all requests pass through.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        # If no API key configured, skip auth (development mode)
        if not settings.api_key:
            return await call_next(request)

        path = request.url.path

        # Skip auth for exempt endpoints
        if path in AUTH_EXEMPT_PATHS or path.startswith(AUTH_EXEMPT_PREFIXES):
            return await call_next(request)

        # Skip auth for OPTIONS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Validate API key
        provided_key = request.headers.get("X-API-Key", "")
        if not provided_key or not hmac.compare_digest(provided_key, settings.api_key):
            logger.warning(
                f"Unauthorized request to {path} from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS only in production
        settings = get_settings()
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that rejects requests with bodies exceeding the configured limit."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"error": "Request body too large"},
            )

        return await call_next(request)
