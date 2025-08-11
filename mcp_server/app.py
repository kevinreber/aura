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
            "description": "Model Context Protocol server providing morning routine tools for AI agents",
            "contact": {
                "responsibleOrganization": "Personal Learning Project",
                "responsibleDeveloper": "Kevin Reber",
            },
            "version": "0.1.0"
        },
        "host": "localhost:8000" if settings.environment == "development" else None,
        "basePath": "/",
        "schemes": ["http"] if settings.environment == "development" else ["https"],
        "produces": ["application/json"],
        "consumes": ["application/json"]
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
        """Get daily weather forecast."""
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
        """Get commute information."""
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
        """List calendar events."""
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
    
    # Todo tool endpoint
    @app.route('/tools/todo.list', methods=['POST'])
    async def todo_list():
        """List todo items."""
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
