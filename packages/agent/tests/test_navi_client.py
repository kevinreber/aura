"""Tests for NaviClient error categorization and auth, using respx to mock httpx.

These cover the failure paths that matter for observability: a slow Navi
(timeout), an unreachable Navi (connect error), a rejected request (401), and
the happy path (auth header is sent). Each failure must raise a NaviError with a
user-safe message so the tool can relay it instead of failing silently.
"""

import httpx
import pytest
import respx

from daily_ai_agent.models.config import reset_settings
from daily_ai_agent.services.navi_client import NaviClient, NaviError


@pytest.fixture(autouse=True)
def navi_env(monkeypatch):
    monkeypatch.setenv("NAVI_URL", "https://navi.test")
    monkeypatch.setenv("NAVI_INTERNAL_AUTH_SECRET", "s3cret")
    monkeypatch.setenv("NAVI_TIMEOUT", "5")
    reset_settings()
    yield
    reset_settings()


@pytest.mark.asyncio
@respx.mock
async def test_plan_success_sends_auth_header():
    route = respx.post("https://navi.test/plan").mock(
        return_value=httpx.Response(200, json={"intent": "x", "summary": "ok", "blocks": []})
    )
    data = await NaviClient().plan("plan my saturday")
    assert data["summary"] == "ok"
    assert route.calls.last.request.headers["X-Internal-Auth"] == "s3cret"


@pytest.mark.asyncio
@respx.mock
async def test_plan_401_raises_auth_navierror():
    respx.post("https://navi.test/plan").mock(return_value=httpx.Response(401, text="nope"))
    with pytest.raises(NaviError) as ei:
        await NaviClient().plan("x")
    assert "401" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_plan_timeout_raises_navierror():
    respx.post("https://navi.test/plan").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(NaviError) as ei:
        await NaviClient().plan("x")
    assert "didn't respond" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_plan_connect_error_raises_navierror():
    respx.post("https://navi.test/plan").mock(side_effect=httpx.ConnectError("no route"))
    with pytest.raises(NaviError) as ei:
        await NaviClient().plan("x")
    assert "reach Navi" in str(ei.value)
