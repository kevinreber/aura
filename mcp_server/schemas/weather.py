"""Pydantic schemas for weather tool validation."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class WhenEnum(str, Enum):
    """Valid time options for weather queries."""
    TODAY = "today"
    TOMORROW = "tomorrow"


class WeatherInput(BaseModel):
    """Input schema for weather.get_daily tool."""
    
    location: str = Field(
        description="Location name (city, state/country) or coordinates",
        examples=["San Francisco, CA", "New York", "40.7128,-74.0060"]
    )
    when: WhenEnum = Field(
        default=WhenEnum.TODAY,
        description="Whether to get weather for today or tomorrow"
    )


class WeatherOutput(BaseModel):
    """Output schema for weather.get_daily tool."""
    
    temp_hi: float = Field(description="High temperature in Fahrenheit")
    temp_lo: float = Field(description="Low temperature in Fahrenheit")
    precip_chance: Optional[float] = Field(
        default=None,
        description="Precipitation chance as percentage (0-100)"
    )
    summary: str = Field(description="Brief weather summary")
    location: str = Field(description="Resolved location name")
    date: str = Field(description="Date for the forecast (YYYY-MM-DD)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "temp_hi": 72.5,
                "temp_lo": 58.2,
                "precip_chance": 20.0,
                "summary": "Partly cloudy with light winds",
                "location": "San Francisco, CA",
                "date": "2024-01-15"
            }
        }
