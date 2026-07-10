"""Tests for the Navi planning tool (Aura -> Navi wiring).

Mirrors test_tools.py's convention: patch the tool's client accessor and mock
the async client method, so no network is touched.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from daily_ai_agent.agent.tools import NaviPlannerTool, get_all_tools


SAMPLE_PLAN = {
    "intent": "chill saturday in SF",
    "summary": "A relaxed Saturday: coffee, a coastal walk, then tacos.",
    "blocks": [
        {
            "title": "Andytown Coffee",
            "detail": "Start slow with a latte in the Outer Sunset.",
            "when": "09:00–10:00",
            "location": "Outer Sunset",
            "grounding": "reference",
            "source_ref": "r1",
        },
        {
            "title": "Lands End coastal trail",
            "detail": "Easy cliffside walk with ocean views.",
            "when": "10:30–12:00",
            "location": "Lands End",
            "grounding": "tool",
        },
    ],
}


class TestNaviPlannerTool:
    @pytest.fixture
    def tool(self) -> NaviPlannerTool:
        return NaviPlannerTool()

    def test_tool_name(self, tool):
        assert tool.name == "plan_outing"

    def test_tool_has_description(self, tool):
        assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_arun_formats_plan(self, tool):
        with patch.object(tool, "_get_navi_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.plan = AsyncMock(return_value=SAMPLE_PLAN)
            mock_get_client.return_value = mock_client

            result = await tool._arun("chill saturday in SF")

            assert "relaxed Saturday" in result
            assert "Andytown Coffee" in result
            assert "Lands End coastal trail" in result
            assert "Outer Sunset" in result

    @pytest.mark.asyncio
    async def test_arun_passes_intent_and_date(self, tool):
        with patch.object(tool, "_get_navi_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.plan = AsyncMock(return_value=SAMPLE_PLAN)
            mock_get_client.return_value = mock_client

            await tool._arun("weekend near Tahoe", on="2026-07-18")

            kwargs = mock_client.plan.call_args.kwargs
            assert kwargs["intent"] == "weekend near Tahoe"
            assert kwargs["on"] == "2026-07-18"
            # Aura hands Navi the user's home base as planning context.
            assert "home_base" in kwargs["context"]

    @pytest.mark.asyncio
    async def test_arun_handles_error(self, tool):
        with patch.object(tool, "_get_navi_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.plan = AsyncMock(side_effect=Exception("boom"))
            mock_get_client.return_value = mock_client

            result = await tool._arun("plan something")

            assert "Error planning via Navi" in result

    @pytest.mark.asyncio
    async def test_arun_empty_plan(self, tool):
        with patch.object(tool, "_get_navi_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.plan = AsyncMock(return_value={"summary": "nothing fit", "blocks": []})
            mock_get_client.return_value = mock_client

            result = await tool._arun("plan something impossible")

            assert "no plan blocks" in result


def test_navi_tool_registered_and_supersedes_itinerary():
    names = {t.name for t in get_all_tools()}
    assert "plan_outing" in names
    assert "generate_weekend_itinerary" not in names
