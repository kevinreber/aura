"""Tests for the weekend orchestrator tools."""

import pytest

from mcp_server.tools.weekend import WeekendTools
from mcp_server.schemas.weekend import (
    ActivityType,
    ConcertSearchInput,
    ItineraryInput,
    POICategory,
    TicketStatus,
    TrailDifficulty,
    TrailSearchInput,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the cache between tests so cached mock results don't bleed between cases."""
    import mcp_server.utils.cache as cache_module

    cache_module._cache_service = None
    yield
    cache_module._cache_service = None


@pytest.fixture
def weekend_tools():
    return WeekendTools()


class TestGetTrails:
    """Tests for weekend.get_trails (mock mode)."""

    @pytest.mark.asyncio
    async def test_returns_mock_trails_without_api_key(self, weekend_tools):
        result = await weekend_tools.get_trails(
            TrailSearchInput(location="Boulder, CO", activity_type=ActivityType.HIKING)
        )

        assert result.source == "mock"
        assert result.cached is False
        assert len(result.trails) > 0
        # Mock trails should be tagged with the requested location
        assert all("Boulder, CO" in t.location for t in result.trails)

    @pytest.mark.asyncio
    async def test_filters_by_max_distance(self, weekend_tools):
        result = await weekend_tools.get_trails(
            TrailSearchInput(location="San Francisco, CA", max_distance_miles=5)
        )

        assert all(t.distance_miles <= 5 for t in result.trails)

    @pytest.mark.asyncio
    async def test_filters_by_difficulty(self, weekend_tools):
        result = await weekend_tools.get_trails(
            TrailSearchInput(location="Denver, CO", difficulty=TrailDifficulty.EASY)
        )

        assert len(result.trails) > 0
        assert all(t.difficulty == TrailDifficulty.EASY for t in result.trails)

    @pytest.mark.asyncio
    async def test_second_call_is_cached(self, weekend_tools):
        first = await weekend_tools.get_trails(
            TrailSearchInput(location="Tahoe, CA")
        )
        second = await weekend_tools.get_trails(
            TrailSearchInput(location="Tahoe, CA")
        )

        assert first.cached is False
        assert second.cached is True
        assert len(first.trails) == len(second.trails)


class TestGetConcerts:
    """Tests for weekend.get_concerts (mock mode)."""

    @pytest.mark.asyncio
    async def test_returns_mock_concerts_without_api_key(self, weekend_tools):
        result = await weekend_tools.get_concerts(
            ConcertSearchInput(location="San Francisco, CA")
        )

        assert result.source == "mock"
        assert result.cached is False
        assert len(result.events) > 0

    @pytest.mark.asyncio
    async def test_filters_by_artist(self, weekend_tools):
        result = await weekend_tools.get_concerts(
            ConcertSearchInput(location="San Francisco, CA", artists=["Tycho"])
        )

        assert len(result.events) > 0
        assert all("Tycho" in e.artist for e in result.events)

    @pytest.mark.asyncio
    async def test_unknown_artist_returns_no_events(self, weekend_tools):
        result = await weekend_tools.get_concerts(
            ConcertSearchInput(location="Anywhere", artists=["DefinitelyNotAnArtist"])
        )

        assert result.events == []
        # Empty result is not an error
        assert result.error is None

    @pytest.mark.asyncio
    async def test_includes_varied_ticket_statuses(self, weekend_tools):
        result = await weekend_tools.get_concerts(
            ConcertSearchInput(location="Denver, CO")
        )

        statuses = {e.ticket_status for e in result.events}
        # The mock fixture includes available, sold_out, and unknown — agent should
        # see this variety so it can make recommendations accordingly.
        assert TicketStatus.AVAILABLE in statuses
        assert TicketStatus.SOLD_OUT in statuses


class TestGenerateItinerary:
    """Tests for weekend.generate_itinerary (mock mode)."""

    @pytest.mark.asyncio
    async def test_returns_mock_itinerary_without_api_key(self, weekend_tools):
        result = await weekend_tools.generate_itinerary(
            ItineraryInput(destination="Denver, CO", duration_days=3)
        )

        assert result.source == "mock"
        assert result.destination == "Denver, CO"
        assert result.duration_days == 3
        assert len(result.points_of_interest) > 0
        # No base_location → no transit estimates
        assert result.transit_estimates is None

    @pytest.mark.asyncio
    async def test_filters_pois_by_interests(self, weekend_tools):
        result = await weekend_tools.generate_itinerary(
            ItineraryInput(
                destination="Denver, CO",
                duration_days=2,
                interests=["food"],
            )
        )

        assert len(result.points_of_interest) > 0
        assert all(
            poi.category == POICategory.RESTAURANT
            for poi in result.points_of_interest
        )

    @pytest.mark.asyncio
    async def test_caps_results_by_duration(self, weekend_tools):
        result = await weekend_tools.generate_itinerary(
            ItineraryInput(destination="Denver, CO", duration_days=1)
        )

        # Cap is duration_days * 8 — for 1 day, max 8 POIs
        assert len(result.points_of_interest) <= 8

    @pytest.mark.asyncio
    async def test_includes_transit_when_base_location_set(self, weekend_tools):
        result = await weekend_tools.generate_itinerary(
            ItineraryInput(
                destination="Denver, CO",
                duration_days=2,
                base_location="123 Main St, Denver, CO",
            )
        )

        assert result.transit_estimates is not None
        assert len(result.transit_estimates) > 0
        for estimate in result.transit_estimates:
            assert estimate.from_location == "123 Main St, Denver, CO"
            assert estimate.drive_time_min > 0
            assert estimate.distance_miles > 0
