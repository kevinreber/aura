"""Tests for the mobility tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from mcp_server.tools.mobility import MobilityTool
from mcp_server.schemas.mobility import (
    MobilityInput, MobilityOutput, TransportMode,
    CommuteInput, CommuteOutput, CommuteDirection,
    ShuttleScheduleInput, ShuttleScheduleOutput, ShuttleStop
)


class TestMobilityTool:
    """Test the MobilityTool class."""

    @pytest.fixture
    def mobility_tool(self):
        """Create a MobilityTool instance."""
        return MobilityTool()

    @pytest.mark.asyncio
    async def test_get_commute_mock_data(self, mobility_tool):
        """Test getting commute with mock data (no API key)."""
        input_data = MobilityInput(
            origin="San Francisco, CA",
            destination="Mountain View, CA",
            mode=TransportMode.DRIVING
        )

        result = await mobility_tool.get_commute(input_data)

        assert isinstance(result, MobilityOutput)
        assert result.origin == "San Francisco, CA"
        assert result.destination == "Mountain View, CA"
        assert result.mode == TransportMode.DRIVING
        assert isinstance(result.duration_minutes, int)
        assert isinstance(result.distance_miles, float)
        assert result.route_summary is not None
        assert result.traffic_status is not None

    @pytest.mark.asyncio
    async def test_get_commute_transit_mode(self, mobility_tool):
        """Test getting commute with transit mode."""
        input_data = MobilityInput(
            origin="Oakland, CA",
            destination="San Jose, CA",
            mode=TransportMode.TRANSIT
        )

        result = await mobility_tool.get_commute(input_data)

        assert result.mode == TransportMode.TRANSIT
        assert result.traffic_status == "N/A"  # Transit doesn't have traffic

    @pytest.mark.asyncio
    async def test_get_commute_bicycling_mode(self, mobility_tool):
        """Test getting commute with bicycling mode."""
        input_data = MobilityInput(
            origin="Palo Alto, CA",
            destination="Menlo Park, CA",
            mode=TransportMode.BICYCLING
        )

        result = await mobility_tool.get_commute(input_data)

        assert result.mode == TransportMode.BICYCLING

    @pytest.mark.asyncio
    async def test_get_commute_walking_mode(self, mobility_tool):
        """Test getting commute with walking mode."""
        input_data = MobilityInput(
            origin="Downtown SF",
            destination="Union Square, SF",
            mode=TransportMode.WALKING
        )

        result = await mobility_tool.get_commute(input_data)

        assert result.mode == TransportMode.WALKING

    def test_mock_directions_data_structure(self, mobility_tool):
        """Test that mock directions data has correct structure."""
        mock_data = mobility_tool._get_mock_directions_data(
            "Origin", "Destination", TransportMode.DRIVING
        )

        assert "mock" in mock_data
        assert "duration_minutes" in mock_data
        assert "distance_miles" in mock_data
        assert "route_summary" in mock_data
        assert "traffic_status" in mock_data

        # Basic sanity checks
        assert mock_data["duration_minutes"] > 0
        assert mock_data["distance_miles"] > 0

    def test_clean_location_name(self, mobility_tool):
        """Test location name cleaning."""
        assert mobility_tool._clean_location_name("south san francisco, ca") == "South SF"
        assert mobility_tool._clean_location_name("mountain view, ca") == "Mountain View"
        assert mobility_tool._clean_location_name("linkedin headquarters") == "LinkedIn"
        assert mobility_tool._clean_location_name("palo alto, ca") == "Palo Alto"

    def test_generate_clean_route_summary(self, mobility_tool):
        """Test route summary generation."""
        summary = mobility_tool._generate_clean_route_summary(
            "South San Francisco", "LinkedIn HQ"
        )

        assert "South SF" in summary
        assert "LinkedIn" in summary
        assert "→" in summary

    def test_calculate_fuel_consumption(self, mobility_tool):
        """Test fuel consumption calculation."""
        # 26 miles at 26 mpg = 1 gallon
        fuel = mobility_tool._calculate_fuel_consumption(26.0)
        assert fuel == 1.0

        # 0 miles = 0 gallons
        fuel = mobility_tool._calculate_fuel_consumption(0.0)
        assert fuel == 0.0

        # Negative miles = 0 gallons
        fuel = mobility_tool._calculate_fuel_consumption(-10.0)
        assert fuel == 0.0

    def test_determine_traffic_status(self, mobility_tool):
        """Test traffic status determination."""
        # Light traffic
        leg = {"duration": {"value": 1000}, "duration_in_traffic": {"value": 1000}}
        assert mobility_tool._determine_traffic_status(leg, TransportMode.DRIVING) == "Light traffic"

        # Moderate traffic (1.2x normal)
        leg = {"duration": {"value": 1000}, "duration_in_traffic": {"value": 1200}}
        assert mobility_tool._determine_traffic_status(leg, TransportMode.DRIVING) == "Moderate traffic"

        # Heavy traffic (1.4x normal)
        leg = {"duration": {"value": 1000}, "duration_in_traffic": {"value": 1400}}
        assert mobility_tool._determine_traffic_status(leg, TransportMode.DRIVING) == "Heavy traffic"

        # N/A for non-driving modes
        assert mobility_tool._determine_traffic_status(leg, TransportMode.TRANSIT) == "N/A"

    def test_parse_time(self, mobility_tool):
        """Test time parsing."""
        # 12-hour format
        parsed = mobility_tool._parse_time("8:30 AM")
        assert parsed.hour == 8
        assert parsed.minute == 30

        # 24-hour format
        parsed = mobility_tool._parse_time("14:45")
        assert parsed.hour == 14
        assert parsed.minute == 45

        # Invalid format
        with pytest.raises(ValueError):
            mobility_tool._parse_time("invalid time")


class TestCommuteOptions:
    """Test the get_commute_options method."""

    @pytest.fixture
    def mobility_tool(self):
        """Create a MobilityTool instance."""
        return MobilityTool()

    @pytest.mark.asyncio
    async def test_get_commute_options_to_work(self, mobility_tool):
        """Test getting commute options for morning commute."""
        input_data = CommuteInput(
            direction=CommuteDirection.TO_WORK,
            include_driving=True,
            include_transit=True
        )

        result = await mobility_tool.get_commute_options(input_data)

        assert isinstance(result, CommuteOutput)
        assert result.direction == CommuteDirection.TO_WORK
        assert result.query_time is not None
        assert result.recommendation is not None

    @pytest.mark.asyncio
    async def test_get_commute_options_from_work(self, mobility_tool):
        """Test getting commute options for evening commute."""
        input_data = CommuteInput(
            direction=CommuteDirection.FROM_WORK,
            include_driving=True,
            include_transit=True
        )

        result = await mobility_tool.get_commute_options(input_data)

        assert result.direction == CommuteDirection.FROM_WORK

    @pytest.mark.asyncio
    async def test_get_commute_options_driving_only(self, mobility_tool):
        """Test getting only driving option."""
        input_data = CommuteInput(
            direction=CommuteDirection.TO_WORK,
            include_driving=True,
            include_transit=False
        )

        result = await mobility_tool.get_commute_options(input_data)

        assert result.driving is not None
        # Transit may or may not be None depending on implementation

    @pytest.mark.asyncio
    async def test_get_commute_options_with_departure_time(self, mobility_tool):
        """Test getting commute options with specific departure time."""
        input_data = CommuteInput(
            direction=CommuteDirection.TO_WORK,
            departure_time="8:00 AM"
        )

        result = await mobility_tool.get_commute_options(input_data)

        assert result is not None

    def test_generate_recommendation(self, mobility_tool):
        """Test recommendation generation."""
        from mcp_server.schemas.mobility import DrivingOption, TransitOption

        # No options available
        rec = mobility_tool._generate_recommendation(None, None, datetime.now())
        assert "No commute options" in rec

        # Only driving available
        driving = DrivingOption(
            duration_minutes=30,
            distance_miles=25.0,
            route_summary="via Highway 101",
            traffic_status="Light traffic",
            departure_time="8:00 AM",
            arrival_time="8:30 AM",
            estimated_fuel_gallons=1.0
        )
        rec = mobility_tool._generate_recommendation(driving, None, datetime.now())
        assert "Drive" in rec


class TestShuttleSchedule:
    """Test the get_shuttle_schedule method."""

    @pytest.fixture
    def mobility_tool(self):
        """Create a MobilityTool instance."""
        return MobilityTool()

    @pytest.mark.asyncio
    async def test_get_shuttle_schedule_mv_to_linkedin(self, mobility_tool):
        """Test getting shuttle schedule from MV to LinkedIn."""
        input_data = ShuttleScheduleInput(
            origin=ShuttleStop.MOUNTAIN_VIEW_CALTRAIN,
            destination=ShuttleStop.LINKEDIN_TRANSIT_CENTER
        )

        result = await mobility_tool.get_shuttle_schedule(input_data)

        assert isinstance(result, ShuttleScheduleOutput)
        assert result.origin == ShuttleStop.MOUNTAIN_VIEW_CALTRAIN
        assert result.destination == ShuttleStop.LINKEDIN_TRANSIT_CENTER
        assert result.duration_minutes > 0
        assert result.service_hours is not None
        assert result.frequency_minutes > 0

    @pytest.mark.asyncio
    async def test_get_shuttle_schedule_linkedin_to_mv(self, mobility_tool):
        """Test getting shuttle schedule from LinkedIn to MV."""
        input_data = ShuttleScheduleInput(
            origin=ShuttleStop.LINKEDIN_TRANSIT_CENTER,
            destination=ShuttleStop.MOUNTAIN_VIEW_CALTRAIN
        )

        result = await mobility_tool.get_shuttle_schedule(input_data)

        assert result.origin == ShuttleStop.LINKEDIN_TRANSIT_CENTER
        assert result.destination == ShuttleStop.MOUNTAIN_VIEW_CALTRAIN

    @pytest.mark.asyncio
    async def test_get_shuttle_schedule_with_departure_time(self, mobility_tool):
        """Test getting shuttle schedule with specific departure time."""
        input_data = ShuttleScheduleInput(
            origin=ShuttleStop.MOUNTAIN_VIEW_CALTRAIN,
            destination=ShuttleStop.LINKEDIN_TRANSIT_CENTER,
            departure_time="9:00 AM"
        )

        result = await mobility_tool.get_shuttle_schedule(input_data)

        assert result is not None
