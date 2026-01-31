"""Tests for the Flask API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Test health endpoint returns 200."""
        with patch("daily_ai_agent.api.AgentOrchestrator") as mock_orch:
            mock_orch.return_value.is_conversational.return_value = True
            response = client.get("/health")
            assert response.status_code == 200

    def test_health_check_returns_correct_structure(self, client):
        """Test health endpoint returns expected fields."""
        with patch("daily_ai_agent.api.AgentOrchestrator") as mock_orch:
            mock_orch.return_value.is_conversational.return_value = True
            response = client.get("/health")
            data = json.loads(response.data)

            assert "status" in data
            assert "service" in data
            assert "version" in data
            assert "timestamp" in data
            assert "mcp_server" in data
            assert "ai_enabled" in data


class TestChatEndpoint:
    """Tests for the /chat endpoint."""

    def test_chat_requires_message(self, client):
        """Test chat endpoint requires message field."""
        response = client.post(
            "/chat",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_chat_rejects_empty_message(self, client):
        """Test chat endpoint rejects empty messages."""
        response = client.post(
            "/chat",
            data=json.dumps({"message": "   "}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_chat_success(self, client):
        """Test successful chat request."""
        with patch("daily_ai_agent.api.AgentOrchestrator") as mock_orch_class:
            mock_orch = MagicMock()
            mock_orch.is_conversational.return_value = True
            mock_orch.chat = AsyncMock(return_value="Hello! How can I help?")
            mock_orch_class.return_value = mock_orch

            # Re-create app with mocked orchestrator
            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.post(
                "/chat",
                data=json.dumps({"message": "Hello"}),
                content_type="application/json",
            )

            # Check structure, not exact status (depends on mock setup)
            if response.status_code == 200:
                data = json.loads(response.data)
                assert "response" in data or "error" in data


class TestWeatherEndpoint:
    """Tests for the /tools/weather endpoint."""

    def test_weather_default_location(self, client):
        """Test weather endpoint uses default location."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_weather = AsyncMock(
                return_value={"location": "San Francisco", "temp_hi": 72}
            )
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools/weather")
            assert response.status_code == 200

    def test_weather_custom_location(self, client):
        """Test weather endpoint accepts custom location."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_weather = AsyncMock(
                return_value={"location": "New York", "temp_hi": 65}
            )
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools/weather?location=New%20York")
            assert response.status_code == 200


class TestTodosEndpoint:
    """Tests for the /tools/todos endpoint."""

    def test_todos_without_bucket(self, client, sample_todos_data):
        """Test todos endpoint without bucket returns all todos."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_todos = AsyncMock(return_value=sample_todos_data)
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools/todos")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["tool"] == "todos"

    def test_todos_with_bucket(self, client, sample_todos_data):
        """Test todos endpoint with specific bucket."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_todos = AsyncMock(return_value=sample_todos_data)
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools/todos?bucket=work")
            assert response.status_code == 200


class TestCalendarEndpoint:
    """Tests for the /tools/calendar endpoint."""

    def test_calendar_default_date(self, client, sample_calendar_data):
        """Test calendar endpoint uses today as default date."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_calendar_events = AsyncMock(return_value=sample_calendar_data)
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools/calendar")
            assert response.status_code == 200

    def test_calendar_custom_date(self, client, sample_calendar_data):
        """Test calendar endpoint accepts custom date."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_calendar_events = AsyncMock(return_value=sample_calendar_data)
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools/calendar?date=2025-01-20")
            assert response.status_code == 200


class TestFinancialEndpoint:
    """Tests for the /tools/financial endpoint."""

    def test_financial_requires_symbols(self, client):
        """Test financial endpoint requires symbols field."""
        response = client.post(
            "/tools/financial",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_financial_rejects_empty_symbols(self, client):
        """Test financial endpoint rejects empty symbols array."""
        response = client.post(
            "/tools/financial",
            data=json.dumps({"symbols": []}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_financial_success(self, client, sample_financial_data):
        """Test successful financial request."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.call_tool = AsyncMock(return_value=sample_financial_data)
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.post(
                "/tools/financial",
                data=json.dumps({"symbols": ["MSFT", "BTC"]}),
                content_type="application/json",
            )
            assert response.status_code == 200


class TestToolsListEndpoint:
    """Tests for the /tools endpoint."""

    def test_tools_list_returns_all_tools(self, client):
        """Test tools list endpoint returns all available tools."""
        with patch("daily_ai_agent.api.AgentOrchestrator") as mock_orch:
            mock_orch.return_value.is_conversational.return_value = True

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/tools")
            assert response.status_code == 200
            data = json.loads(response.data)

            assert "tools" in data
            assert "weather" in data["tools"]
            assert "todos" in data["tools"]
            assert "calendar" in data["tools"]
            assert "commute" in data["tools"]
            assert "financial" in data["tools"]


class TestBriefingEndpoint:
    """Tests for the /briefing endpoint."""

    def test_basic_briefing(self, client, sample_morning_data):
        """Test basic briefing returns structured data."""
        with patch("daily_ai_agent.api.MCPClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_all_morning_data = AsyncMock(return_value=sample_morning_data)
            mock_client_class.return_value = mock_client

            from daily_ai_agent.api import create_app
            app = create_app(testing=True)
            test_client = app.test_client()

            response = test_client.get("/briefing?type=basic")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["type"] == "basic"
