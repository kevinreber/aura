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

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class GoogleCalendarClient:
    """Client for accessing Google Calendar API."""
    
    def __init__(self, credentials_path: str):
        """
        Initialize Google Calendar client.
        
        Args:
            credentials_path: Path to Google API credentials JSON file
        """
        self.credentials_path = credentials_path
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
            calendar_events = []
            for event in events:
                try:
                    calendar_event = self._convert_google_event(event)
                    if calendar_event:
                        calendar_events.append(calendar_event)
                except Exception as e:
                    logger.error(f"Error converting event {event.get('id', 'unknown')}: {e}")
                    continue
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events: {e}")
            return []
    
    def _convert_google_event(self, google_event: Dict[str, Any]) -> Optional[CalendarEvent]:
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
                attendees=attendees if attendees else None
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
            calendar_events = []
            for event in events:
                converted_event = self._convert_google_event(event)
                if converted_event:
                    calendar_events.append(converted_event)
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Error fetching Google Calendar events for range: {e}")
            return []

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
