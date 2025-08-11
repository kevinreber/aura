"""MCP protocol server implementation.

This module provides a simple MCP-like interface for the morning routine tools.
It can be extended to use the official MCP SDK when available.
"""

from typing import Dict, Any, List
import json
from datetime import datetime

from .tools import WeatherTool, MobilityTool, CalendarTool, TodoTool
from .schemas import (
    WeatherInput, WeatherOutput,
    MobilityInput, MobilityOutput, 
    CalendarInput, CalendarOutput,
    TodoInput, TodoOutput
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
            "weather.get_daily": {
                "tool": WeatherTool(),
                "input_schema": WeatherInput,
                "output_schema": WeatherOutput,
                "description": "Get daily weather forecast for a location",
                "method": "get_daily"
            },
            "mobility.get_commute": {
                "tool": MobilityTool(),
                "input_schema": MobilityInput,
                "output_schema": MobilityOutput,
                "description": "Get commute information between two locations",
                "method": "get_commute"
            },
            "calendar.list_events": {
                "tool": CalendarTool(),
                "input_schema": CalendarInput,
                "output_schema": CalendarOutput,
                "description": "List calendar events for a specific date",
                "method": "list_events"
            },
            "todo.list": {
                "tool": TodoTool(),
                "input_schema": TodoInput,
                "output_schema": TodoOutput,
                "description": "List todo items from a specific bucket",
                "method": "list_todos"
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
            "supported_tool_types": ["weather", "mobility", "calendar", "todo"],
            "created_at": datetime.now().isoformat()
        }


# Global MCP server instance
mcp_server = MCPServer()


def get_mcp_server() -> MCPServer:
    """Get the global MCP server instance."""
    return mcp_server
