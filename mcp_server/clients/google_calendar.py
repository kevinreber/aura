"""Google Calendar API client for fetching real calendar events."""

import os
import pickle
import datetime as dt
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..schemas.calendar import CalendarEvent
from ..utils.logging import get_logger

logger = get_logger("google_calendar_client")

# Google Calendar API scopes - updated to include write permissions for event creation
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]


class GoogleCalendarClient:
    """Client for accessing Google Calendar API."""
    
    def __init__(self, credentials_path: str = None, credentials_json: str = None):
        """
        Initialize Google Calendar client.
        
        Args:
            credentials_path: Path to Google API credentials JSON file (for local dev)
            credentials_json: JSON string of credentials (for production env var)
        """
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the Google Calendar API service."""
        try:
            creds = self._get_credentials()
            if creds:
                self.service = build('calendar', 'v3', credentials=creds)
                logger.info("Google Calendar API service initialized successfully")
            else:
                logger.error("Failed to obtain Google Calendar credentials")
        except Exception as e:
            logger.error(f"Error initializing Google Calendar service: {e}")
            self.service = None
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh Google API credentials."""
        creds = None
        
        # Production mode: Use credentials from environment variable
        if self.credentials_json:
            try:
                import json
                creds_info = json.loads(self.credentials_json)
                
                # Create credentials from the JSON data
                if 'refresh_token' in creds_info:
                    # Has refresh token - create credentials directly
                    creds = Credentials(
                        token=creds_info.get('token'),
                        refresh_token=creds_info.get('refresh_token'),
                        token_uri=creds_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
                        client_id=creds_info.get('client_id'),
                        client_secret=creds_info.get('client_secret'),
                        scopes=SCOPES
                    )
                    
                    # Refresh if needed
                    if not creds.valid and creds.refresh_token:
                        try:
                            creds.refresh(Request())
                            logger.info("Refreshed Google Calendar credentials from env var")
                        except Exception as e:
                            logger.error(f"Error refreshing credentials from env var: {e}")
                            return None
                else:
                    logger.error("No refresh token found in credentials JSON")
                    return None
                    
                return creds
                
            except Exception as e:
                logger.error(f"Error parsing credentials JSON: {e}")
                return None
        
        # Development mode: Use file-based credentials
        if not self.credentials_path:
            logger.error("No credentials path or JSON provided")
            return None
            
        # The file token.pickle stores the user's access and refresh tokens
        token_path = str(Path(self.credentials_path).parent / "token.pickle")
        
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed Google Calendar credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    logger.info("Completed Google Calendar OAuth flow")
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {e}")
                    return None
            
            # Save the credentials for the next run
            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Saved Google Calendar credentials")
            except Exception as e:
                logger.error(f"Error saving credentials: {e}")
        
        return creds
    
    def _get_calendar_display_name(self, calendar_id: str) -> str:
        """Convert calendar ID to a user-friendly display name."""
        if calendar_id == 'primary':
            return 'primary'
        
        # Get calendar list to find the display name
        calendar_mapping = self.get_calendar_list()
        for name, cal_id in calendar_mapping.items():
            if cal_id == calendar_id:
                return name
        
        # If not found, return the ID itself
        return calendar_id

    async def get_events_for_date(self, query_date: dt.date, calendar_id: str = 'primary') -> List[CalendarEvent]:
        """
        Get calendar events for a specific date.
        
        Args:
            query_date: Date to query events for
            calendar_id: Google Calendar ID (default: 'primary' for main calendar)
            
        Returns:
            List of CalendarEvent objects
        """
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return []
        
        try:
            # Set up time range for the query date (start of day to end of day)
            start_time = datetime.combine(query_date, datetime.min.time())
            end_time = start_time + timedelta(days=1)
            
            # Convert to RFC3339 timestamp format required by Google Calendar API
            time_min = start_time.isoformat() + 'Z'
            time_max = end_time.isoformat() + 'Z'
            
            logger.info(f"Fetching Google Calendar events for {query_date} (calendar: {calendar_id})")
            
            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            logger.info(f"Found {len(events)} events for {query_date}")
            
            # Convert Google Calendar events to our CalendarEvent schema
            calendar_source = self._get_calendar_display_name(calendar_id)
            calendar_events = []
            for event in events:
                try:
                    calendar_event = self._convert_google_event(event, calendar_source)
                    if calendar_event:
                        calendar_events.append(calendar_event)
                except Exception as e:
                    logger.error(f"Error converting event {event.get('id', 'unknown')}: {e}")
                    continue
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events: {e}")
            return []
    
    def _convert_google_event(self, google_event: Dict[str, Any], calendar_source: str = "primary") -> Optional[CalendarEvent]:
        """Convert a Google Calendar event to our CalendarEvent schema."""
        try:
            # Extract basic event info
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
                
                if not start_time or not end_time:
                    logger.warning(f"Could not parse times for event {event_id}")
                    return None
            
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
            logger.error(f"Error converting Google Calendar event: {e}")
            return None
    
    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse RFC3339 datetime string from Google Calendar."""
        if not datetime_str:
            return None
        
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
            return None
    
    def get_calendar_list(self) -> Dict[str, str]:
        """
        Get a list of all available calendars for the authenticated user.
        
        Returns:
            Dictionary mapping calendar names to calendar IDs
        """
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return {}
        
        try:
            # Get all calendars including hidden/secondary ones
            calendar_list = self.service.calendarList().list(
                showHidden=True,
                showDeleted=False
            ).execute()
            calendars = {}
            
            for calendar_item in calendar_list.get('items', []):
                calendar_id = calendar_item['id']
                calendar_name = calendar_item.get('summary', calendar_id)
                access_role = calendar_item.get('accessRole', 'unknown')
                primary = calendar_item.get('primary', False)
                
                calendars[calendar_name] = calendar_id
                logger.info(f"Found calendar: '{calendar_name}' (ID: {calendar_id}, Access: {access_role}, Primary: {primary})")
            
            return calendars
        except Exception as e:
            logger.error(f"Error fetching calendar list: {e}")
            return {}
    
    async def get_events_for_multiple_calendars(self, start_date: dt.date, end_date: dt.date, calendar_names: List[str] = None) -> List[CalendarEvent]:
        """
        Get calendar events from multiple calendars for a date range.
        
        Args:
            start_date: Start date of the range (inclusive)
            end_date: End date of the range (inclusive)
            calendar_names: List of calendar names to fetch from. If None, fetches from primary + Runna + Family
            
        Returns:
            Combined list of CalendarEvent objects from all specified calendars
        """
        if calendar_names is None:
            # Default to primary calendar + Runna + Family calendars
            # Note: Work calendar is an Outlook import and not accessible via Google Calendar API
            calendar_names = ['primary', 'Runna', 'Family']
        
        # Get the mapping of calendar names to IDs
        calendar_mapping = self.get_calendar_list()
        
        all_events = []
        
        for calendar_name in calendar_names:
            try:
                # Handle 'primary' specially
                if calendar_name == 'primary':
                    calendar_id = 'primary'
                else:
                    # Find the calendar ID by name
                    calendar_id = None
                    for name, cal_id in calendar_mapping.items():
                        if name.lower() == calendar_name.lower():
                            calendar_id = cal_id
                            break
                    
                    if not calendar_id:
                        logger.warning(f"Calendar '{calendar_name}' not found. Available calendars: {list(calendar_mapping.keys())}")
                        continue
                
                # Fetch events from this calendar
                logger.info(f"Fetching events from calendar: {calendar_name} (ID: {calendar_id})")
                calendar_events = await self.get_events_for_range(start_date, end_date, calendar_id)
                
                # The calendar_source is now set by _convert_google_event
                all_events.extend(calendar_events)
                
            except Exception as e:
                logger.error(f"Error fetching events from calendar '{calendar_name}': {e}")
                continue
        
        # Sort all events by start time (handle timezone-aware and naive datetimes)
        def get_sort_key(event):
            if not hasattr(event, 'start_time') or not event.start_time:
                return datetime.min.replace(tzinfo=None)
            
            start_time = event.start_time
            # If it's timezone-aware, convert to naive for consistent comparison
            if hasattr(start_time, 'tzinfo') and start_time.tzinfo is not None:
                return start_time.replace(tzinfo=None)
            return start_time
        
        all_events.sort(key=get_sort_key)
        
        logger.info(f"Total events fetched from {len(calendar_names)} calendars: {len(all_events)}")
        return all_events

    async def get_events_for_range(self, start_date: dt.date, end_date: dt.date, calendar_id: str = 'primary') -> List[CalendarEvent]:
        """
        Get calendar events for a date range (much more efficient than multiple single-date calls).
        
        Args:
            start_date: Start date of the range (inclusive)
            end_date: End date of the range (inclusive) 
            calendar_id: Google Calendar ID (default: 'primary' for main calendar)
            
        Returns:
            List of CalendarEvent objects for the entire range
        """
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return []
        
        try:
            # Set up time range for the entire date range
            start_time = datetime.combine(start_date, datetime.min.time())
            end_time = datetime.combine(end_date + timedelta(days=1), datetime.min.time())  # Include end_date
            
            # Convert to RFC3339 timestamp format required by Google Calendar API
            time_min = start_time.isoformat() + 'Z'
            time_max = end_time.isoformat() + 'Z'
            
            logger.info(f"Fetching Google Calendar events from {start_date} to {end_date} (calendar: {calendar_id})")
            
            # Call the Calendar API - single request for entire range!
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=250  # Increase limit for range queries
            ).execute()
            
            events = events_result.get('items', [])
            
            logger.info(f"Found {len(events)} events from {start_date} to {end_date}")
            
            # Convert Google Calendar events to our CalendarEvent schema (reuse existing logic)
            calendar_source = self._get_calendar_display_name(calendar_id)
            calendar_events = []
            for event in events:
                converted_event = self._convert_google_event(event, calendar_source)
                if converted_event:
                    calendar_events.append(converted_event)
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events for range: {e}")
            return []

    async def create_event(self, title: str, start_time: datetime, end_time: datetime, 
                          description: str = None, location: str = None, 
                          attendees: List[str] = None, calendar_id: str = 'primary',
                          all_day: bool = False) -> Dict[str, Any]:
        """
        Create a new calendar event.
        
        Args:
            title: Event title/summary
            start_time: Event start time
            end_time: Event end time  
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendee email addresses (optional)
            calendar_id: Target calendar ID (default: 'primary')
            all_day: Whether this is an all-day event
            
        Returns:
            Dictionary with created event details or error info
        """
        if not self.service:
            logger.error("Google Calendar service not initialized")
            return {
                'success': False,
                'error': 'Google Calendar service not available',
                'event_id': None,
                'event_url': None
            }
        
        try:
            # Build the event object
            event_body = {
                'summary': title,
                'description': description or '',
                'location': location or '',
            }
            
            # Handle all-day vs timed events
            if all_day:
                # All-day events use date format (YYYY-MM-DD)
                start_date = start_time.date().isoformat()
                end_date = end_time.date().isoformat()
                event_body['start'] = {'date': start_date}
                event_body['end'] = {'date': end_date}
            else:
                # Timed events use dateTime format (RFC3339)
                event_body['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Los_Angeles',  # TODO: Make timezone configurable
                }
                event_body['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Los_Angeles',
                }
            
            # Add attendees if provided
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]
            
            logger.info(f"Creating calendar event: {title} on {calendar_id}")
            logger.debug(f"Event body: {event_body}")
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=calendar_id, 
                body=event_body
            ).execute()
            
            event_id = created_event.get('id')
            event_url = created_event.get('htmlLink', f"https://calendar.google.com/calendar/event?eid={event_id}")
            
            logger.info(f"Successfully created event: {event_id}")
            
            return {
                'success': True,
                'event_id': event_id,
                'event_url': event_url,
                'created_event': created_event,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Error creating calendar event: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'event_id': None,
                'event_url': None
            }

    def test_connection(self) -> bool:
        """Test if the Google Calendar connection is working."""
        if not self.service:
            return False
        
        try:
            # Try to get the primary calendar info
            calendar = self.service.calendars().get(calendarId='primary').execute()
            logger.info(f"Connected to Google Calendar: {calendar.get('summary', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Google Calendar connection test failed: {e}")
            return False
