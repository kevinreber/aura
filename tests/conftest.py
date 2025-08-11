"""Pytest configuration and fixtures for the MCP server tests."""

import pytest
import asyncio
from unittest.mock import Mock
from datetime import date, datetime

from mcp_server.app import create_app
from mcp_server.config import Settings


@pytest.fixture
def app():
    """Create a Flask app configured for testing."""
    # Override settings for testing
    test_settings = Settings(
        environment="testing",
        debug=True,
        weather_api_key="test_weather_key",
        google_maps_api_key="test_maps_key",
        secret_key="test_secret_key"
    )
    
    # Mock the settings
    import mcp_server.config
    original_get_settings = mcp_server.config.get_settings
    mcp_server.config.get_settings = lambda: test_settings
    
    app = create_app()
    app.config['TESTING'] = True
    
    yield app
    
    # Restore original settings
    mcp_server.config.get_settings = original_get_settings


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask app."""
    return app.test_cli_runner()


@pytest.fixture
def sample_weather_input():
    """Sample weather tool input data."""
    return {
        "location": "San Francisco, CA",
        "when": "today"
    }


@pytest.fixture
def sample_mobility_input():
    """Sample mobility tool input data."""
    return {
        "origin": "San Francisco, CA",
        "destination": "Oakland, CA",
        "mode": "driving"
    }


@pytest.fixture
def sample_calendar_input():
    """Sample calendar tool input data."""
    return {
        "date": "2024-01-15"
    }


@pytest.fixture
def sample_todo_input():
    """Sample todo tool input data."""
    return {
        "bucket": "work",
        "include_completed": False
    }


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
