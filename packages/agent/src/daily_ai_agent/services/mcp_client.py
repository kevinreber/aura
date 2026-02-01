"""MCP client using official MCP SDK with SSE transport.

This client connects to the MCP server using Server-Sent Events (SSE),
enabling standards-compliant communication and dynamic tool discovery.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, ClassVar
from dataclasses import dataclass
from contextlib import asynccontextmanager

from loguru import logger
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool

from ..models.config import get_settings
from ..utils.constants import (
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRY_EXPONENTIAL_BASE,
    HEALTH_CHECK_TIMEOUT,
)
from ..utils.error_handlers import MCPError


@dataclass
class MCPConnection:
    """Represents an active MCP SSE connection."""

    session: ClientSession
    tools: List[Tool]


class MCPClient:
    """MCP client using official SDK with SSE transport.

    Provides tool calling capabilities via the Model Context Protocol,
    with automatic reconnection and retry logic.
    """

    # Class-level connection cache
    _connection: ClassVar[Optional[MCPConnection]] = None
    _connection_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _tools_cache: ClassVar[Optional[Dict[str, Tool]]] = None

    def __init__(self) -> None:
        self.settings = get_settings()
        # SSE endpoint for MCP protocol
        self.sse_url: str = f"{self.settings.mcp_server_url.rstrip('/')}/mcp/sse"
        # HTTP endpoint for health checks (non-MCP)
        self.health_url: str = f"{self.settings.mcp_server_url.rstrip('/')}/health"
        self.timeout: int = self.settings.mcp_server_timeout

    @classmethod
    async def _create_session(cls, sse_url: str) -> MCPConnection:
        """Create a new MCP session via SSE transport.

        Args:
            sse_url: URL of the MCP SSE endpoint

        Returns:
            MCPConnection with active session and discovered tools
        """
        logger.info(f"Connecting to MCP server via SSE: {sse_url}")

        async with sse_client(sse_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the session
                await session.initialize()
                logger.info("MCP session initialized")

                # Discover available tools
                tools_response = await session.list_tools()
                tools = tools_response.tools
                logger.info(f"Discovered {len(tools)} tools from MCP server")

                return MCPConnection(session=session, tools=tools)

    @classmethod
    def _get_tools_cache(cls) -> Dict[str, Tool]:
        """Get cached tools dictionary."""
        if cls._tools_cache is None:
            cls._tools_cache = {}
        return cls._tools_cache

    @classmethod
    async def discover_tools(cls, sse_url: str) -> List[Dict[str, Any]]:
        """Discover available tools from the MCP server.

        Args:
            sse_url: URL of the MCP SSE endpoint

        Returns:
            List of tool definitions with name, description, and schema
        """
        try:
            async with sse_client(sse_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()

                    tools_list = []
                    for tool in tools_response.tools:
                        tools_list.append({
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                        })

                    # Cache the tools
                    cls._tools_cache = {t.name: t for t in tools_response.tools}

                    return tools_list

        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            raise MCPError(f"Tool discovery failed: {e}")

    async def _call_tool_with_retry(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        max_retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """Call a tool with retry logic.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool input arguments
            max_retries: Maximum retry attempts

        Returns:
            Tool response data

        Raises:
            MCPError: If all retries fail
        """
        last_exception: Optional[Exception] = None
        delay = RETRY_BASE_DELAY

        for attempt in range(max_retries + 1):
            try:
                async with sse_client(self.sse_url) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()

                        # Call the tool
                        result = await session.call_tool(tool_name, arguments)

                        # Extract text content from response
                        if result.content and len(result.content) > 0:
                            content = result.content[0]
                            if hasattr(content, 'text'):
                                # Parse JSON response
                                try:
                                    return json.loads(content.text)
                                except json.JSONDecodeError:
                                    # Return as-is if not JSON
                                    return {"result": content.text}

                        return {"result": None}

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"MCP call attempt {attempt + 1}/{max_retries + 1} failed: {e}"
                )

                if attempt < max_retries:
                    logger.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    delay = min(delay * RETRY_EXPONENTIAL_BASE, RETRY_MAX_DELAY)

        error_msg = f"Tool {tool_name} failed after {max_retries + 1} attempts: {last_exception}"
        logger.error(error_msg)
        raise MCPError(error_msg)

    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server.

        Args:
            tool_name: Name of the tool (e.g., 'weather.get_daily')
            input_data: Input parameters for the tool

        Returns:
            Tool response data

        Raises:
            MCPError: If the tool call fails
        """
        logger.info(f"Calling MCP tool: {tool_name} with data: {input_data}")

        try:
            result = await self._call_tool_with_retry(tool_name, input_data)
            logger.success(f"Tool {tool_name} completed successfully")
            return result

        except MCPError:
            raise
        except Exception as e:
            error_msg = f"Error calling {tool_name}: {str(e)}"
            logger.error(error_msg)
            raise MCPError(error_msg)

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
        """Get calendar events for a date range (more efficient than multiple single-date calls)."""
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
        """Get comprehensive commute options with driving and transit (Caltrain + shuttle)."""
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
        """Get all morning routine data in parallel for speed.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Combined data from all tools
        """
        settings = get_settings()

        # Call all tools in parallel for speed
        tasks = [
            self.get_weather(settings.user_location),
            self.get_calendar_events(date),
            self.get_todos("work"),
            self.get_commute_options("to_work")
        ]

        try:
            weather, calendar, todos, commute = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions gracefully
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
        """Check if the MCP server is healthy.

        Uses the MCP health endpoint to verify connectivity.
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                # Check both standard health and MCP health endpoints
                response = await client.get(self.health_url)
                response.raise_for_status()

                # Also verify MCP endpoint is accessible
                mcp_health_url = f"{self.settings.mcp_server_url.rstrip('/')}/mcp/health"
                mcp_response = await client.get(mcp_health_url)
                mcp_response.raise_for_status()

                return True

        except Exception as e:
            logger.error(f"MCP server health check failed: {e}")
            return False

    async def list_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the MCP server.

        Returns:
            List of tool definitions
        """
        return await self.discover_tools(self.sse_url)


# Convenience function for one-off tool discovery
async def discover_mcp_tools(server_url: str) -> List[Dict[str, Any]]:
    """Discover tools from an MCP server.

    Args:
        server_url: Base URL of the MCP server

    Returns:
        List of available tools
    """
    sse_url = f"{server_url.rstrip('/')}/mcp/sse"
    return await MCPClient.discover_tools(sse_url)
