"""Pydantic schemas for calendar tool validation."""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime, timezone
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


class CalendarUpdateInput(BaseModel):
    """Input schema for calendar.update_event tool."""
    event_id: str = Field(description="Google Calendar event ID to update")
    title: Optional[str] = Field(default=None, description="New event title/summary")
    start_time: Optional[datetime] = Field(default=None, description="New event start time")
    end_time: Optional[datetime] = Field(default=None, description="New event end time")
    description: Optional[str] = Field(default=None, description="New event description/notes")
    location: Optional[str] = Field(default=None, description="New event location")
    attendees: Optional[List[str]] = Field(default=None, description="New list of attendee email addresses")
    calendar_name: Optional[str] = Field(default="primary", description="Calendar to update event in (primary, work, personal, etc.)")
    all_day: Optional[bool] = Field(default=None, description="Whether this should be an all-day event")

    @field_validator('attendees')
    @classmethod
    def validate_attendees(cls, v):
        if v is not None:
            for email in v:
                if not email or '@' not in email:
                    raise ValueError(f"Invalid email address: {email}")
        return v

    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_times(cls, v):
        if v is not None and v.tzinfo is None:
            # Add UTC timezone if none specified
            v = v.replace(tzinfo=timezone.utc)
        return v

    @model_validator(mode='after')
    def validate_time_range(self):
        if self.start_time is not None and self.end_time is not None:
            if self.start_time >= self.end_time:
                raise ValueError("Start time must be before end time")
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "abc123def456",
                "title": "Updated Lunch Meeting",
                "start_time": "2024-01-15T13:00:00",
                "end_time": "2024-01-15T14:00:00",
                "location": "New Location",
                "description": "Updated description",
                "attendees": ["john@example.com", "sarah@example.com"],
                "calendar_name": "primary"
            }
        }


class CalendarUpdateOutput(BaseModel):
    """Output schema for calendar.update_event tool."""
    success: bool = Field(description="Whether the event was updated successfully")
    event_id: str = Field(description="Google Calendar event ID that was updated")
    event_url: Optional[str] = Field(description="URL to view the updated event in Google Calendar")
    updated_event: Optional[CalendarEvent] = Field(description="The updated event details")
    original_event: Optional[CalendarEvent] = Field(description="The original event details before update")
    changes_made: List[str] = Field(default_factory=list, description="List of changes that were made")
    message: str = Field(description="Success or error message")
    conflicts: Optional[List[CalendarEvent]] = Field(default=None, description="Any conflicting events found at the new time")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "abc123def456",
                "event_url": "https://calendar.google.com/calendar/event?eid=abc123def456",
                "updated_event": {
                    "id": "abc123def456",
                    "title": "Updated Lunch Meeting",
                    "start_time": "2024-01-15T13:00:00Z",
                    "end_time": "2024-01-15T14:00:00Z",
                    "location": "New Location",
                    "description": "Updated description",
                    "all_day": False,
                    "attendees": ["john@example.com", "sarah@example.com"],
                    "calendar_source": "primary"
                },
                "changes_made": ["title", "start_time", "end_time", "location", "attendees"],
                "message": "Event updated successfully from 12:00 PM to 1:00 PM with 2 changes",
                "conflicts": []
            }
        }


class CalendarDeleteInput(BaseModel):
    """Input schema for calendar.delete_event tool."""
    event_id: str = Field(description="Google Calendar event ID to delete")
    calendar_name: Optional[str] = Field(default="primary", description="Calendar to delete event from (primary, work, personal, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "abc123def456",
                "calendar_name": "primary"
            }
        }


class CalendarDeleteOutput(BaseModel):
    """Output schema for calendar.delete_event tool."""
    success: bool = Field(description="Whether the event was deleted successfully")
    event_id: str = Field(description="Google Calendar event ID that was deleted")
    deleted_event: Optional[CalendarEvent] = Field(description="The deleted event details")
    message: str = Field(description="Success or error message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "event_id": "abc123def456",
                "deleted_event": {
                    "id": "abc123def456",
                    "title": "Team Meeting",
                    "start_time": "2024-01-15T14:00:00Z",
                    "end_time": "2024-01-15T15:00:00Z",
                    "location": "Conference Room A",
                    "description": "Weekly team sync",
                    "all_day": False,
                    "attendees": ["john@example.com", "jane@example.com"],
                    "calendar_source": "primary"
                },
                "message": "Event 'Team Meeting' deleted successfully"
            }
        }


