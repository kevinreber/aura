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
from .server import get_mcp_server
from .schemas import (
    WeatherInput, MobilityInput, CalendarInput, TodoInput, FinancialInput
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
            "description": """Model Context Protocol server providing comprehensive morning routine tools for AI agents.

🌤️ **Weather**: Real-time conditions via OpenWeatherMap  
📅 **Calendar**: Google Calendar integration with real events  
💰 **Financial**: Stock/crypto prices via Alpha Vantage & CoinGecko  
🚗 **Mobility**: Commute times via Google Maps  
✅ **Todo**: Task management with filtering  

**Quick Start**: All endpoints require POST with JSON body. Real APIs available when configured.""",
            "contact": {
                "responsibleOrganization": "Personal Learning Project",
                "responsibleDeveloper": "Kevin Reber",
                "email": "kevinreber1@gmail.com"
            },
            "version": "0.1.0",
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
            {"name": "Health", "description": "System health and status"},
            {"name": "Tools", "description": "Available MCP tools"},
            {"name": "Weather", "description": "Real-time weather via OpenWeatherMap"},
            {"name": "Calendar", "description": "Google Calendar integration"},
            {"name": "Financial", "description": "Stock and crypto market data"},
            {"name": "Mobility", "description": "Commute and traffic info"},
            {"name": "Todo", "description": "Task management"}
        ]
    }
    
    swagger = Swagger(app, config=swagger_config, template=swagger_template)
    
    # Initialize MCP server
    mcp_server = get_mcp_server()
    
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
            "version": "0.1.0",
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
        """List todo items and tasks with optional filtering and categorization.
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
                filter:
                  type: string
                  enum: ['all', 'pending', 'completed', 'high_priority']
                  default: 'all'
                  description: "Filter todos by status or priority"
                category:
                  type: string
                  example: "work"
                  description: "Filter by category (optional)"
                limit:
                  type: integer
                  example: 10
                  description: "Maximum number of todos to return (optional)"
        responses:
          200:
            description: List of todo items
            schema:
              type: object
              properties:
                total_todos:
                  type: integer
                  example: 5
                  description: "Total number of todos"
                filter_applied:
                  type: string
                  example: "all"
                  description: "Filter that was applied"
                todos:
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
