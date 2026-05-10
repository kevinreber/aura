"""Pydantic schemas for the weekend orchestrator tools."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ==================== Enums ====================


class ActivityType(str, Enum):
    """Trail activity types."""

    HIKING = "hiking"
    RUNNING = "running"
    CYCLING = "cycling"
    ALL = "all"


class TrailDifficulty(str, Enum):
    """Trail difficulty ratings."""

    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"


class TicketStatus(str, Enum):
    """Concert ticket availability."""

    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    UNKNOWN = "unknown"


class POICategory(str, Enum):
    """Point-of-interest categories for itineraries."""

    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    NIGHTLIFE = "nightlife"
    OUTDOORS = "outdoors"
    LODGING = "lodging"
    OTHER = "other"


# ==================== Supporting Models ====================


class Trail(BaseModel):
    """A single trail recommendation."""

    name: str = Field(description="Trail name")
    distance_miles: float = Field(description="Trail distance in miles")
    elevation_gain_ft: Optional[int] = Field(
        default=None, description="Elevation gain in feet (None when provider doesn't report it)"
    )
    difficulty: Optional[TrailDifficulty] = Field(
        default=None, description="Difficulty rating"
    )
    rating: Optional[float] = Field(
        default=None, description="Average user rating (0-5 scale)"
    )
    url: Optional[str] = Field(default=None, description="Source URL for trail details")
    location: str = Field(description="Trail location (city, region, or coordinates)")


class ConcertEvent(BaseModel):
    """A single live music event."""

    artist: str = Field(description="Performing artist name")
    venue: str = Field(description="Venue name")
    date: str = Field(description="Event date in ISO format (YYYY-MM-DD)")
    time: Optional[str] = Field(default=None, description="Event start time (HH:MM)")
    ticket_url: Optional[str] = Field(default=None, description="Link to ticket purchase page")
    ticket_status: TicketStatus = Field(
        default=TicketStatus.UNKNOWN, description="Ticket availability"
    )
    on_sale_date: Optional[str] = Field(
        default=None, description="ISO date when tickets go on sale (if not yet available)"
    )


class POI(BaseModel):
    """A point of interest for itinerary planning."""

    name: str = Field(description="Place name")
    category: POICategory = Field(description="Category of place")
    rating: Optional[float] = Field(default=None, description="Average rating (0-5 scale)")
    address: str = Field(description="Street address or general location")
    hours: Optional[str] = Field(default=None, description="Opening hours summary")
    price_level: Optional[int] = Field(
        default=None, description="Price level 1-4 (1=$, 4=$$$$)"
    )
    description: Optional[str] = Field(default=None, description="Short description")


class TransitEstimate(BaseModel):
    """Drive-time estimate between two points."""

    from_location: str = Field(description="Origin")
    to_location: str = Field(description="Destination")
    drive_time_min: int = Field(description="Drive time in minutes")
    distance_miles: float = Field(description="Distance in miles")


# ==================== get_trails ====================


class TrailSearchInput(BaseModel):
    """Input for weekend.get_trails."""

    location: str = Field(
        description="City or region to search near",
        examples=["Boulder, CO", "San Francisco, CA"],
    )
    activity_type: ActivityType = Field(
        default=ActivityType.ALL, description="Type of trail activity"
    )
    max_distance_miles: int = Field(
        default=25, description="Maximum trail distance in miles", ge=1, le=200
    )
    difficulty: Optional[TrailDifficulty] = Field(
        default=None, description="Filter by difficulty (omit for any)"
    )


class TrailSearchOutput(BaseModel):
    """Output for weekend.get_trails."""

    trails: List[Trail] = Field(default_factory=list, description="Matching trails")
    source: str = Field(description="Provider used (e.g. 'google_places', 'mock')")
    cached: bool = Field(default=False, description="True if served from cache")
    error: Optional[str] = Field(
        default=None, description="Error message when no trails could be returned"
    )


# ==================== get_concerts ====================


class ConcertSearchInput(BaseModel):
    """Input for weekend.get_concerts."""

    location: str = Field(
        description="City to search around",
        examples=["Denver, CO", "San Francisco, CA"],
    )
    artists: Optional[List[str]] = Field(
        default=None, description="Specific artists to track (omit for all events in radius)"
    )
    radius_miles: int = Field(default=50, description="Search radius in miles", ge=1, le=500)
    date_range_days: int = Field(
        default=14, description="How far ahead to look (days)", ge=1, le=90
    )


class ConcertSearchOutput(BaseModel):
    """Output for weekend.get_concerts."""

    events: List[ConcertEvent] = Field(default_factory=list, description="Matching events")
    source: str = Field(description="Provider used (e.g. 'bandsintown', 'mock')")
    cached: bool = Field(default=False, description="True if served from cache")
    error: Optional[str] = Field(
        default=None, description="Error message when no events could be returned"
    )


# ==================== generate_itinerary ====================


class ItineraryInput(BaseModel):
    """Input for weekend.generate_itinerary."""

    destination: str = Field(
        description="City or region for the trip",
        examples=["Denver, CO", "Asheville, NC"],
    )
    duration_days: int = Field(description="Number of days (1-7)", ge=1, le=7)
    interests: List[str] = Field(
        default_factory=list,
        description="Interest tags",
        examples=[["outdoors", "live music", "food"]],
    )
    base_location: Optional[str] = Field(
        default=None,
        description="Hotel or Airbnb address — used to compute transit estimates",
    )


class ItineraryOutput(BaseModel):
    """Output for weekend.generate_itinerary."""

    destination: str = Field(description="Resolved destination")
    duration_days: int = Field(description="Trip duration in days")
    points_of_interest: List[POI] = Field(
        default_factory=list, description="Places to visit, ranked by relevance"
    )
    transit_estimates: Optional[List[TransitEstimate]] = Field(
        default=None, description="Drive-time estimates from base_location (when provided)"
    )
    source: str = Field(description="Provider used (e.g. 'google_places', 'mock')")
    cached: bool = Field(default=False, description="True if served from cache")
    error: Optional[str] = Field(
        default=None, description="Error message when generation could not complete"
    )
