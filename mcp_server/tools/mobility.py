"""Mobility tool for getting commute time and route information."""

import asyncio
from typing import Dict, Any
import random

from ..schemas.mobility import MobilityInput, MobilityOutput, TransportMode
from ..utils.http_client import HTTPClient
from ..utils.logging import get_logger, log_tool_call
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
        """Get directions from Google Maps Directions API."""
        
        if not self.settings.google_maps_api_key:
            # Return mock directions data for development
            logger.warning("No Google Maps API key configured, returning mock data")
            return self._get_mock_directions_data(origin, destination, mode)
        
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
            data = response.json()
            
            if data.get("status") != "OK":
                raise ValueError(f"Google Maps API error: {data.get('status', 'Unknown error')}")
            
            return data
    
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
