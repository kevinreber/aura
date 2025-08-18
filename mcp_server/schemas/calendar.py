"""Pydantic schemas for calendar tool validation."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import datetime as dt  # Import module to avoid name clash


class CalendarInput(BaseModel):
    """Input schema for calendar.list_events tool."""
    
    date: dt.date = Field(
        description="Date to list events for (YYYY-MM-DD format)",
        examples=["2024-01-15"]
    )


class CalendarRangeInput(BaseModel):
    """Input schema for calendar.list_events_range tool."""
    
    start_date: dt.date = Field(
        description="Start date of the range (YYYY-MM-DD format, inclusive)",
        examples=["2024-01-15"]
    )
    end_date: dt.date = Field(
        description="End date of the range (YYYY-MM-DD format, inclusive)",
        examples=["2024-01-21"]
    )


class CalendarEvent(BaseModel):
    """Schema for a single calendar event."""
    
    id: str = Field(description="Unique event identifier")
    title: str = Field(description="Event title/summary")
    start_time: datetime = Field(description="Event start time (ISO format)")
    end_time: datetime = Field(description="Event end time (ISO format)")
    location: Optional[str] = Field(default=None, description="Event location")
    description: Optional[str] = Field(default=None, description="Event description")
    all_day: bool = Field(default=False, description="Whether this is an all-day event")
    attendees: Optional[List[str]] = Field(default=None, description="List of attendee emails")
    calendar_source: Optional[str] = Field(default=None, description="Source calendar name (e.g., 'Work', 'Runna', 'primary')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "event_123",
                "title": "Team Meeting",
                "start_time": "2024-01-15T10:00:00Z",
                "end_time": "2024-01-15T11:00:00Z",
                "location": "Conference Room A",
                "description": "Weekly team sync",
                "all_day": False,
                "attendees": ["alice@example.com", "bob@example.com"],
                "calendar_source": "Work"
            }
        }


class CalendarOutput(BaseModel):
    """Output schema for calendar.list_events tool."""
    
    date: dt.date = Field(description="Date queried for events")
    events: List[CalendarEvent] = Field(description="List of events for the date")
    total_events: int = Field(description="Total number of events found")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-01-15",
                "events": [
                    {
                        "id": "event_123",
                        "title": "Team Meeting", 
                        "start_time": "2024-01-15T10:00:00Z",
                        "end_time": "2024-01-15T11:00:00Z",
                        "location": "Conference Room A",
                        "description": "Weekly team sync",
                        "all_day": False,
                        "attendees": ["alice@example.com"]
                    }
                ],
                "total_events": 1
            }
        }


class CalendarRangeOutput(BaseModel):
    """Output schema for calendar.list_events_range tool."""
    
    start_date: dt.date = Field(description="Start date of the queried range")
    end_date: dt.date = Field(description="End date of the queried range")
    events: List[CalendarEvent] = Field(description="List of events in the date range")
    total_events: int = Field(description="Total number of events found in the range")
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2024-01-15",
                "end_date": "2024-01-21", 
                "events": [
                    {
                        "id": "event_123",
                        "title": "Team Meeting", 
                        "start_time": "2024-01-15T10:00:00Z",
                        "end_time": "2024-01-15T11:00:00Z",
                        "location": "Conference Room A",
                        "description": "Weekly team sync",
                        "all_day": False,
                        "attendees": ["alice@example.com"]
                    }
                ],
                "total_events": 1
            }
        }
