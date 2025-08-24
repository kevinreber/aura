"""Mobility tool for getting commute time, route information, and shuttle schedules."""

import asyncio
from typing import Dict, Any, List, Optional
import random
from datetime import datetime, timedelta

from ..schemas.mobility import (
    MobilityInput, MobilityOutput, TransportMode,
    CommuteInput, CommuteOutput, CommuteDirection,
    DrivingOption, TransitOption, CaltrainDeparture, ShuttleDeparture,
    ShuttleScheduleInput, ShuttleScheduleOutput, ShuttleStop
)
from ..utils.http_client import HTTPClient
from ..utils.logging import get_logger, log_tool_call
from ..utils.cache import get_cache_service, cached, CacheTTL, generate_cache_key
from ..utils.shuttle_data import MVConnectorSchedule, get_mv_to_linkedin_shuttles, get_linkedin_to_mv_shuttles
from ..clients.caltrain import get_caltrain_client
from ..config import get_settings

logger = get_logger("mobility_tool")


class MobilityTool:
    """Tool for getting commute information using Google Maps Directions API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    async def get_commute(self, input_data: MobilityInput) -> MobilityOutput:
        """
        Get commute information between two locations.
        
        Args:
            input_data: MobilityInput with origin, destination, and mode
            
        Returns:
            MobilityOutput with commute details
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting commute from {input_data.origin} to {input_data.destination} via {input_data.mode}")
            
            # Get directions from Google Maps API
            directions_data = await self._get_directions(
                input_data.origin,
                input_data.destination, 
                input_data.mode
            )
            
            # Parse and format the response
            result = await self._format_directions_response(
                directions_data,
                input_data.origin,
                input_data.destination,
                input_data.mode
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("mobility.get_commute", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("mobility.get_commute", input_data.dict(), duration_ms)
            logger.error(f"Error getting commute data: {e}")
            raise
    
    async def _get_directions(
        self, 
        origin: str, 
        destination: str, 
        mode: TransportMode
    ) -> Dict[str, Any]:
        """Get directions from Google Maps Directions API with caching."""
        cache = await get_cache_service()
        
        # Create cache key based on origin, destination, and mode
        # For driving mode, we use shorter TTL due to traffic changes
        cache_key = generate_cache_key("mobility_directions", 
                                     origin.lower(), 
                                     destination.lower(), 
                                     mode.value)
        
        # Check cache first
        cached_directions = await cache.get(cache_key)
        if cached_directions:
            logger.debug(f"Using cached directions for {origin} -> {destination} ({mode.value})")
            return cached_directions
        
        if not self.settings.google_maps_api_key:
            # Return mock directions data for development
            logger.warning("No Google Maps API key configured, returning mock data")
            directions_data = self._get_mock_directions_data(origin, destination, mode)
        else:
            # Map our transport modes to Google's API
            google_mode_map = {
                TransportMode.DRIVING: "driving",
                TransportMode.TRANSIT: "transit",
                TransportMode.BICYCLING: "bicycling", 
                TransportMode.WALKING: "walking"
            }
            
            params = {
                "origin": origin,
                "destination": destination,
                "mode": google_mode_map[mode],
                "departure_time": "now",  # For current traffic conditions
                "key": self.settings.google_maps_api_key
            }
            
            async with HTTPClient() as client:
                response = await client.get(self.base_url, params=params)
                directions_data = response.json()
                
                if directions_data.get("status") != "OK":
                    raise ValueError(f"Google Maps API error: {directions_data.get('status', 'Unknown error')}")
        
        # Cache the directions data
        await cache.set(cache_key, directions_data, CacheTTL.MOBILITY_DIRECTIONS)
        logger.debug(f"Cached directions for {origin} -> {destination} ({mode.value})")
        
        return directions_data
    
    async def _format_directions_response(
        self,
        directions_data: Dict[str, Any],
        origin: str,
        destination: str,
        mode: TransportMode
    ) -> MobilityOutput:
        """Format Google Maps Directions response into our schema."""
        
        # Handle mock data
        if "mock" in directions_data:
            return MobilityOutput(
                duration_minutes=directions_data["duration_minutes"],
                distance_miles=directions_data["distance_miles"],
                route_summary=directions_data["route_summary"],
                traffic_status=directions_data["traffic_status"],
                origin=origin,
                destination=destination,
                mode=mode
            )
        
        # Parse real Google Maps response
        if not directions_data.get("routes"):
            raise ValueError("No routes found for the given locations")
        
        route = directions_data["routes"][0]
        leg = route["legs"][0]
        
        # Extract duration (convert seconds to minutes)
        duration_seconds = leg["duration"]["value"]
        duration_minutes = round(duration_seconds / 60)
        
        # Extract distance (convert meters to miles)
        distance_meters = leg["distance"]["value"]
        distance_miles = round(distance_meters * 0.000621371, 1)
        
        # Generate route summary from steps
        route_summary = self._generate_route_summary(leg.get("steps", []))
        
        # Determine traffic status
        traffic_status = self._determine_traffic_status(leg, mode)
        
        # Get resolved location names
        resolved_origin = leg["start_address"]
        resolved_destination = leg["end_address"]
        
        return MobilityOutput(
            duration_minutes=duration_minutes,
            distance_miles=distance_miles,
            route_summary=route_summary,
            traffic_status=traffic_status,
            origin=resolved_origin,
            destination=resolved_destination,
            mode=mode
        )
    
    def _generate_route_summary(self, steps: list) -> str:
        """Generate a brief route summary from direction steps."""
        if not steps:
            return "Direct route"
        
        # Extract major roads/highways mentioned in instructions
        major_roads = []
        for step in steps:
            instruction = step.get("html_instructions", "")
            # Simple extraction of road names (this could be more sophisticated)
            if "on " in instruction.lower():
                parts = instruction.lower().split("on ")
                if len(parts) > 1:
                    road_part = parts[1].split()[0:2]  # Take first 1-2 words after "on"
                    road_name = " ".join(road_part).strip(",")
                    if road_name and len(road_name) > 2:
                        major_roads.append(road_name)
        
        if major_roads:
            unique_roads = list(dict.fromkeys(major_roads[:3]))  # Remove duplicates, keep order, limit to 3
            return f"via {', '.join(unique_roads)}"
        else:
            return "Most direct route available"
    
    def _determine_traffic_status(self, leg: Dict[str, Any], mode: TransportMode) -> str:
        """Determine traffic status based on duration data."""
        if mode != TransportMode.DRIVING:
            return "N/A"
        
        # Check if duration_in_traffic is available
        normal_duration = leg.get("duration", {}).get("value", 0)
        traffic_duration = leg.get("duration_in_traffic", {}).get("value", normal_duration)
        
        if traffic_duration <= normal_duration * 1.1:
            return "Light traffic"
        elif traffic_duration <= normal_duration * 1.3:
            return "Moderate traffic"
        elif traffic_duration <= normal_duration * 1.5:
            return "Heavy traffic"
        else:
            return "Very heavy traffic"
    
    def _get_mock_directions_data(
        self, 
        origin: str, 
        destination: str, 
        mode: TransportMode
    ) -> Dict[str, Any]:
        """Return mock directions data for development/testing."""
        
        # Generate realistic but random data based on mode
        base_duration = {
            TransportMode.DRIVING: 25,
            TransportMode.TRANSIT: 45,
            TransportMode.BICYCLING: 60,
            TransportMode.WALKING: 120
        }[mode]
        
        base_distance = {
            TransportMode.DRIVING: 15.0,
            TransportMode.TRANSIT: 12.0,
            TransportMode.BICYCLING: 8.0,
            TransportMode.WALKING: 3.0
        }[mode]
        
        # Add some randomness
        duration_minutes = base_duration + random.randint(-10, 10)
        distance_miles = base_distance + random.uniform(-3.0, 3.0)
        
        traffic_statuses = ["Light traffic", "Moderate traffic", "Heavy traffic"]
        traffic_status = random.choice(traffic_statuses) if mode == TransportMode.DRIVING else "N/A"
        
        route_summaries = {
            TransportMode.DRIVING: "via Main St and Highway 101",
            TransportMode.TRANSIT: "via Metro Red Line and Bus Route 42", 
            TransportMode.BICYCLING: "via bike lanes on Oak Ave",
            TransportMode.WALKING: "via pedestrian paths"
        }
        
        return {
            "mock": True,
            "duration_minutes": max(1, duration_minutes),
            "distance_miles": max(0.1, round(distance_miles, 1)),
            "route_summary": route_summaries[mode],
            "traffic_status": traffic_status
        }
    
    async def get_commute_options(self, input_data: CommuteInput) -> CommuteOutput:
        """
        Get comprehensive commute options including driving and transit.
        
        Args:
            input_data: CommuteInput with direction and preferences
            
        Returns:
            CommuteOutput with driving and transit options
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting commute options for {input_data.direction.value}")
            
            # Determine origin and destination based on direction and configured addresses
            settings = self.settings
            
            if input_data.direction == CommuteDirection.TO_WORK:
                # Morning commute: home to work
                origin = settings.home_address if settings.home_address else "South San Francisco, CA"
                destination = settings.work_address if settings.work_address else "Mountain View, CA"
                caltrain_origin = settings.home_caltrain_station
                caltrain_destination = settings.work_caltrain_station
            else:
                # Evening commute: work to home
                origin = settings.work_address if settings.work_address else "Mountain View, CA"
                destination = settings.home_address if settings.home_address else "South San Francisco, CA"
                caltrain_origin = settings.work_caltrain_station
                caltrain_destination = settings.home_caltrain_station
            
            # Get current time or use provided departure time
            if input_data.departure_time:
                query_time = self._parse_time(input_data.departure_time)
            else:
                query_time = datetime.now()
            
            # Initialize result
            driving_option = None
            transit_option = None
            
            # Get driving option if requested
            if input_data.include_driving:
                driving_option = await self._get_driving_option(
                    origin, destination, query_time
                )
            
            # Get transit option if requested  
            if input_data.include_transit:
                transit_option = await self._get_transit_option(
                    caltrain_origin, caltrain_destination, 
                    input_data.direction, query_time
                )
            
            # Generate AI recommendation
            recommendation = self._generate_recommendation(
                driving_option, transit_option, query_time
            )
            
            result = CommuteOutput(
                direction=input_data.direction,
                query_time=query_time.strftime("%Y-%m-%d %H:%M:%S"),
                driving=driving_option,
                transit=transit_option,
                recommendation=recommendation
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("mobility.get_commute_options", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("mobility.get_commute_options", input_data.dict(), duration_ms)
            logger.error(f"Error getting commute options: {e}")
            raise
    
    async def get_shuttle_schedule(self, input_data: ShuttleScheduleInput) -> ShuttleScheduleOutput:
        """
        Get MV Connector shuttle schedule between stops.
        
        Args:
            input_data: ShuttleScheduleInput with stops and time preferences
            
        Returns:
            ShuttleScheduleOutput with schedule information
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Getting shuttle schedule from {input_data.origin.value} to {input_data.destination.value}")
            
            # Parse departure time if provided
            after_time = None
            if input_data.departure_time:
                after_time = self._parse_time(input_data.departure_time)
            
            # Map enum values to shuttle data names
            stop_name_map = {
                ShuttleStop.MOUNTAIN_VIEW_CALTRAIN: "Mountain View Caltrain",
                ShuttleStop.LINKEDIN_TRANSIT_CENTER: "LinkedIn Transit Center", 
                ShuttleStop.LINKEDIN_950_1000: "LinkedIn 950|1000"
            }
            
            origin_name = stop_name_map[input_data.origin]
            dest_name = stop_name_map[input_data.destination]
            
            # Get next departures
            departures = MVConnectorSchedule.get_next_shuttles(
                origin_name, dest_name, after_time, limit=5
            )
            
            # Format departures for response
            shuttle_departures = []
            for dep in departures:
                shuttle_departures.append(ShuttleDeparture(
                    departure_time=dep["departure_time"],
                    stops=dep["all_stops"]
                ))
            
            # Get travel time and service info
            duration = MVConnectorSchedule.get_travel_time(origin_name, dest_name)
            
            # Determine direction for service hours
            if input_data.origin == ShuttleStop.MOUNTAIN_VIEW_CALTRAIN:
                direction = "inbound"
            else:
                direction = "outbound"
            
            start_hour, end_hour = MVConnectorSchedule.get_service_hours(direction)
            service_hours = f"{start_hour} - {end_hour}"
            frequency = MVConnectorSchedule.get_frequency(direction)
            
            result = ShuttleScheduleOutput(
                origin=input_data.origin,
                destination=input_data.destination,
                duration_minutes=duration,
                next_departures=shuttle_departures,
                service_hours=service_hours,
                frequency_minutes=frequency
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("mobility.get_shuttle_schedule", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("mobility.get_shuttle_schedule", input_data.dict(), duration_ms)
            logger.error(f"Error getting shuttle schedule: {e}")
            raise
    
    async def _get_driving_option(
        self, 
        origin: str, 
        destination: str, 
        departure_time: datetime
    ) -> DrivingOption:
        """Get driving option with real-time traffic data."""
        
        # Use existing get_commute method for driving data
        mobility_input = MobilityInput(
            origin=origin,
            destination=destination,
            mode=TransportMode.DRIVING
        )
        
        driving_data = await self.get_commute(mobility_input)
        
        # Calculate departure and arrival times
        arrival_time = departure_time + timedelta(minutes=driving_data.duration_minutes)
        
        return DrivingOption(
            duration_minutes=driving_data.duration_minutes,
            distance_miles=driving_data.distance_miles,
            route_summary=driving_data.route_summary,
            traffic_status=driving_data.traffic_status,
            departure_time=departure_time.strftime("%I:%M %p"),
            arrival_time=arrival_time.strftime("%I:%M %p")
        )
    
    async def _get_transit_option(
        self, 
        caltrain_origin: str,
        caltrain_destination: str, 
        direction: CommuteDirection,
        departure_time: datetime
    ) -> TransitOption:
        """Get transit option with Caltrain + shuttle data."""
        
        # Get real Caltrain data using GTFS API
        caltrain_client = await get_caltrain_client()
        
        try:
            if direction == CommuteDirection.TO_WORK:
                # Morning: SSF to MV
                caltrain_departures_data = await caltrain_client.get_next_trains_ssf_to_mv(
                    departure_time, limit=3
                )
            else:
                # Evening: MV to SSF
                caltrain_departures_data = await caltrain_client.get_next_trains_mv_to_ssf(
                    departure_time, limit=3
                )
                
            # Convert to our schema format
            caltrain_departures = []
            avg_duration = 47  # Default fallback
            
            for dep in caltrain_departures_data:
                duration = int((dep['arrival_datetime'] - dep['departure_datetime']).total_seconds() / 60)
                if duration > 0:
                    avg_duration = duration  # Use actual duration from first valid result
                
                caltrain_departures.append(CaltrainDeparture(
                    departure_time=dep['departure_time'],
                    arrival_time=dep['arrival_time'],
                    train_number=dep.get('route_id', 'N/A'),
                    platform=dep.get('platform', 'TBD'),
                    delay_minutes=0  # Real-time delay would go here
                ))
            
            if not caltrain_departures:
                logger.warning("No Caltrain departures found, using mock data as fallback")
                caltrain_departures = self._get_mock_caltrain_departures(
                    caltrain_origin, caltrain_destination, departure_time
                )
                avg_duration = 47
            
        except Exception as e:
            logger.error(f"Error fetching Caltrain data: {e}, falling back to mock data")
            caltrain_departures = self._get_mock_caltrain_departures(
                caltrain_origin, caltrain_destination, departure_time
            )
            avg_duration = 47
        
        # Get shuttle information based on direction
        if direction == CommuteDirection.TO_WORK:
            # Morning: need shuttle from MV Caltrain to LinkedIn
            shuttle_origin = "Mountain View Caltrain"
            shuttle_dest = "LinkedIn Transit Center"
            shuttle_duration = MVConnectorSchedule.get_travel_time(shuttle_origin, shuttle_dest)
            shuttle_departures_data = get_mv_to_linkedin_shuttles(departure_time, limit=3)
        else:
            # Evening: need shuttle from LinkedIn to MV Caltrain 
            shuttle_origin = "LinkedIn Transit Center"
            shuttle_dest = "Mountain View Caltrain"
            shuttle_duration = MVConnectorSchedule.get_travel_time(shuttle_origin, shuttle_dest)
            shuttle_departures_data = get_linkedin_to_mv_shuttles(departure_time, limit=3)
        
        # Format shuttle departures
        shuttle_departures = []
        for dep in shuttle_departures_data:
            shuttle_departures.append(ShuttleDeparture(
                departure_time=dep["departure_time"],
                stops=dep["all_stops"]
            ))
        
        # Calculate total duration (includes transfer buffer)
        transfer_time = 5
        walking_time = 3
        total_duration = avg_duration + shuttle_duration + transfer_time + walking_time
        
        return TransitOption(
            total_duration_minutes=total_duration,
            caltrain_duration_minutes=avg_duration,
            shuttle_duration_minutes=shuttle_duration,
            walking_duration_minutes=walking_time,
            next_departures=caltrain_departures,
            shuttle_departures=shuttle_departures,
            transfer_time_minutes=transfer_time
        )
    
    def _get_mock_caltrain_departures(
        self, 
        origin: str, 
        destination: str, 
        after_time: datetime,
        limit: int = 3
    ) -> List[CaltrainDeparture]:
        """Generate mock Caltrain departures (will be replaced with real API)."""
        
        departures = []
        current_time = after_time
        
        # Generate reasonable departure times
        for i in range(limit):
            # Caltrain typically runs every 15-30 minutes during peak hours
            departure_offset = 15 + (i * 20)  # 15, 35, 55 minutes from now
            departure_dt = current_time + timedelta(minutes=departure_offset)
            arrival_dt = departure_dt + timedelta(minutes=47)  # SSF to MV is ~47 mins
            
            departures.append(CaltrainDeparture(
                departure_time=departure_dt.strftime("%I:%M %p"),
                arrival_time=arrival_dt.strftime("%I:%M %p"),
                train_number=f"{150 + i * 2}",  # Mock train numbers
                platform="TBD",
                delay_minutes=0
            ))
        
        return departures
    
    def _generate_recommendation(
        self, 
        driving: Optional[DrivingOption], 
        transit: Optional[TransitOption],
        query_time: datetime
    ) -> str:
        """Generate AI recommendation based on current conditions."""
        
        if not driving and not transit:
            return "No commute options available"
        
        if not driving:
            return "Take transit - driving option not available"
        
        if not transit:
            return f"Drive - estimated {driving.duration_minutes} minutes with {driving.traffic_status.lower()}"
        
        # Compare options
        time_diff = transit.total_duration_minutes - driving.duration_minutes
        
        if "Heavy" in driving.traffic_status or "Very heavy" in driving.traffic_status:
            if time_diff <= 20:
                return f"Take transit - heavy traffic makes driving much slower ({driving.duration_minutes} min driving vs {transit.total_duration_minutes} min transit)"
            else:
                return f"Drive despite traffic - transit takes {time_diff} minutes longer"
        
        elif time_diff <= -10:  # Transit is 10+ minutes faster
            return f"Take transit - {abs(time_diff)} minutes faster than driving"
        
        elif time_diff >= 30:  # Driving is 30+ minutes faster
            return f"Drive - {time_diff} minutes faster than transit with {driving.traffic_status.lower()}"
        
        else:
            return f"Both options similar - drive ({driving.duration_minutes} min) or transit ({transit.total_duration_minutes} min)"
    
    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string like '8:15 AM' to datetime object (today)."""
        try:
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            today = datetime.now().date()
            return datetime.combine(today, time_obj.time())
        except ValueError:
            try:
                time_obj = datetime.strptime(time_str, "%H:%M")
                today = datetime.now().date()
                return datetime.combine(today, time_obj.time())
            except ValueError:
                raise ValueError(f"Invalid time format: {time_str}. Use 'HH:MM AM/PM' or 'HH:MM'")
