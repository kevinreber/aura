"""Weekend orchestrator tools: trail scouting, concert lookup, itinerary generation.

Phase 1 ships with mock-data fallbacks for every method. Real provider integrations
(Ticketmaster Discovery API for concerts, Google Places for trails + POIs) are stubbed
and called only when the corresponding API key is configured. This keeps Phase 1
testable end-to-end without API keys and mirrors the pattern used by `weather.py`.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..schemas.weekend import (
    ActivityType,
    ConcertEvent,
    ConcertSearchInput,
    ConcertSearchOutput,
    ItineraryInput,
    ItineraryOutput,
    POI,
    POICategory,
    TicketStatus,
    Trail,
    TrailDifficulty,
    TrailSearchInput,
    TrailSearchOutput,
    TransitEstimate,
)
from ..utils.cache import CacheTTL, generate_cache_key, get_cache_service
from ..utils.logging import get_logger, log_tool_call

logger = get_logger("weekend_tool")


# Mock fixtures live in tests/fixtures/weekend/ so they're shared between dev mode + tests.
_FIXTURES_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "weekend"
)


def _load_fixture(filename: str) -> List[Dict[str, Any]]:
    """Load a JSON fixture from tests/fixtures/weekend/."""
    path = _FIXTURES_DIR / filename
    if not path.exists():
        logger.warning(f"Mock fixture not found at {path}, returning empty list")
        return []
    with path.open() as f:
        return json.load(f)


class WeekendTools:
    """Weekend orchestrator tools — trail scouting, concert lookup, itinerary generation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ticketmaster_base_url = "https://app.ticketmaster.com/discovery/v2"
        self.places_base_url = "https://maps.googleapis.com/maps/api/place"
        self.directions_base_url = "https://maps.googleapis.com/maps/api/directions/json"

    # ==================== get_trails ====================

    async def get_trails(self, input_data: TrailSearchInput) -> TrailSearchOutput:
        """Find trails near a location.

        v1 strategy: Google Places (already integrated). Outdooractive is an optional
        upgrade once the user has an API key — for now we skip it and use Places only.
        Falls back to mock fixtures when no `google_maps_api_key` is configured.
        """
        start_time = asyncio.get_event_loop().time()
        try:
            logger.info(
                f"Getting trails near {input_data.location} "
                f"(activity={input_data.activity_type.value}, "
                f"max_distance={input_data.max_distance_miles}mi)"
            )

            cache = await get_cache_service()
            cache_key = generate_cache_key(
                "weekend_trails",
                input_data.location.lower(),
                input_data.activity_type.value,
                input_data.max_distance_miles,
                input_data.difficulty.value if input_data.difficulty else "any",
            )
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(f"Trail cache hit for {input_data.location}")
                cached["cached"] = True
                return TrailSearchOutput(**cached)

            if not self.settings.google_maps_api_key:
                logger.warning("No google_maps_api_key configured, returning mock trails")
                trails = self._mock_trails(input_data)
                source = "mock"
            else:
                # Real Google Places integration goes here in a follow-up commit.
                # For Phase 1 we always return mocks — flip this branch on once we
                # validate the response shape against the live API.
                logger.info(
                    "Google Places trail provider not yet implemented in Phase 1, "
                    "returning mock trails"
                )
                trails = self._mock_trails(input_data)
                source = "mock"

            result = TrailSearchOutput(trails=trails, source=source, cached=False)
            await cache.set(cache_key, result.model_dump(), CacheTTL.WEEKEND_TRAILS)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("weekend.get_trails", input_data.model_dump(), duration_ms)
            return result

        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("weekend.get_trails", input_data.model_dump(), duration_ms)
            logger.error(f"Error getting trails: {e}")
            return TrailSearchOutput(
                trails=[],
                source="error",
                cached=False,
                error=f"Trail data temporarily unavailable: {e}",
            )

    def _mock_trails(self, input_data: TrailSearchInput) -> List[Trail]:
        """Build a list of mock trails filtered by the input criteria."""
        raw = _load_fixture("mock_trails.json")
        trails: List[Trail] = []
        for entry in raw:
            entry["location"] = entry["location"].format(location=input_data.location)
            trail = Trail(**entry)

            if trail.distance_miles > input_data.max_distance_miles:
                continue
            if (
                input_data.difficulty is not None
                and trail.difficulty != input_data.difficulty
            ):
                continue
            trails.append(trail)
        return trails

    # ==================== get_concerts ====================

    async def get_concerts(self, input_data: ConcertSearchInput) -> ConcertSearchOutput:
        """Find concerts in a location for tracked artists or all artists in radius.

        v1 strategy: Ticketmaster Discovery API when `ticketmaster_api_key` is set; otherwise mock data.
        """
        start_time = asyncio.get_event_loop().time()
        try:
            logger.info(
                f"Getting concerts near {input_data.location} "
                f"(artists={input_data.artists}, radius={input_data.radius_miles}mi, "
                f"days={input_data.date_range_days})"
            )

            cache = await get_cache_service()
            artists_key = ",".join(sorted(input_data.artists)) if input_data.artists else "all"
            cache_key = generate_cache_key(
                "weekend_concerts",
                input_data.location.lower(),
                artists_key,
                input_data.radius_miles,
                input_data.date_range_days,
            )
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(f"Concert cache hit for {input_data.location}")
                cached["cached"] = True
                return ConcertSearchOutput(**cached)

            if not self.settings.ticketmaster_api_key:
                logger.warning("No ticketmaster_api_key configured, returning mock concerts")
                events = self._mock_concerts(input_data)
                source = "mock"
            else:
                # Real Ticketmaster Discovery API integration goes here in a follow-up commit.
                logger.info(
                    "Ticketmaster provider not yet implemented in Phase 1, "
                    "returning mock concerts"
                )
                events = self._mock_concerts(input_data)
                source = "mock"

            result = ConcertSearchOutput(events=events, source=source, cached=False)
            await cache.set(cache_key, result.model_dump(), CacheTTL.WEEKEND_CONCERTS)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("weekend.get_concerts", input_data.model_dump(), duration_ms)
            return result

        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("weekend.get_concerts", input_data.model_dump(), duration_ms)
            logger.error(f"Error getting concerts: {e}")
            return ConcertSearchOutput(
                events=[],
                source="error",
                cached=False,
                error=f"Concert data temporarily unavailable: {e}",
            )

    def _mock_concerts(self, input_data: ConcertSearchInput) -> List[ConcertEvent]:
        """Build a list of mock concerts filtered by artists if specified."""
        raw = _load_fixture("mock_concerts.json")
        events: List[ConcertEvent] = []
        for entry in raw:
            event = ConcertEvent(**entry)
            if input_data.artists:
                # Match by substring (case-insensitive) so "Tycho" matches "Mock Artist: Tycho".
                if not any(
                    a.lower() in event.artist.lower() for a in input_data.artists
                ):
                    continue
            events.append(event)
        return events

    # ==================== generate_itinerary ====================

    async def generate_itinerary(
        self, input_data: ItineraryInput
    ) -> ItineraryOutput:
        """Generate POIs and (optionally) transit estimates for a multi-day trip.

        Returns raw POI + transit data — the agent's LLM is responsible for stitching
        the day-by-day narrative. v1 uses mock fixtures.
        """
        start_time = asyncio.get_event_loop().time()
        try:
            logger.info(
                f"Generating itinerary for {input_data.destination} "
                f"({input_data.duration_days}d, interests={input_data.interests})"
            )

            cache = await get_cache_service()
            interests_key = ",".join(sorted(input_data.interests)) if input_data.interests else "any"
            cache_key = generate_cache_key(
                "weekend_itinerary",
                input_data.destination.lower(),
                input_data.duration_days,
                interests_key,
                (input_data.base_location or "none").lower(),
            )
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(f"Itinerary cache hit for {input_data.destination}")
                cached["cached"] = True
                return ItineraryOutput(**cached)

            if not self.settings.google_maps_api_key:
                logger.warning(
                    "No google_maps_api_key configured, returning mock itinerary"
                )
                pois = self._mock_pois(input_data)
                transit = self._mock_transit(input_data, pois) if input_data.base_location else None
                source = "mock"
            else:
                logger.info(
                    "Google Places itinerary provider not yet implemented in Phase 1, "
                    "returning mock itinerary"
                )
                pois = self._mock_pois(input_data)
                transit = self._mock_transit(input_data, pois) if input_data.base_location else None
                source = "mock"

            result = ItineraryOutput(
                destination=input_data.destination,
                duration_days=input_data.duration_days,
                points_of_interest=pois,
                transit_estimates=transit,
                source=source,
                cached=False,
            )
            await cache.set(cache_key, result.model_dump(), CacheTTL.WEEKEND_POIS)

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call(
                "weekend.generate_itinerary", input_data.model_dump(), duration_ms
            )
            return result

        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call(
                "weekend.generate_itinerary", input_data.model_dump(), duration_ms
            )
            logger.error(f"Error generating itinerary: {e}")
            return ItineraryOutput(
                destination=input_data.destination,
                duration_days=input_data.duration_days,
                points_of_interest=[],
                transit_estimates=None,
                source="error",
                cached=False,
                error=f"Itinerary generation temporarily unavailable: {e}",
            )

    def _mock_pois(self, input_data: ItineraryInput) -> List[POI]:
        """Build mock POIs filtered loosely by interest tags."""
        raw = _load_fixture("mock_pois.json")
        # Map free-text interests onto our POICategory enum.
        interest_to_category = {
            "outdoors": POICategory.OUTDOORS,
            "hiking": POICategory.OUTDOORS,
            "live music": POICategory.NIGHTLIFE,
            "music": POICategory.NIGHTLIFE,
            "nightlife": POICategory.NIGHTLIFE,
            "food": POICategory.RESTAURANT,
            "restaurants": POICategory.RESTAURANT,
            "craft beer": POICategory.NIGHTLIFE,
        }
        wanted_categories = {
            interest_to_category[i.lower()]
            for i in input_data.interests
            if i.lower() in interest_to_category
        }

        pois: List[POI] = []
        for entry in raw:
            entry["address"] = entry["address"].format(destination=input_data.destination)
            poi = POI(**entry)
            if wanted_categories and poi.category not in wanted_categories:
                continue
            pois.append(poi)

        # Cap at duration_days * 8, matching the cost-control note in the spec.
        return pois[: input_data.duration_days * 8]

    def _mock_transit(
        self, input_data: ItineraryInput, pois: List[POI]
    ) -> Optional[List[TransitEstimate]]:
        """Generate mock transit estimates from base_location to each POI."""
        if not input_data.base_location:
            return None
        # Deterministic-ish synthetic distances based on POI index.
        estimates: List[TransitEstimate] = []
        for i, poi in enumerate(pois[:6]):  # Cap at 6 to avoid noise
            estimates.append(
                TransitEstimate(
                    from_location=input_data.base_location,
                    to_location=poi.address,
                    drive_time_min=8 + i * 5,
                    distance_miles=round(2.5 + i * 1.7, 1),
                )
            )
        return estimates
