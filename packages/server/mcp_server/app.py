"""FastAPI application for the MCP server.

This module provides a FastAPI-based REST API with:
- Automatic OpenAPI/Swagger documentation from Pydantic models
- Native async support for all endpoints
- SSE transport for MCP protocol compatibility
- Rate limiting and CORS support
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .utils.logging import setup_logging, get_logger
from .utils.cache import get_cache_service
from .server import get_mcp_server
from .mcp_sse import router as mcp_router
from .schemas import (
    WeatherInput,
    MobilityInput, CommuteInput, ShuttleScheduleInput,
    CalendarInput, CalendarRangeInput, CalendarCreateInput,
    CalendarUpdateInput, CalendarDeleteInput, FindFreeTimeInput,
    TodoInput, TodoCreateInput, TodoUpdateInput, TodoCompleteInput, TodoDeleteInput,
    FinancialInput,
)

# Initialize logger
logger = get_logger("fastapi_app")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    setup_logging()
    logger.info("Starting MCP Server...")

    # Initialize cache
    cache_service = await get_cache_service()
    stats = await cache_service.get_cache_stats()
    logger.info(f"Cache service initialized: {stats}")

    yield

    # Shutdown
    logger.info("Shutting down MCP Server...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Daily MCP Server API",
        description="""🎉 **Model Context Protocol Server** - Production-ready API for AI agents

**📊 Read Operations**:
- 🌤️ **Weather**: Real-time conditions via OpenWeatherMap
- 📅 **Calendar**: Multi-calendar events via Google Calendar API
- 💰 **Financial**: Live stock/crypto prices via Alpha Vantage & CoinGecko
- 🚗🚂 **Mobility**: Complete commute intelligence with traffic and transit
- ✅ **Todo**: Task management with Todoist integration

**✨ Write Operations**:
- 📅+ **Calendar CRUD**: Create, update, delete events with conflict detection
- ✅+ **Todo CRUD**: Full task management with Todoist sync

