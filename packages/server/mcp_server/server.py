"""MCP protocol server implementation.

This module provides a simple MCP-like interface for the morning routine tools.
It can be extended to use the official MCP SDK when available.
"""

from typing import Dict, Any, List
import json
from datetime import datetime

from .tools import WeatherTool, MobilityTool, CalendarTool, TodoTool, FinancialTool, WeekendTools, VaultTool
from .schemas import (
    WeatherInput, WeatherOutput,
    MobilityInput, MobilityOutput, CommuteInput, CommuteOutput,
    ShuttleScheduleInput, ShuttleScheduleOutput,
    CalendarInput, CalendarOutput, CalendarRangeInput, CalendarRangeOutput,
    CalendarCreateInput, CalendarCreateOutput, CalendarUpdateInput, CalendarUpdateOutput,
    CalendarDeleteInput, CalendarDeleteOutput, CalendarFindFreeTimeInput, CalendarFindFreeTimeOutput,
    TodoInput, TodoOutput, TodoCreateInput, TodoCreateOutput,
    TodoUpdateInput, TodoUpdateOutput, TodoCompleteInput, TodoCompleteOutput,
    TodoDeleteInput, TodoDeleteOutput,
    FinancialInput, FinancialOutput,
    TrailSearchInput, TrailSearchOutput,
    ConcertSearchInput, ConcertSearchOutput,
    ItineraryInput, ItineraryOutput,
    VaultSearchInput, VaultSearchOutput,
    VaultReadInput, VaultReadOutput,
    VaultListInput, VaultListOutput,
)
from .utils.logging import get_logger

logger = get_logger("mcp_server")


