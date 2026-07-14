"""Tests for LangChain tool implementations."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from daily_ai_agent.agent.tools import (
    WeatherTool,
    CalendarTool,
    CalendarRangeTool,
    TodoTool,
    CommuteTool,
    CommuteOptionsTool,
    FinancialTool,
    MorningBriefingTool,
    TrailScoutTool,
    ConcertAlertTool,
    ItineraryTool,
    get_all_tools,
)


class TestWeatherTool:
    """Tests for WeatherTool."""

    @pytest.fixture
    def tool(self) -> WeatherTool:
        """Create WeatherTool instance."""
        return WeatherTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_weather"

    def test_tool_has_description(self, tool):
        """Test tool has a description."""
        assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_arun_success(self, tool, sample_weather_data):
        """Test _arun returns formatted weather string."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_weather = AsyncMock(return_value=sample_weather_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun("San Francisco", "today")

            assert "San Francisco" in result
            assert "72.5" in result or "Partly Cloudy" in result

    @pytest.mark.asyncio
    async def test_arun_handles_error(self, tool):
        """Test _arun handles errors gracefully."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_weather = AsyncMock(side_effect=Exception("API error"))
            mock_get_client.return_value = mock_client

            result = await tool._arun("San Francisco", "today")

            assert "Error" in result


class TestCalendarTool:
    """Tests for CalendarTool."""

    @pytest.fixture
    def tool(self) -> CalendarTool:
        """Create CalendarTool instance."""
        return CalendarTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_calendar"

    @pytest.mark.asyncio
    async def test_arun_with_events(self, tool, sample_calendar_data):
        """Test _arun returns formatted calendar string."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_calendar_events = AsyncMock(return_value=sample_calendar_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun("2025-01-15")

            assert "2 events" in result
            assert "Team Standup" in result

    @pytest.mark.asyncio
    async def test_arun_no_events(self, tool):
        """Test _arun handles no events case."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_calendar_events = AsyncMock(
                return_value={"events": [], "total_events": 0}
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("2025-01-15")

            assert "No events" in result

    @pytest.mark.asyncio
    async def test_arun_surfaces_auth_error_payload(self, tool):
        """An error payload (expired Google auth) must not read as 'no events'."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_calendar_events = AsyncMock(
                return_value={
                    "date": "2025-01-15",
                    "events": [],
                    "total_events": 0,
                    "error": "Google Calendar authentication expired — "
                             "re-authentication required",
                    "auth_expired": True,
                }
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("2025-01-15")

            assert "re-authentication required" in result
            assert "No events" not in result