**🔌 MCP Protocol**:
- SSE transport for Claude Desktop, Cursor, and other MCP clients
- Connect via `/mcp/sse` endpoint
""",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiter
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"}
        )

    # Get MCP server instance
    mcp_server = get_mcp_server()

    # Include MCP SSE router
    app.include_router(mcp_router, prefix="/mcp", tags=["MCP Protocol"])

    # ==================== System Endpoints ====================

    @app.get("/health", tags=["System"])
    async def health_check():
        """Check service health status."""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "environment": settings.environment
        }

    @app.get("/tools", tags=["System"])
    async def list_tools():
        """List all available MCP tools and their schemas."""
        return mcp_server.list_tools()

    @app.get("/calendars", tags=["System"])
    async def list_calendars():
        """List all available Google calendars."""
        try:
            from .tools.calendar import CalendarTool
            calendar_tool = CalendarTool()

            if calendar_tool.google_calendar_client:
                calendars = calendar_tool.google_calendar_client.get_calendar_list()
                return {
                    "available_calendars": calendars,
                    "total_calendars": len(calendars),
                    "status": "success"
                }
            else:
                raise HTTPException(status_code=500, detail="Google Calendar client not available")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/cache/stats", tags=["System"])
    async def cache_stats():
        """Get cache statistics for monitoring."""
        try:
            cache_service = await get_cache_service()
            stats = await cache_service.get_cache_stats()
            return {"cache_stats": stats, "status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Weather Endpoints ====================

    @app.post("/tools/weather.get_daily", response_model=None, tags=["Weather"])
    async def weather_get_daily(input_data: WeatherInput):
        """Get current weather and daily forecast.

        Returns real-time weather data from OpenWeatherMap including
        temperature, conditions, humidity, and wind speed.
        """
        try:
            result = await mcp_server.call_tool("weather.get_daily", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in weather.get_daily: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Mobility Endpoints ====================

    @app.post("/tools/mobility.get_commute", response_model=None, tags=["Mobility"])
    async def mobility_get_commute(input_data: MobilityInput):
        """Get commute information with travel times and route options.

        Returns driving, walking, transit, or bicycling directions
        with real-time traffic data from Google Maps.
        """
        try:
            result = await mcp_server.call_tool("mobility.get_commute", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in mobility.get_commute: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/mobility.get_commute_options", response_model=None, tags=["Mobility"])
    async def mobility_get_commute_options(input_data: CommuteInput):
        """Get comprehensive commute analysis with driving AND transit options.

        Returns complete analysis including real-time traffic, Caltrain schedules,
        shuttle connections, fuel estimates, and AI recommendations.
        """
        try:
            result = await mcp_server.call_tool("mobility.get_commute_options", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in mobility.get_commute_options: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/mobility.get_shuttle_schedule", response_model=None, tags=["Mobility"])
    async def mobility_get_shuttle_schedule(input_data: ShuttleScheduleInput):
        """Get MV Connector shuttle schedules.

        Returns shuttle times between Mountain View Caltrain,
        LinkedIn Transit Center, and LinkedIn 950|1000.
        """
        try:
            result = await mcp_server.call_tool("mobility.get_shuttle_schedule", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in mobility.get_shuttle_schedule: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Calendar Endpoints ====================

    @app.post("/tools/calendar.list_events", response_model=None, tags=["Calendar"])
    async def calendar_list_events(input_data: CalendarInput):
        """List calendar events for a specific date.

        Returns all events from Google Calendar for the specified date,
        including title, time, location, and attendees.
        """
        try:
            result = await mcp_server.call_tool("calendar.list_events", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in calendar.list_events: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/calendar.list_events_range", response_model=None, tags=["Calendar"])
    async def calendar_list_events_range(input_data: CalendarRangeInput):
        """List calendar events for a date range.

        More efficient than multiple single-date calls. Returns all events
        between start_date and end_date inclusive.
        """
        try:
            result = await mcp_server.call_tool("calendar.list_events_range", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in calendar.list_events_range: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/calendar.create_event", response_model=None, tags=["Calendar"])
    async def calendar_create_event(input_data: CalendarCreateInput):
        """Create a new calendar event.

        Creates an event in Google Calendar with optional attendees,
        location, and conflict detection.
        """
        try:
            result = await mcp_server.call_tool("calendar.create_event", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in calendar.create_event: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/calendar.update_event", response_model=None, tags=["Calendar"])
    async def calendar_update_event(input_data: CalendarUpdateInput):
        """Update an existing calendar event.

        Updates specified fields of an existing Google Calendar event.
        Returns the updated event and list of changes made.
        """
        try:
            result = await mcp_server.call_tool("calendar.update_event", input_data.model_dump())
            if not result.get('success') and 'not found' in result.get('message', '').lower():
                raise HTTPException(status_code=404, detail=result.get('message'))
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in calendar.update_event: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/calendar.delete_event", response_model=None, tags=["Calendar"])
    async def calendar_delete_event(input_data: CalendarDeleteInput):
        """Delete a calendar event.

        Permanently removes an event from Google Calendar.
        Returns the deleted event details for confirmation.
        """
        try:
            result = await mcp_server.call_tool("calendar.delete_event", input_data.model_dump())
            if not result.get('success') and 'not found' in result.get('message', '').lower():
                raise HTTPException(status_code=404, detail=result.get('message'))
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in calendar.delete_event: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/calendar.find_free_time", response_model=None, tags=["Calendar"])
    async def calendar_find_free_time(input_data: FindFreeTimeInput):
        """Find available time slots for scheduling.

        Searches for free time slots across specified calendars,
        with optional time preferences and duration requirements.
        """
        try:
            result = await mcp_server.call_tool("calendar.find_free_time", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in calendar.find_free_time: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Todo Endpoints ====================

    @app.post("/tools/todo.list", response_model=None, tags=["Todo"])
    async def todo_list(input_data: TodoInput):
        """List todo items from Todoist.

        Returns todos from specified bucket (work, home, errands, personal)
        or all buckets if none specified. Supports filtering completed items.
        """
        try:
            result = await mcp_server.call_tool("todo.list", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in todo.list: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/tools/todos", response_model=None, tags=["Todo"])
    async def todos_get(
        bucket: Optional[str] = Query(None, description="Filter by bucket (work, home, errands, personal)"),
        include_completed: bool = Query(False, description="Include completed items")
    ):
        """GET endpoint for todos - frontend compatibility."""
        try:
            input_data = TodoInput(bucket=bucket, include_completed=include_completed)
            result = await mcp_server.call_tool("todo.list", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in todos GET: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/todo.create", response_model=None, tags=["Todo"])
    async def todo_create(input_data: TodoCreateInput):
        """Create a new todo item in Todoist.

        Supports natural language due dates (e.g., "next Friday"),
        priority levels, and bucket categorization.
        """
        try:
            result = await mcp_server.call_tool("todo.create", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in todo.create: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/todo.update", response_model=None, tags=["Todo"])
    async def todo_update(input_data: TodoUpdateInput):
        """Update an existing todo item.

        Update title, priority, due date, or other properties.
        Returns the updated todo and list of changes made.
        """
        try:
            result = await mcp_server.call_tool("todo.update", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in todo.update: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/todo.complete", response_model=None, tags=["Todo"])
    async def todo_complete(input_data: TodoCompleteInput):
        """Mark a todo item as completed or uncompleted.

        Toggle the completion status of a todo item.
        """
        try:
            result = await mcp_server.call_tool("todo.complete", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in todo.complete: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/todo.delete", response_model=None, tags=["Todo"])
    async def todo_delete(input_data: TodoDeleteInput):
        """Delete a todo item permanently.

        Removes the todo from Todoist. Returns deleted item for audit trail.
        """
        try:
            result = await mcp_server.call_tool("todo.delete", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in todo.delete: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Financial Endpoints ====================

    @app.post("/tools/financial.get_data", response_model=None, tags=["Financial"])
    async def financial_get_data(input_data: FinancialInput):
        """Get real-time financial data for stocks and cryptocurrencies.

        Returns current prices, changes, and market status for
        specified symbols from Alpha Vantage and CoinGecko.
        """
        try:
            result = await mcp_server.call_tool("financial.get_data", input_data.model_dump())
            return result
        except Exception as e:
            logger.error(f"Error in financial.get_data: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== Error Handlers ====================

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=404, content={"error": "Endpoint not found"})

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=405, content={"error": "Method not allowed"})

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: HTTPException):
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    logger.info("FastAPI application created successfully")
    return app


# Create app instance for uvicorn
app = create_app()
