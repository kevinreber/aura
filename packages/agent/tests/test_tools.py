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

    def test_all_tools_have_descriptions(self):
        """Test all tools have descriptions."""
        tools = get_all_tools()

        for tool in tools:
            assert len(tool.description) > 0, f"Tool {tool.name} missing description"
