"""MV Connector shuttle schedule data extracted from official timetables."""

from typing import Dict, List, Tuple
from datetime import time, datetime, timedelta
import re

# MV Connector Schedule Data (as of 08/07/2025)
# Source: Official MV Connector timetables

class MVConnectorSchedule:
    """Mountain View Connector shuttle schedule with all stops and timing data."""
    
    # Inbound Schedule (Morning: Mountain View Caltrain → LinkedIn Transit Center → LinkedIn 950|1000)
    INBOUND_SCHEDULE = [
        ("6:50 AM", "6:58 AM", "7:01 AM"),
        ("7:11 AM", "7:19 AM", "7:22 AM"),
        ("7:28 AM", "7:36 AM", "7:39 AM"),
        ("7:44 AM", "7:52 AM", "7:55 AM"),
        ("7:58 AM", "8:06 AM", "8:09 AM"),
        ("8:11 AM", "8:19 AM", "8:22 AM"),
        ("8:28 AM", "8:36 AM", "8:39 AM"),
        ("8:44 AM", "8:52 AM", "8:55 AM"),
        ("8:58 AM", "9:06 AM", "9:09 AM"),
        ("9:11 AM", "9:19 AM", "9:22 AM"),
        ("9:28 AM", "9:36 AM", "9:39 AM"),
        ("9:44 AM", "9:52 AM", "9:55 AM"),
        ("9:58 AM", "10:06 AM", "10:09 AM"),
        ("10:28 AM", "10:36 AM", "10:39 AM"),
        ("10:58 AM", "11:06 AM", "11:09 AM"),
    ]
    
    # Outbound Schedule (Evening: LinkedIn 950|1000 → LinkedIn Transit Center → Mountain View Caltrain)
    OUTBOUND_SCHEDULE = [
        ("3:16 PM", "3:21 PM", "3:29 PM"),
        ("3:29 PM", "3:34 PM", "3:42 PM"),
        ("3:42 PM", "3:47 PM", "3:55 PM"),
        ("3:59 PM", "4:04 PM", "4:12 PM"),
        ("4:16 PM", "4:21 PM", "4:29 PM"),
        ("4:29 PM", "4:34 PM", "4:42 PM"),
        ("4:42 PM", "4:47 PM", "4:55 PM"),
        ("4:59 PM", "5:04 PM", "5:12 PM"),
        ("5:16 PM", "5:21 PM", "5:29 PM"),
        ("5:29 PM", "5:34 PM", "5:42 PM"),
        ("5:42 PM", "5:47 PM", "5:55 PM"),
        ("5:59 PM", "6:04 PM", "6:12 PM"),
        ("6:16 PM", "6:21 PM", "6:29 PM"),
        ("6:42 PM", "6:47 PM", "6:55 PM"),
    ]
    
    # Stop definitions
    STOPS = {
        "inbound": ["Mountain View Caltrain", "LinkedIn Transit Center", "LinkedIn 950|1000"],
        "outbound": ["LinkedIn 950|1000", "LinkedIn Transit Center", "Mountain View Caltrain"]
    }
    
    # Travel time matrix (in minutes)
    TRAVEL_TIMES = {
        ("Mountain View Caltrain", "LinkedIn Transit Center"): 8,
        ("LinkedIn Transit Center", "LinkedIn 950|1000"): 3,
        ("Mountain View Caltrain", "LinkedIn 950|1000"): 11,
        ("LinkedIn 950|1000", "LinkedIn Transit Center"): 5,
        ("LinkedIn Transit Center", "Mountain View Caltrain"): 8,
        ("LinkedIn 950|1000", "Mountain View Caltrain"): 13,
    }
    
    @staticmethod
    def parse_time(time_str: str) -> datetime:
        """Parse time string like '8:15 AM' to datetime object (today)."""
        try:
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            today = datetime.now().date()
            return datetime.combine(today, time_obj.time())
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")
    
    @classmethod
    def get_next_shuttles(
        cls, 
        origin: str, 
        destination: str, 
        after_time: datetime = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        Get next shuttle departures between two stops.
        
        Args:
            origin: Starting stop name
            destination: Destination stop name  
            after_time: Only show departures after this time (default: now)
            limit: Max number of departures to return
            
        Returns:
            List of departure info with times and stops
        """
        if after_time is None:
            after_time = datetime.now()
            
        # Determine direction and schedule
        if origin == "Mountain View Caltrain" and destination in ["LinkedIn Transit Center", "LinkedIn 950|1000"]:
            schedule = cls.INBOUND_SCHEDULE
            stops = cls.STOPS["inbound"]
        elif origin in ["LinkedIn 950|1000", "LinkedIn Transit Center"] and destination == "Mountain View Caltrain":
            schedule = cls.OUTBOUND_SCHEDULE  
            stops = cls.STOPS["outbound"]
        elif origin == "LinkedIn Transit Center" and destination == "LinkedIn 950|1000":
            # Use inbound schedule but start from transit center
            schedule = cls.INBOUND_SCHEDULE
            stops = cls.STOPS["inbound"]
        elif origin == "LinkedIn 950|1000" and destination == "LinkedIn Transit Center":
            # Use outbound schedule but end at transit center  
            schedule = cls.OUTBOUND_SCHEDULE
            stops = cls.STOPS["outbound"]
        else:
            return []
        
        # Find origin and destination indices
        try:
            origin_idx = stops.index(origin)
            dest_idx = stops.index(destination)
        except ValueError:
            return []
        
        # Get departures after specified time
        next_departures = []
        for departure in schedule:
            departure_time = cls.parse_time(departure[origin_idx])
            
            # Handle next day if departure time is earlier than current time
            if departure_time < after_time:
                departure_time += timedelta(days=1)
            
            if departure_time >= after_time:
                arrival_time = cls.parse_time(departure[dest_idx])
                if arrival_time < cls.parse_time(departure[origin_idx]):
                    arrival_time += timedelta(days=1)
                    
                next_departures.append({
                    "departure_time": departure[origin_idx],
                    "arrival_time": departure[dest_idx],
                    "all_stops": list(departure),
                    "stop_names": stops,
                    "departure_datetime": departure_time,
                    "arrival_datetime": arrival_time
                })
                
            if len(next_departures) >= limit:
                break
                
        return next_departures
    
    @classmethod
    def get_travel_time(cls, origin: str, destination: str) -> int:
        """Get travel time in minutes between two stops."""
        return cls.TRAVEL_TIMES.get((origin, destination), 0)
    
    @classmethod
    def get_service_hours(cls, direction: str) -> Tuple[str, str]:
        """Get service hours for a given direction."""
        if direction.lower() == "inbound":
            return ("6:50 AM", "10:58 AM")
        elif direction.lower() == "outbound":
            return ("3:16 PM", "6:42 PM")
        else:
            return ("N/A", "N/A")
    
    @classmethod
    def get_frequency(cls, direction: str) -> str:
        """Get typical frequency between shuttles."""
        if direction.lower() in ["inbound", "outbound"]:
            return "13-17 minutes"
        else:
            return "N/A"
    
    @classmethod
    def is_service_running(cls, check_time: datetime = None) -> Dict[str, bool]:
        """Check if shuttle service is currently running."""
        if check_time is None:
            check_time = datetime.now()
            
        # Convert to time object for comparison
        current_time = check_time.time()
        
        # Service hours
        inbound_start = datetime.strptime("6:50 AM", "%I:%M %p").time()
        inbound_end = datetime.strptime("11:09 AM", "%I:%M %p").time()
        outbound_start = datetime.strptime("3:16 PM", "%I:%M %p").time()
        outbound_end = datetime.strptime("6:55 PM", "%I:%M %p").time()
        
        return {
            "inbound": inbound_start <= current_time <= inbound_end,
            "outbound": outbound_start <= current_time <= outbound_end,
            "any": (inbound_start <= current_time <= inbound_end) or 
                   (outbound_start <= current_time <= outbound_end)
        }


# Convenience functions for common routes
def get_mv_to_linkedin_shuttles(after_time: datetime = None, limit: int = 3) -> List[Dict]:
    """Get shuttles from Mountain View Caltrain to LinkedIn Transit Center."""
    return MVConnectorSchedule.get_next_shuttles(
        "Mountain View Caltrain", 
        "LinkedIn Transit Center", 
        after_time, 
        limit
    )

def get_linkedin_to_mv_shuttles(after_time: datetime = None, limit: int = 3) -> List[Dict]:
    """Get shuttles from LinkedIn Transit Center to Mountain View Caltrain."""
    return MVConnectorSchedule.get_next_shuttles(
        "LinkedIn Transit Center", 
        "Mountain View Caltrain", 
        after_time, 
        limit
    )
