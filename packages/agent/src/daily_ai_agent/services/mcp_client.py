"""HTTP client for communicating with the deployed MCP server."""

import httpx
import asyncio
from typing import Dict, Any, Optional, ClassVar
from loguru import logger
from contextlib import asynccontextmanager

from ..models.config import get_settings
from ..utils.constants import (
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    RETRY_EXPONENTIAL_BASE,
    HEALTH_CHECK_TIMEOUT,
)
from ..utils.error_handlers import MCPError


class MCPClient:
    """HTTP client for calling MCP server tools with connection pooling and retry logic."""

    # Class-level connection pool for reuse across instances
    _client: ClassVar[Optional[httpx.AsyncClient]] = None
    _client_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url: str = self.settings.mcp_server_url.rstrip('/')
        self.timeout: int = self.settings.mcp_server_timeout

    @classmethod
    async def get_client(cls, timeout: int = 45) -> httpx.AsyncClient:
        """
        Get or create the shared HTTP client with connection pooling.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Shared AsyncClient instance
        """
        async with cls._client_lock:
            if cls._client is None or cls._client.is_closed:
                cls._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout),
                    limits=httpx.Limits(
                        max_connections=100,
                        max_keepalive_connections=20,
                        keepalive_expiry=30.0,
                    ),
                    headers={"Content-Type": "application/json"},
                )
                logger.debug("Created new HTTP client with connection pooling")
            return cls._client

    @classmethod
    async def close_client(cls) -> None:
        """Close the shared HTTP client."""
        async with cls._client_lock:
            if cls._client is not None and not cls._client.is_closed:
                await cls._client.aclose()
                cls._client = None
                logger.debug("Closed HTTP client")

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = MAX_RETRIES,
    ) -> httpx.Response:
        """
        Make an HTTP request with exponential backoff retry.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            json_data: JSON payload for POST requests
            max_retries: Maximum number of retry attempts

        Returns:
            HTTP response

        Raises:
            MCPError: If all retries fail
        """
        last_exception: Optional[Exception] = None
        delay = RETRY_BASE_DELAY

        client = await self.get_client(self.timeout)

        for attempt in range(max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(url, json=json_data)

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise MCPError(
                        f"HTTP {e.response.status_code}: {e.response.text}",
                        status_code=e.response.status_code,
                    )
                last_exception = e

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e

            except Exception as e:
                last_exception = e

            # Retry logic
            if attempt < max_retries:
                logger.warning(
                    f"Request attempt {attempt + 1}/{max_retries + 1} failed: {last_exception}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * RETRY_EXPONENTIAL_BASE, RETRY_MAX_DELAY)
            else:
                logger.error(f"All {max_retries + 1} attempts failed: {last_exception}")

        raise MCPError(f"Request failed after {max_retries + 1} attempts: {last_exception}")

    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a specific tool on the MCP server.

        Args:
            tool_name: Name of the tool (e.g., 'weather.get_daily')
            input_data: Input parameters for the tool

        Returns:
            Tool response data

        Raises:
            MCPError: If the tool call fails
        """
        url = f"{self.base_url}/tools/{tool_name}"

        logger.info(f"Calling MCP tool: {tool_name} with data: {input_data}")

        try:
            response = await self._request_with_retry("POST", url, json_data=input_data)
            result = response.json()
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
        """
        Get all morning routine data in parallel for speed.

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
            self.get_todos("work"),  # Still use "work" for morning briefing
            self.get_commute_options("to_work")  # Use enhanced commute options for morning briefing
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
        """Check if the MCP server is healthy."""
        try:
            url = f"{self.base_url}/health"
            client = await self.get_client(HEALTH_CHECK_TIMEOUT)
            response = await client.get(url)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"MCP server health check failed: {e}")
            return False
