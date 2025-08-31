"""Flask application factory for the MCP server."""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
import asyncio
from typing import Dict, Any

from .config import get_settings
from .utils.logging import setup_logging, get_logger
from .utils.cache import get_cache_service
from .server import get_mcp_server
from .schemas import (
    WeatherInput, MobilityInput, CommuteInput, ShuttleScheduleInput,
    CalendarInput, TodoInput, FinancialInput
)

# Initialize logger
logger = get_logger("flask_app")


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    settings = get_settings()
    
    # Configure Flask
    app.config['SECRET_KEY'] = settings.secret_key
    app.config['DEBUG'] = settings.debug
    
    # Setup logging
    setup_logging()
    
    # Setup CORS
    CORS(app, origins=settings.allowed_origins)
    
    # Setup rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute} per minute"]
    )
    
    # Setup Swagger UI
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Daily MCP Server API",
            "description": """🎉 **Phase 2.0 Complete** - Model Context Protocol server with comprehensive READ and WRITE operations!

**🆕 NEW: Todoist Integration + Enhanced Todo Management** - Full CRUD operations with real Todoist API integration!

**📊 Read Operations**:
🌤️ **Weather**: Real-time conditions via OpenWeatherMap  
📅 **Calendar**: Multi-calendar events via Google Calendar API  
💰 **Financial**: Live stock/crypto prices via Alpha Vantage & CoinGecko  
🚗 **Basic Mobility**: Real-time commute times via Google Maps  
🚗🚂 **Commute Intelligence**: Complete analysis with driving + transit options + fuel estimates  
🚌 **Shuttle Schedules**: MV Connector timetables with real-time queries (Mon-Fri only)  
✅ **Todo**: Task management with smart filtering across buckets (work, home, errands, personal)  

**✨ Write Operations**:
📅+ **Calendar CRUD**: Create, update, delete events with conflict detection  
✅+ **Todo CRUD**: Create, update, complete, delete todos with Todoist API integration  

**🎯 Features**: Live traffic data, official transit schedules, fuel consumption estimates, city-based routing, AI recommendations, production deployment, real Todoist sync
**⚡ Quick Start**: All endpoints require POST with JSON body. Try `/docs` for interactive testing!""",
            "contact": {
                "responsibleOrganization": "Personal Learning Project",
                "responsibleDeveloper": "Kevin Reber",
                "email": "kevinreber1@gmail.com"
            },
            "version": "2.0.0",
            "license": {
                "name": "MIT"
            }
        },
        "host": "localhost:8000" if settings.environment == "development" else None,
        "basePath": "/",
        "schemes": ["http"] if settings.environment == "development" else ["https"],
        "produces": ["application/json"],
        "consumes": ["application/json"],
        "tags": [
            {"name": "Health", "description": "System health and status monitoring"},
            {"name": "Tools", "description": "Available MCP tools and capabilities"},
            {"name": "Weather", "description": "🌤️ Real-time weather via OpenWeatherMap API"},
            {"name": "Calendar", "description": "📅 Google Calendar R/W - Events, creation, conflict detection"},
            {"name": "Financial", "description": "💰 Live stock and crypto market data"},
            {"name": "Mobility", "description": "🚗🚂 Complete commute intelligence - Real traffic, live transit, AI recommendations"},
            {"name": "Todo", "description": "✅ Full CRUD task management with Todoist API integration - Create, read, update, complete, and delete todos across work, home, errands, and personal buckets"}
        ]
    }
    
    swagger = Swagger(app, config=swagger_config, template=swagger_template)
    
    # Initialize MCP server
    mcp_server = get_mcp_server()
    
    # Initialize cache service
    async def init_cache():
        """Initialize cache service on startup."""
        cache_service = await get_cache_service()
        stats = await cache_service.get_cache_stats()
        logger.info(f"Cache service initialized: {stats}")
    
    # Initialize cache service on startup
    with app.app_context():
        import asyncio
        asyncio.run(init_cache())
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint.
        ---
        tags:
          - System
        responses:
          200:
            description: Service health status
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "healthy"
                version:
                  type: string
                  example: "0.1.0"
                environment:
                  type: string
                  example: "development"
        """
        return jsonify({
            "status": "healthy",
            "version": "0.5.0",
            "environment": settings.environment
        })
    
    # List available tools
    @app.route('/tools')
    def list_tools():
        """List all available MCP tools.
        ---
        tags:
          - Tools
        responses:
          200:
            description: List of available tools and their schemas
            schema:
              type: object
              properties:
                server_info:
                  type: object
                  properties:
                    name:
                      type: string
                      example: "Daily MCP Server"
                    description:
                      type: string
                      example: "Morning routine tools for AI agents"
                    version:
                      type: string
                      example: "0.1.0"
                tools:
                  type: object
                  additionalProperties:
                    type: object
                    properties:
                      description:
                        type: string
                      input_schema:
                        type: object
                      output_schema:
                        type: string
        """
        return jsonify(mcp_server.list_tools())
    
    @app.route('/calendars')
    def list_calendars():
        """List all available Google calendars for debugging multi-calendar integration."""
        try:
            from .tools.calendar import CalendarTool
            calendar_tool = CalendarTool()
            
            if calendar_tool.google_calendar_client:
                calendars = calendar_tool.google_calendar_client.get_calendar_list()
                return jsonify({
                    "available_calendars": calendars,
                    "total_calendars": len(calendars),
                    "status": "success"
                })
            else:
                return jsonify({
                    "error": "Google Calendar client not available",
                    "status": "error"
                }), 500
        except Exception as e:
            return jsonify({
                "error": str(e),
                "status": "error"
            }), 500
    
    @app.route('/cache/stats')
    async def cache_stats():
        """Get cache statistics for monitoring."""
        try:
            cache_service = await get_cache_service()
            stats = await cache_service.get_cache_stats()
            return jsonify({
                "cache_stats": stats,
                "status": "success"
            })
        except Exception as e:
            return jsonify({
                "error": str(e),
                "status": "error"
            }), 500
    
    # Weather tool endpoint
    @app.route('/tools/weather.get_daily', methods=['POST'])
    async def weather_get_daily():
        """Get current weather and daily forecast with real OpenWeatherMap data.
        ---
        tags:
          - Weather
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - location
              properties:
                location:
                  type: string
                  example: "San Francisco, CA"
                  description: "City and state/country for weather lookup"
        responses:
          200:
            description: Current weather and forecast data
            schema:
              type: object
              properties:
                location:
                  type: string
                  example: "San Francisco, CA"
                  description: "Location queried"
                current:
                  type: object
                  properties:
                    temperature:
                      type: number
                      example: 18.5
                      description: "Current temperature in Celsius"
                    description:
                      type: string
                      example: "Partly cloudy"
                      description: "Weather condition description"
                    humidity:
                      type: number
                      example: 65
                      description: "Humidity percentage"
                    wind_speed:
                      type: number
                      example: 12.5
                      description: "Wind speed in km/h"
                forecast:
                  type: array
                  items:
                    type: object
                    properties:
                      date:
                        type: string
                        format: date
                        example: "2024-12-18"
                      high:
                        type: number
                        example: 22.0
                        description: "High temperature"
                      low:
                        type: number
                        example: 15.0
                        description: "Low temperature"
                      description:
                        type: string
                        example: "Sunny"
          400:
            description: Invalid request format or missing location
          500:
            description: Weather service error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("weather.get_daily", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in weather.get_daily: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Mobility tool endpoint  
    @app.route('/tools/mobility.get_commute', methods=['POST'])
    async def mobility_get_commute():
        """Get commute and traffic information with travel times and route options.
        ---
        tags:
          - Mobility
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - origin
                - destination
              properties:
                origin:
                  type: string
                  example: "123 Main St, San Francisco, CA"
                  description: "Starting location (address or place name)"
                destination:
                  type: string
                  example: "456 Market St, San Francisco, CA"
                  description: "Destination location (address or place name)"
                mode:
                  type: string
                  enum: ['driving', 'walking', 'transit', 'bicycling']
                  default: 'driving'
                  description: "Transportation mode"
                departure_time:
                  type: string
                  format: date-time
                  example: "2024-12-18T08:00:00Z"
                  description: "Departure time (optional, defaults to now)"
        responses:
          200:
            description: Commute information with travel times and routes
            schema:
              type: object
              properties:
                origin:
                  type: string
                  example: "123 Main St, San Francisco, CA"
                destination:
                  type: string
                  example: "456 Market St, San Francisco, CA"
                mode:
                  type: string
                  example: "driving"
                routes:
                  type: array
                  items:
                    type: object
                    properties:
                      summary:
                        type: string
                        example: "Via US-101 N"
                        description: "Route summary"
                      duration:
                        type: string
                        example: "25 mins"
                        description: "Estimated travel time"
                      distance:
                        type: string
                        example: "12.3 km"
                        description: "Total distance"
                      traffic_info:
                        type: string
                        example: "Light traffic"
                        description: "Current traffic conditions"
          400:
            description: Invalid request format or missing origin/destination
          500:
            description: Maps service error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("mobility.get_commute", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in mobility.get_commute: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Commute intelligence tool endpoint
    @app.route('/tools/mobility.get_commute_options', methods=['POST'])
    async def mobility_get_commute_options():
        """Get comprehensive commute analysis with driving AND transit options including real-time traffic and live schedules.
        ---
        tags:
          - Mobility
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - direction
              properties:
                direction:
                  type: string
                  enum: ['to_work', 'from_work']
                  example: "to_work"
                  description: "Direction of commute (morning or evening)"
                departure_time:
                  type: string
                  example: "8:00 AM"
                  description: "Preferred departure time (format HH-MM AM/PM, optional)"
                include_driving:
                  type: boolean
                  default: true
                  description: "Include driving option with real-time traffic"
                include_transit:
                  type: boolean
                  default: true
                  description: "Include transit option with Caltrain + shuttle schedules"
        responses:
          200:
            description: Comprehensive commute analysis with AI recommendations
            schema:
              type: object
              properties:
                direction:
                  type: string
                  example: "to_work"
                  description: "Direction of commute"
                query_time:
                  type: string
                  example: "2024-01-15 08:00:00"
                  description: "Time when analysis was generated"
                driving:
                  type: object
                  properties:
                    duration_minutes:
                      type: integer
                      example: 43
                      description: "Driving time with current traffic"
                    distance_miles:
                      type: number
                      example: 40.1
                      description: "Total driving distance"
                    route_summary:
                      type: string
                      example: "South SF → LinkedIn"
                      description: "Clean origin to destination route"
                    traffic_status:
                      type: string
                      example: "Light traffic"
                      description: "Current traffic conditions"
                    estimated_fuel_gallons:
                      type: number
                      example: 1.54
                      description: "Estimated fuel consumption in gallons (26 MPG average)"
                    departure_time:
                      type: string
                      example: "8:00 AM"
                      description: "Recommended departure time"
                    arrival_time:
                      type: string
                      example: "8:43 AM"
                      description: "Estimated arrival time"
                transit:
                  type: object
                  properties:
                    total_duration_minutes:
                      type: integer
                      example: 63
                      description: "Total transit time including all segments"
                    caltrain_duration_minutes:
                      type: integer
                      example: 47
                      description: "Time on Caltrain only"
                    shuttle_duration_minutes:
                      type: integer
                      example: 8
                      description: "Time on MV Connector shuttle"
                    walking_duration_minutes:
                      type: integer
                      example: 3
                      description: "Walking time to/from stations"
                    next_departures:
                      type: array
                      items:
                        type: object
                        properties:
                          departure_time:
                            type: string
                            example: "8:15 AM"
                          arrival_time:
                            type: string
                            example: "9:02 AM"
                          train_number:
                            type: string
                            example: "150"
                      description: "Next available Caltrain departures"
                    shuttle_departures:
                      type: array
                      items:
                        type: object
                        properties:
                          departure_time:
                            type: string
                            example: "9:11 AM"
                          stops:
                            type: array
                            items:
                              type: string
                            example: ["9:11 AM", "9:19 AM", "9:22 AM"]
                      description: "Next available MV Connector shuttles"
                recommendation:
                  type: string
                  example: "Drive - 43 minutes vs Transit - 63 minutes. Driving is 20 minutes faster with light traffic."
                  description: "AI recommendation comparing all options"
          400:
            description: Invalid request format or missing direction
          500:
            description: Commute service error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("mobility.get_commute_options", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in mobility.get_commute_options: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Shuttle schedule tool endpoint
    @app.route('/tools/mobility.get_shuttle_schedule', methods=['POST'])
    async def mobility_get_shuttle_schedule():
        """Get detailed MV Connector shuttle schedules between Mountain View Caltrain, LinkedIn Transit Center, and LinkedIn 950|1000.
        ---
        tags:
          - Mobility
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - origin
                - destination
              properties:
                origin:
                  type: string
                  enum: ['mountain_view_caltrain', 'linkedin_transit_center', 'linkedin_950_1000']
                  example: "mountain_view_caltrain"
                  description: "Starting shuttle stop"
                destination:
                  type: string
                  enum: ['mountain_view_caltrain', 'linkedin_transit_center', 'linkedin_950_1000']
                  example: "linkedin_transit_center"
                  description: "Destination shuttle stop"
                departure_time:
                  type: string
                  example: "9:00 AM"
                  description: "Preferred departure time (format HH-MM AM/PM, optional)"
        responses:
          200:
            description: MV Connector shuttle schedule information
            schema:
              type: object
              properties:
                origin:
                  type: string
                  example: "mountain_view_caltrain"
                  description: "Starting shuttle stop"
                destination:
                  type: string
                  example: "linkedin_transit_center"
                  description: "Destination shuttle stop"
                duration_minutes:
                  type: integer
                  example: 8
                  description: "Travel time between stops in minutes"
                next_departures:
                  type: array
                  items:
                    type: object
                    properties:
                      departure_time:
                        type: string
                        example: "9:11 AM"
                        description: "Departure time from origin"
                      stops:
                        type: array
                        items:
                          type: string
                        example: ["9:11 AM", "9:19 AM", "9:22 AM"]
                        description: "All stop times for this departure"
                  description: "Next available shuttle departures"
                service_hours:
                  type: string
                  example: "6:50 AM - 10:58 AM"
                  description: "Operating hours for this route"
                frequency_minutes:
                  type: string
                  example: "13-17 minutes"
                  description: "Typical frequency between shuttles"
          400:
            description: Invalid request format or missing origin/destination
          500:
            description: Shuttle service error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("mobility.get_shuttle_schedule", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in mobility.get_shuttle_schedule: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Calendar tool endpoint
    @app.route('/tools/calendar.list_events', methods=['POST'])
    async def calendar_list_events():
        """List calendar events for a specific date with Google Calendar integration.
        ---
        tags:
          - Calendar
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - date
              properties:
                date:
                  type: string
                  format: date
                  example: "2024-12-18"
                  description: "Date to list events for (YYYY-MM-DD format)"
        responses:
          200:
            description: Calendar events for the specified date
            schema:
              type: object
              properties:
                date:
                  type: string
                  format: date
                  example: "2024-12-18"
                  description: "Date queried for events"
                events:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        example: "event_123"
                        description: "Unique event identifier"
                      title:
                        type: string
                        example: "Team Meeting"
                        description: "Event title/summary"
                      start_time:
                        type: string
                        format: date-time
                        example: "2024-12-18T10:00:00Z"
                        description: "Event start time (ISO format)"
                      end_time:
                        type: string
                        format: date-time
                        example: "2024-12-18T11:00:00Z"
                        description: "Event end time (ISO format)"
                      location:
                        type: string
                        example: "Conference Room A"
                        description: "Event location (optional)"
                      description:
                        type: string
                        example: "Weekly team sync"
                        description: "Event description (optional)"
                      all_day:
                        type: boolean
                        example: false
                        description: "Whether this is an all-day event"
                      attendees:
                        type: array
                        items:
                          type: string
                        example: ["alice@example.com", "bob@example.com"]
                        description: "List of attendee emails (optional)"
                total_events:
                  type: integer
                  example: 3
                  description: "Total number of events found"
          400:
            description: Invalid request format or missing date
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "JSON body required"
          500:
            description: Internal server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error fetching calendar events"
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("calendar.list_events", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in calendar.list_events: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Calendar range tool endpoint  
    @app.route('/tools/calendar.list_events_range', methods=['POST'])
    async def calendar_list_events_range():
        """List calendar events for a date range (much more efficient than multiple single-date calls).
        ---
        tags:
          - Calendar
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - start_date
                - end_date
              properties:
                start_date:
                  type: string
                  format: date
                  example: "2025-08-18"
                  description: "Start date of the range (YYYY-MM-DD format, inclusive)"
                end_date:
                  type: string
                  format: date
                  example: "2025-08-24"
                  description: "End date of the range (YYYY-MM-DD format, inclusive)"
        responses:
          200:
            description: Calendar events for the specified date range
            schema:
              type: object
              properties:
                start_date:
                  type: string
                  format: date
                  example: "2025-08-18"
                  description: "Start date of the queried range"
                end_date:
                  type: string
                  format: date
                  example: "2025-08-24"
                  description: "End date of the queried range"
                events:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        example: "event_123"
                        description: "Unique event identifier"
                      title:
                        type: string
                        example: "Team Meeting"
                        description: "Event title/summary"
                      start_time:
                        type: string
                        format: date-time
                        example: "2025-08-18T10:00:00Z"
                        description: "Event start time (ISO format)"
                      end_time:
                        type: string
                        format: date-time
                        example: "2025-08-18T11:00:00Z"
                        description: "Event end time (ISO format)"
                      location:
                        type: string
                        example: "Conference Room A"
                        description: "Event location (optional)"
                      description:
                        type: string
                        example: "Weekly team sync"
                        description: "Event description (optional)"
                      all_day:
                        type: boolean
                        example: false
                        description: "Whether this is an all-day event"
                      attendees:
                        type: array
                        items:
                          type: string
                        example: ["alice@example.com", "bob@example.com"]
                        description: "List of attendee emails (optional)"
                total_events:
                  type: integer
                  example: 3
                  description: "Total number of events found in the range"
          400:
            description: Invalid request format or missing dates
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "JSON body required"
          500:
            description: Internal server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error fetching calendar events for range"
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("calendar.list_events_range", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in calendar.list_events_range: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Todo tool endpoint
    @app.route('/tools/todo.list', methods=['POST'])
    async def todo_list():
        """List todo items from Todoist with optional bucket-based filtering.
        ---
        tags:
          - Todo
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              properties:
                bucket:
                  type: string
                  enum: ['work', 'home', 'errands', 'personal']
                  description: "Category/bucket to list todos from. If omitted, returns all todos from all projects."
                  example: "work"
                include_completed:
                  type: boolean
                  default: false
                  description: "Whether to include completed todo items in the results"
                  example: false
        responses:
          200:
            description: List of todo items from specified bucket or all buckets if none specified
            schema:
              type: object
              properties:
                bucket:
                  type: string
                  enum: ['work', 'home', 'errands', 'personal']
                  example: "work"
                  description: "Bucket/category that was queried"
                items:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: string
                        example: "todo_123"
                        description: "Unique todo identifier"
                      title:
                        type: string
                        example: "Complete project proposal"
                        description: "Todo title"
                      description:
                        type: string
                        example: "Finalize the Q1 project proposal document"
                        description: "Detailed description"
                      completed:
                        type: boolean
                        example: false
                        description: "Whether the todo is completed"
                      priority:
                        type: string
                        enum: ['low', 'medium', 'high', 'urgent']
                        example: "high"
                        description: "Priority level"
                      category:
                        type: string
                        example: "work"
                        description: "Todo category"
                      due_date:
                        type: string
                        format: date
                        example: "2024-12-20"
                        description: "Due date (optional)"
                      created_at:
                        type: string
                        format: date-time
                        example: "2024-12-18T10:00:00Z"
                        description: "Creation timestamp"
                total_items:
                  type: integer
                  example: 5
                  description: "Total number of items found"
                completed_count:
                  type: integer
                  example: 1
                  description: "Number of completed items"
                pending_count:
                  type: integer
                  example: 4
                  description: "Number of pending items"
          400:
            description: Invalid request format
          500:
            description: Todo service error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("todo.list", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in todo.list: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Frontend compatibility endpoint for todos
    @app.route('/tools/todos', methods=['GET'])
    async def todos_get():
        """GET endpoint for todos - frontend compatibility."""
        try:
            # Get bucket from query parameters
            bucket = request.args.get('bucket')
            include_completed = request.args.get('include_completed', 'false').lower() == 'true'
            
            # Create TodoInput data
            data = {'include_completed': include_completed}
            if bucket:
                data['bucket'] = bucket
            
            # Create TodoInput instance
            input_data = TodoInput(**data)
            
            # Call the todo tool directly
            from .tools.todo import TodoTool
            todo_tool = TodoTool()
            result = await todo_tool.list_todos(input_data)
            
            # Convert to dict if needed
            if hasattr(result, 'dict'):
                result_dict = result.dict()
            else:
                result_dict = result
                
            return jsonify(result_dict)
            
        except Exception as e:
            logger.error(f"Error in todos GET endpoint: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Todo create tool endpoint
    @app.route('/tools/todo.create', methods=['POST'])
    async def todo_create():
        """Create a new todo item in Todoist with smart categorization and natural language due dates.
        ---
        tags:
          - Todo
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - title
              properties:
                title:
                  type: string
                  description: Todo item title/description
                  example: "Review quarterly reports"
                priority:
                  type: string
                  enum: [low, medium, high, urgent]
                  description: Priority level (defaults to medium)
                  example: "high"
                bucket:
                  type: string
                  enum: [work, home, errands, personal]
                  description: Category/bucket for the todo (defaults to personal)
                  example: "work"
                due_date:
                  type: string
                  description: Due date in natural language
                  example: "next Friday"
                tags:
                  type: array
                  items:
                    type: string
                  description: Tags to associate with the todo
                  example: ["reports", "quarterly"]
                description:
                  type: string
                  description: Additional description or notes
                  example: "Need to review Q4 financial reports"
        responses:
          200:
            description: Todo created successfully
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  description: Whether the todo was created successfully
                todo:
                  type: object
                  description: The created todo item
                message:
                  type: string
                  description: Success message
          400:
            description: Invalid input data
          500:
            description: Internal server error
        """
        try:
            # Get and validate the input data
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("todo.create", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in todo.create: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Todo update tool endpoint
    @app.route('/tools/todo.update', methods=['POST'])
    async def todo_update():
        """Update an existing todo item.
        ---
        tags:
          - Todo
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - id
              properties:
                id:
                  type: string
                  description: Unique todo item identifier to update
                  example: "todo_123"
                title:
                  type: string
                  description: New title/description
                  example: "Review Q4 financial reports (updated)"
                priority:
                  type: string
                  enum: [low, medium, high, urgent]
                  description: New priority level
                  example: "urgent"
                due_date:
                  type: string
                  description: New due date in natural language
                  example: "tomorrow"
                tags:
                  type: array
                  items:
                    type: string
                  description: New tags (replaces existing)
                  example: ["reports", "q4"]
                description:
                  type: string
                  description: New description or notes
        responses:
          200:
            description: Todo updated successfully
            schema:
              type: object
              properties:
                success:
                  type: boolean
                todo:
                  type: object
                  description: The updated todo item
                changes:
                  type: array
                  items:
                    type: string
                  description: List of fields that were changed
                message:
                  type: string
          400:
            description: Invalid input data
          500:
            description: Internal server error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            result = await mcp_server.call_tool("todo.update", data)
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in todo.update: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Todo complete tool endpoint
    @app.route('/tools/todo.complete', methods=['POST'])
    async def todo_complete():
        """Mark a todo item as completed or uncompleted.
        ---
        tags:
          - Todo
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - id
              properties:
                id:
                  type: string
                  description: Unique todo item identifier to complete
                  example: "todo_123"
                completed:
                  type: boolean
                  description: Whether to mark as completed (defaults to true)
                  example: true
        responses:
          200:
            description: Todo completion status updated successfully
            schema:
              type: object
              properties:
                success:
                  type: boolean
                todo:
                  type: object
                  description: The updated todo item
                message:
                  type: string
          400:
            description: Invalid input data
          500:
            description: Internal server error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            result = await mcp_server.call_tool("todo.complete", data)
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in todo.complete: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Todo delete tool endpoint
    @app.route('/tools/todo.delete', methods=['POST'])
    async def todo_delete():
        """Delete a todo item permanently.
        ---
        tags:
          - Todo
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - id
              properties:
                id:
                  type: string
                  description: Unique todo item identifier to delete
                  example: "todo_123"
        responses:
          200:
            description: Todo deleted successfully
            schema:
              type: object
              properties:
                success:
                  type: boolean
                deleted_todo:
                  type: object
                  description: The deleted todo item (for audit trail)
                message:
                  type: string
          400:
            description: Invalid input data
          500:
            description: Internal server error
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            result = await mcp_server.call_tool("todo.delete", data)
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in todo.delete: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Calendar create event tool endpoint
    @app.route('/tools/calendar.create_event', methods=['POST'])
    async def calendar_create_event():
        """Create a new calendar event with Google Calendar integration.
        ---
        tags:
          - Calendar
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - title
                - start_time
                - end_time
              properties:
                title:
                  type: string
                  example: "Lunch with John"
                  description: "Event title/summary"
                start_time:
                  type: string
                  format: date-time
                  example: "2024-12-18T12:00:00"
                  description: "Event start time (ISO format)"
                end_time:
                  type: string
                  format: date-time
                  example: "2024-12-18T13:00:00"
                  description: "Event end time (ISO format)"
                description:
                  type: string
                  example: "Catching up over lunch"
                  description: "Event description/notes (optional)"
                location:
                  type: string
                  example: "Downtown Cafe"
                  description: "Event location (optional)"
                attendees:
                  type: array
                  items:
                    type: string
                  example: ["john@example.com"]
                  description: "List of attendee email addresses (optional)"
                calendar_name:
                  type: string
                  example: "primary"
                  description: "Target calendar name (defaults to primary)"
                all_day:
                  type: boolean
                  example: false
                  description: "Whether this is an all-day event"
        responses:
          200:
            description: Calendar event creation result
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                  description: "Whether the event was created successfully"
                event_id:
                  type: string
                  example: "abc123def456"
                  description: "Google Calendar event ID if created"
                event_url:
                  type: string
                  example: "https://calendar.google.com/calendar/event?eid=abc123def456"
                  description: "URL to view the event in Google Calendar"
                created_event:
                  type: object
                  description: "The created event details"
                message:
                  type: string
                  example: "Event 'Lunch with John' created successfully for December 18, 2024 at 12:00 PM"
                  description: "Success or error message"
                conflicts:
                  type: array
                  items:
                    type: object
                  description: "Any conflicting events found at the same time"
          400:
            description: Invalid request format or missing required fields
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "JSON body required"
          500:
            description: Internal server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error creating calendar event"
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("calendar.create_event", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in calendar.create_event: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/tools/calendar.update_event', methods=['POST'])
    async def calendar_update_event():
        """Update an existing calendar event with Google Calendar integration.
        ---
        tags:
          - Calendar
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - event_id
              properties:
                event_id:
                  type: string
                  example: "abc123def456"
                  description: "Google Calendar event ID to update"
                title:
                  type: string
                  example: "Updated Lunch Meeting"
                  description: "New event title/summary (optional)"
                start_time:
                  type: string
                  format: date-time
                  example: "2024-12-18T13:00:00"
                  description: "New event start time (ISO format, optional)"
                end_time:
                  type: string
                  format: date-time
                  example: "2024-12-18T14:00:00"
                  description: "New event end time (ISO format, optional)"
                description:
                  type: string
                  example: "Updated meeting agenda and notes"
                  description: "New event description/notes (optional)"
                location:
                  type: string
                  example: "Conference Room B"
                  description: "New event location (optional)"
                attendees:
                  type: array
                  items:
                    type: string
                  example: ["john@example.com", "sarah@example.com"]
                  description: "New list of attendee email addresses (optional)"
                calendar_name:
                  type: string
                  example: "primary"
                  description: "Target calendar name (defaults to primary)"
                all_day:
                  type: boolean
                  example: false
                  description: "Whether this should be an all-day event (optional)"
        responses:
          200:
            description: Calendar event update result
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                  description: "Whether the event was updated successfully"
                event_id:
                  type: string
                  example: "abc123def456"
                  description: "Google Calendar event ID that was updated"
                event_url:
                  type: string
                  example: "https://calendar.google.com/calendar/event?eid=abc123def456"
                  description: "URL to view the updated event in Google Calendar"
                updated_event:
                  type: object
                  description: "The updated event details"
                original_event:
                  type: object
                  description: "The original event details before update"
                changes_made:
                  type: array
                  items:
                    type: string
                  example: ["title", "start_time", "location"]
                  description: "List of fields that were changed"
                message:
                  type: string
                  example: "Event 'Updated Lunch Meeting' updated successfully (3 changes: title, start_time, location)"
                  description: "Success or error message"
                conflicts:
                  type: array
                  items:
                    type: object
                  description: "Any conflicting events found at the new time"
          400:
            description: Invalid request format or missing event_id
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "JSON body required"
          404:
            description: Event not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Event with ID abc123def456 not found"
          500:
            description: Internal server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error updating calendar event"
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            if not data.get('event_id'):
                return jsonify({"error": "event_id is required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("calendar.update_event", data)
            
            # Handle event not found as 404
            if not result.get('success') and 'not found' in result.get('message', '').lower():
                return jsonify({"error": result.get('message', 'Event not found')}), 404
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in calendar.update_event: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/tools/calendar.delete_event', methods=['POST'])
    async def calendar_delete_event():
        """Delete a calendar event from Google Calendar.
        ---
        tags:
          - Calendar
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - event_id
              properties:
                event_id:
                  type: string
                  example: "abc123def456"
                  description: "Google Calendar event ID to delete"
                calendar_name:
                  type: string
                  example: "primary"
                  description: "Calendar to delete event from (defaults to primary)"
        responses:
          200:
            description: Calendar event deletion result
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                  description: "Whether the event was deleted successfully"
                event_id:
                  type: string
                  example: "abc123def456"
                  description: "Google Calendar event ID that was deleted"
                deleted_event:
                  type: object
                  description: "The deleted event details"
                message:
                  type: string
                  example: "Event 'Team Meeting' deleted successfully"
                  description: "Success or error message"
          400:
            description: Invalid request format or missing event_id
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "JSON body required"
          404:
            description: Event not found
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Event with ID abc123def456 not found"
          500:
            description: Internal server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error deleting calendar event"
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            if not data.get('event_id'):
                return jsonify({"error": "event_id is required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("calendar.delete_event", data)
            
            # Handle event not found as 404
            if not result.get('success') and 'not found' in result.get('message', '').lower():
                return jsonify({"error": result.get('message', 'Event not found')}), 404
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in calendar.delete_event: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/tools/calendar.find_free_time', methods=['POST'])
    async def calendar_find_free_time():
        """Find available time slots for smart scheduling.
        ---
        tags:
          - Calendar
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - duration_minutes
                - start_date
              properties:
                duration_minutes:
                  type: integer
                  example: 60
                  description: "Duration needed in minutes (e.g., 30, 60, 120)"
                  minimum: 1
                  maximum: 480
                start_date:
                  type: string
                  example: "2024-01-15"
                  description: "Start date to search from (YYYY-MM-DD format)"
                end_date:
                  type: string
                  example: "2024-01-19"
                  description: "End date to search until (YYYY-MM-DD format, defaults to start_date)"
                earliest_time:
                  type: string
                  example: "09:00"
                  description: "Earliest time to consider (format HH-MM 24-hour, defaults to 09-00)"
                latest_time:
                  type: string
                  example: "18:00"
                  description: "Latest time to consider (format HH-MM 24-hour, defaults to 18-00)"
                calendar_names:
                  type: array
                  items:
                    type: string
                  example: ["primary", "work"]
                  description: "Calendars to check for conflicts (defaults to all)"
                max_results:
                  type: integer
                  example: 5
                  description: "Maximum number of time slots to return (defaults to 5)"
                preferred_time:
                  type: string
                  example: "afternoon"
                  enum: ["morning", "afternoon", "evening"]
                  description: "Preferred time preference for scoring"
        responses:
          200:
            description: Available time slots found successfully
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                  description: "Whether free time slots were found"
                free_slots:
                  type: array
                  description: "Available time slots matching criteria"
                  items:
                    type: object
                    properties:
                      start_time:
                        type: string
                        example: "2024-01-15T14:00:00Z"
                        description: "Start time of the free slot"
                      end_time:
                        type: string
                        example: "2024-01-15T15:00:00Z"
                        description: "End time of the free slot"
                      duration_minutes:
                        type: integer
                        example: 60
                        description: "Duration of the slot in minutes"
                      date:
                        type: string
                        example: "2024-01-15"
                        description: "Date of the slot (YYYY-MM-DD)"
                      day_of_week:
                        type: string
                        example: "Monday"
                        description: "Day of week"
                      time_period:
                        type: string
                        example: "afternoon"
                        description: "Time period (morning, afternoon, evening)"
                      preference_score:
                        type: number
                        example: 0.9
                        description: "Score based on preferences (0-1, higher is better)"
                total_slots_found:
                  type: integer
                  example: 3
                  description: "Total number of slots found"
                search_criteria:
                  type: object
                  description: "Summary of search parameters used"
                message:
                  type: string
                  example: "Found 3 available time slots. Top result: Monday 2:00 PM (60 minutes)"
                  description: "Summary message about the search results"
          400:
            description: Invalid input parameters
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "duration_minutes must be positive"
          500:
            description: Internal server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Error finding free time: ..."
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            result = await mcp_server.call_tool("calendar.find_free_time", data)
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in calendar.find_free_time: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Financial tool endpoint
    @app.route('/tools/financial.get_data', methods=['POST'])
    async def financial_get_data():
        """Get real-time financial data for stocks and cryptocurrencies.
        ---
        tags:
          - Financial
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - symbols
              properties:
                symbols:
                  type: array
                  items:
                    type: string
                  example: ["MSFT", "BTC", "ETH", "NVDA"]
                  description: "List of stock/crypto symbols to fetch prices for"
                data_type:
                  type: string
                  enum: ['stocks', 'crypto', 'mixed']
                  default: 'mixed'
                  description: "Type of financial data to retrieve"
        responses:
          200:
            description: Real-time financial market data
            schema:
              type: object
              properties:
                request_time:
                  type: string
                  example: "2025-08-11T11:15:57.827414"
                  description: "Timestamp of request in ISO format"
                total_items:
                  type: integer
                  example: 3
                  description: "Number of financial instruments returned"
                market_status:
                  type: string
                  enum: ['open', 'closed', 'mixed', '24/7']
                  example: "mixed"
                  description: "Current market status"
                summary:
                  type: string
                  example: "📊 3 instruments tracked | 📈 2 gaining | 🏆 Best: BTC (+2.3%)"
                  description: "Human-readable market summary"
                data:
                  type: array
                  items:
                    type: object
                    properties:
                      symbol:
                        type: string
                        example: "MSFT"
                        description: "Trading symbol"
                      name:
                        type: string
                        example: "Microsoft Corporation"
                        description: "Full company/cryptocurrency name"
                      price:
                        type: number
                        example: 522.04
                        description: "Current price in USD"
                      change:
                        type: number
                        example: 1.2
                        description: "Price change since last period"
                      change_percent:
                        type: number
                        example: 0.23
                        description: "Percentage change since last period"
                      currency:
                        type: string
                        example: "USD"
                        description: "Currency of the price"
                      data_type:
                        type: string
                        enum: ['stocks', 'crypto']
                        example: "stocks"
                        description: "Type of financial instrument"
                      last_updated:
                        type: string
                        example: "2025-08-11T11:15:57.826064"
                        description: "Timestamp of last update in ISO format"
          400:
            description: Invalid request format
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "JSON body required"
          500:
            description: Server error
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Internal server error"
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "JSON body required"}), 400
            
            # Call the tool via MCP server
            result = await mcp_server.call_tool("financial.get_data", data)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Error in financial.get_data: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    logger.info("Flask application created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    settings = get_settings()
    app.run(
        host=settings.host,
        port=settings.port,
        debug=settings.debug
    )
