"""The briefing's Navi-suggestions section: best-effort and cadence-gated.

The section must be {} when Navi is down OR says the window isn't worth it
(worth_notifying False) — the briefing never breaks or nags on Navi's account.
"""

import pytest

from daily_ai_agent.agent.briefing import _fetch_navi_suggestions
from daily_ai_agent.services.navi_client import NaviError


class _FakeNavi:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    async def suggest(self, limit: int = 5):
        if self._error:
            raise self._error
        return self._result


@pytest.mark.asyncio
async def test_worth_notifying_window_becomes_a_section(monkeypatch):
    monkeypatch.setattr(
        "daily_ai_agent.agent.briefing.NaviClient",
        lambda: _FakeNavi({
            "window_label": "weekend", "window_start": "2026-07-18",
            "window_end": "2026-07-19", "worth_notifying": True,
            "suggestions": [{"id": f"s{i}", "title": f"t{i}"} for i in range(5)],
        }),
    )
    section = await _fetch_navi_suggestions()
    assert section["window_label"] == "weekend"
    assert len(section["suggestions"]) == 3  # briefing altitude: top 3 only


@pytest.mark.asyncio
async def test_quiet_gate_and_failures_yield_empty(monkeypatch):
    monkeypatch.setattr(
        "daily_ai_agent.agent.briefing.NaviClient",
        lambda: _FakeNavi({"worth_notifying": False, "suggestions": [{"id": "s1"}]}),
    )
    assert await _fetch_navi_suggestions() == {}

    monkeypatch.setattr(
        "daily_ai_agent.agent.briefing.NaviClient",
        lambda: _FakeNavi(error=NaviError("down")),
    )
    assert await _fetch_navi_suggestions() == {}
