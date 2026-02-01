"""MCP client using official MCP SDK with SSE transport.

This client connects to the MCP server using Server-Sent Events (SSE),
enabling standards-compliant communication and dynamic tool discovery.

Falls back to HTTP REST API if SSE connection fails.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, ClassVar
from dataclasses import dataclass

import httpx
from loguru import logger

from ..models.config import get_settings
from ..utils.constants import (
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRY_EXPONENTIAL_BASE,
    HEALTH_CHECK_TIMEOUT,
)
from ..utils.error_handlers import MCPError


# Try to import MCP SDK - fall back to HTTP-only mode if not available
try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.types import Tool
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    logger.warning("MCP SDK not available, using HTTP-only mode")


@dataclass
class MCPConnection:
    """Represents an active MCP SSE connection."""
    session: Any  # ClientSession when MCP SDK available
    tools: List[Any]


class MCPClient:
    """MCP client with SSE transport and HTTP fallback.

    Provides tool calling capabilities via the Model Context Protocol.
    Falls back to HTTP REST API if SSE is unavailable or fails.
    """

    # Class-level connection cache
    _connection: ClassVar[Optional[MCPConnection]] = None
    _connection_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _tools_cache: ClassVar[Optional[Dict[str, Any]]] = None
    _use_http_fallback: ClassVar[bool] = False
    _http_client: ClassVar[Optional[httpx.AsyncClient]] = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url: str = self.settings.mcp_server_url.rstrip('/')
        # SSE endpoint for MCP protocol
        self.sse_url: str = f"{self.base_url}/mcp/sse"
        # HTTP endpoint for health checks and fallback
        self.health_url: str = f"{self.base_url}/health"
        self.timeout: int = self.settings.mcp_server_timeout

    @classmethod
    async def get_http_client(cls, timeout: int = 45) -> httpx.AsyncClient:
        """Get or create shared HTTP client for fallback mode."""
        async with cls._connection_lock:
            if cls._http_client is None or cls._http_client.is_closed:
                cls._http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout),
                    limits=httpx.Limits(
                        max_connections=100,
                        max_keepalive_connections=20,
                        keepalive_expiry=30.0,
                    ),
                    headers={"Content-Type": "application/json"},
                )
            return cls._http_client

    @classmethod
    async def close_client(cls) -> None:
        """Close the shared HTTP client."""
        async with cls._connection_lock:
            if cls._http_client is not None and not cls._http_client.is_closed:
                await cls._http_client.aclose()
                cls._http_client = None

    async def _call_tool_via_http(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        max_retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """Call a tool via HTTP REST API (fallback mode)."""
        url = f"{self.base_url}/tools/{tool_name}"
        last_exception: Optional[Exception] = None
        delay = RETRY_BASE_DELAY

        client = await self.get_http_client(self.timeout)

        for attempt in range(max_retries + 1):
            try:
                response = await client.post(url, json=arguments)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    raise MCPError(
                        f"HTTP {e.response.status_code}: {e.response.text}",
                    )
                last_exception = e

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e

            except Exception as e:
                last_exception = e

            if attempt < max_retries:
                logger.warning(
                    f"HTTP call attempt {attempt + 1}/{max_retries + 1} failed: {last_exception}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * RETRY_EXPONENTIAL_BASE, RETRY_MAX_DELAY)

        raise MCPError(f"Tool {tool_name} failed after {max_retries + 1} attempts: {last_exception}")

    async def _call_tool_via_sse(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        max_retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """Call a tool via MCP SSE transport."""
        if not MCP_SDK_AVAILABLE:
            raise MCPError("MCP SDK not available")

        last_exception: Optional[Exception] = None
        delay = RETRY_BASE_DELAY

        for attempt in range(max_retries + 1):
            try:
                async with sse_client(self.sse_url) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)

                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                try:
                                    return json.loads(content.text)
                                except json.JSONDecodeError:
                                    return {"result": content.text}

                        return {"result": None}

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"SSE call attempt {attempt + 1}/{max_retries + 1} failed: {e}"
                )

                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * RETRY_EXPONENTIAL_BASE, RETRY_MAX_DELAY)

        raise MCPError(f"SSE call failed after {max_retries + 1} attempts: {last_exception}")

    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server.

        Tries SSE first, falls back to HTTP if SSE fails.
        """
        logger.info(f"Calling MCP tool: {tool_name} with data: {input_data}")

        # If we've already determined SSE doesn't work, use HTTP
        if self._use_http_fallback or not MCP_SDK_AVAILABLE:
            try:
                result = await self._call_tool_via_http(tool_name, input_data)
                logger.success(f"Tool {tool_name} completed via HTTP")
                return result
            except MCPError:
                raise
            except Exception as e:
                raise MCPError(f"HTTP call failed: {e}")

        # Try SSE first
        try:
            result = await self._call_tool_via_sse(tool_name, input_data)
            logger.success(f"Tool {tool_name} completed via SSE")
            return result

        except Exception as sse_error:
            logger.warning(f"SSE failed, falling back to HTTP: {sse_error}")
            MCPClient._use_http_fallback = True

            try:
                result = await self._call_tool_via_http(tool_name, input_data)
                logger.success(f"Tool {tool_name} completed via HTTP fallback")
                return result
            except MCPError:
                raise
            except Exception as e:
                raise MCPError(f"Both SSE and HTTP failed: SSE={sse_error}, HTTP={e}")

    async def get_weather(self, location: str, when: str = "today") -> Dict[str, Any]:
        """Get weather forecast for a location."""
        return await self.call_tool("weather.get_daily", {
            "location": location,
            "when": when
        })

    async def get_calendar_events(self, date: str) -> Dict[str, Any]:
        """Get calendar events for a specific date."""
        return await self.call_tool("calendar.list_events", {
            "date": date
        })

    async def get_calendar_events_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get calendar events for a date range."""
        return await self.call_tool("calendar.list_events_range", {
            "start_date": start_date,
            "end_date": end_date
        })

    async def get_todos(self, bucket: Optional[str] = None, include_completed: bool = False) -> Dict[str, Any]:
        """Get todo items from a bucket or all buckets if bucket is None."""
        params: Dict[str, Any] = {"include_completed": include_completed}
        if bucket is not None:
            params["bucket"] = bucket
        return await self.call_tool("todo.list", params)

    async def get_commute(self, origin: str, destination: str, mode: str = "driving") -> Dict[str, Any]:
        """Get basic commute information between locations."""
        return await self.call_tool("mobility.get_commute", {
            "origin": origin,
            "destination": destination,
            "mode": mode
        })

    async def get_commute_options(
        self,
        direction: str,
        departure_time: Optional[str] = None,
        include_driving: bool = True,
        include_transit: bool = True,
    ) -> Dict[str, Any]:
        """Get comprehensive commute options with driving and transit."""
        params: Dict[str, Any] = {
            "direction": direction,
            "include_driving": include_driving,
            "include_transit": include_transit
        }
        if departure_time:
            params["departure_time"] = departure_time
        return await self.call_tool("mobility.get_commute_options", params)

    async def get_shuttle_schedule(
        self,
        origin: str,
        destination: str,
        departure_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get MV Connector shuttle schedule between stops."""
        params: Dict[str, Any] = {
            "origin": origin,
            "destination": destination
        }
        if departure_time:
            params["departure_time"] = departure_time
        return await self.call_tool("mobility.get_shuttle_schedule", params)

    async def get_all_morning_data(self, date: str) -> Dict[str, Any]:
        """Get all morning routine data in parallel for speed."""
        settings = get_settings()

        tasks = [
            self.get_weather(settings.user_location),
            self.get_calendar_events(date),
            self.get_todos("work"),
            self.get_commute_options("to_work")
        ]

        try:
            weather, calendar, todos, commute = await asyncio.gather(*tasks, return_exceptions=True)

            result: Dict[str, Any] = {}

            if isinstance(weather, Exception):
                logger.warning(f"Weather call failed: {weather}")
                result["weather"] = {"error": str(weather)}
            else:
                result["weather"] = weather

            if isinstance(calendar, Exception):
                logger.warning(f"Calendar call failed: {calendar}")
                result["calendar"] = {"error": str(calendar)}
            else:
                result["calendar"] = calendar

            if isinstance(todos, Exception):
                logger.warning(f"Todos call failed: {todos}")
                result["todos"] = {"error": str(todos)}
            else:
                result["todos"] = todos

            if isinstance(commute, Exception):
                logger.warning(f"Commute call failed: {commute}")
                result["commute"] = {"error": str(commute)}
            else:
                result["commute"] = commute

            return result

        except Exception as e:
            logger.error(f"Error getting morning data: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the MCP server is healthy."""
        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                response = await client.get(self.health_url)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"MCP server health check failed: {e}")
            return False

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the MCP server."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/tools")
                response.raise_for_status()
                data = response.json()
                return [
                    {"name": name, **info}
                    for name, info in data.get("tools", {}).items()
                ]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise MCPError(f"Tool discovery failed: {e}")


# Convenience function for tool discovery
async def discover_mcp_tools(server_url: str) -> List[Dict[str, Any]]:
    """Discover tools from an MCP server."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{server_url.rstrip('/')}/tools")
        response.raise_for_status()
        data = response.json()
        return [
            {"name": name, **info}
            for name, info in data.get("tools", {}).items()
        ]
