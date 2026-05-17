"""Structured "tomorrow" briefing — deterministic, no LLM.

Fans out to weather, calendar, and todos in parallel, then computes
per-event driving commute (origin = previous event's location, or HOME
for the first located event of the day). Returns JSON the UI can render
directly into the TomorrowBriefingWidget.

The smart/narrative variant is intentionally separate — this builder
exists so the dashboard can render a fast, deterministic briefing on
every page load without paying for an LLM call.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

from loguru import logger

from ..models.config import get_settings
from ..services.mcp_client import MCPClient


async def compute_per_event_commute(
    events: list[dict[str, Any]],
    home_address: str,
    client: MCPClient,
) -> list[Optional[dict[str, Any]]]:
    """Driving commute for each event, parallel to the events list.

    Origin = previous located event's location, or `home_address` for the
    first event with a location. Events without a location get `None`.

    Note: `mobility.get_commute` uses current traffic. Tomorrow-morning
    predicted traffic would need an extension to that tool that mirrors
    `mobility.get_commute_options`'s `departure_time` param. V1 ships
    with current-traffic durations + a clear label in the UI.
    """
    results: list[Optional[dict[str, Any]]] = []
    prev_location: Optional[str] = None

    for event in events:
        location = event.get("location")
        if not location:
            results.append(None)
            continue

        origin = prev_location or home_address
        if not origin:
            # No home_address configured and no previous event — skip rather
            # than send "Home" as a literal string to the geocoder.
            logger.warning(
                f"Skipping commute for event {event.get('id')} — no origin available "
                "(HOME_ADDRESS not set and no previous located event)"
            )
            results.append(None)
            prev_location = location
            continue

        try:
            commute_data = await client.get_commute(origin, location, mode="driving")
        except Exception as e:
            logger.warning(f"Commute lookup failed for event {event.get('id')}: {e}")
            results.append(None)
            prev_location = location
            continue

        duration_min = commute_data.get("duration_minutes")
        leave_by: Optional[str] = None
        start_time_iso = event.get("start_time", "")
        if start_time_iso and not event.get("all_day") and duration_min is not None:
            try:
                start_dt = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
                leave_by = (start_dt - timedelta(minutes=duration_min)).isoformat()
            except ValueError as parse_err:
                logger.warning(f"Could not parse start_time for leave_by: {parse_err}")

        results.append({
            "origin": origin,
            "destination": location,
            "duration_minutes": duration_min,
            "distance_miles": commute_data.get("distance_miles"),
            "traffic_status": commute_data.get("traffic_status"),
            "leave_by": leave_by,
        })
        prev_location = location

    return results


def _filter_todos_due_on(items: list[dict[str, Any]], target_date: str) -> list[dict[str, Any]]:
    """Items whose due_date falls on target_date (YYYY-MM-DD)."""
    matching: list[dict[str, Any]] = []
    for item in items:
        due = item.get("due_date")
        if isinstance(due, str) and due.startswith(target_date):
            matching.append(item)
    return matching


def _compute_flags(events_with_commute: list[dict[str, Any]]) -> list[str]:
    """Surface noteworthy patterns: tight back-to-back transitions where the
    gap between two events is smaller than the commute between their locations.
    """
    flags: list[str] = []
    for i in range(1, len(events_with_commute)):
        prev = events_with_commute[i - 1]
        curr = events_with_commute[i]
        commute = curr.get("commute")
        if not commute or commute.get("duration_minutes") is None:
            continue
        try:
            prev_end = datetime.fromisoformat(prev.get("end_time", "").replace("Z", "+00:00"))
            curr_start = datetime.fromisoformat(curr.get("start_time", "").replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        gap_minutes = (curr_start - prev_end).total_seconds() / 60
        commute_min = commute["duration_minutes"]
        if gap_minutes < commute_min:
            flags.append(
                f"Tight transition: {curr.get('title', 'Event')} starts "
                f"{int(gap_minutes)} min after {prev.get('title', 'previous event')} "
                f"ends, but commute is {commute_min} min."
            )
    return flags


def resolve_tomorrow_date(timezone_name: str) -> str:
    """User-local tomorrow as YYYY-MM-DD. Single-user-app heuristic."""
    tz = ZoneInfo(timezone_name)
    return (datetime.now(tz) + timedelta(days=1)).strftime("%Y-%m-%d")


async def build_tomorrow_briefing(
    tomorrow_date: str,
    client: Optional[MCPClient] = None,
) -> dict[str, Any]:
    """Structured briefing for `tomorrow_date` (YYYY-MM-DD)."""
    settings = get_settings()
    client = client or MCPClient()

    weather, calendar, todos = await asyncio.gather(
        client.get_weather(settings.user_location, when="tomorrow"),
        client.get_calendar_events(tomorrow_date),
        client.get_todos(),
        return_exceptions=True,
    )

    weather_data: dict[str, Any] = {} if isinstance(weather, BaseException) else weather
    if isinstance(weather, BaseException):
        logger.warning(f"Weather fetch failed: {weather}")

    if isinstance(calendar, BaseException):
        logger.warning(f"Calendar fetch failed: {calendar}")
        events: list[dict[str, Any]] = []
        calendar_error: Optional[str] = str(calendar)
    else:
        events = calendar.get("events", [])
        calendar_error = None

    if isinstance(todos, BaseException):
        logger.warning(f"Todos fetch failed: {todos}")
        prep_todos: list[dict[str, Any]] = []
    else:
        prep_todos = _filter_todos_due_on(todos.get("items", []), tomorrow_date)

    commutes = await compute_per_event_commute(events, settings.home_address, client)
    events_with_commute = [
        {**event, "commute": commute} for event, commute in zip(events, commutes)
    ]

    return {
        "date": tomorrow_date,
        "weather": weather_data,
        "events": events_with_commute,
        "prep_todos": prep_todos,
        "flags": _compute_flags(events_with_commute),
        "calendar_error": calendar_error,
    }
