"""Calendar tool for listing daily events."""

import asyncio
from datetime import datetime, timedelta, timezone
import datetime as dt
from typing import Dict, Any, List
import random
import os
import pytz

from ..schemas.calendar import (
    CalendarInput, CalendarOutput, CalendarEvent, CalendarRangeInput, CalendarRangeOutput,
    CalendarCreateInput, CalendarCreateOutput, CalendarUpdateInput, CalendarUpdateOutput,
    CalendarDeleteInput, CalendarDeleteOutput, CalendarFindFreeTimeInput, CalendarFindFreeTimeOutput,
    FreeTimeSlot
)
from ..utils.logging import get_logger, log_tool_call
from ..utils.cache import get_cache_service, cached, CacheTTL, generate_cache_key
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
        """Get events for a specific date from multiple calendars with caching."""
        cache = await get_cache_service()
        cache_key = generate_cache_key("calendar_events", query_date.isoformat())
        
        # Check cache first
        cached_events = await cache.get(cache_key)
        if cached_events:
            logger.debug(f"Using cached calendar events for {query_date}")
            # Convert dict back to CalendarEvent objects
            return [CalendarEvent(**event) for event in cached_events]
        
        if self.google_calendar_client:
            try:
                logger.info(f"Fetching real Google Calendar events for {query_date} from multiple calendars")
                # Use the multi-calendar method for consistency, with same start/end date
                events = await self.google_calendar_client.get_events_for_multiple_calendars(query_date, query_date)
                logger.info(f"Retrieved {len(events)} events from Google Calendar across all calendars")
                
                # Cache the events (convert to dicts for JSON serialization)
                events_dict = [event.dict() if hasattr(event, 'dict') else event.__dict__ for event in events]
                await cache.set(cache_key, events_dict, CacheTTL.CALENDAR_EVENTS)
                logger.debug(f"Cached {len(events)} calendar events for {query_date}")
                
                return events
            except Exception as e:
                logger.error(f"Error fetching Google Calendar events, falling back to mock data: {e}")
                events = await self._get_mock_events(query_date)
                # Cache mock events too (but with shorter TTL)
                events_dict = [event.dict() if hasattr(event, 'dict') else event.__dict__ for event in events]
                await cache.set(cache_key, events_dict, 60)  # 1 minute for mock data
                return events
        else:
            logger.info("Google Calendar client not available, using mock data")
            events = await self._get_mock_events(query_date)
            # Cache mock events too (but with shorter TTL)
            events_dict = [event.dict() if hasattr(event, 'dict') else event.__dict__ for event in events]
            await cache.set(cache_key, events_dict, 60)  # 1 minute for mock data
            return events
    
    async def _get_events_for_range(self, start_date: dt.date, end_date: dt.date) -> List[CalendarEvent]:
        """Get events for a date range from multiple calendars with caching."""
        cache = await get_cache_service()
        cache_key = generate_cache_key("calendar_events_range", 
                                     start_date.isoformat(), 
                                     end_date.isoformat())
        
        # Check cache first
        cached_events = await cache.get(cache_key)
        if cached_events:
            logger.debug(f"Using cached calendar events for range {start_date} to {end_date}")
            # Convert dict back to CalendarEvent objects
            return [CalendarEvent(**event) for event in cached_events]
        
        if self.google_calendar_client:
            try:
                logger.info(f"Fetching real Google Calendar events for range {start_date} to {end_date} from multiple calendars")
                # Fetch from primary + Runna + Family calendars by default
                events = await self.google_calendar_client.get_events_for_multiple_calendars(start_date, end_date)
                logger.info(f"Retrieved {len(events)} events from Google Calendar for range across all calendars")
                
                # Cache the events (convert to dicts for JSON serialization)
                events_dict = [event.dict() if hasattr(event, 'dict') else event.__dict__ for event in events]
                await cache.set(cache_key, events_dict, CacheTTL.CALENDAR_EVENTS)
                logger.debug(f"Cached {len(events)} calendar events for range {start_date} to {end_date}")
                
                return events
            except Exception as e:
                logger.error(f"Error fetching Google Calendar events for range, falling back to mock data: {e}")
                events = await self._get_mock_events_range(start_date, end_date)
                # Cache mock events too (but with shorter TTL)
                events_dict = [event.dict() if hasattr(event, 'dict') else event.__dict__ for event in events]
                await cache.set(cache_key, events_dict, 60)  # 1 minute for mock data
                return events
        else:
            logger.info("Google Calendar client not available, using mock data for range")
            events = await self._get_mock_events_range(start_date, end_date)
            # Cache mock events too (but with shorter TTL)
            events_dict = [event.dict() if hasattr(event, 'dict') else event.__dict__ for event in events]
            await cache.set(cache_key, events_dict, 60)  # 1 minute for mock data
            return events
    
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
            
            # Invalidate cache for the event date
            await self._invalidate_calendar_cache(input_data.start_time.date())
            
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
                    
                    # Invalidate cache for relevant dates
                    if input_data.start_time:
                        await self._invalidate_calendar_cache(input_data.start_time.date())
                    
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
                    
                    # Invalidate calendar cache (we don't know the date, so invalidate recent dates)
                    await self._invalidate_recent_calendar_cache()
                    
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
                
                # Invalidate calendar cache for mock deletion too
                await self._invalidate_recent_calendar_cache()
                
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
    
    async def find_free_time(self, input_data: CalendarFindFreeTimeInput) -> CalendarFindFreeTimeOutput:
        """
        Find available time slots based on duration and constraints.
        
        Args:
            input_data: The search criteria for free time slots
            
        Returns:
            CalendarFindFreeTimeOutput with available time slots
        """
        try:
            # Parse dates
            start_date = datetime.strptime(input_data.start_date, '%Y-%m-%d').date()
            end_date = start_date if not input_data.end_date else datetime.strptime(input_data.end_date, '%Y-%m-%d').date()
            
            # Parse time constraints
            earliest_time = datetime.strptime(input_data.earliest_time, '%H:%M').time()
            latest_time = datetime.strptime(input_data.latest_time, '%H:%M').time()
            
            # Get all events in the date range
            all_events = []
            current_date = start_date
            while current_date <= end_date:
                day_events = await self._get_events_for_date(current_date)
                all_events.extend(day_events)
                current_date += timedelta(days=1)
            
            # Find free time slots
            free_slots = []
            current_date = start_date
            
            while current_date <= end_date:
                day_slots = await self._find_free_slots_for_day(
                    current_date, 
                    all_events,
                    input_data.duration_minutes,
                    earliest_time,
                    latest_time,
                    input_data.preferred_time
                )
                free_slots.extend(day_slots)
                current_date += timedelta(days=1)
            
            # Sort slots by preference score (highest first)
            free_slots.sort(key=lambda x: x.preference_score, reverse=True)
            
            # Limit results
            limited_slots = free_slots[:input_data.max_results]
            
            # Build search criteria summary
            search_criteria = {
                "duration": f"{input_data.duration_minutes} minutes",
                "date_range": f"{input_data.start_date}" + (f" to {input_data.end_date}" if input_data.end_date else ""),
                "time_window": f"{input_data.earliest_time} to {input_data.latest_time}",
                "calendars": input_data.calendar_names or "all",
                "preference": input_data.preferred_time or "none"
            }
            
            # Generate message
            if limited_slots:
                top_slot = limited_slots[0]
                message = f"Found {len(free_slots)} available time slots. Top result: {top_slot.day_of_week} {top_slot.start_time.strftime('%I:%M %p')} ({input_data.duration_minutes} minutes)"
            else:
                message = f"No available time slots found matching your criteria. Try expanding your time window or reducing duration."
            
            return CalendarFindFreeTimeOutput(
                success=len(limited_slots) > 0,
                free_slots=limited_slots,
                total_slots_found=len(free_slots),
                search_criteria=search_criteria,
                message=message
            )
                
        except Exception as e:
            logger.error(f"Error finding free time: {str(e)}")
            return CalendarFindFreeTimeOutput(
                success=False,
                free_slots=[],
                total_slots_found=0,
                search_criteria={},
                message=f"Error finding free time: {str(e)}"
            )
    
    async def _find_free_slots_for_day(self, date: dt.date, all_events: List[CalendarEvent], 
                                     duration_minutes: int, earliest_time: dt.time, 
                                     latest_time: dt.time, preferred_time: str = None) -> List[FreeTimeSlot]:
        """Find free time slots for a specific day."""
        
        # Filter events for this specific day and convert to datetime objects
        # Handle timezone-aware events properly
        utc = pytz.UTC
        day_events = []
        
        for event in all_events:
            # Handle both timezone-aware and naive datetime objects
            if hasattr(event.start_time, 'date'):
                event_start = event.start_time
            else:
                event_start = datetime.fromisoformat(str(event.start_time))
            
            # Extract date for comparison
            event_date = event_start.date() if hasattr(event_start, 'date') else event_start.date()
            
            if event_date == date:
                # Skip all-day events as they shouldn't block specific time slots
                if hasattr(event, 'all_day') and event.all_day:
                    continue
                day_events.append(event)
        
        # Sort events by start time
        day_events.sort(key=lambda x: self._get_event_datetime(x.start_time))
        
        # Create timezone-aware time boundaries for the day
        # Use UTC timezone to match Google Calendar events
        day_start = datetime.combine(date, earliest_time, tzinfo=utc)
        day_end = datetime.combine(date, latest_time, tzinfo=utc)
        
        # Find gaps between events
        free_slots = []
        current_time = day_start
        
        for event in day_events:
            event_start = self._get_event_datetime(event.start_time)
            event_end = self._get_event_datetime(event.end_time)
            
            # Skip events outside our time window
            if event_end <= day_start or event_start >= day_end:
                continue
                
            # Adjust event times to our window
            event_start = max(event_start, day_start)
            event_end = min(event_end, day_end)
            
            # Check if there's a gap before this event
            if current_time < event_start:
                gap_duration = int((event_start - current_time).total_seconds() / 60)
                if gap_duration >= duration_minutes:
                    slot = await self._create_free_time_slot(
                        current_time, 
                        event_start,
                        duration_minutes,
                        preferred_time,
                        day_events,
                        event
                    )
                    free_slots.append(slot)
            
            # Move current time to end of this event
            current_time = max(current_time, event_end)
        
        # Check for gap after the last event
        if current_time < day_end:
            gap_duration = int((day_end - current_time).total_seconds() / 60)
            if gap_duration >= duration_minutes:
                slot = await self._create_free_time_slot(
                    current_time,
                    day_end, 
                    duration_minutes,
                    preferred_time,
                    day_events,
                    None
                )
                free_slots.append(slot)
        
        return free_slots
    
    async def _create_free_time_slot(self, gap_start: datetime, gap_end: datetime, 
                                   duration_minutes: int, preferred_time: str,
                                   day_events: List[CalendarEvent], 
                                   next_event: CalendarEvent = None) -> FreeTimeSlot:
        """Create a FreeTimeSlot object from a time gap."""
        
        # Calculate actual slot time (use full gap or just the needed duration)
        slot_start = gap_start
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        
        # Ensure we don't exceed the gap
        if slot_end > gap_end:
            slot_end = gap_end
            slot_start = slot_end - timedelta(minutes=duration_minutes)
        
        # Find events before and after this slot
        conflicts_before = None
        conflicts_after = next_event
        
        for event in day_events:
            event_end = self._get_event_datetime(event.end_time)
            if event_end <= slot_start:
                if not conflicts_before or self._get_event_datetime(conflicts_before.end_time) < event_end:
                    conflicts_before = event
        
        # Calculate preference score
        preference_score = await self._calculate_preference_score(slot_start, preferred_time)
        
        # Determine time period
        hour = slot_start.hour
        if hour < 12:
            time_period = "morning"
        elif hour < 17:
            time_period = "afternoon"
        else:
            time_period = "evening"
        
        return FreeTimeSlot(
            start_time=slot_start,
            end_time=slot_end,
            duration_minutes=int((slot_end - slot_start).total_seconds() / 60),
            date=slot_start.strftime('%Y-%m-%d'),
            day_of_week=slot_start.strftime('%A'),
            time_period=time_period,
            conflicts_before=conflicts_before,
            conflicts_after=conflicts_after,
            preference_score=preference_score
        )
    
    async def _calculate_preference_score(self, slot_start: datetime, preferred_time: str = None) -> float:
        """Calculate preference score for a time slot (0-1, higher is better)."""
        
        base_score = 0.5  # Default score
        hour = slot_start.hour
        
        # Time-based scoring
        if preferred_time == "morning" and 8 <= hour <= 11:
            base_score = 0.9
        elif preferred_time == "afternoon" and 13 <= hour <= 16:
            base_score = 0.9
        elif preferred_time == "evening" and 17 <= hour <= 19:
            base_score = 0.8
        elif not preferred_time:
            # General preference for mid-morning and mid-afternoon
            if 9 <= hour <= 11 or 14 <= hour <= 16:
                base_score = 0.7
            elif 8 <= hour <= 12 or 13 <= hour <= 17:
                base_score = 0.6
        
        # Avoid very early or very late times
        if hour < 8 or hour > 18:
            base_score *= 0.5
        
        # Prefer non-lunch hours
        if 12 <= hour <= 13:
            base_score *= 0.7
        
        return min(1.0, base_score)
    
    def _get_event_datetime(self, dt_obj) -> datetime:
        """Convert various datetime representations to timezone-aware datetime objects."""
        if hasattr(dt_obj, 'tzinfo') and dt_obj.tzinfo is not None:
            # Already timezone-aware
            return dt_obj
        elif hasattr(dt_obj, 'time'):
            # timezone-naive datetime object
            return dt_obj.replace(tzinfo=pytz.UTC)
        else:
            # String representation
            parsed = datetime.fromisoformat(str(dt_obj))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=pytz.UTC)
            return parsed
    
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
    
    async def _invalidate_calendar_cache(self, target_date: dt.date):
        """Invalidate calendar cache for a specific date and related ranges."""
        cache = await get_cache_service()
        
        # Invalidate single date cache
        single_cache_key = generate_cache_key("calendar_events", target_date.isoformat())
        await cache.delete(single_cache_key)
        
        # Invalidate range caches that might include this date
        # We'll invalidate common ranges around this date
        for days_before in range(0, 8):  # up to a week before
            for days_after in range(1, 8):  # up to a week after
                start_date = target_date - timedelta(days=days_before)
                end_date = target_date + timedelta(days=days_after)
                range_cache_key = generate_cache_key("calendar_events_range", 
                                                   start_date.isoformat(), 
                                                   end_date.isoformat())
                await cache.delete(range_cache_key)
        
        logger.debug(f"Invalidated calendar cache for {target_date}")
    
    async def _invalidate_recent_calendar_cache(self):
        """Invalidate calendar cache for recent dates (when exact date is unknown)."""
        cache = await get_cache_service()
        
        # Invalidate cache for the past week and next week
        today = dt.date.today()
        for days_offset in range(-7, 8):
            target_date = today + timedelta(days=days_offset)
            await self._invalidate_calendar_cache(target_date)
        
        logger.debug("Invalidated recent calendar cache")
