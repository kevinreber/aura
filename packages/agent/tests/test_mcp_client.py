"""Tests for the MCP client service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from daily_ai_agent.services.mcp_client import MCPClient


class TestMCPClient:
    """Tests for MCPClient class."""

    @pytest.fixture
    def client(self, mock_settings) -> MCPClient:
        """Create MCPClient instance with mocked settings."""
        return MCPClient()

    @pytest.mark.asyncio
    async def test_call_tool_success(self, client, sample_weather_data):
        """Test successful tool call."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_weather_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.call_tool("weather.get_daily", {"location": "SF"})
            assert result == sample_weather_data
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_http_error(self, client):
        """Test tool call handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception) as exc_info:
                await client.call_tool("weather.get_daily", {"location": "SF"})
            # Error message comes from retry logic - check for server error indication
            assert "Server error" in str(exc_info.value) or "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_tool_timeout(self, client):
        """Test tool call handles timeout."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception) as exc_info:
                await client.call_tool("weather.get_daily", {"location": "SF"})
            assert "Timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_weather(self, client, sample_weather_data):
        """Test get_weather convenience method."""
        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_weather_data

            result = await client.get_weather("San Francisco", "today")

            mock_call.assert_called_once_with(
                "weather.get_daily", {"location": "San Francisco", "when": "today"}
            )
            assert result == sample_weather_data

    @pytest.mark.asyncio
    async def test_get_calendar_events(self, client, sample_calendar_data):
        """Test get_calendar_events convenience method."""
        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_calendar_data

            result = await client.get_calendar_events("2025-01-15")

            mock_call.assert_called_once_with(
                "calendar.list_events", {"date": "2025-01-15"}
            )
            assert result == sample_calendar_data

    @pytest.mark.asyncio
    async def test_get_todos_with_bucket(self, client, sample_todos_data):
        """Test get_todos with specific bucket."""
        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_todos_data

            result = await client.get_todos("work", include_completed=False)

            mock_call.assert_called_once_with(
                "todo.list", {"include_completed": False, "bucket": "work"}
            )
            assert result == sample_todos_data

    @pytest.mark.asyncio
    async def test_get_todos_without_bucket(self, client, sample_todos_data):
        """Test get_todos without bucket returns all todos."""
        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_todos_data

            result = await client.get_todos(None, include_completed=False)

            mock_call.assert_called_once_with(
                "todo.list", {"include_completed": False}
            )
            assert result == sample_todos_data

    @pytest.mark.asyncio
    async def test_get_commute(self, client, sample_commute_data):
        """Test get_commute convenience method."""
        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_commute_data

            result = await client.get_commute("Home", "Office", "driving")

            mock_call.assert_called_once_with(
                "mobility.get_commute",
                {"origin": "Home", "destination": "Office", "mode": "driving"},
            )
            assert result == sample_commute_data

    @pytest.mark.asyncio
    async def test_get_all_morning_data_success(
        self, client, sample_weather_data, sample_calendar_data,
        sample_todos_data, sample_commute_options_data, mock_settings
    ):
        """Test get_all_morning_data fetches all data in parallel."""
        with patch.object(client, "get_weather", new_callable=AsyncMock) as mock_weather, \
             patch.object(client, "get_calendar_events", new_callable=AsyncMock) as mock_cal, \
             patch.object(client, "get_todos", new_callable=AsyncMock) as mock_todos, \
             patch.object(client, "get_commute_options", new_callable=AsyncMock) as mock_commute:

            mock_weather.return_value = sample_weather_data
            mock_cal.return_value = sample_calendar_data
            mock_todos.return_value = sample_todos_data
            mock_commute.return_value = sample_commute_options_data

            result = await client.get_all_morning_data("2025-01-15")

            assert result["weather"] == sample_weather_data
            assert result["calendar"] == sample_calendar_data
            assert result["todos"] == sample_todos_data
            assert result["commute"] == sample_commute_options_data

    @pytest.mark.asyncio
    async def test_get_all_morning_data_partial_failure(
        self, client, sample_weather_data, sample_calendar_data, mock_settings
    ):
        """Test get_all_morning_data handles partial failures gracefully."""
        with patch.object(client, "get_weather", new_callable=AsyncMock) as mock_weather, \
             patch.object(client, "get_calendar_events", new_callable=AsyncMock) as mock_cal, \
             patch.object(client, "get_todos", new_callable=AsyncMock) as mock_todos, \
             patch.object(client, "get_commute_options", new_callable=AsyncMock) as mock_commute:

            mock_weather.return_value = sample_weather_data
            mock_cal.return_value = sample_calendar_data
            mock_todos.side_effect = Exception("Todo service unavailable")
            mock_commute.side_effect = Exception("Commute service unavailable")

            result = await client.get_all_morning_data("2025-01-15")

            assert result["weather"] == sample_weather_data
            assert result["calendar"] == sample_calendar_data
            assert "error" in result["todos"]
            assert "error" in result["commute"]

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health_check returns True when server is healthy."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health_check returns False when server is unhealthy."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await client.health_check()
            assert result is False