class MCPServer:
    """
    Simple MCP-like server implementation.
    
    This provides a structured interface for AI agents to discover and call tools.
    When the official MCP SDK is available, this can be replaced or extended.
    """
    
    def __init__(self):
        """Initialize the MCP server with available tools."""
        self.tools = {
            "weather_get_daily": {
                "tool": WeatherTool(),
                "input_schema": WeatherInput,
                "output_schema": WeatherOutput,
                "description": "Get daily weather forecast for a location",
                "method": "get_daily"
            },
            "mobility_get_commute": {
                "tool": MobilityTool(),
                "input_schema": MobilityInput,
                "output_schema": MobilityOutput,
                "description": "Get commute information between two locations",
                "method": "get_commute"
            },
            "mobility_get_commute_options": {
                "tool": MobilityTool(),
                "input_schema": CommuteInput,
                "output_schema": CommuteOutput,
                "description": "Get comprehensive commute options with driving and transit (Caltrain + shuttle) for morning/evening commutes",
                "method": "get_commute_options"
            },
            "mobility_get_shuttle_schedule": {
                "tool": MobilityTool(),
                "input_schema": ShuttleScheduleInput,
                "output_schema": ShuttleScheduleOutput,
                "description": "Get MV Connector shuttle schedule between Mountain View Caltrain, LinkedIn Transit Center, and LinkedIn 950|1000",
                "method": "get_shuttle_schedule"
            },
            "calendar_list_events": {
                "tool": CalendarTool(),
                "input_schema": CalendarInput,
                "output_schema": CalendarOutput,
                "description": "List calendar events for a specific date",
                "method": "list_events"
            },
            "calendar_list_events_range": {
                "tool": CalendarTool(),
                "input_schema": CalendarRangeInput,
                "output_schema": CalendarRangeOutput,
                "description": "List calendar events for a date range (more efficient than multiple single-date calls)",
                "method": "list_events_range"
            },
            "calendar_create_event": {
                "tool": CalendarTool(),
                "input_schema": CalendarCreateInput,
                "output_schema": CalendarCreateOutput,
                "description": "Create a new calendar event with conflict detection and smart scheduling",
                "method": "create_event"
            },
            "calendar_update_event": {
                "tool": CalendarTool(),
                "input_schema": CalendarUpdateInput,
                "output_schema": CalendarUpdateOutput,
                "description": "Update an existing calendar event with conflict detection",
                "method": "update_event"
            },
            "calendar_delete_event": {
                "tool": CalendarTool(),
                "input_schema": CalendarDeleteInput,
                "output_schema": CalendarDeleteOutput,
                "description": "Delete a calendar event",
                "method": "delete_event"
            },
            "calendar_find_free_time": {
                "tool": CalendarTool(),
                "input_schema": CalendarFindFreeTimeInput,
                "output_schema": CalendarFindFreeTimeOutput,
                "description": "Find available time slots based on duration and constraints for smart scheduling",
                "method": "find_free_time"
            },
            "todo_list": {
                "tool": TodoTool(),
                "input_schema": TodoInput,
                "output_schema": TodoOutput,
                "description": "List todo items from a specific bucket",
                "method": "list_todos"
            },
            "todo_create": {
                "tool": TodoTool(),
                "input_schema": TodoCreateInput,
                "output_schema": TodoCreateOutput,
                "description": "Create a new todo item with smart categorization and natural language due dates",
                "method": "create_todo"
            },
            "todo_update": {
                "tool": TodoTool(),
                "input_schema": TodoUpdateInput,
                "output_schema": TodoUpdateOutput,
                "description": "Update an existing todo item (title, priority, due date, tags)",
                "method": "update_todo"
            },
            "todo_complete": {
                "tool": TodoTool(),
                "input_schema": TodoCompleteInput,
                "output_schema": TodoCompleteOutput,
                "description": "Mark a todo item as completed or uncompleted",
                "method": "complete_todo"
            },
            "todo_delete": {
                "tool": TodoTool(),
                "input_schema": TodoDeleteInput,
                "output_schema": TodoDeleteOutput,
                "description": "Delete a todo item permanently",
                "method": "delete_todo"
            },
            "financial_get_data": {
                "tool": FinancialTool(),
                "input_schema": FinancialInput,
                "output_schema": FinancialOutput,
                "description": "Get financial data for stocks and cryptocurrencies",
                "method": "get_financial_data"
            },
            "weekend_get_trails": {
                "tool": WeekendTools(),
                "input_schema": TrailSearchInput,
                "output_schema": TrailSearchOutput,
                "description": "Scout outdoor trails near a location, filtered by activity type and difficulty",
                "method": "get_trails"
            },
            "weekend_get_concerts": {
                "tool": WeekendTools(),
                "input_schema": ConcertSearchInput,
                "output_schema": ConcertSearchOutput,
                "description": "Find upcoming concerts and live music events for tracked artists or by location",
                "method": "get_concerts"
            },
            "weekend_generate_itinerary": {
                "tool": WeekendTools(),
                "input_schema": ItineraryInput,
                "output_schema": ItineraryOutput,
                "description": "Generate a structured multi-day itinerary with points of interest and transit estimates",
                "method": "generate_itinerary"
            },
            "vault_search": {
                "tool": VaultTool(),
                "input_schema": VaultSearchInput,
                "output_schema": VaultSearchOutput,
                "description": "Search Kevin's personal markdown vault (projects, career, meetings, decisions) by keyword or regex; returns ranked snippets with file paths and line numbers",
                "method": "search"
            },
            "vault_read": {
                "tool": VaultTool(),
                "input_schema": VaultReadInput,
                "output_schema": VaultReadOutput,
                "description": "Read a single markdown file from Kevin's personal vault by vault-relative path (use vault_search first to discover paths)",
                "method": "read"
            },
            "vault_list": {
                "tool": VaultTool(),
                "input_schema": VaultListInput,
                "output_schema": VaultListOutput,
                "description": "List immediate children of a folder in Kevin's vault (one level deep) — use to explore vault structure (e.g., list Projects/ to find a project note)",
                "method": "list"
            }
        }
    
    def list_tools(self) -> Dict[str, Any]:
        """
        List all available tools with their schemas.
        
        Returns:
            Dictionary of available tools and their metadata
        """
        tools_info = {}
        
        for tool_name, tool_info in self.tools.items():
            tools_info[tool_name] = {
                "description": tool_info["description"],
                "input_schema": tool_info["input_schema"].model_json_schema(),
                "output_schema": tool_info["output_schema"].__name__
            }
        
        return {
            "tools": tools_info,
            "server_info": {
                "name": "Daily MCP Server",
                "version": "0.1.0",
                "description": "Morning routine tools for AI agents",
                "protocol_version": "custom-1.0"
            }
        }
    
    async def call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a specific tool with input data.
        
        Args:
            tool_name: Name of the tool to call
            input_data: Input parameters for the tool
            
        Returns:
            Tool output data
            
        Raises:
            ValueError: If tool not found or invalid input
        """
        if tool_name not in self.tools:
            available_tools = list(self.tools.keys())
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available_tools}")
        
        tool_info = self.tools[tool_name]
        
        try:
            # Validate input data
            validated_input = tool_info["input_schema"](**input_data)
            
            # Get the tool instance and method
            tool_instance = tool_info["tool"]
            method_name = tool_info["method"]
            method = getattr(tool_instance, method_name)
            
            # Call the tool method
            logger.info(f"Calling tool {tool_name} with input: {input_data}")
            result = await method(validated_input)
            
            # Convert result to dictionary
            if hasattr(result, 'dict'):
                output_data = result.dict()
            else:
                output_data = result
            
            logger.info(f"Tool {tool_name} completed successfully")
            return output_data
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise
    
    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the input/output schema for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Schema information for the tool
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool_info = self.tools[tool_name]
        return {
            "tool_name": tool_name,
            "description": tool_info["description"],
            "input_schema": tool_info["input_schema"].model_json_schema(),
            "output_schema": tool_info["output_schema"].model_json_schema()
        }
    
    def get_server_capabilities(self) -> Dict[str, Any]:
        """
        Get server capabilities and metadata.
        
        Returns:
            Server capabilities information
        """
        return {
            "protocol_version": "custom-1.0",
            "server_name": "Daily MCP Server",
            "server_version": "0.1.0",
            "capabilities": {
                "tools": True,
                "resources": False,  # Not implemented yet
                "prompts": False,    # Not implemented yet
                "sampling": False    # Not implemented yet
            },
            "tool_count": len(self.tools),
            "supported_tool_types": ["weather", "mobility", "calendar", "todo", "financial", "weekend", "vault"],
            "created_at": datetime.now().isoformat()
        }


# Global MCP server instance
mcp_server = MCPServer()


def get_mcp_server() -> MCPServer:
    """Get the global MCP server instance."""
    return mcp_server
