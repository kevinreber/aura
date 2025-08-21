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


class CalendarCreateInput(BaseModel):
    """Input schema for calendar.create_event tool."""
    
    title: str = Field(
        description="Event title/summary",
        examples=["Lunch with John", "Team Meeting", "Doctor Appointment"]
    )
    start_time: datetime = Field(
        description="Event start time (ISO format)",
        examples=["2024-01-15T12:00:00"]
    )
    end_time: datetime = Field(
        description="Event end time (ISO format)",
        examples=["2024-01-15T13:00:00"]
    )
    description: Optional[str] = Field(
        default=None,
        description="Event description/notes",
        examples=["Weekly team sync to discuss project progress"]
    )
    location: Optional[str] = Field(
        default=None,
        description="Event location",
        examples=["Conference Room A", "Downtown Cafe", "Zoom"]
    )
    attendees: Optional[List[str]] = Field(
        default=None,
        description="List of attendee email addresses",
        examples=[["john@example.com", "jane@example.com"]]
    )
    calendar_name: Optional[str] = Field(
        default="primary",
        description="Target calendar name (defaults to primary calendar)",
        examples=["primary", "Work", "Personal"]
    )
    all_day: bool = Field(
        default=False,
        description="Whether this is an all-day event"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Lunch with John",
                "start_time": "2024-01-15T12:00:00",
                "end_time": "2024-01-15T13:00:00",
                "description": "Catching up over lunch",
                "location": "Downtown Cafe",
                "attendees": ["john@example.com"],
                "calendar_name": "primary",
                "all_day": False
            }
        }


class CalendarCreateOutput(BaseModel):
    """Output schema for calendar.create_event tool."""
    
    success: bool = Field(description="Whether the event was created successfully")
    event_id: Optional[str] = Field(description="Google Calendar event ID if created")
    event_url: Optional[str] = Field(description="URL to view the event in Google Calendar")
    created_event: Optional[CalendarEvent] = Field(description="The created event details")
    message: str = Field(description="Success or error message")
    conflicts: Optional[List[CalendarEvent]] = Field(
        default=None,
        description="Any conflicting events found at the same time"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "abc123def456",
                "event_url": "https://calendar.google.com/calendar/event?eid=abc123def456",
                "created_event": {
                    "id": "abc123def456",
                    "title": "Lunch with John",
                    "start_time": "2024-01-15T12:00:00Z",
                    "end_time": "2024-01-15T13:00:00Z",
                    "location": "Downtown Cafe",
                    "description": "Catching up over lunch",
                    "all_day": False,
                    "attendees": ["john@example.com"],
                    "calendar_source": "primary"
                },
                "message": "Event 'Lunch with John' created successfully for January 15, 2024 at 12:00 PM",
                "conflicts": []
            }
        }
