"""Pytest configuration and shared fixtures for the Daily AI Agent tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Generator
import os

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["OPENAI_API_KEY"] = "test-api-key"
os.environ["MCP_SERVER_URL"] = "http://test-mcp-server:8000"


@pytest.fixture
def mock_settings() -> Generator[MagicMock, None, None]:
    """Provide mock settings for tests."""
    with patch("daily_ai_agent.models.config.get_settings") as mock:
        settings = MagicMock()
        settings.openai_api_key = "test-api-key"
        settings.anthropic_api_key = None
        settings.default_llm = "openai"
        settings.mcp_server_url = "http://test-mcp-server:8000"
        settings.mcp_server_timeout = 30
        settings.log_level = "INFO"
        settings.enable_memory = True
        settings.debug = True
        settings.environment = "testing"
        settings.host = "0.0.0.0"
        settings.port = 8001
        settings.allowed_origins = ["http://localhost:3000"]
        settings.rate_limit_per_minute = 60
        settings.user_name = "Test User"
        settings.user_location = "San Francisco"
        settings.default_commute_origin = "Home"
        settings.default_commute_destination = "Office"
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_mcp_client() -> Generator[AsyncMock, None, None]:
    """Provide a mock MCP client for tests."""
    with patch("daily_ai_agent.services.mcp_client.MCPClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_weather_data() -> Dict[str, Any]:
    """Sample weather data for testing."""
    return {
        "location": "San Francisco, US",
        "temp_hi": 72.5,
        "temp_lo": 58.3,
        "summary": "Partly Cloudy",
        "precip_chance": 10,
        "humidity": 65,
        "wind_speed": 12,
        "date": "2025-01-15",
    }


@pytest.fixture
def sample_calendar_data() -> Dict[str, Any]:
    """Sample calendar data for testing."""
    return {
        "events": [
            {
                "id": "event1",
                "title": "Team Standup",
                "time": "09:00 AM",
                "start_time": "2025-01-15T09:00:00",
                "end_time": "2025-01-15T09:30:00",
                "location": "Conference Room A",
            },
            {
                "id": "event2",
                "title": "Lunch with John",
                "time": "12:00 PM",
                "start_time": "2025-01-15T12:00:00",
                "end_time": "2025-01-15T13:00:00",
                "location": "Cafe",
            },
        ],
        "total_events": 2,
        "date": "2025-01-15",
    }


@pytest.fixture
def sample_todos_data() -> Dict[str, Any]:
    """Sample todos data for testing."""
    return {
        "items": [
            {
                "id": "todo1",
                "title": "Review quarterly reports",
                "priority": "high",
                "due_date": "2025-01-16",
                "bucket": "work",
            },
            {
                "id": "todo2",
                "title": "Code review for PR #123",
                "priority": "medium",
                "due_date": "2025-01-15",
                "bucket": "work",
            },
            {
                "id": "todo3",
                "title": "Buy groceries",
                "priority": "low",
                "due_date": "2025-01-17",
                "bucket": "home",
            },
        ],
        "pending_count": 3,
        "bucket": "all",
    }


@pytest.fixture
def sample_commute_data() -> Dict[str, Any]:
    """Sample commute data for testing."""
    return {
        "origin": "Home",
        "destination": "Office",
        "mode": "driving",
        "duration_minutes": 35,
        "distance_miles": 15.2,
        "traffic_status": "moderate",
        "route_summary": "Via US-101 N",
    }


@pytest.fixture
def sample_commute_options_data() -> Dict[str, Any]:
    """Sample comprehensive commute options data for testing."""
    return {
        "direction": "to_work",
        "recommendation": "Take transit today - traffic is heavy",
        "driving": {
            "duration_minutes": 45,
            "route_summary": "Via US-101 N",
            "traffic_status": "heavy",
            "departure_time": "8:00 AM",
            "arrival_time": "8:45 AM",
        },
        "transit": {
            "total_duration_minutes": 55,
            "caltrain_duration_minutes": 35,
            "shuttle_duration_minutes": 10,
            "next_departures": [
                {
                    "departure_time": "8:15 AM",
                    "arrival_time": "9:10 AM",
                    "train_number": "207",
                },
            ],
        },
    }


@pytest.fixture
def sample_financial_data() -> Dict[str, Any]:
    """Sample financial data for testing."""
    return {
        "summary": "3 instruments tracked | 2 gaining | 1 declining",
        "total_items": 3,
        "market_status": "mixed",
        "data": [
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "price": 425.50,
                "change": 2.30,
                "change_percent": 0.54,
                "currency": "USD",
                "data_type": "stocks",
            },
            {
                "symbol": "BTC",
                "name": "Bitcoin",
                "price": 98500.00,
                "change": 1250.00,
                "change_percent": 1.29,
                "currency": "USD",
                "data_type": "crypto",
            },
        ],
    }


@pytest.fixture
def sample_morning_data(
    sample_weather_data: Dict[str, Any],
    sample_calendar_data: Dict[str, Any],
    sample_todos_data: Dict[str, Any],
    sample_commute_options_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Combined morning data for testing."""
    return {
        "weather": sample_weather_data,
        "calendar": sample_calendar_data,
        "todos": sample_todos_data,
        "commute": sample_commute_options_data,
    }


@pytest.fixture
def app():
    """Create Flask test app."""
    # Import here to ensure test environment is set
    from daily_ai_agent.api import create_app

    app = create_app(testing=True)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create Flask CLI test runner."""
    return app.test_cli_runner()
