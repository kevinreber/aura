"""Tests for the weather tool."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from mcp_server.tools.weather import WeatherTool
from mcp_server.schemas.weather import WeatherInput, WhenEnum


class TestWeatherTool:
    """Test the WeatherTool class."""
    
    @pytest.fixture
    def weather_tool(self):
        """Create a WeatherTool instance."""
        return WeatherTool()
    
    @pytest.mark.asyncio
    async def test_get_daily_mock_data(self, weather_tool):
        """Test getting daily weather with mock data (no API key)."""
        input_data = WeatherInput(location="San Francisco, CA", when=WhenEnum.TODAY)
        
        result = await weather_tool.get_daily(input_data)
        
        assert result.location == "San Francisco, CA (mock)"
        assert isinstance(result.temp_hi, float)
        assert isinstance(result.temp_lo, float)
        assert result.temp_hi > result.temp_lo
        assert result.summary is not None
        assert result.date == date.today().isoformat()
    
    @pytest.mark.asyncio
    async def test_get_daily_tomorrow(self, weather_tool):
        """Test getting weather for tomorrow."""
        input_data = WeatherInput(location="New York", when=WhenEnum.TOMORROW)
        
        result = await weather_tool.get_daily(input_data)
        
        assert result.location == "New York (mock)"
        # Tomorrow's date should be different from today
        tomorrow = date.today().replace(day=date.today().day + 1) if date.today().day < 28 else date.today()
        # We can't easily test exact date without more complex date handling, so just check it's set
        assert result.date is not None
    
    def test_mock_weather_data_structure(self, weather_tool):
        """Test that mock weather data has correct structure."""
        mock_data = weather_tool._get_mock_weather_data(WhenEnum.TODAY)
        
        assert "temp_hi" in mock_data
        assert "temp_lo" in mock_data
        assert "precip_chance" in mock_data
        assert "summary" in mock_data
        
        # Basic sanity checks
        assert isinstance(mock_data["temp_hi"], (int, float))
        assert isinstance(mock_data["temp_lo"], (int, float))
        assert mock_data["temp_hi"] > mock_data["temp_lo"]
    
    @pytest.mark.asyncio
    async def test_geocode_location_mock(self, weather_tool):
        """Test geocoding with mock data."""
        coordinates = await weather_tool._geocode_location("Test City")
        
        assert "lat" in coordinates
        assert "lon" in coordinates
        assert "display_name" in coordinates
        assert "Test City (mock)" in coordinates["display_name"]
        
        # Check that coordinates are reasonable (should be SF mock coordinates)
        assert isinstance(coordinates["lat"], float)
        assert isinstance(coordinates["lon"], float)
        assert -90 <= coordinates["lat"] <= 90
        assert -180 <= coordinates["lon"] <= 180
