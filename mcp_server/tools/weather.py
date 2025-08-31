"""Weather tool for getting daily weather forecasts."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from ..schemas.weather import WeatherInput, WeatherOutput, WhenEnum
from ..utils.http_client import HTTPClient
from ..utils.logging import get_logger, log_tool_call
from ..utils.cache import get_cache_service, cached, CacheTTL, generate_cache_key
from ..config import get_settings

logger = get_logger("weather_tool")


class WeatherTool:
    """Tool for getting daily weather forecasts using OpenWeatherMap API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "http://api.openweathermap.org/data/2.5"
    
    async def get_daily(self, input_data: WeatherInput) -> WeatherOutput:
        """
        Get daily weather forecast for a location.
        
        Args:
            input_data: WeatherInput with location and when parameters
            
        Returns:
            WeatherOutput with weather forecast data
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting weather for {input_data.location} ({input_data.when})")
            
            # First, get coordinates for the location
            coordinates = await self._geocode_location(input_data.location)
            
            # Then get weather forecast
            weather_data = await self._get_weather_forecast(
                coordinates["lat"], 
                coordinates["lon"],
                input_data.when
            )
            
            # Parse and format the weather data
            result = await self._format_weather_response(
                weather_data, 
                coordinates["display_name"],
                input_data.when
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("weather.get_daily", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("weather.get_daily", input_data.dict(), duration_ms)
            logger.error(f"Error getting weather data: {e}")
            raise
    
    async def _geocode_location(self, location: str) -> Dict[str, Any]:
        """Convert location string to coordinates using OpenWeatherMap Geocoding API with caching."""
        cache = await get_cache_service()
        cache_key = generate_cache_key("weather_geocoding", location.lower())
        
        # Check cache first (coordinates don't change)
        cached_coords = await cache.get(cache_key)
        if cached_coords:
            logger.debug(f"Using cached coordinates for {location}")
            return cached_coords
        
        if not self.settings.weather_api_key:
            # Return mock coordinates for development
            logger.warning("No weather API key configured, using mock coordinates")
            coordinates = {
                "lat": 37.7749,
                "lon": -122.4194,
                "display_name": f"{location} (mock)"
            }
        else:
            url = f"http://api.openweathermap.org/geo/1.0/direct"
            params = {
                "q": location,
                "limit": 1,
                "appid": self.settings.weather_api_key
            }
            
            async with HTTPClient() as client:
                response = await client.get(url, params=params)
                data = response.json()
                
                if not data:
                    raise ValueError(f"Location '{location}' not found")
                
                location_data = data[0]
                coordinates = {
                    "lat": location_data["lat"],
                    "lon": location_data["lon"],
                    "display_name": f"{location_data.get('name', location)}, {location_data.get('country', '')}"
                }
        
        # Cache coordinates (they don't change, so long TTL)
        await cache.set(cache_key, coordinates, CacheTTL.WEATHER_GEOCODING)
        logger.debug(f"Cached coordinates for {location}")
        
        return coordinates
    
    async def _get_weather_forecast(self, lat: float, lon: float, when: WhenEnum) -> Dict[str, Any]:
        """Get weather forecast from OpenWeatherMap API with caching."""
        cache = await get_cache_service()
        
        # Create cache key based on location and date (not exact time since forecast covers periods)
        today = datetime.now().date()
        target_date = today if when == WhenEnum.TODAY else today + timedelta(days=1)
        cache_key = generate_cache_key("weather_forecast", f"{lat:.4f}_{lon:.4f}", target_date.isoformat())
        
        # Check cache first
        cached_forecast = await cache.get(cache_key)
        if cached_forecast:
            logger.debug(f"Using cached weather forecast for {lat:.4f}, {lon:.4f} on {target_date}")
            return cached_forecast
        
        if not self.settings.weather_api_key:
            # Return mock weather data for development
            logger.warning("No weather API key configured, returning mock data")
            forecast_data = self._get_mock_weather_data(when)
        else:
            url = f"{self.base_url}/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.settings.weather_api_key,
                "units": "imperial"  # Fahrenheit
            }
            
            async with HTTPClient() as client:
                response = await client.get(url, params=params)
                forecast_data = response.json()
        
        # Cache the forecast data
        await cache.set(cache_key, forecast_data, CacheTTL.WEATHER_FORECAST)
        logger.debug(f"Cached weather forecast for {lat:.4f}, {lon:.4f} on {target_date}")
        
        return forecast_data
    
    async def _format_weather_response(
        self, 
        weather_data: Dict[str, Any], 
        location_name: str,
        when: WhenEnum
    ) -> WeatherOutput:
        """Format OpenWeatherMap response into our schema."""
        
        # Determine target date
        today = datetime.now().date()
        target_date = today if when == WhenEnum.TODAY else today + timedelta(days=1)
        
        # For mock data or simple current weather, use simplified logic
        if "list" not in weather_data:
            return WeatherOutput(
                temp_hi=weather_data.get("temp_hi", 72.0),
                temp_lo=weather_data.get("temp_lo", 58.0),
                current_temp=weather_data.get("current_temp", 65.0),
                condition=weather_data.get("condition", "Partly Cloudy"),
                precip_chance=weather_data.get("precip_chance", 20.0),
                summary=weather_data.get("summary", "Partly cloudy"),
                location=location_name,
                date=target_date.isoformat()
            )
        
        # Find forecasts for the target date
        target_forecasts = []
        for forecast in weather_data["list"]:
            forecast_date = datetime.fromtimestamp(forecast["dt"]).date()
            if forecast_date == target_date:
                target_forecasts.append(forecast)
        
        if not target_forecasts:
            logger.warning(f"No weather forecast data available for {target_date}, using fallback")
            return self._get_fallback_weather_response(location_name, when)
        
        # Calculate daily high/low from all forecasts for the day
        temps = [f["main"]["temp"] for f in target_forecasts]
        temp_hi = max(temps)
        temp_lo = min(temps)
        
        # Get precipitation chance (use highest from the day)
        precip_chances = [f.get("pop", 0) * 100 for f in target_forecasts]
        precip_chance = max(precip_chances) if precip_chances else None
        
        # Get weather summary from the midday forecast
        midday_forecast = target_forecasts[len(target_forecasts) // 2]
        summary = midday_forecast["weather"][0]["description"].title()
        
        return WeatherOutput(
            temp_hi=round(temp_hi, 1),
            temp_lo=round(temp_lo, 1),
            current_temp=round(midday_forecast["main"]["temp"], 1),
            condition=summary,
            precip_chance=round(precip_chance, 1) if precip_chance else None,
            summary=summary,
            location=location_name,
            date=target_date.isoformat()
        )
    
    def _get_fallback_weather_response(self, location_name: str, when: WhenEnum) -> WeatherOutput:
        """Generate a fallback weather response when API data is unavailable."""
        today = datetime.now().date()
        target_date = today if when == WhenEnum.TODAY else today + timedelta(days=1)
        
        # Provide reasonable default weather data
        return WeatherOutput(
            temp_hi=72.0,
            temp_lo=58.0,
            current_temp=65.0,
            condition="Partly Cloudy",
            precip_chance=20.0,
            summary="Weather data temporarily unavailable",
            location=location_name,
            date=target_date.isoformat()
        )
    
    def _get_mock_weather_data(self, when: WhenEnum) -> Dict[str, Any]:
        """Return mock weather data for development/testing."""
        base_temp = 70 if when == WhenEnum.TODAY else 68
        return {
            "temp_hi": base_temp + 5,
            "temp_lo": base_temp - 10,
            "current_temp": base_temp,
            "condition": "Partly Cloudy",
            "precip_chance": 25.0,
            "summary": "Partly cloudy with light winds"
        }
