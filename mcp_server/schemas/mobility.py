"""Pydantic schemas for mobility tool validation."""

from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional
from datetime import time


class TransportMode(str, Enum):
    """Valid transportation modes for commute queries."""
    DRIVING = "driving"
    TRANSIT = "transit"
    BICYCLING = "bicycling"
    WALKING = "walking"


class CommuteDirection(str, Enum):
    """Direction of commute for context-aware routing."""
    TO_WORK = "to_work"  # Morning commute
    FROM_WORK = "from_work"  # Evening commute


class ShuttleStop(str, Enum):
    """MV Connector shuttle stops."""
    MOUNTAIN_VIEW_CALTRAIN = "mountain_view_caltrain"
    LINKEDIN_TRANSIT_CENTER = "linkedin_transit_center"
    LINKEDIN_950_1000 = "linkedin_950_1000"


class ShuttleDeparture(BaseModel):
    """Individual shuttle departure time."""
    departure_time: str = Field(description="Departure time in HH:MM AM/PM format")
    stops: List[str] = Field(description="Sequential stop times for this departure")


class CaltrainDeparture(BaseModel):
    """Individual Caltrain departure."""
    departure_time: str = Field(description="Departure time in HH:MM AM/PM format")
    arrival_time: str = Field(description="Arrival time in HH:MM AM/PM format")
    train_number: Optional[str] = Field(default=None, description="Train number if available")
    platform: Optional[str] = Field(default=None, description="Platform number if available")
    delay_minutes: Optional[int] = Field(default=0, description="Current delay in minutes")
    
class TransitOption(BaseModel):
    """Transit commute option with Caltrain + shuttle details."""
    total_duration_minutes: int = Field(description="Total transit time including all segments")
    caltrain_duration_minutes: int = Field(description="Time on Caltrain only")
    shuttle_duration_minutes: int = Field(description="Time on shuttle only")
    walking_duration_minutes: int = Field(default=3, description="Walking time to/from stations")
    next_departures: List[CaltrainDeparture] = Field(description="Next available Caltrain departures")
    shuttle_departures: List[ShuttleDeparture] = Field(description="Next available shuttle departures")
    transfer_time_minutes: int = Field(default=5, description="Buffer time for transfers")


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


class CommuteInput(BaseModel):
    """Input schema for commute-specific queries."""
    
    direction: CommuteDirection = Field(description="Direction of commute (to work or from work)")
    departure_time: Optional[str] = Field(
        default=None,
        description="Preferred departure time in HH:MM AM/PM format. If not provided, uses current time"
    )
    include_driving: bool = Field(default=True, description="Include driving option in results")
    include_transit: bool = Field(default=True, description="Include transit option in results")
    

class DrivingOption(BaseModel):
    """Driving commute option with real-time traffic."""
    duration_minutes: int = Field(description="Driving time with current traffic")
    distance_miles: float = Field(description="Total distance")
    route_summary: str = Field(description="Main roads/highways")
    traffic_status: str = Field(description="Current traffic conditions")
    departure_time: str = Field(description="Recommended departure time")
    arrival_time: str = Field(description="Estimated arrival time")
    estimated_fuel_gallons: float = Field(description="Estimated fuel consumption in gallons")


class CommuteOutput(BaseModel):
    """Output schema for comprehensive commute information."""
    
    direction: CommuteDirection = Field(description="Direction of commute")
    query_time: str = Field(description="Time when this data was generated")
    driving: Optional[DrivingOption] = Field(default=None, description="Driving option with traffic data")
    transit: Optional[TransitOption] = Field(default=None, description="Transit option with schedules")
    recommendation: str = Field(description="AI recommendation based on current conditions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "direction": "to_work",
                "query_time": "2024-01-15 08:00:00",
                "driving": {
                    "duration_minutes": 45,
                    "distance_miles": 28.5,
                    "route_summary": "via US-101 S",
                    "traffic_status": "Heavy traffic",
                    "departure_time": "8:00 AM",
                    "arrival_time": "8:45 AM"
                },
                "transit": {
                    "total_duration_minutes": 85,
                    "caltrain_duration_minutes": 47,
                    "shuttle_duration_minutes": 11,
                    "walking_duration_minutes": 3,
                    "next_departures": [
                        {
                            "departure_time": "8:15 AM",
                            "arrival_time": "9:02 AM", 
                            "train_number": "152",
                            "delay_minutes": 0
                        }
                    ],
                    "shuttle_departures": [
                        {
                            "departure_time": "9:11 AM",
                            "stops": ["9:11 AM", "9:19 AM", "9:22 AM"]
                        }
                    ],
                    "transfer_time_minutes": 5
                },
                "recommendation": "Take Caltrain - heavy traffic makes driving significantly slower"
            }
        }


class ShuttleScheduleInput(BaseModel):
    """Input schema for shuttle schedule queries."""
    
    origin: ShuttleStop = Field(description="Starting shuttle stop")
    destination: ShuttleStop = Field(description="Destination shuttle stop")
    departure_time: Optional[str] = Field(
        default=None,
        description="Preferred departure time in HH:MM AM/PM format. If not provided, uses current time"
    )
    

class ShuttleScheduleOutput(BaseModel):
    """Output schema for shuttle schedule information."""
    
    origin: ShuttleStop = Field(description="Starting shuttle stop")
    destination: ShuttleStop = Field(description="Destination shuttle stop")
    duration_minutes: int = Field(description="Travel time between stops")
    next_departures: List[ShuttleDeparture] = Field(description="Next available departures")
    service_hours: str = Field(description="Operating hours for this route")
    frequency_minutes: str = Field(description="Typical frequency between shuttles")
