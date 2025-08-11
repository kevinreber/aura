"""Pydantic schemas for mobility tool validation."""

from pydantic import BaseModel, Field
from enum import Enum


class TransportMode(str, Enum):
    """Valid transportation modes for commute queries."""
    DRIVING = "driving"
    TRANSIT = "transit"
    BICYCLING = "bicycling"
    WALKING = "walking"


class MobilityInput(BaseModel):
    """Input schema for mobility.get_commute tool."""
    
    origin: str = Field(
        description="Starting location (address, place name, or coordinates)",
        examples=["123 Main St, San Francisco, CA", "Union Square", "37.7749,-122.4194"]
    )
    destination: str = Field(
        description="Destination location (address, place name, or coordinates)",
        examples=["456 Oak Ave, Oakland, CA", "SF Airport", "37.6213,-122.3790"]
    )
    mode: TransportMode = Field(
        default=TransportMode.DRIVING,
        description="Transportation mode for the commute"
    )


class MobilityOutput(BaseModel):
    """Output schema for mobility.get_commute tool."""
    
    duration_minutes: int = Field(description="Estimated travel time in minutes")
    distance_miles: float = Field(description="Total distance in miles")
    route_summary: str = Field(description="Brief description of the route")
    traffic_status: str = Field(description="Current traffic conditions")
    origin: str = Field(description="Resolved origin location")
    destination: str = Field(description="Resolved destination location")
    mode: TransportMode = Field(description="Transportation mode used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "duration_minutes": 35,
                "distance_miles": 18.2,
                "route_summary": "via US-101 S and I-880 S",
                "traffic_status": "Light traffic",
                "origin": "San Francisco, CA",
                "destination": "Oakland, CA", 
                "mode": "driving"
            }
        }
