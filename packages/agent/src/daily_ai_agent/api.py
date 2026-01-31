"""Flask API for the AI agent - provides web endpoints for all agent functionality."""

import asyncio
import uuid
import time
from datetime import datetime
from flask import Flask, request, jsonify, make_response, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from werkzeug.exceptions import BadRequest, InternalServerError
from loguru import logger
from typing import Dict, Any, Optional

from .agent.orchestrator import AgentOrchestrator
from .services.mcp_client import MCPClient
from .models.config import get_settings
from .utils.constants import (
    APP_VERSION,
    APP_NAME,
    APP_DESCRIPTION,
    REQUEST_ID_HEADER,
    RATE_LIMIT_HEADERS,
)
from .utils.error_handlers import handle_api_error, APIError


def create_app(testing: bool = False) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    settings = get_settings()

    # Configure CORS
    CORS(app, origins=settings.allowed_origins)

    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute} per minute"]
    )

    # Configure Swagger UI
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
            "title": APP_NAME + " API",
            "description": APP_DESCRIPTION,
            "contact": {
                "responsibleOrganization": "Personal Learning Project",
                "responsibleDeveloper": "Kevin Reber",
            },
            "version": APP_VERSION
        },
        "host": "localhost:8001" if settings.environment == "development" else None,
        "basePath": "/",
        "schemes": ["http"] if settings.environment == "development" else ["https"],
        "produces": ["application/json"],
        "consumes": ["application/json"]
    }

    swagger = Swagger(app, config=swagger_config, template=swagger_template)

    # Initialize services
    orchestrator = AgentOrchestrator()
    mcp_client = MCPClient()

    # ==================== Middleware ====================

    @app.before_request
    def before_request():
        """Add request ID and start timing for each request."""
        # Generate or use existing request ID
        g.request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        g.start_time = time.time()

        # Log incoming request
        logger.info(
            f"[{g.request_id}] {request.method} {request.path} "
            f"- Client: {request.remote_addr}"
        )

    @app.after_request
    def after_request(response):
        """Add standard headers to response."""
        # Add request ID to response
        response.headers[REQUEST_ID_HEADER] = g.get('request_id', 'unknown')

        # Calculate request duration
        duration = time.time() - g.get('start_time', time.time())
        response.headers['X-Response-Time'] = f"{duration:.3f}s"

        # Log response
        logger.info(
            f"[{g.get('request_id', 'unknown')}] {request.method} {request.path} "
            f"- Status: {response.status_code} - Duration: {duration:.3f}s"
        )

        return response

    # ==================== Error Handlers ====================

    @app.errorhandler(Exception)
    def handle_error(error):
        """Global error handler with request ID."""
        request_id = g.get('request_id', 'unknown')
        logger.error(f"[{request_id}] API error: {error}")

        if isinstance(error, BadRequest):
            return jsonify({
                "error": "Invalid request format",
                "request_id": request_id,
            }), 400
        elif isinstance(error, APIError):
            response_dict, status_code = handle_api_error(error)
            response_dict["request_id"] = request_id
            return jsonify(response_dict), status_code
        else:
            return jsonify({
                "error": "Internal server error",
                "request_id": request_id,
            }), 500

    # ==================== System Endpoints ====================

    @app.route('/health', methods=['GET'])
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
                service:
                  type: string
                  example: "Daily AI Agent API"
                version:
                  type: string
                  example: "0.2.0"
                ai_enabled:
                  type: boolean
                  example: true
                mcp_server:
                  type: string
                  example: "https://web-production-66f9.up.railway.app"
        """
        return jsonify({
            "status": "healthy",
            "service": APP_NAME,
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
            "mcp_server": settings.mcp_server_url,
            "ai_enabled": orchestrator.is_conversational(),
            "request_id": g.get('request_id', 'unknown'),
        })

    @app.route('/version', methods=['GET'])
    def get_version():
        """Get API version information.
        ---
        tags:
          - System
        responses:
          200:
            description: Version information
            schema:
              type: object
              properties:
                version:
                  type: string
                  example: "0.2.0"
                name:
                  type: string
                  example: "Daily AI Agent"
                environment:
                  type: string
                  example: "production"
        """
        return jsonify({
            "version": APP_VERSION,
            "name": APP_NAME,
            "description": APP_DESCRIPTION,
            "environment": settings.environment,
            "timestamp": datetime.now().isoformat(),
        })

    # ==================== AI Features ====================

    @app.route('/chat', methods=['POST'])
    @limiter.limit("10 per minute")
    async def chat():
        """Natural language conversation with AI assistant
        ---
        tags:
          - AI Features
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - message
              properties:
                message:
                  type: string
                  example: "What's my day looking like?"
                  description: "Natural language query to the AI assistant"
        responses:
          200:
            description: AI assistant response
            schema:
              type: object
              properties:
                response:
                  type: string
                  example: "Today you should focus on your 3 pending tasks. Weather is nice at 77°F!"
                timestamp:
                  type: string
                  example: "2025-08-11T00:16:05.255826"
          400:
            description: Invalid request format
          503:
            description: AI features not available (missing OpenAI API key)
        """
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                raise BadRequest("Missing 'message' field in request body")

            message = data['message'].strip()
            if not message:
                raise BadRequest("Message cannot be empty")

            if not orchestrator.is_conversational():
                return jsonify({
                    "error": "Conversational AI not available",
                    "message": "OpenAI API key required for chat functionality",
                    "request_id": g.get('request_id', 'unknown'),
                }), 503

            logger.info(f"[{g.request_id}] Chat request: {message[:100]}...")
            response = await orchestrator.chat(message)

            return jsonify({
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except BadRequest as e:
            raise e
        except Exception as e:
            logger.error(f"[{g.request_id}] Chat error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/briefing', methods=['GET'])
    @limiter.limit("20 per minute")
    async def briefing():
        """Get morning briefing (basic data or AI-powered)
        ---
        tags:
          - AI Features
        parameters:
          - name: type
            in: query
            type: string
            enum: ['basic', 'smart']
            default: 'basic'
            description: "Type of briefing: 'basic' (structured data) or 'smart' (AI-generated)"
        responses:
          200:
            description: Morning briefing
            schema:
              type: object
              properties:
                type:
                  type: string
                  example: "smart"
                briefing:
                  type: string
                  example: "Good morning! Weather is 77°F, you have 3 pending tasks..."
                timestamp:
                  type: string
          503:
            description: Smart briefing not available (missing OpenAI API key)
        """
        try:
            briefing_type = request.args.get('type', 'basic').lower()

            if briefing_type == 'smart':
                if not orchestrator.is_conversational():
                    return jsonify({
                        "error": "Smart briefing not available",
                        "message": "OpenAI API key required for AI briefings",
                        "request_id": g.get('request_id', 'unknown'),
                    }), 503

                logger.info(f"[{g.request_id}] Generating smart briefing")
                briefing_text = await orchestrator.get_smart_briefing()

                return jsonify({
                    "type": "smart",
                    "briefing": briefing_text,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.get('request_id', 'unknown'),
                })

            else:  # Basic briefing
                logger.info(f"[{g.request_id}] Generating basic briefing")
                today = datetime.now().strftime('%Y-%m-%d')
                data = await mcp_client.get_all_morning_data(today)

                return jsonify({
                    "type": "basic",
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.get('request_id', 'unknown'),
                })

        except Exception as e:
            logger.error(f"[{g.request_id}] Briefing error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    # ==================== Tool Endpoints ====================

    @app.route('/tools/weather', methods=['GET'])
    async def get_weather():
        """Get weather forecast with real OpenWeatherMap data
        ---
        tags:
          - Tools
        parameters:
          - name: location
            in: query
            type: string
            default: "San Francisco"
            description: "Location name (city, state/country)"
            example: "San Francisco"
          - name: when
            in: query
            type: string
            enum: ['today', 'tomorrow']
            default: 'today'
            description: "Time period for forecast"
        responses:
          200:
            description: Weather forecast data
        """
        try:
            location = request.args.get('location', settings.user_location)
            when = request.args.get('when', 'today')

            logger.info(f"[{g.request_id}] Weather request: {location}, {when}")
            weather_data = await mcp_client.get_weather(location, when)

            return jsonify({
                "tool": "weather",
                "data": weather_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Weather error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools/todos', methods=['GET'])
    async def get_todos():
        """Get todo items."""
        try:
            bucket = request.args.get('bucket')
            include_completed = request.args.get('include_completed', 'false').lower() == 'true'

            bucket_label = bucket if bucket else "all"
            logger.info(f"[{g.request_id}] Todos request: {bucket_label}, include_completed={include_completed}")
            todos_data = await mcp_client.get_todos(bucket, include_completed)

            return jsonify({
                "tool": "todos",
                "data": todos_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Todos error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools/calendar', methods=['GET'])
    async def get_calendar():
        """Get calendar events."""
        try:
            date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

            logger.info(f"[{g.request_id}] Calendar request: {date}")
            calendar_data = await mcp_client.get_calendar_events(date)

            return jsonify({
                "tool": "calendar",
                "data": calendar_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Calendar error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools/commute', methods=['GET'])
    async def get_commute():
        """Get commute information."""
        try:
            origin = request.args.get('origin', settings.default_commute_origin)
            destination = request.args.get('destination', settings.default_commute_destination)
            mode = request.args.get('mode', 'driving')

            logger.info(f"[{g.request_id}] Commute request: {origin} -> {destination} ({mode})")
            commute_data = await mcp_client.get_commute(origin, destination, mode)

            return jsonify({
                "tool": "commute",
                "data": commute_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Commute error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools/commute-options', methods=['POST'])
    async def get_commute_options():
        """Get comprehensive commute options with driving and transit analysis."""
        try:
            data = request.get_json() or {}
            direction = data.get('direction', 'to_work')
            departure_time = data.get('departure_time')
            include_driving = data.get('include_driving', True)
            include_transit = data.get('include_transit', True)

            logger.info(f"[{g.request_id}] Commute options request: {direction}")
            commute_data = await mcp_client.get_commute_options(
                direction, departure_time, include_driving, include_transit
            )

            return jsonify({
                "tool": "commute_options",
                "data": commute_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Commute options error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools/shuttle', methods=['POST'])
    async def get_shuttle_schedule():
        """Get MV Connector shuttle schedule."""
        try:
            data = request.get_json() or {}
            origin = data.get('origin')
            destination = data.get('destination')
            departure_time = data.get('departure_time')

            if not origin or not destination:
                return jsonify({
                    "error": "origin and destination are required",
                    "request_id": g.get('request_id', 'unknown'),
                }), 400

            logger.info(f"[{g.request_id}] Shuttle request: {origin} -> {destination}")
            shuttle_data = await mcp_client.get_shuttle_schedule(origin, destination, departure_time)

            return jsonify({
                "tool": "shuttle",
                "data": shuttle_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Shuttle error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools/financial', methods=['POST'])
    async def get_financial():
        """Get real-time stock and cryptocurrency market data."""
        try:
            data = request.get_json()
            if not data or 'symbols' not in data:
                return jsonify({
                    "error": "Missing 'symbols' field in request body",
                    "request_id": g.get('request_id', 'unknown'),
                }), 400

            symbols = data['symbols']
            data_type = data.get('data_type', 'mixed')

            if not isinstance(symbols, list) or not symbols:
                return jsonify({
                    "error": "'symbols' must be a non-empty array",
                    "request_id": g.get('request_id', 'unknown'),
                }), 400

            logger.info(f"[{g.request_id}] Financial request: {symbols} ({data_type})")
            financial_data = await mcp_client.call_tool("financial.get_data", {
                "symbols": symbols,
                "data_type": data_type
            })

            return jsonify({
                "tool": "financial",
                "data": financial_data,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.get('request_id', 'unknown'),
            })

        except Exception as e:
            logger.error(f"[{g.request_id}] Financial error: {e}")
            return jsonify({
                "error": str(e),
                "request_id": g.get('request_id', 'unknown'),
            }), 500

    @app.route('/tools', methods=['GET'])
    def list_tools():
        """List all available tools and their endpoints."""
        return jsonify({
            "tools": {
                "weather": {
                    "endpoint": "/tools/weather",
                    "method": "GET",
                    "description": "Get weather forecast",
                    "params": ["location", "when"]
                },
                "todos": {
                    "endpoint": "/tools/todos",
                    "method": "GET",
                    "description": "Get todo items",
                    "params": ["bucket", "include_completed"]
                },
                "calendar": {
                    "endpoint": "/tools/calendar",
                    "method": "GET",
                    "description": "Get calendar events",
                    "params": ["date"]
                },
                "commute": {
                    "endpoint": "/tools/commute",
                    "method": "GET",
                    "description": "Get basic commute information",
                    "params": ["origin", "destination", "mode"]
                },
                "commute_options": {
                    "endpoint": "/tools/commute-options",
                    "method": "POST",
                    "description": "Get comprehensive commute analysis with driving vs transit options",
                    "body": ["direction", "departure_time", "include_driving", "include_transit"]
                },
                "shuttle": {
                    "endpoint": "/tools/shuttle",
                    "method": "POST",
                    "description": "Get MV Connector shuttle schedule",
                    "body": ["origin", "destination", "departure_time"]
                },
                "financial": {
                    "endpoint": "/tools/financial",
                    "method": "POST",
                    "description": "Get real-time stock and crypto prices",
                    "params": ["symbols", "data_type"]
                }
            },
            "ai_features": {
                "chat": {
                    "endpoint": "/chat",
                    "method": "POST",
                    "description": "Natural language conversation",
                    "body": {"message": "string"}
                },
                "briefing": {
                    "endpoint": "/briefing",
                    "method": "GET",
                    "description": "Morning briefing (basic or smart)",
                    "params": ["type"]
                }
            },
            "system": {
                "health": {
                    "endpoint": "/health",
                    "method": "GET",
                    "description": "Health check"
                },
                "version": {
                    "endpoint": "/version",
                    "method": "GET",
                    "description": "Version information"
                }
            },
            "version": APP_VERSION,
            "available": orchestrator.is_conversational(),
            "timestamp": datetime.now().isoformat(),
            "request_id": g.get('request_id', 'unknown'),
        })

    return app
