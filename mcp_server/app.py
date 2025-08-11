"""Flask application factory for the MCP server."""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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
    
    # Initialize MCP server
    mcp_server = get_mcp_server()
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.environment
        })
    
    # List available tools
    @app.route('/tools')
    def list_tools():
        """List all available MCP tools."""
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
        """Get financial data for stocks and cryptocurrencies."""
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