class CalendarFindFreeTimeInput(BaseModel):
    """Input schema for calendar.find_free_time tool."""
    duration_minutes: int = Field(description="Duration needed in minutes (e.g., 30, 60, 120)")
    start_date: str = Field(description="Start date to search from (YYYY-MM-DD format)")
    end_date: Optional[str] = Field(default=None, description="End date to search until (YYYY-MM-DD format, defaults to start_date)")
    earliest_time: Optional[str] = Field(default="09:00", description="Earliest time to consider (HH:MM format, 24-hour)")
    latest_time: Optional[str] = Field(default="18:00", description="Latest time to consider (HH:MM format, 24-hour)")
    calendar_names: Optional[List[str]] = Field(default=None, description="Calendars to check for conflicts (defaults to all)")
    max_results: Optional[int] = Field(default=5, description="Maximum number of time slots to return")
    preferred_time: Optional[str] = Field(default=None, description="Preferred time preference: 'morning', 'afternoon', 'evening'")

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError('duration_minutes must be positive')
        if v > 480:  # 8 hours
            raise ValueError('duration_minutes cannot exceed 480 (8 hours)')
        return v

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @field_validator('earliest_time', 'latest_time')
    @classmethod
    def validate_time_format(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format (24-hour)')

    class Config:
        json_schema_extra = {
            "example": {
                "duration_minutes": 60,
                "start_date": "2024-01-15",
                "end_date": "2024-01-19", 
                "earliest_time": "09:00",
                "latest_time": "17:00",
                "calendar_names": ["primary", "work"],
                "max_results": 3,
                "preferred_time": "afternoon"
            }
        }


class FreeTimeSlot(BaseModel):
    """Schema for a single free time slot."""
    start_time: datetime = Field(description="Start time of the free slot")
    end_time: datetime = Field(description="End time of the free slot") 
    duration_minutes: int = Field(description="Duration of the slot in minutes")
    date: str = Field(description="Date of the slot (YYYY-MM-DD)")
    day_of_week: str = Field(description="Day of week (Monday, Tuesday, etc.)")
    time_period: str = Field(description="Time period (morning, afternoon, evening)")
    conflicts_before: Optional[CalendarEvent] = Field(default=None, description="Event immediately before this slot")
    conflicts_after: Optional[CalendarEvent] = Field(default=None, description="Event immediately after this slot")
    preference_score: float = Field(description="Score based on preferences (0-1, higher is better)")


class CalendarFindFreeTimeOutput(BaseModel):
    """Output schema for calendar.find_free_time tool."""
    success: bool = Field(description="Whether free time slots were found")
    free_slots: List[FreeTimeSlot] = Field(description="Available time slots matching criteria")
    total_slots_found: int = Field(description="Total number of slots found")
    search_criteria: dict = Field(description="Summary of search parameters used")
    message: str = Field(description="Summary message about the search results")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "free_slots": [
                    {
                        "start_time": "2024-01-15T14:00:00Z",
                        "end_time": "2024-01-15T15:00:00Z",
                        "duration_minutes": 60,
                        "date": "2024-01-15",
                        "day_of_week": "Monday",
                        "time_period": "afternoon",
                        "conflicts_before": {
                            "title": "Team Standup",
                            "end_time": "2024-01-15T13:30:00Z"
                        },
                        "conflicts_after": {
                            "title": "Client Call",
                            "start_time": "2024-01-15T15:30:00Z"
                        },
                        "preference_score": 0.9
                    }
                ],
                "total_slots_found": 3,
                "search_criteria": {
                    "duration": "60 minutes",
                    "date_range": "2024-01-15 to 2024-01-19",
                    "time_window": "09:00 to 17:00",
                    "preference": "afternoon"
                },
                "message": "Found 3 available time slots matching your criteria. Top result: Monday 2:00 PM (60 minutes)"
            }
        }