class TestCalendarRangeTool:
    """Tests for CalendarRangeTool."""

    @pytest.fixture
    def tool(self) -> CalendarRangeTool:
        """Create CalendarRangeTool instance."""
        return CalendarRangeTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_calendar_range"

    @pytest.mark.asyncio
    async def test_arun_groups_by_date(self, tool):
        """Test _arun groups events by date."""
        events_data = {
            "events": [
                {"title": "Event 1", "start_time": "2025-01-15T09:00:00"},
                {"title": "Event 2", "start_time": "2025-01-16T10:00:00"},
            ],
            "total_events": 2,
        }

        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_calendar_events_range = AsyncMock(return_value=events_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun("2025-01-15", "2025-01-16")

            assert "2 events" in result
            assert "2025-01-15" in result
            assert "2025-01-16" in result

    @pytest.mark.asyncio
    async def test_arun_surfaces_auth_error_payload(self, tool):
        """An error payload (expired Google auth) must not read as an empty week."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_calendar_events_range = AsyncMock(
                return_value={
                    "start_date": "2025-01-15",
                    "end_date": "2025-01-16",
                    "events": [],
                    "total_events": 0,
                    "error": "Google Calendar authentication expired — "
                             "re-authentication required",
                    "auth_expired": True,
                }
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("2025-01-15", "2025-01-16")

            assert "re-authentication required" in result
            assert "No events" not in result


class TestTodoTool:
    """Tests for TodoTool."""

    @pytest.fixture
    def tool(self) -> TodoTool:
        """Create TodoTool instance."""
        return TodoTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_todos"

    @pytest.mark.asyncio
    async def test_arun_prioritizes_high_priority(self, tool, sample_todos_data):
        """Test _arun shows high priority items first."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_todos = AsyncMock(return_value=sample_todos_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun("work")

            assert "HIGH" in result
            assert "pending" in result

    @pytest.mark.asyncio
    async def test_arun_no_pending(self, tool):
        """Test _arun handles no pending tasks."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_todos = AsyncMock(
                return_value={"items": [], "pending_count": 0}
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("work")

            assert "No pending" in result


class TestCommuteTool:
    """Tests for CommuteTool."""

    @pytest.fixture
    def tool(self) -> CommuteTool:
        """Create CommuteTool instance."""
        return CommuteTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_commute"

    @pytest.mark.asyncio
    async def test_arun_returns_commute_info(self, tool, sample_commute_data):
        """Test _arun returns formatted commute string."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_commute = AsyncMock(return_value=sample_commute_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun("Home", "Office", "driving")

            assert "Home" in result
            assert "Office" in result
            assert "35" in result  # duration


class TestCommuteOptionsTool:
    """Tests for CommuteOptionsTool."""

    @pytest.fixture
    def tool(self) -> CommuteOptionsTool:
        """Create CommuteOptionsTool instance."""
        return CommuteOptionsTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_commute_options"

    @pytest.mark.asyncio
    async def test_arun_includes_recommendation(self, tool, sample_commute_options_data):
        """Test _arun includes recommendation."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_commute_options = AsyncMock(
                return_value=sample_commute_options_data
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("to_work")

            assert "Recommendation" in result
            assert "transit" in result.lower() or "driving" in result.lower()


class TestFinancialTool:
    """Tests for FinancialTool."""

    @pytest.fixture
    def tool(self) -> FinancialTool:
        """Create FinancialTool instance."""
        return FinancialTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_financial_data"

    @pytest.mark.asyncio
    async def test_arun_formats_prices(self, tool, sample_financial_data):
        """Test _arun formats prices correctly."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=sample_financial_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun(["MSFT", "BTC"], "mixed")

            assert "MSFT" in result
            assert "$" in result


class TestMorningBriefingTool:
    """Tests for MorningBriefingTool."""

    @pytest.fixture
    def tool(self) -> MorningBriefingTool:
        """Create MorningBriefingTool instance."""
        return MorningBriefingTool()

    def test_tool_has_correct_name(self, tool):
        """Test tool has correct name."""
        assert tool.name == "get_morning_briefing"

    @pytest.mark.asyncio
    async def test_arun_combines_all_data(
        self, tool, sample_morning_data, sample_financial_data
    ):
        """Test _arun combines weather, calendar, todos, and commute."""
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_all_morning_data = AsyncMock(return_value=sample_morning_data)
            mock_client.call_tool = AsyncMock(return_value=sample_financial_data)
            mock_get_client.return_value = mock_client

            result = await tool._arun()

            assert "Weather" in result
            assert "Calendar" in result
            assert "Todos" in result


class TestGetAllTools:
    """Tests for get_all_tools function."""

    def test_returns_all_tools(self):
        """Test get_all_tools returns all expected tools."""
        tools = get_all_tools()

        tool_names = [t.name for t in tools]
        assert "get_weather" in tool_names
        assert "get_calendar" in tool_names
        assert "get_calendar_range" in tool_names
        assert "get_todos" in tool_names
        assert "get_commute" in tool_names
        assert "get_commute_options" in tool_names
        assert "get_financial_data" in tool_names
        assert "get_morning_briefing" in tool_names
        assert "get_weekend_trails" in tool_names
        assert "get_weekend_concerts" in tool_names
        # Navi supersedes the built-in itinerary generator (see NAVI_BOUNDARY.md).
        assert "plan_outing" in tool_names
        assert "generate_weekend_itinerary" not in tool_names

    def test_all_tools_have_descriptions(self):
        """Test all tools have descriptions."""
        tools = get_all_tools()

        for tool in tools:
            assert len(tool.description) > 0, f"Tool {tool.name} missing description"


# ==================== Weekend Orchestrator Tools ====================


SAMPLE_TRAILS_RESPONSE = {
    "trails": [
        {
            "name": "Marin Headlands Loop",
            "distance_miles": 6.2,
            "elevation_gain_ft": 1100,
            "difficulty": "moderate",
            "rating": 4.7,
            "url": "https://example.com/marin",
            "location": "San Francisco, CA",
        },
        {
            "name": "Lands End Trail",
            "distance_miles": 3.4,
            "elevation_gain_ft": 240,
            "difficulty": "easy",
            "rating": 4.5,
            "url": "https://example.com/lands-end",
            "location": "San Francisco, CA",
        },
    ],
    "source": "mock",
    "cached": False,
    "error": None,
}


SAMPLE_CONCERTS_RESPONSE = {
    "events": [
        {
            "artist": "Tycho",
            "venue": "The Fillmore",
            "date": "2026-03-21",
            "time": "20:00",
            "ticket_url": "https://example.com/tycho",
            "ticket_status": "available",
            "on_sale_date": None,
        },
    ],
    "source": "mock",
    "cached": False,
    "error": None,
}


SAMPLE_ITINERARY_RESPONSE = {
    "destination": "Denver, CO",
    "duration_days": 2,
    "points_of_interest": [
        {
            "name": "Hop Alley",
            "category": "restaurant",
            "rating": 4.5,
            "address": "RiNo, Denver, CO",
            "hours": "Wed-Sun 5pm-10pm",
            "price_level": 3,
            "description": "Modern Chinese cuisine",
        },
        {
            "name": "Bear Creek Trail",
            "category": "outdoors",
            "rating": 4.8,
            "address": "Bear Creek Park, Denver, CO",
            "hours": "Sunrise to sunset",
            "price_level": None,
            "description": "5.4 mi loop, moderate climb",
        },
    ],
    "transit_estimates": [
        {
            "from_location": "123 Main St",
            "to_location": "RiNo, Denver, CO",
            "drive_time_min": 13,
            "distance_miles": 4.2,
        }
    ],
    "source": "mock",
    "cached": False,
    "error": None,
}


class TestTrailScoutTool:
    """Tests for TrailScoutTool."""

    @pytest.fixture
    def tool(self) -> TrailScoutTool:
        return TrailScoutTool()

    def test_tool_has_correct_name(self, tool):
        assert tool.name == "get_weekend_trails"

    def test_tool_has_description(self, tool):
        assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_arun_formats_trails(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_TRAILS_RESPONSE)
            mock_get_client.return_value = mock_client

            result = await tool._arun("San Francisco, CA", "hiking", 10)

            assert "Marin Headlands Loop" in result
            assert "6.2 mi" in result
            assert "moderate" in result
            assert "★ 4.7" in result
            assert "mock" in result  # source is surfaced

    @pytest.mark.asyncio
    async def test_arun_omits_difficulty_when_none(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_TRAILS_RESPONSE)
            mock_get_client.return_value = mock_client

            await tool._arun("San Francisco, CA")

            payload = mock_client.call_tool.call_args.args[1]
            assert "difficulty" not in payload  # None should be stripped

    @pytest.mark.asyncio
    async def test_arun_handles_empty_trails(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(
                return_value={"trails": [], "source": "mock", "cached": False}
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("Nowhere, ZZ")

            assert "No trails found" in result

    @pytest.mark.asyncio
    async def test_arun_handles_error(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(side_effect=Exception("MCP down"))
            mock_get_client.return_value = mock_client

            result = await tool._arun("San Francisco, CA")

            assert "Error" in result


class TestConcertAlertTool:
    """Tests for ConcertAlertTool."""

    @pytest.fixture
    def tool(self) -> ConcertAlertTool:
        return ConcertAlertTool()

    def test_tool_has_correct_name(self, tool):
        assert tool.name == "get_weekend_concerts"

    @pytest.mark.asyncio
    async def test_arun_formats_concerts(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_CONCERTS_RESPONSE)
            mock_get_client.return_value = mock_client

            result = await tool._arun("San Francisco, CA", artists=["Tycho"])

            assert "Tycho" in result
            assert "The Fillmore" in result
            assert "2026-03-21" in result
            assert "🎟️" in result  # available ticket status

    @pytest.mark.asyncio
    async def test_arun_omits_artists_when_none(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_CONCERTS_RESPONSE)
            mock_get_client.return_value = mock_client

            await tool._arun("San Francisco, CA")

            payload = mock_client.call_tool.call_args.args[1]
            assert "artists" not in payload

    @pytest.mark.asyncio
    async def test_arun_handles_empty_events(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(
                return_value={"events": [], "source": "mock", "cached": False}
            )
            mock_get_client.return_value = mock_client

            result = await tool._arun("Nowhere, ZZ", artists=["NoOne"])

            assert "No upcoming concerts" in result


class TestItineraryTool:
    """Tests for ItineraryTool."""

    @pytest.fixture
    def tool(self) -> ItineraryTool:
        return ItineraryTool()

    def test_tool_has_correct_name(self, tool):
        assert tool.name == "generate_weekend_itinerary"

    @pytest.mark.asyncio
    async def test_arun_formats_itinerary_with_categories(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_ITINERARY_RESPONSE)
            mock_get_client.return_value = mock_client

            result = await tool._arun("Denver, CO", duration_days=2, interests=["food", "outdoors"])

            assert "Denver, CO" in result
            assert "Hop Alley" in result
            assert "Bear Creek Trail" in result
            # Categories grouped with emoji headers
            assert "Restaurant" in result
            assert "Outdoors" in result

    @pytest.mark.asyncio
    async def test_arun_includes_transit_when_present(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_ITINERARY_RESPONSE)
            mock_get_client.return_value = mock_client

            result = await tool._arun(
                "Denver, CO", duration_days=2, base_location="123 Main St"
            )

            assert "Transit" in result
            assert "13 min" in result

    @pytest.mark.asyncio
    async def test_arun_omits_base_location_when_none(self, tool):
        with patch.object(tool, "_get_mcp_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=SAMPLE_ITINERARY_RESPONSE)
            mock_get_client.return_value = mock_client

            await tool._arun("Denver, CO", duration_days=2)

            payload = mock_client.call_tool.call_args.args[1]
            assert "base_location" not in payload
