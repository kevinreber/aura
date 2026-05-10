"""Weekend orchestrator tools: trail scouting, concert lookup, itinerary generation.

Each method has a real-provider path AND a mock fallback. The real path runs when the
relevant API key is configured (`google_maps_api_key` for trails + itineraries,
`ticketmaster_api_key` for concerts). When keys are missing, we serve from the
JSON fixtures in `tests/fixtures/weekend/` so dev mode + tests stay deterministic.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
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
from ..utils.http_client import HTTPClient
from ..utils.logging import get_logger, log_tool_call

logger = get_logger("weekend_tool")


# Mock fixtures live in tests/fixtures/weekend/ so they're shared between dev mode + tests.
_FIXTURES_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "weekend"
)


# Map our ActivityType to Google Places (New) place types.
# Google's taxonomy is limited — running/cycling don't have first-class types,
# so we route them to "park" which usually contains the relevant trails.
_ACTIVITY_TO_PLACE_TYPES = {
    ActivityType.HIKING: ["hiking_area", "park"],
    ActivityType.RUNNING: ["park"],
    ActivityType.CYCLING: ["park"],
    ActivityType.ALL: ["park", "hiking_area"],
}

# Map free-text user interests to (POICategory, list of Google place types).
_INTEREST_TO_CATEGORY: Dict[str, tuple] = {
    "outdoors": (POICategory.OUTDOORS, ["park", "hiking_area"]),
    "hiking": (POICategory.OUTDOORS, ["park", "hiking_area"]),
    "live music": (POICategory.NIGHTLIFE, ["night_club", "bar"]),
    "music": (POICategory.NIGHTLIFE, ["night_club", "bar"]),
    "nightlife": (POICategory.NIGHTLIFE, ["night_club", "bar"]),
    "food": (POICategory.RESTAURANT, ["restaurant", "cafe"]),
    "restaurants": (POICategory.RESTAURANT, ["restaurant", "cafe"]),
    "craft beer": (POICategory.NIGHTLIFE, ["bar"]),
    "attractions": (POICategory.ATTRACTION, ["tourist_attraction", "museum"]),
}


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
        self.places_base_url = "https://places.googleapis.com/v1/places:searchNearby"
        self.geocoding_base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.directions_base_url = "https://maps.googleapis.com/maps/api/directions/json"

    # ==================== Geocoding helper ====================

    async def _geocode_location(self, location: str) -> Optional[Dict[str, float]]:
        """Convert a location string to lat/lng.

        Tries Google Geocoding first; falls back to Nominatim (OpenStreetMap)
        if Google's API isn't enabled or returns no results. Both results are
        cached for 7 days (coordinates don't change). Returns None only when
        every provider fails — callers then fall back to mock data.
        """
        cache = await get_cache_service()
        cache_key = generate_cache_key("weekend_geocode", location.lower())
        cached = await cache.get(cache_key)
        if cached:
            return cached

        # Try Google Geocoding first (faster, more accurate than Nominatim for
        # disambiguated queries like "Boulder, CO").
        coords = await self._geocode_google(location)
        if coords is None:
            # Fall back to Nominatim — free, no key needed, but rate-limited.
            coords = await self._geocode_nominatim(location)

        if coords is not None:
            await cache.set(cache_key, coords, CacheTTL.WEATHER_GEOCODING)  # 7 days

        return coords

    async def _geocode_google(self, location: str) -> Optional[Dict[str, float]]:
        """Geocode via Google Geocoding API. Returns None if the API isn't
        enabled, the key isn't configured, or no results are found."""
        if not self.settings.google_maps_api_key:
            return None

        try:
            async with HTTPClient() as client:
                response = await client.get(
                    self.geocoding_base_url,
                    params={"address": location, "key": self.settings.google_maps_api_key},
                )
                data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.info(
                    f"Google Geocoding returned status={data.get('status')} "
                    f"for '{location}' — will try Nominatim fallback"
                )
                return None

            geo = data["results"][0]["geometry"]["location"]
            return {"lat": geo["lat"], "lng": geo["lng"]}

        except Exception as e:
            logger.warning(f"Google Geocoding error for '{location}': {e}")
            return None

    async def _geocode_nominatim(self, location: str) -> Optional[Dict[str, float]]:
        """Geocode via OpenStreetMap Nominatim. Free, no key, no GCP enablement.

        Polite usage policy requires a meaningful User-Agent header — Nominatim
        will block default httpx user agents.
        """
        try:
            async with HTTPClient() as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": location, "format": "json", "limit": 1},
                    headers={"User-Agent": "Aura-Weekend-Orchestrator/1.0"},
                )
                data = response.json()

            if not data:
                logger.warning(f"Nominatim returned no results for '{location}'")
                return None

            return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}

        except Exception as e:
            logger.warning(f"Nominatim error for '{location}': {e}")
            return None

    # ==================== get_trails ====================

    async def get_trails(self, input_data: TrailSearchInput) -> TrailSearchOutput:
        """Find trails near a location.

        v1 strategy: Google Places (New) searchNearby filtered by activity type.
        Note: Google Places returns parks/hiking areas but no trail-specific data
        like distance or difficulty — those fields are None for this provider.
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
                trails = await self._fetch_real_trails(input_data)
                source = "google_places"
                if not trails:
                    logger.info(
                        "Google Places returned no trails — falling back to mock fixtures"
                    )
                    trails = self._mock_trails(input_data)
                    source = "mock_fallback"

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

    async def _fetch_real_trails(self, input_data: TrailSearchInput) -> List[Trail]:
        """Call Google Places (New) searchNearby and map results to Trail schema."""
        coords = await self._geocode_location(input_data.location)
        if not coords:
            return []

        place_types = _ACTIVITY_TO_PLACE_TYPES.get(input_data.activity_type, ["park"])
        radius_meters = min(input_data.max_distance_miles * 1609, 50000)  # API max is 50km

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_maps_api_key,
            "X-Goog-FieldMask": "places.displayName,places.rating,places.formattedAddress,places.googleMapsUri",
        }
        body = {
            "includedTypes": place_types,
            "maxResultCount": 10,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": coords["lat"], "longitude": coords["lng"]},
                    "radius": radius_meters,
                }
            },
        }

        async with HTTPClient() as client:
            response = await client.post(self.places_base_url, json=body, headers=headers)
            data = response.json()

        trails: List[Trail] = []
        for place in data.get("places", []):
            trails.append(
                Trail(
                    name=place.get("displayName", {}).get("text", "Unnamed"),
                    distance_miles=None,  # Not available from Google Places
                    elevation_gain_ft=None,
                    difficulty=None,
                    rating=place.get("rating"),
                    url=place.get("googleMapsUri"),
                    location=place.get("formattedAddress", input_data.location),
                )
            )
        return trails

    def _mock_trails(self, input_data: TrailSearchInput) -> List[Trail]:
        """Build a list of mock trails filtered by the input criteria."""
        raw = _load_fixture("mock_trails.json")
        trails: List[Trail] = []
        for entry in raw:
            entry["location"] = entry["location"].format(location=input_data.location)
            trail = Trail(**entry)

            # Distance filter only applies when the provider gave us a value.
            if (
                trail.distance_miles is not None
                and trail.distance_miles > input_data.max_distance_miles
            ):
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
        """Find concerts in a location for tracked artists or all events in radius.

        v1 strategy: Ticketmaster Discovery API when `ticketmaster_api_key` is set;
        otherwise mock data. If `artists` provided, search per-artist via the
        `keyword` parameter; else search by city + classificationName=music.
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
                events = await self._fetch_real_concerts(input_data)
                source = "ticketmaster"
                if not events:
                    # No events found is a valid result — don't fall back to mocks
                    # since "no concerts" is meaningful information.
                    logger.info("Ticketmaster returned 0 events for this query")

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

    async def _fetch_real_concerts(
        self, input_data: ConcertSearchInput
    ) -> List[ConcertEvent]:
        """Call Ticketmaster Discovery API and map results to ConcertEvent schema."""
        # Date range: from now to date_range_days ahead, ISO 8601 in UTC.
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=input_data.date_range_days)
        start_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

        # The Discovery API accepts city directly. Strip state code if present
        # (e.g. "San Francisco, CA" → "San Francisco") since it's a separate filter.
        city = input_data.location.split(",")[0].strip()

        common_params = {
            "apikey": self.settings.ticketmaster_api_key,
            "classificationName": "music",
            "city": city,
            "radius": input_data.radius_miles,
            "unit": "miles",
            "startDateTime": start_str,
            "endDateTime": end_str,
            "size": 20,
        }

        # If artists provided, query once per artist via `keyword`. Otherwise one
        # query for all music events in the area.
        artist_queries = input_data.artists or [None]
        all_events: List[ConcertEvent] = []
        seen_event_ids: set = set()

        async with HTTPClient() as client:
            for artist in artist_queries:
                params = dict(common_params)
                if artist:
                    params["keyword"] = artist

                try:
                    response = await client.get(
                        f"{self.ticketmaster_base_url}/events.json", params=params
                    )
                    data = response.json()
                except Exception as e:
                    logger.warning(f"Ticketmaster query failed for artist={artist}: {e}")
                    continue

                events_raw = data.get("_embedded", {}).get("events", [])
                for ev in events_raw:
                    if ev.get("id") in seen_event_ids:
                        continue
                    seen_event_ids.add(ev["id"])

                    venue = "Unknown venue"
                    venues = ev.get("_embedded", {}).get("venues", [])
                    if venues:
                        venue = venues[0].get("name", venue)

                    # Artist name comes from attractions; fall back to event name.
                    artist_name = ev.get("name", "TBA")
                    attractions = ev.get("_embedded", {}).get("attractions", [])
                    if attractions:
                        artist_name = attractions[0].get("name", artist_name)

                    dates = ev.get("dates", {})
                    local_date = dates.get("start", {}).get("localDate")
                    local_time = dates.get("start", {}).get("localTime")

                    # Map sales status to our TicketStatus enum.
                    sale_status = ev.get("dates", {}).get("status", {}).get("code", "")
                    if sale_status == "onsale":
                        ticket_status = TicketStatus.AVAILABLE
                    elif sale_status in ("offsale", "cancelled"):
                        ticket_status = TicketStatus.SOLD_OUT
                    else:
                        ticket_status = TicketStatus.UNKNOWN

                    public_sales = ev.get("sales", {}).get("public", {})
                    on_sale_date = public_sales.get("startDateTime", "")[:10] or None

                    all_events.append(
                        ConcertEvent(
                            artist=artist_name,
                            venue=venue,
                            date=local_date or "",
                            time=local_time,
                            ticket_url=ev.get("url"),
                            ticket_status=ticket_status,
                            on_sale_date=on_sale_date,
                        )
                    )

        return all_events

    def _mock_concerts(self, input_data: ConcertSearchInput) -> List[ConcertEvent]:
        """Build a list of mock concerts filtered by artists if specified."""
        raw = _load_fixture("mock_concerts.json")
        events: List[ConcertEvent] = []
        for entry in raw:
            event = ConcertEvent(**entry)
            if input_data.artists:
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
        the day-by-day narrative.
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
                pois = await self._fetch_real_pois(input_data)
                if pois and input_data.base_location:
                    transit = await self._fetch_real_transit(input_data, pois)
                else:
                    transit = None
                source = "google_places"
                if not pois:
                    logger.info(
                        "Google Places returned no POIs — falling back to mock fixtures"
                    )
                    pois = self._mock_pois(input_data)
                    transit = self._mock_transit(input_data, pois) if input_data.base_location else None
                    source = "mock_fallback"

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

    async def _fetch_real_pois(self, input_data: ItineraryInput) -> List[POI]:
        """Call Google Places (New) per interest and merge results into POI list.

        Cap per-category to keep API cost bounded — total POIs ≤ duration_days * 8.
        """
        coords = await self._geocode_location(input_data.destination)
        if not coords:
            return []

        # Map user interests to (category, place_types); skip unknown interests.
        category_queries: Dict[POICategory, List[str]] = {}
        for interest in input_data.interests:
            mapping = _INTEREST_TO_CATEGORY.get(interest.lower())
            if not mapping:
                continue
            category, place_types = mapping
            # Merge place types if the same category appears multiple times.
            existing = category_queries.get(category, [])
            for t in place_types:
                if t not in existing:
                    existing.append(t)
            category_queries[category] = existing

        # If no recognized interests, default to a broad search.
        if not category_queries:
            category_queries = {POICategory.ATTRACTION: ["tourist_attraction"]}

        radius_meters = 25000  # 25km — cover the destination metro area
        per_category_cap = max(4, (input_data.duration_days * 8) // len(category_queries))

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_maps_api_key,
            "X-Goog-FieldMask": "places.displayName,places.rating,places.formattedAddress,places.priceLevel,places.editorialSummary",
        }

        all_pois: List[POI] = []
        seen_addresses: set = set()

        async with HTTPClient() as client:
            for category, place_types in category_queries.items():
                body = {
                    "includedTypes": place_types,
                    "maxResultCount": per_category_cap,
                    "locationRestriction": {
                        "circle": {
                            "center": {
                                "latitude": coords["lat"],
                                "longitude": coords["lng"],
                            },
                            "radius": radius_meters,
                        }
                    },
                }
                try:
                    response = await client.post(
                        self.places_base_url, json=body, headers=headers
                    )
                    data = response.json()
                except Exception as e:
                    logger.warning(f"Places query failed for {category.value}: {e}")
                    continue

                for place in data.get("places", []):
                    addr = place.get("formattedAddress", "")
                    if addr in seen_addresses:
                        continue
                    seen_addresses.add(addr)

                    # Map Google's PRICE_LEVEL_INEXPENSIVE etc. to 1-4 integer.
                    price_str = place.get("priceLevel", "")
                    price_map = {
                        "PRICE_LEVEL_FREE": 1,
                        "PRICE_LEVEL_INEXPENSIVE": 1,
                        "PRICE_LEVEL_MODERATE": 2,
                        "PRICE_LEVEL_EXPENSIVE": 3,
                        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
                    }
                    price_level = price_map.get(price_str)

                    summary = place.get("editorialSummary", {}).get("text") if isinstance(
                        place.get("editorialSummary"), dict
                    ) else None

                    all_pois.append(
                        POI(
                            name=place.get("displayName", {}).get("text", "Unnamed"),
                            category=category,
                            rating=place.get("rating"),
                            address=addr or input_data.destination,
                            hours=None,  # Would require Place Details call (extra cost)
                            price_level=price_level,
                            description=summary,
                        )
                    )

        return all_pois[: input_data.duration_days * 8]

    async def _fetch_real_transit(
        self, input_data: ItineraryInput, pois: List[POI]
    ) -> Optional[List[TransitEstimate]]:
        """Call Google Directions API for drive-time estimates from base_location to top POIs."""
        if not input_data.base_location:
            return None

        estimates: List[TransitEstimate] = []
        async with HTTPClient() as client:
            for poi in pois[:6]:  # Cap at 6 to limit Directions API cost
                try:
                    response = await client.get(
                        self.directions_base_url,
                        params={
                            "origin": input_data.base_location,
                            "destination": poi.address,
                            "mode": "driving",
                            "key": self.settings.google_maps_api_key,
                        },
                    )
                    data = response.json()
                except Exception as e:
                    logger.warning(f"Directions query failed for {poi.address}: {e}")
                    continue

                if data.get("status") != "OK" or not data.get("routes"):
                    continue

                leg = data["routes"][0]["legs"][0]
                duration_min = round(leg["duration"]["value"] / 60)
                distance_miles = round(leg["distance"]["value"] / 1609, 1)

                estimates.append(
                    TransitEstimate(
                        from_location=input_data.base_location,
                        to_location=poi.address,
                        drive_time_min=duration_min,
                        distance_miles=distance_miles,
                    )
                )
        return estimates if estimates else None

    def _mock_pois(self, input_data: ItineraryInput) -> List[POI]:
        """Build mock POIs filtered loosely by interest tags."""
        raw = _load_fixture("mock_pois.json")
        wanted_categories = {
            _INTEREST_TO_CATEGORY[i.lower()][0]
            for i in input_data.interests
            if i.lower() in _INTEREST_TO_CATEGORY
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
