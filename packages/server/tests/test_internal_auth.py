"""Auth-boundary tests for the MCP server's shared-secret middleware.

Self-contained and offline: builds the FastAPI app with a patched settings
object and drives it via Starlette's TestClient. The middleware short-circuits
before routing, so the protected-endpoint tests never touch an external API.

(The legacy tests/conftest.py fixtures are Flask-style — `app.test_client()`,
`response.data` — and don't apply to this FastAPI app; hence a fresh module.)
"""

import pytest
from fastapi.testclient import TestClient

import mcp_server.app as app_module
from mcp_server.config import Settings

SECRET = "test-internal-secret"


def _build_app(secret):
    """create_app() captures get_settings() into the auth middleware, so patch
    the name app.py resolves before building."""
    settings = Settings(environment="testing", debug=True, internal_auth_secret=secret)
    orig = app_module.get_settings
    app_module.get_settings = lambda: settings
    try:
        return app_module.create_app()
    finally:
        app_module.get_settings = orig


@pytest.fixture
def enforced_client():
    # Bare TestClient (no `with`) skips lifespan — no Redis/vault-sync needed.
    return TestClient(_build_app(SECRET))


@pytest.fixture
def open_client():
    return TestClient(_build_app(None))


def test_health_is_public_without_header(enforced_client):
    assert enforced_client.get("/health").status_code == 200


def test_tools_list_rejected_without_header(enforced_client):
    assert enforced_client.get("/tools").status_code == 401


def test_rejected_with_wrong_secret(enforced_client):
    assert enforced_client.get("/tools", headers={"X-Internal-Auth": "nope"}).status_code == 401


def test_sensitive_tool_call_rejected_without_header(enforced_client):
    # Rejected by the middleware before the calendar tool runs — no side effect.
    assert enforced_client.post("/tools/calendar_create_event", json={}).status_code == 401


def test_allowed_with_correct_secret(enforced_client):
    r = enforced_client.get("/tools", headers={"X-Internal-Auth": SECRET})
    assert r.status_code == 200
    assert "tools" in r.json()


def test_open_mode_allows_without_header(open_client):
    # Secret unset -> middleware is a no-op (local dev / not-yet-provisioned).
    assert open_client.get("/tools").status_code == 200
