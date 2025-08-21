"""Calendar tool for listing daily events."""

import asyncio
from datetime import datetime, timedelta
import datetime as dt
from typing import Dict, Any, List
import random
import os

from ..schemas.calendar import (
    CalendarInput, CalendarOutput, CalendarEvent, CalendarRangeInput, CalendarRangeOutput,
    CalendarCreateInput, CalendarCreateOutput, CalendarUpdateInput, CalendarUpdateOutput,
    CalendarDeleteInput, CalendarDeleteOutput
)
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
        try:
            # Try production mode first (env var credentials)
            if self.settings.google_calendar_credentials_json:
                logger.info("Initializing Google Calendar client with environment credentials")
                self.google_calendar_client = GoogleCalendarClient(
                    credentials_json=self.settings.google_calendar_credentials_json
                )
            # Fall back to development mode (file credentials)
            elif self.settings.google_calendar_credentials_path:
                if os.path.exists(self.settings.google_calendar_credentials_path):
                    logger.info("Initializing Google Calendar client with file credentials")
                    self.google_calendar_client = GoogleCalendarClient(
                        credentials_path=self.settings.google_calendar_credentials_path
                    )
                else:
                    logger.warning(f"Google Calendar credentials file not found: {self.settings.google_calendar_credentials_path}")
                    return
            else:
                logger.info("Google Calendar credentials not configured (neither env var nor file)")
                return
            
            # Test the connection
            if self.google_calendar_client and self.google_calendar_client.test_connection():
                logger.info("Google Calendar client initialized successfully")
            else:
                logger.warning("Google Calendar client failed connection test")
                self.google_calendar_client = None
                
        except Exception as e:
            logger.error(f"Error initializing Google Calendar client: {e}")
            self.google_calendar_client = None
    
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
        """Get events for a specific date from multiple calendars (primary, Runna, Family)."""
        
        if self.google_calendar_client:
            try:
                logger.info(f"Fetching real Google Calendar events for {query_date} from multiple calendars")
                # Use the multi-calendar method for consistency, with same start/end date
                events = await self.google_calendar_client.get_events_for_multiple_calendars(query_date, query_date)
                logger.info(f"Retrieved {len(events)} events from Google Calendar across all calendars")
                return events
            except Exception as e:
                logger.error(f"Error fetching Google Calendar events, falling back to mock data: {e}")
                return await self._get_mock_events(query_date)
        else:
            logger.info("Google Calendar client not available, using mock data")
            return await self._get_mock_events(query_date)
    
    async def _get_events_for_range(self, start_date: dt.date, end_date: dt.date) -> List[CalendarEvent]:
        """Get events for a date range from multiple calendars (primary, Runna, Family)."""
        
        if self.google_calendar_client:
            try:
                logger.info(f"Fetching real Google Calendar events for range {start_date} to {end_date} from multiple calendars")
                # Fetch from primary + Runna + Family calendars by default
                events = await self.google_calendar_client.get_events_for_multiple_calendars(start_date, end_date)
                logger.info(f"Retrieved {len(events)} events from Google Calendar for range across all calendars")
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
                attendees=["team@company.com"],
                calendar_source="Work"
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
                attendees=["colleague@company.com"],
                calendar_source="Work"
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
                attendees=["friend@company.com"],
                calendar_source="primary"
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
                attendees=["manager@company.com"],
                calendar_source="Work"
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
                attendees=None,
                calendar_source="Runna" if "Run" in title or "Workout" in title else "primary"
            ))
        
        return events
    
    async def create_event(self, input_data: CalendarCreateInput) -> CalendarCreateOutput:
        """
        Create a new calendar event with conflict detection.
        
        Args:
            input_data: CalendarCreateInput with event details
            
        Returns:
            CalendarCreateOutput with creation result and any conflicts
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Creating calendar event: {input_data.title}")
            
            # Check for conflicts first
            conflicts = await self._detect_conflicts(input_data.start_time, input_data.end_time, input_data.calendar_name)
            
            # Determine target calendar ID
            calendar_id = await self._resolve_calendar_id(input_data.calendar_name)
            
            if self.google_calendar_client:
                # Create the event using Google Calendar API
                result = await self.google_calendar_client.create_event(
                    title=input_data.title,
                    start_time=input_data.start_time,
                    end_time=input_data.end_time,
                    description=input_data.description,
                    location=input_data.location,
                    attendees=input_data.attendees,
                    calendar_id=calendar_id,
                    all_day=input_data.all_day
                )
                
                if result['success']:
                    # Convert the created event to our schema
                    created_event = self._convert_google_event_from_api(
                        result['created_event'], 
                        input_data.calendar_name or "primary"
                    )
                    
                    # Format success message
                    event_date = input_data.start_time.strftime("%A, %B %d, %Y")
                    event_time = input_data.start_time.strftime("%I:%M %p") if not input_data.all_day else "all day"
                    message = f"Event '{input_data.title}' created successfully for {event_date}"
                    if not input_data.all_day:
                        message += f" at {event_time}"
                    
                    if conflicts:
                        message += f" (Warning: {len(conflicts)} conflicting event(s) detected)"
                    
                    output = CalendarCreateOutput(
                        success=True,
                        event_id=result['event_id'],
                        event_url=result['event_url'],
                        created_event=created_event,
                        message=message,
                        conflicts=conflicts if conflicts else None
                    )
                else:
                    # Handle API creation failure
                    output = CalendarCreateOutput(
                        success=False,
                        event_id=None,
                        event_url=None,
                        created_event=None,
                        message=f"Failed to create event: {result['error']}",
                        conflicts=conflicts if conflicts else None
                    )
            else:
                # Google Calendar client not available - return mock success for testing
                logger.warning("Google Calendar client not available, returning mock success")
                
                mock_event_id = f"mock_{input_data.title.lower().replace(' ', '_')}_{int(input_data.start_time.timestamp())}"
                mock_event = CalendarEvent(
                    id=mock_event_id,
                    title=input_data.title,
                    start_time=input_data.start_time,
                    end_time=input_data.end_time,
                    location=input_data.location,
                    description=input_data.description,
                    all_day=input_data.all_day,
                    attendees=input_data.attendees,
                    calendar_source=input_data.calendar_name or "primary"
                )
                
                output = CalendarCreateOutput(
                    success=True,
                    event_id=mock_event_id,
                    event_url=f"https://calendar.google.com/calendar/event?eid={mock_event_id}",
                    created_event=mock_event,
                    message=f"Event '{input_data.title}' would be created (Google Calendar not configured)",
                    conflicts=conflicts if conflicts else None
                )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("calendar.create_event", input_data.dict(), duration_ms)
            
            return output
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("calendar.create_event", input_data.dict(), duration_ms)
            logger.error(f"Error creating calendar event: {e}")
            
            return CalendarCreateOutput(
                success=False,
                event_id=None,
                event_url=None,
                created_event=None,
                message=f"Error creating event: {str(e)}",
                conflicts=None
            )

    async def update_event(self, input_data: CalendarUpdateInput) -> CalendarUpdateOutput:
        """
        Update an existing calendar event with conflict detection.
        
        Args:
            input_data: CalendarUpdateInput with update details
            
        Returns:
            CalendarUpdateOutput with update result and any conflicts
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Updating calendar event: {input_data.event_id}")
            
            # Check for conflicts if time is being changed
            conflicts = []
            if input_data.start_time is not None and input_data.end_time is not None:
                conflicts = await self._detect_conflicts(
                    input_data.start_time, 
                    input_data.end_time, 
                    input_data.calendar_name,
                    exclude_event_id=input_data.event_id
                )
            
            # Determine target calendar ID
            calendar_id = await self._resolve_calendar_id(input_data.calendar_name)
            
            if self.google_calendar_client:
                # Update the event using Google Calendar API
                result = await self.google_calendar_client.update_event(
                    event_id=input_data.event_id,
                    title=input_data.title,
                    start_time=input_data.start_time,
                    end_time=input_data.end_time,
                    description=input_data.description,
                    location=input_data.location,
                    attendees=input_data.attendees,
                    calendar_id=calendar_id,
                    all_day=input_data.all_day
                )
                
                if result['success']:
                    # Convert the events to our schema
                    original_event = None
                    updated_event = None
                    
                    if result.get('original_event'):
                        original_event = self._convert_google_event_from_api(
                            result['original_event'], 
                            input_data.calendar_name or "primary"
                        )
                    
                    if result.get('updated_event'):
                        updated_event = self._convert_google_event_from_api(
                            result['updated_event'], 
                            input_data.calendar_name or "primary"
                        )
                    
                    # Format success message
                    changes_made = result.get('changes_made', [])
                    message = result.get('message', 'Event updated successfully')
                    
                    if conflicts:
                        message += f" (Warning: {len(conflicts)} conflicting event(s) detected)"

                    logger.info(f"Event updated successfully in {asyncio.get_event_loop().time() - start_time:.2f}s")
                    
                    return CalendarUpdateOutput(
                        success=True,
                        event_id=result['event_id'],
                        event_url=result['event_url'],
                        updated_event=updated_event,
                        original_event=original_event,
                        changes_made=changes_made,
                        message=message,
                        conflicts=conflicts
                    )
                else:
                    # Google Calendar API call failed
                    error_msg = result.get('error', 'Unknown error updating event')
                    logger.error(f"Google Calendar update failed: {error_msg}")
                    
                    return CalendarUpdateOutput(
                        success=False,
                        event_id=input_data.event_id,
                        event_url=None,
                        updated_event=None,
                        original_event=None,
                        changes_made=[],
                        message=error_msg,
                        conflicts=conflicts
                    )
            else:
                # Mock success when Google Calendar is not available
                logger.info("Google Calendar not available, returning mock update success")
                
                # Create a mock updated event
                mock_event = CalendarEvent(
                    id=input_data.event_id,
                    title=input_data.title or "Updated Event",
                    start_time=input_data.start_time or datetime.now(),
                    end_time=input_data.end_time or (datetime.now() + timedelta(hours=1)),
                    location=input_data.location or "",
                    description=input_data.description or "",
                    all_day=input_data.all_day or False,
                    attendees=input_data.attendees or [],
                    calendar_source=input_data.calendar_name or "primary"
                )
                
                changes_made = []
                if input_data.title is not None:
                    changes_made.append('title')
                if input_data.start_time is not None:
                    changes_made.append('start_time')
                if input_data.end_time is not None:
                    changes_made.append('end_time')
                if input_data.location is not None:
                    changes_made.append('location')
                if input_data.description is not None:
                    changes_made.append('description')
                if input_data.attendees is not None:
                    changes_made.append('attendees')
                
                message = f"Mock: Event '{mock_event.title}' updated successfully"
                if changes_made:
                    message += f" ({len(changes_made)} changes: {', '.join(changes_made)})"
                
                return CalendarUpdateOutput(
                    success=True,
                    event_id=input_data.event_id,
                    event_url=f"https://calendar.google.com/calendar/event?eid={input_data.event_id}",
                    updated_event=mock_event,
                    original_event=None,
                    changes_made=changes_made,
                    message=message,
                    conflicts=conflicts
                )
                
        except Exception as e:
            logger.error(f"Error updating calendar event: {str(e)}")
            
            return CalendarUpdateOutput(
                success=False,
                event_id=input_data.event_id,
                event_url=None,
                updated_event=None,
                original_event=None,
                changes_made=[],
                message=f"Error updating event: {str(e)}",
                conflicts=[]
            )
    
    async def delete_event(self, input_data: CalendarDeleteInput) -> CalendarDeleteOutput:
        """
        Delete a calendar event.
        
        Args:
            input_data: The delete request with event_id and calendar_name
            
        Returns:
            CalendarDeleteOutput with success status and deleted event details
        """
        try:
            # Resolve calendar ID from name
            calendar_id = await self._resolve_calendar_id(input_data.calendar_name)
            
            if self.google_calendar_client:
                # Call the Google Calendar API to delete the event
                result = await self.google_calendar_client.delete_event(
                    event_id=input_data.event_id,
                    calendar_id=calendar_id
                )
                
                if result['success']:
                    logger.info(f"Successfully deleted event {input_data.event_id}")
                    return CalendarDeleteOutput(
                        success=True,
                        event_id=input_data.event_id,
                        deleted_event=result.get('deleted_event'),
                        message=result.get('message', f"Event {input_data.event_id} deleted successfully")
                    )
                else:
                    logger.error(f"Google Calendar delete failed: {result.get('error', 'Unknown error')}")
                    return CalendarDeleteOutput(
                        success=False,
                        event_id=input_data.event_id,
                        deleted_event=None,
                        message=result.get('message', f"Failed to delete event {input_data.event_id}")
                    )
            else:
                # Mock success for development without Google Calendar
                logger.info(f"MOCK: Delete event {input_data.event_id} from {input_data.calendar_name}")
                mock_deleted_event = CalendarEvent(
                    id=input_data.event_id,
                    title="Deleted Event (Mock)",
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(hours=1),
                    location="Mock Location",
                    description="This event was deleted in mock mode",
                    all_day=False,
                    attendees=[],
                    calendar_source=input_data.calendar_name or "primary"
                )
                
                return CalendarDeleteOutput(
                    success=True,
                    event_id=input_data.event_id,
                    deleted_event=mock_deleted_event,
                    message=f"Event {input_data.event_id} deleted successfully (mock mode)"
                )
                
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return CalendarDeleteOutput(
                success=False,
                event_id=input_data.event_id,
                deleted_event=None,
                message=f"Error deleting event: {str(e)}"
            )
    
    async def _detect_conflicts(self, start_time: datetime, end_time: datetime, calendar_name: str = None, exclude_event_id: str = None) -> List[CalendarEvent]:
        """Detect conflicting events at the same time."""
        try:
            # Get events for the same date
            event_date = start_time.date()
            existing_events = await self._get_events_for_date(event_date)
            
            conflicts = []
            for event in existing_events:
                # Skip the event being updated (if specified)
                if exclude_event_id and event.id == exclude_event_id:
                    continue
                    
                # Check if events overlap
                if self._events_overlap(start_time, end_time, event.start_time, event.end_time):
                    conflicts.append(event)
            
            if conflicts:
                logger.info(f"Found {len(conflicts)} conflicting events")
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []
    
    def _events_overlap(self, start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and end1 > start2
    
    async def _resolve_calendar_id(self, calendar_name: str = None) -> str:
        """Resolve calendar name to calendar ID."""
        if not calendar_name or calendar_name == "primary":
            return "primary"
        
        if self.google_calendar_client:
            try:
                calendar_mapping = self.google_calendar_client.get_calendar_list()
                for name, cal_id in calendar_mapping.items():
                    if name.lower() == calendar_name.lower():
                        return cal_id
                
                logger.warning(f"Calendar '{calendar_name}' not found, using primary")
                return "primary"
            except Exception as e:
                logger.error(f"Error resolving calendar ID: {e}")
                return "primary"
        else:
            return "primary"
    
    def _convert_google_event_from_api(self, google_event: Dict[str, Any], calendar_source: str) -> CalendarEvent:
        """Convert a Google Calendar API event to our CalendarEvent schema."""
        try:
            # This is similar to the existing _convert_google_event method but adapted for API response
            event_id = google_event.get('id', '')
            title = google_event.get('summary', '(No title)')
            description = google_event.get('description', '')
            location = google_event.get('location', '')
            
            # Handle start and end times
            start = google_event.get('start', {})
            end = google_event.get('end', {})
            
            # Check if it's an all-day event
            all_day = 'date' in start
            
            if all_day:
                # All-day events use 'date' field
                start_date = dt.datetime.strptime(start['date'], '%Y-%m-%d').date()
                start_time = datetime.combine(start_date, datetime.min.time())
                end_date = dt.datetime.strptime(end['date'], '%Y-%m-%d').date()
                end_time = datetime.combine(end_date, datetime.min.time())
            else:
                # Timed events use 'dateTime' field
                start_time = self._parse_datetime(start.get('dateTime'))
                end_time = self._parse_datetime(end.get('dateTime'))
            
            # Extract attendees
            attendees = []
            for attendee in google_event.get('attendees', []):
                email = attendee.get('email')
                if email:
                    attendees.append(email)
            
            return CalendarEvent(
                id=event_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                location=location if location else None,
                description=description if description else None,
                all_day=all_day,
                attendees=attendees if attendees else None,
                calendar_source=calendar_source
            )
            
        except Exception as e:
            logger.error(f"Error converting Google Calendar event from API: {e}")
            # Return a basic event as fallback
            return CalendarEvent(
                id=google_event.get('id', 'unknown'),
                title=google_event.get('summary', 'Unknown Event'),
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
                calendar_source=calendar_source
            )
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse RFC3339 datetime string from Google Calendar."""
        if not datetime_str:
            return datetime.now()
        
        try:
            # Handle timezone-aware datetime strings
            if datetime_str.endswith('Z'):
                # UTC timezone
                return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            elif '+' in datetime_str or datetime_str.count('-') > 2:
                # Timezone offset present
                return datetime.fromisoformat(datetime_str)
            else:
                # Assume local time
                return datetime.fromisoformat(datetime_str)
        except Exception as e:
            logger.error(f"Error parsing datetime '{datetime_str}': {e}")
            return datetime.now()
