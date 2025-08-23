"""Caltrain API client using official GTFS data."""

import asyncio
import csv
import io
import zipfile
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import os
from pathlib import Path

from ..utils.http_client import HTTPClient
from ..utils.logging import get_logger
from ..utils.cache import get_cache_service, CacheTTL, generate_cache_key

logger = get_logger("caltrain_client")


class CaltrainClient:
    """Client for Caltrain schedule data using official GTFS feeds."""
    
    # Official Caltrain GTFS data URLs
    GTFS_STATIC_URL = "https://data.trilliumtransit.com/gtfs/caltrain-ca-us/caltrain-ca-us.zip"
    
    # Key station IDs for South SF and Mountain View
    STATIONS = {
        "south_san_francisco": {
            "stop_id": "70261",
            "name": "South San Francisco",
            "zone_id": "2"
        },
        "mountain_view": {
            "stop_id": "70261",  # This needs to be corrected with actual ID
            "name": "Mountain View", 
            "zone_id": "4"
        }
    }
    
    def __init__(self):
        self.gtfs_data: Dict[str, List[Dict]] = {}
        self.data_loaded = False
        self.data_timestamp: Optional[datetime] = None
        
    async def ensure_data_loaded(self, force_refresh: bool = False) -> None:
        """Ensure GTFS data is loaded and up to date."""
        cache = await get_cache_service()
        
        # Check if we need to reload data
        if (not self.data_loaded or force_refresh or 
            (self.data_timestamp and datetime.now() - self.data_timestamp > timedelta(hours=24))):
            
            # Try to get from cache first
            cache_key = "caltrain_gtfs_data"
            cached_data = await cache.get(cache_key)
            
            if cached_data and not force_refresh:
                logger.info("Loading Caltrain GTFS data from cache")
                self.gtfs_data = cached_data
                self.data_loaded = True
                self.data_timestamp = datetime.now()
            else:
                logger.info("Downloading fresh Caltrain GTFS data")
                await self._download_and_parse_gtfs()
                
                # Cache the parsed data for 12 hours
                await cache.set(cache_key, self.gtfs_data, ttl=43200)  # 12 hours
                
    async def _download_and_parse_gtfs(self) -> None:
        """Download and parse the GTFS zip file."""
        async with HTTPClient() as client:
            try:
                logger.info(f"Downloading GTFS data from {self.GTFS_STATIC_URL}")
                response = await client.get(self.GTFS_STATIC_URL)
                
                # Create temporary file to store the zip
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = tmp_file.name
                
                # Extract and parse the GTFS files
                await self._parse_gtfs_zip(tmp_path)
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                self.data_loaded = True
                self.data_timestamp = datetime.now()
                logger.info("Successfully loaded Caltrain GTFS data")
                
            except Exception as e:
                logger.error(f"Failed to download GTFS data: {e}")
                raise
                
    async def _parse_gtfs_zip(self, zip_path: str) -> None:
        """Parse GTFS files from the downloaded zip."""
        
        # Files we need from the GTFS feed
        required_files = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt', 'calendar.txt']
        
        self.gtfs_data = {}
        
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            for file_name in required_files:
                if file_name in zip_file.namelist():
                    logger.debug(f"Parsing {file_name}")
                    
                    with zip_file.open(file_name) as file:
                        content = file.read().decode('utf-8')
                        reader = csv.DictReader(io.StringIO(content))
                        self.gtfs_data[file_name.replace('.txt', '')] = list(reader)
                        
                    logger.debug(f"Loaded {len(self.gtfs_data[file_name.replace('.txt', '')])} records from {file_name}")
                else:
                    logger.warning(f"Required GTFS file {file_name} not found in zip")
        
        # Post-process the data for easier querying
        await self._build_indexes()
                    
    async def _build_indexes(self) -> None:
        """Build indexes for faster data querying."""
        # Build stop index
        self.stop_index = {}
        if 'stops' in self.gtfs_data:
            for stop in self.gtfs_data['stops']:
                self.stop_index[stop['stop_id']] = stop
                
        # Build route index  
        self.route_index = {}
        if 'routes' in self.gtfs_data:
            for route in self.gtfs_data['routes']:
                self.route_index[route['route_id']] = route
                
        logger.info(f"Built indexes: {len(self.stop_index)} stops, {len(self.route_index)} routes")
        
    async def get_stations(self) -> List[Dict[str, Any]]:
        """Get all Caltrain stations."""
        await self.ensure_data_loaded()
        
        if 'stops' not in self.gtfs_data:
            return []
            
        # Filter for Caltrain stations (exclude bus stops, etc.)
        stations = []
        for stop in self.gtfs_data['stops']:
            # Caltrain stations typically have specific naming patterns
            if 'Caltrain' in stop.get('stop_name', '') or stop.get('location_type') == '1':
                stations.append({
                    'stop_id': stop['stop_id'],
                    'name': stop['stop_name'],
                    'lat': float(stop.get('stop_lat', 0)),
                    'lon': float(stop.get('stop_lon', 0)),
                    'zone_id': stop.get('zone_id', '')
                })
                
        return sorted(stations, key=lambda x: x['name'])
    
    async def find_station_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a station by name (fuzzy matching)."""
        stations = await self.get_stations()
        
        name_lower = name.lower()
        
        # Try exact match first
        for station in stations:
            if station['name'].lower() == name_lower:
                return station
                
        # Try substring match
        for station in stations:
            if name_lower in station['name'].lower():
                return station
                
        # Try word matching
        name_words = name_lower.split()
        for station in stations:
            station_words = station['name'].lower().split()
            if all(word in station_words for word in name_words):
                return station
                
        return None
    
    async def get_departures_between_stations(
        self,
        origin_station: str,
        destination_station: str,
        departure_time: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get train departures between two stations.
        
        Args:
            origin_station: Origin station name or ID
            destination_station: Destination station name or ID  
            departure_time: Desired departure time
            limit: Maximum number of results
            
        Returns:
            List of departure information
        """
        await self.ensure_data_loaded()
        
        # Find origin and destination stations
        origin = await self.find_station_by_name(origin_station)
        destination = await self.find_station_by_name(destination_station)
        
        if not origin or not destination:
            logger.warning(f"Could not find stations: {origin_station} -> {destination_station}")
            return []
            
        logger.info(f"Finding departures: {origin['name']} -> {destination['name']}")
        
        # Find trips that serve both stations
        departures = []
        
        if 'stop_times' in self.gtfs_data and 'trips' in self.gtfs_data:
            # Group stop times by trip
            trips_stop_times = {}
            for stop_time in self.gtfs_data['stop_times']:
                trip_id = stop_time['trip_id']
                if trip_id not in trips_stop_times:
                    trips_stop_times[trip_id] = []
                trips_stop_times[trip_id].append(stop_time)
            
            # Find trips serving both stations
            for trip_id, stop_times in trips_stop_times.items():
                origin_stop_time = None
                dest_stop_time = None
                
                for stop_time in stop_times:
                    if stop_time['stop_id'] == origin['stop_id']:
                        origin_stop_time = stop_time
                    elif stop_time['stop_id'] == destination['stop_id']:
                        dest_stop_time = stop_time
                
                if origin_stop_time and dest_stop_time:
                    # Parse times with sequence check
                    origin_seq = int(origin_stop_time.get('stop_sequence', 0))
                    dest_seq = int(dest_stop_time.get('stop_sequence', 0))
                    
                    # Only include if destination comes after origin in the trip sequence
                    if dest_seq > origin_seq:
                        origin_time_raw = origin_stop_time['departure_time']
                        dest_time_raw = dest_stop_time['arrival_time']
                        
                        origin_time = self._parse_gtfs_time(origin_time_raw)
                        dest_time = self._parse_gtfs_time(dest_time_raw)
                        
                        if origin_time and dest_time:
                            # Create datetime objects, handling day rollover
                            departure_dt = datetime.combine(departure_time.date(), origin_time)
                            arrival_dt = datetime.combine(departure_time.date(), dest_time)
                            
                            # Handle times that cross midnight (arrival next day)
                            if arrival_dt < departure_dt:
                                arrival_dt += timedelta(days=1)
                            
                            # Check if departure is after desired time
                            if departure_dt.time() >= departure_time.time():
                                # Find trip info
                                trip_info = None
                                for trip in self.gtfs_data['trips']:
                                    if trip['trip_id'] == trip_id:
                                        trip_info = trip
                                        break
                                
                                if trip_info:
                                    departures.append({
                                        'trip_id': trip_id,
                                        'departure_time': origin_time.strftime("%I:%M %p"),
                                        'arrival_time': dest_time.strftime("%I:%M %p"),
                                        'departure_datetime': departure_dt,
                                        'arrival_datetime': arrival_dt,
                                        'route_id': trip_info.get('route_id', ''),
                                        'trip_headsign': trip_info.get('trip_headsign', ''),
                                        'direction_id': trip_info.get('direction_id', '0'),
                                        'duration_minutes': int((arrival_dt - departure_dt).total_seconds() / 60)
                                    })
        
        # Sort by departure time and limit results
        departures.sort(key=lambda x: x['departure_datetime'])
        return departures[:limit]
    
    def _parse_gtfs_time(self, time_str: str) -> Optional[dt_time]:
        """Parse GTFS time format (HH:MM:SS, can be > 24 hours)."""
        try:
            parts = time_str.split(':')
            if len(parts) != 3:
                return None
                
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            
            # Handle times >= 24:00:00 (next day)
            if hours >= 24:
                hours = hours - 24
                
            return dt_time(hours, minutes, seconds)
            
        except (ValueError, IndexError):
            logger.warning(f"Could not parse time: {time_str}")
            return None
    
    async def get_next_trains_ssf_to_mv(
        self, 
        after_time: datetime = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get next trains from South San Francisco to Mountain View."""
        if after_time is None:
            after_time = datetime.now()
            
        return await self.get_departures_between_stations(
            "South San Francisco",
            "Mountain View",
            after_time,
            limit
        )
    
    async def get_next_trains_mv_to_ssf(
        self,
        after_time: datetime = None, 
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get next trains from Mountain View to South San Francisco."""
        if after_time is None:
            after_time = datetime.now()
            
        return await self.get_departures_between_stations(
            "Mountain View",
            "South San Francisco", 
            after_time,
            limit
        )


# Global instance
_caltrain_client: Optional[CaltrainClient] = None

async def get_caltrain_client() -> CaltrainClient:
    """Get the global Caltrain client instance."""
    global _caltrain_client
    if _caltrain_client is None:
        _caltrain_client = CaltrainClient()
    return _caltrain_client
