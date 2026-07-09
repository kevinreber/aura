"""Shared-secret authentication for the MCP server.

The server is deployed publicly on Fly and exposes calendar-write and vault-read
tools, so every internal caller (Aura's Agent, Navi) must prove it's trusted.
This is a **pure-ASGI** middleware, deliberately NOT a FastAPI
`@app.middleware("http")` / `BaseHTTPMiddleware`: the latter buffers responses
and breaks the long-lived `/mcp/sse` stream. Pure ASGI inspects the request on
the way in and passes the stream through untouched.

Behavior:
  - `INTERNAL_AUTH_SECRET` unset  -> open (local dev only; matches how the Agent
    and Navi skip their own auth when the secret is unset).
  - set -> every request except the public allowlist must carry a matching
    `X-Internal-Auth` header (constant-time compared).

Only `/health` stays public — Fly's health check hits it unauthenticated.
"""

from __future__ import annotations

import hmac

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

PUBLIC_PATHS = frozenset({"/health"})


class InternalAuthMiddleware:
    """Reject requests lacking a valid ``X-Internal-Auth`` header when a secret
    is configured. No-op when unset."""

    def __init__(self, app: ASGIApp, *, secret: str | None) -> None:
        self.app = app
        self.secret = secret or None  # treat "" as unset

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.secret is None:
            await self.app(scope, receive, send)
            return

        # CORS preflight carries no auth header; never gate it.
        if scope.get("method") == "OPTIONS" or scope.get("path") in PUBLIC_PATHS:
            await self.app(scope, receive, send)
            return

        provided = ""
        for name, value in scope.get("headers", []):
            if name == b"x-internal-auth":
                provided = value.decode("latin-1")
                break

        if not hmac.compare_digest(provided, self.secret):
            response = JSONResponse(
                {"error": "Unauthorized", "detail": "missing or invalid X-Internal-Auth"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
