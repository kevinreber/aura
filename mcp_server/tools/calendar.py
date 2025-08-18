"""Calendar tool for listing daily events."""

import asyncio
from datetime import datetime, timedelta
import datetime as dt
from typing import Dict, Any, List
import random
import os

from ..schemas.calendar import CalendarInput, CalendarOutput, CalendarEvent, CalendarRangeInput, CalendarRangeOutput
from ..utils.logging import get_logger, log_tool_call
from ..config import get_settings
from ..clients.google_calendar import GoogleCalendarClient

logger = get_logger("calendar_tool")


class CalendarTool:
    """Tool for listing calendar events with Google Calendar integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.google_calendar_client = None
        self._initialize_google_calendar()
    
    def _initialize_google_calendar(self):
        """Initialize Google Calendar client if credentials are available."""
        if self.settings.google_calendar_credentials_path:
            if os.path.exists(self.settings.google_calendar_credentials_path):
                try:
                    self.google_calendar_client = GoogleCalendarClient(
                        self.settings.google_calendar_credentials_path
                    )
                    if self.google_calendar_client.test_connection():
                        logger.info("Google Calendar client initialized successfully")
                    else:
                        logger.warning("Google Calendar client failed connection test")
                        self.google_calendar_client = None
                except Exception as e:
                    logger.error(f"Error initializing Google Calendar client: {e}")
                    self.google_calendar_client = None
            else:
                logger.warning(f"Google Calendar credentials file not found: {self.settings.google_calendar_credentials_path}")
        else:
            logger.info("No Google Calendar credentials path configured")
    
    async def list_events(self, input_data: CalendarInput) -> CalendarOutput:
        """
        List calendar events for a specific date.
        
        Args:
            input_data: CalendarInput with date to query
            
        Returns:
            CalendarOutput with list of events for the date
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting calendar events for {input_data.date}")
            
            # For now, use mock data. In production, this would integrate with Google Calendar API
            events = await self._get_events_for_date(input_data.date)
            
            result = CalendarOutput(
                date=input_data.date,
                events=events,
                total_events=len(events)
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("calendar.list_events", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("calendar.list_events", input_data.dict(), duration_ms)
            logger.error(f"Error getting calendar events: {e}")
            raise
    
    async def list_events_range(self, input_data: "CalendarRangeInput") -> "CalendarRangeOutput":
        """
        Get calendar events for a date range (much more efficient than multiple single-date calls).
        
        Args:
            input_data: CalendarRangeInput with start_date and end_date
            
        Returns:
            CalendarRangeOutput with list of events for the entire range
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting calendar events from {input_data.start_date} to {input_data.end_date}")
            
            # Use the new range method from Google Calendar client
            events = await self._get_events_for_range(input_data.start_date, input_data.end_date)
            
            result = CalendarRangeOutput(
                start_date=input_data.start_date,
                end_date=input_data.end_date,
                events=events,
                total_events=len(events)
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("calendar.list_events_range", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("calendar.list_events_range", input_data.dict(), duration_ms)
            logger.error(f"Error getting calendar events for range: {e}")
            raise
    
    async def _get_events_for_date(self, query_date: dt.date) -> List[CalendarEvent]:
        """Get events for a specific date."""
        
        if self.google_calendar_client:
            try:
                logger.info(f"Fetching real Google Calendar events for {query_date}")
                events = await self.google_calendar_client.get_events_for_date(query_date)
                logger.info(f"Retrieved {len(events)} events from Google Calendar")
                return events
            except Exception as e:
                logger.error(f"Error fetching Google Calendar events, falling back to mock data: {e}")
                return await self._get_mock_events(query_date)
        else:
            logger.info("Google Calendar client not available, using mock data")
            return await self._get_mock_events(query_date)
    
    async def _get_events_for_range(self, start_date: dt.date, end_date: dt.date) -> List[CalendarEvent]:
        """Get events for a date range."""
        
        if self.google_calendar_client:
            try:
                logger.info(f"Fetching real Google Calendar events for range {start_date} to {end_date}")
                events = await self.google_calendar_client.get_events_for_range(start_date, end_date)
                logger.info(f"Retrieved {len(events)} events from Google Calendar for range")
                return events
            except Exception as e:
                logger.error(f"Error fetching Google Calendar events for range, falling back to mock data: {e}")
                return await self._get_mock_events_range(start_date, end_date)
        else:
            logger.info("Google Calendar client not available, using mock data for range")
            return await self._get_mock_events_range(start_date, end_date)
    
    async def _get_mock_events_range(self, start_date: dt.date, end_date: dt.date) -> List[CalendarEvent]:
        """Generate mock events for a date range."""
        all_events = []
        current_date = start_date
        
        while current_date <= end_date:
            day_events = await self._get_mock_events(current_date)
            all_events.extend(day_events)
            current_date += timedelta(days=1)
        
        # Sort by start time
        all_events.sort(key=lambda x: x.start_time)
        return all_events
    
    async def _get_mock_events(self, query_date: dt.date) -> List[CalendarEvent]:
        """Generate realistic mock calendar events for the given date."""
        
        # Generate different events based on day of week
        today = dt.date.today()
        weekday = query_date.weekday()  # 0=Monday, 6=Sunday
        
        events = []
        
        # Only generate events for dates close to today (within a week)
        if abs((query_date - today).days) > 7:
            return events
        
        # Generate events based on day type
        if weekday < 5:  # Weekday (Monday-Friday)
            events.extend(self._generate_workday_events(query_date))
        else:  # Weekend
            events.extend(self._generate_weekend_events(query_date))
        
        # Sort events by start time
        events.sort(key=lambda x: x.start_time)
        
        return events
    
    def _generate_workday_events(self, query_date: dt.date) -> List[CalendarEvent]:
        """Generate mock events for a workday."""
        events = []
        base_datetime = datetime.combine(query_date, datetime.min.time())
        
        # Morning standup (random chance)
        if random.random() < 0.7:  # 70% chance
            start_time = base_datetime.replace(hour=9, minute=random.choice([0, 15, 30]))
            events.append(CalendarEvent(
                id=f"event_{query_date}_standup",
                title="Daily Standup",
                start_time=start_time,
                end_time=start_time + timedelta(minutes=30),
                location="Conference Room A",
                description="Daily team sync and planning",
                all_day=False,
                attendees=["team@company.com"]
            ))
        
        # Mid-morning meeting (random chance)
        if random.random() < 0.5:  # 50% chance
            start_time = base_datetime.replace(hour=10, minute=random.choice([0, 30]))
            meeting_types = [
                ("Project Review", "Review project progress and blockers"),
                ("Client Call", "Weekly check-in with client stakeholders"),
                ("Design Review", "Review latest design mockups"),
                ("Planning Session", "Sprint planning and task breakdown")
            ]
            title, description = random.choice(meeting_types)
            
            events.append(CalendarEvent(
                id=f"event_{query_date}_meeting1",
                title=title,
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                location="Zoom",
                description=description,
                all_day=False,
                attendees=["colleague@company.com"]
            ))
        
        # Lunch (sometimes scheduled)
        if random.random() < 0.3:  # 30% chance
            start_time = base_datetime.replace(hour=12, minute=random.choice([0, 30]))
            events.append(CalendarEvent(
                id=f"event_{query_date}_lunch",
                title="Lunch Meeting",
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                location="Local Cafe",
                description="Casual lunch with colleague",
                all_day=False,
                attendees=["friend@company.com"]
            ))
        
        # Afternoon meeting (random chance)
        if random.random() < 0.6:  # 60% chance
            start_time = base_datetime.replace(hour=14, minute=random.choice([0, 30]))
            afternoon_meetings = [
                ("One-on-One", "Weekly 1:1 with manager"),
                ("All Hands", "Company all-hands meeting"),
                ("Workshop", "Technical workshop or training"),
                ("Demo", "Product demo and feedback session")
            ]
            title, description = random.choice(afternoon_meetings)
            
            events.append(CalendarEvent(
                id=f"event_{query_date}_meeting2",
                title=title,
                start_time=start_time,
                end_time=start_time + timedelta(minutes=45),
                location="Conference Room B",
                description=description,
                all_day=False,
                attendees=["manager@company.com"]
            ))
        
        return events
    
    def _generate_weekend_events(self, query_date: dt.date) -> List[CalendarEvent]:
        """Generate mock events for a weekend day."""
        events = []
        base_datetime = datetime.combine(query_date, datetime.min.time())
        
        # Weekend activities (lower chance, more personal)
        if random.random() < 0.4:  # 40% chance
            start_time = base_datetime.replace(hour=random.choice([10, 11, 14, 15]), minute=0)
            weekend_activities = [
                ("Grocery Shopping", "Weekly grocery run", "Whole Foods"),
                ("Workout", "Gym session or outdoor exercise", "Local Gym"),
                ("Coffee with Friends", "Catch up over coffee", "Downtown Cafe"),
                ("Family Dinner", "Sunday family dinner", "Parents' House"),
                ("Hiking", "Nature hike and fresh air", "Local Trail"),
                ("Movie", "Weekend movie night", "Cinema")
            ]
            title, description, location = random.choice(weekend_activities)
            
            duration = timedelta(hours=random.choice([1, 2, 3]))
            
            events.append(CalendarEvent(
                id=f"event_{query_date}_weekend",
                title=title,
                start_time=start_time,
                end_time=start_time + duration,
                location=location,
                description=description,
                all_day=False,
                attendees=None
            ))
        
        return events
