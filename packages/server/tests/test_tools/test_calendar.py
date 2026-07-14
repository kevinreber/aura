"""Tests for the calendar tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date
import pytz

from mcp_server.tools.calendar import CalendarTool
from mcp_server.clients.google_calendar import GoogleCalendarAuthError, GoogleCalendarClient
from mcp_server.schemas.calendar import (
    CalendarInput, CalendarOutput, CalendarEvent,
    CalendarRangeInput, CalendarRangeOutput,
    CalendarCreateInput, CalendarCreateOutput,
    CalendarUpdateInput, CalendarUpdateOutput,
    CalendarDeleteInput, CalendarDeleteOutput,
    CalendarFindFreeTimeInput, CalendarFindFreeTimeOutput
)


class TestCalendarTool:
    """Test the CalendarTool class."""

    @pytest.fixture
    def calendar_tool(self):
        """Create a CalendarTool instance."""
        return CalendarTool()

    @pytest.mark.asyncio
    async def test_list_events_mock_data(self, calendar_tool):
        """Test listing events with mock data (no Google Calendar configured)."""
        today = date.today()
        input_data = CalendarInput(date=today)

        result = await calendar_tool.list_events(input_data)

        assert isinstance(result, CalendarOutput)
        assert result.date == today
        assert isinstance(result.events, list)
        assert result.total_events == len(result.events)

    @pytest.mark.asyncio
    async def test_list_events_weekday(self, calendar_tool):
        """Test listing events for a weekday generates workday events."""
        # Find next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)

        input_data = CalendarInput(date=next_monday)

        result = await calendar_tool.list_events(input_data)

        # Workdays should potentially have events
        assert isinstance(result.events, list)

    @pytest.mark.asyncio
    async def test_list_events_range(self, calendar_tool):
        """Test listing events for a date range."""
        today = date.today()
        end_date = today + timedelta(days=7)

        input_data = CalendarRangeInput(
            start_date=today,
            end_date=end_date
        )

        result = await calendar_tool.list_events_range(input_data)

        assert isinstance(result, CalendarRangeOutput)
        assert result.start_date == today
        assert result.end_date == end_date
        assert isinstance(result.events, list)
        assert result.total_events == len(result.events)

    @pytest.mark.asyncio
    async def test_list_events_far_future_date(self, calendar_tool):
        """Test listing events for a date far in the future returns empty."""
        future_date = date.today() + timedelta(days=30)

        input_data = CalendarInput(date=future_date)

        result = await calendar_tool.list_events(input_data)

        # Far future dates return empty in mock mode
        assert isinstance(result.events, list)


class TestCalendarEventOperations:
    """Test CRUD operations for calendar events."""

    @pytest.fixture
    def calendar_tool(self):
        """Create a CalendarTool instance."""
        return CalendarTool()

    @pytest.mark.asyncio
    async def test_create_event_mock(self, calendar_tool):
        """Test creating an event (mock mode)."""
        start_time = datetime.now() + timedelta(hours=2)
        end_time = start_time + timedelta(hours=1)

        input_data = CalendarCreateInput(
            title="Test Meeting",
            start_time=start_time,
            end_time=end_time,
            description="Test description",
            location="Conference Room A"
        )

        result = await calendar_tool.create_event(input_data)

        assert isinstance(result, CalendarCreateOutput)
        assert result.success is True
        assert result.event_id is not None
        assert "Test Meeting" in result.message

    @pytest.mark.asyncio
    async def test_create_event_all_day(self, calendar_tool):
        """Test creating an all-day event."""
        tomorrow = datetime.now() + timedelta(days=1)

        input_data = CalendarCreateInput(
            title="All Day Event",
            start_time=tomorrow.replace(hour=0, minute=0, second=0),
            end_time=tomorrow.replace(hour=23, minute=59, second=59),
            all_day=True
        )

        result = await calendar_tool.create_event(input_data)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_create_event_with_attendees(self, calendar_tool):
        """Test creating an event with attendees."""
        start_time = datetime.now() + timedelta(hours=3)
        end_time = start_time + timedelta(hours=1)

        input_data = CalendarCreateInput(
            title="Team Sync",
            start_time=start_time,
            end_time=end_time,
            attendees=["alice@example.com", "bob@example.com"]
        )

        result = await calendar_tool.create_event(input_data)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_update_event_mock(self, calendar_tool):
        """Test updating an event (mock mode)."""
        input_data = CalendarUpdateInput(
            event_id="test_event_123",
            title="Updated Meeting Title",
            description="Updated description"
        )

        result = await calendar_tool.update_event(input_data)

        assert isinstance(result, CalendarUpdateOutput)
        assert result.success is True
        assert "title" in result.changes_made
        assert "description" in result.changes_made

    @pytest.mark.asyncio
    async def test_update_event_time(self, calendar_tool):
        """Test updating event time."""
        new_start = datetime.now() + timedelta(hours=4)
        new_end = new_start + timedelta(hours=2)

        input_data = CalendarUpdateInput(
            event_id="test_event_456",
            start_time=new_start,
            end_time=new_end
        )

        result = await calendar_tool.update_event(input_data)

        assert result.success is True
        assert "start_time" in result.changes_made
        assert "end_time" in result.changes_made

    @pytest.mark.asyncio
    async def test_delete_event_mock(self, calendar_tool):
        """Test deleting an event (mock mode)."""
        input_data = CalendarDeleteInput(event_id="test_event_789")

        result = await calendar_tool.delete_event(input_data)

        assert isinstance(result, CalendarDeleteOutput)
        assert result.success is True
        assert result.event_id == "test_event_789"

    @pytest.mark.asyncio
    async def test_delete_event_with_calendar_name(self, calendar_tool):
        """Test deleting an event from a specific calendar."""
        input_data = CalendarDeleteInput(
            event_id="test_event_abc",
            calendar_name="Work"
        )

        result = await calendar_tool.delete_event(input_data)

        assert result.success is True


class TestFindFreeTime:
    """Test the find_free_time method."""

    @pytest.fixture
    def calendar_tool(self):
        """Create a CalendarTool instance."""
        return CalendarTool()

    @pytest.mark.asyncio
    async def test_find_free_time_basic(self, calendar_tool):
        """Test finding free time slots."""
        today = date.today()

        input_data = CalendarFindFreeTimeInput(
            duration_minutes=60,
            start_date=today.isoformat(),
            earliest_time="09:00",
            latest_time="17:00"
        )

        result = await calendar_tool.find_free_time(input_data)

        assert isinstance(result, CalendarFindFreeTimeOutput)
        assert isinstance(result.free_slots, list)
        assert result.search_criteria is not None

    @pytest.mark.asyncio
    async def test_find_free_time_with_preference(self, calendar_tool):
        """Test finding free time with time preference."""
        today = date.today()

        input_data = CalendarFindFreeTimeInput(
            duration_minutes=30,
            start_date=today.isoformat(),
            earliest_time="08:00",
            latest_time="18:00",
            preferred_time="morning"
        )

        result = await calendar_tool.find_free_time(input_data)

        assert result is not None
        assert result.search_criteria.get("preference") == "morning"

    @pytest.mark.asyncio
    async def test_find_free_time_date_range(self, calendar_tool):
        """Test finding free time over a date range."""
        today = date.today()
        end_date = today + timedelta(days=5)

        input_data = CalendarFindFreeTimeInput(
            duration_minutes=45,
            start_date=today.isoformat(),
            end_date=end_date.isoformat(),
            earliest_time="10:00",
            latest_time="16:00",
            max_results=10
        )

        result = await calendar_tool.find_free_time(input_data)

        assert len(result.free_slots) <= 10


class TestCalendarHelperMethods:
    """Test helper methods of the CalendarTool."""

    @pytest.fixture
    def calendar_tool(self):
        """Create a CalendarTool instance."""
        return CalendarTool()

    def test_events_overlap(self, calendar_tool):
        """Test event overlap detection."""
        base = datetime.now()

        # Events that overlap
        assert calendar_tool._events_overlap(
            base, base + timedelta(hours=1),
            base + timedelta(minutes=30), base + timedelta(hours=2)
        ) is True

        # Events that don't overlap
        assert calendar_tool._events_overlap(
            base, base + timedelta(hours=1),
            base + timedelta(hours=2), base + timedelta(hours=3)
        ) is False

        # Adjacent events (don't overlap)
        assert calendar_tool._events_overlap(
            base, base + timedelta(hours=1),
            base + timedelta(hours=1), base + timedelta(hours=2)
        ) is False

    def test_parse_datetime(self, calendar_tool):
        """Test datetime parsing from RFC3339 strings."""
        # UTC timezone
        dt = calendar_tool._parse_datetime("2024-01-15T10:00:00Z")
        assert dt.hour == 10

        # With offset
        dt = calendar_tool._parse_datetime("2024-01-15T10:00:00-08:00")
        assert dt is not None

        # Empty string
        dt = calendar_tool._parse_datetime("")
        assert dt is not None  # Returns now()

    @pytest.mark.asyncio
    async def test_calculate_preference_score(self, calendar_tool):
        """Test preference score calculation."""
        # Morning slot with morning preference
        morning_slot = datetime.now().replace(hour=9, minute=0)
        score = await calendar_tool._calculate_preference_score(morning_slot, "morning")
        assert score >= 0.7

        # Afternoon slot with afternoon preference
        afternoon_slot = datetime.now().replace(hour=14, minute=0)
        score = await calendar_tool._calculate_preference_score(afternoon_slot, "afternoon")
        assert score >= 0.7

        # Lunch time (reduced score)
        lunch_slot = datetime.now().replace(hour=12, minute=30)
        score = await calendar_tool._calculate_preference_score(lunch_slot, None)
        assert score < 0.7

    @pytest.mark.asyncio
    async def test_resolve_calendar_id(self, calendar_tool):
        """Test calendar ID resolution."""
        # Primary calendar
        cal_id = await calendar_tool._resolve_calendar_id("primary")
        assert cal_id == "primary"

        # None defaults to primary
        cal_id = await calendar_tool._resolve_calendar_id(None)
        assert cal_id == "primary"

    def test_generate_workday_events(self, calendar_tool):
        """Test workday event generation."""
        today = date.today()
        events = calendar_tool._generate_workday_events(today)

        assert isinstance(events, list)
        # Events should have proper structure
        for event in events:
            assert isinstance(event, CalendarEvent)
            assert event.title is not None
            assert event.start_time is not None
            assert event.end_time is not None

    def test_generate_weekend_events(self, calendar_tool):
        """Test weekend event generation."""
        # Find next Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        saturday = today + timedelta(days=days_until_saturday)

        events = calendar_tool._generate_weekend_events(saturday)

        assert isinstance(events, list)


class TestCalendarAuthFailure:
    """Auth failures must surface as explicit errors — never mock data or empty lists.

    Dates are >7 days out so mock-event caching from other tests (which only
    populates dates near today) can't short-circuit the fetch under test.
    """

    @pytest.fixture
    def calendar_tool(self):
        """CalendarTool with no Google credentials configured (mock mode)."""
        return CalendarTool()

    @pytest.fixture
    def auth_failing_client(self):
        """Google client whose fetches raise the typed auth error."""
        client = MagicMock()
        client.get_events_for_multiple_calendars = AsyncMock(
            side_effect=GoogleCalendarAuthError()
        )
        return client

    @pytest.mark.asyncio
    async def test_init_auth_error_returns_error_payload(self, calendar_tool):
        """Auth failure detected at init → error payload, not mock events."""
        calendar_tool.google_calendar_client = None
        calendar_tool.google_calendar_auth_error = GoogleCalendarAuthError.DEFAULT_MESSAGE

        result = await calendar_tool.list_events(CalendarInput(date=date.today()))

        assert isinstance(result, CalendarOutput)
        assert result.auth_expired is True
        assert "re-authentication required" in result.error
        assert result.events == []
        assert result.total_events == 0

    @pytest.mark.asyncio
    async def test_init_auth_error_returns_error_payload_for_range(self, calendar_tool):
        calendar_tool.google_calendar_client = None
        calendar_tool.google_calendar_auth_error = GoogleCalendarAuthError.DEFAULT_MESSAGE

        start = date.today()
        result = await calendar_tool.list_events_range(
            CalendarRangeInput(start_date=start, end_date=start + timedelta(days=7))
        )

        assert isinstance(result, CalendarRangeOutput)
        assert result.auth_expired is True
        assert "re-authentication required" in result.error
        assert result.events == []

    @pytest.mark.asyncio
    async def test_runtime_auth_error_no_mock_fallback(self, calendar_tool, auth_failing_client):
        """Token revoked mid-session → error payload; auth error is remembered."""
        calendar_tool.google_calendar_client = auth_failing_client

        query_date = date.today() + timedelta(days=10)
        result = await calendar_tool.list_events(CalendarInput(date=query_date))

        assert result.auth_expired is True
        assert "re-authentication required" in result.error
        assert result.events == []
        # Remembered so subsequent calls fail fast without hitting the API
        assert calendar_tool.google_calendar_auth_error is not None

    @pytest.mark.asyncio
    async def test_runtime_auth_error_no_mock_fallback_for_range(
        self, calendar_tool, auth_failing_client
    ):
        calendar_tool.google_calendar_client = auth_failing_client

        start = date.today() + timedelta(days=10)
        result = await calendar_tool.list_events_range(
            CalendarRangeInput(start_date=start, end_date=start + timedelta(days=1))
        )

        assert result.auth_expired is True
        assert result.events == []
        assert calendar_tool.google_calendar_auth_error is not None

    @pytest.mark.asyncio
    async def test_empty_calendar_with_valid_auth_unchanged(self, calendar_tool):
        """Valid auth + no events stays a plain empty result — no error fields."""
        client = MagicMock()
        client.get_events_for_multiple_calendars = AsyncMock(return_value=[])
        calendar_tool.google_calendar_client = client

        query_date = date.today() + timedelta(days=12)
        result = await calendar_tool.list_events(CalendarInput(date=query_date))

        assert result.error is None
        assert result.auth_expired is False
        assert result.events == []
        assert result.total_events == 0

    @pytest.mark.asyncio
    async def test_non_auth_error_still_falls_back_to_mock(self, calendar_tool):
        """Transient (non-auth) API failures keep the existing mock fallback."""
        client = MagicMock()
        client.get_events_for_multiple_calendars = AsyncMock(
            side_effect=RuntimeError("transient API blip")
        )
        calendar_tool.google_calendar_client = client

        query_date = date.today() + timedelta(days=13)
        result = await calendar_tool.list_events(CalendarInput(date=query_date))

        # Mock fallback path: no error surfaced, normal (possibly empty) payload
        assert result.error is None
        assert result.auth_expired is False

    @pytest.mark.asyncio
    async def test_find_free_time_surfaces_auth_error(self, calendar_tool):
        """find_free_time reports the auth failure instead of fake free slots."""
        calendar_tool.google_calendar_client = None
        calendar_tool.google_calendar_auth_error = GoogleCalendarAuthError.DEFAULT_MESSAGE

        result = await calendar_tool.find_free_time(
            CalendarFindFreeTimeInput(
                duration_minutes=60,
                start_date=date.today().isoformat(),
            )
        )

        assert result.success is False
        assert "re-authentication required" in result.message


class TestGoogleCalendarClientAuth:
    """The client raises a typed error for expired/revoked credentials."""

    _CREDS_JSON = (
        '{"refresh_token": "expired", "client_id": "cid", '
        '"client_secret": "sec", "token": "tok"}'
    )

    def _expired_creds_client(self) -> GoogleCalendarClient:
        """Client whose stored refresh token is rejected by Google."""
        creds = MagicMock()
        creds.valid = False
        creds.refresh_token = "expired"
        creds.refresh.side_effect = Exception(
            "invalid_grant: Token has been expired or revoked."
        )
        with patch("mcp_server.clients.google_calendar.Credentials", return_value=creds):
            return GoogleCalendarClient(credentials_json=self._CREDS_JSON)

    def _client_with_service(self, service) -> GoogleCalendarClient:
        """Client with valid creds and an injected (mock) API service."""
        creds = MagicMock()
        creds.valid = True
        with patch("mcp_server.clients.google_calendar.Credentials", return_value=creds), \
                patch("mcp_server.clients.google_calendar.build", return_value=service):
            return GoogleCalendarClient(credentials_json=self._CREDS_JSON)

    @staticmethod
    def _http_error(status: int):
        import httplib2
        from googleapiclient.errors import HttpError

        resp = httplib2.Response({"status": str(status)})
        return HttpError(resp, b'{"error": {"message": "boom"}}')

    def test_refresh_failure_sets_auth_error(self):
        client = self._expired_creds_client()

        assert client.service is None
        assert client.auth_error is not None
        assert "re-authentication required" in client.auth_error

    @pytest.mark.asyncio
    async def test_fetch_raises_typed_error_after_refresh_failure(self):
        client = self._expired_creds_client()

        with pytest.raises(GoogleCalendarAuthError):
            await client.get_events_for_date(date.today())
        with pytest.raises(GoogleCalendarAuthError):
            await client.get_events_for_range(date.today(), date.today() + timedelta(days=1))

    @pytest.mark.asyncio
    async def test_401_response_raises_typed_error(self):
        service = MagicMock()
        service.events.return_value.list.return_value.execute.side_effect = self._http_error(401)
        client = self._client_with_service(service)

        with pytest.raises(GoogleCalendarAuthError):
            await client.get_events_for_date(date.today())
        assert client.auth_error is not None

    @pytest.mark.asyncio
    async def test_non_auth_http_error_still_returns_empty(self):
        """A 500 from Google is not an auth failure — keep the [] contract."""
        service = MagicMock()
        service.events.return_value.list.return_value.execute.side_effect = self._http_error(500)
        client = self._client_with_service(service)

        events = await client.get_events_for_date(date.today())

        assert events == []
        assert client.auth_error is None
