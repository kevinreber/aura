"""Official MCP Protocol implementation using the MCP SDK.

This module provides a standards-compliant MCP server that wraps the existing
tool implementations, enabling compatibility with Claude Desktop, Cursor,
and other MCP clients.

Transports supported:
- SSE (Server-Sent Events) for networked/containerized deployments
- stdio for local process communication
"""

import json
import asyncio
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .server import get_mcp_server
from .utils.logging import get_logger

logger = get_logger("mcp_protocol")

# Create the MCP SDK server instance
mcp_app = Server("aura-mcp-server")

# Get the existing MCP server with all tool implementations
_mcp_server = get_mcp_server()


@mcp_app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available tools in MCP protocol format.

    Converts our internal tool registry to the official MCP Tool format.
    """
    tools = []

    for name, info in _mcp_server.tools.items():
        tool = Tool(
            name=name,
            description=info["description"],
            inputSchema=info["input_schema"].model_json_schema()
        )
        tools.append(tool)

    logger.info(f"MCP list_tools: returning {len(tools)} tools")
    return tools


@mcp_app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool invocation via MCP protocol.

    Delegates to our existing tool implementations and returns results
    in MCP TextContent format.
    """
    logger.info(f"MCP call_tool: {name} with args: {arguments}")

    try:
        # Call the tool through our existing MCPServer
        result = await _mcp_server.call_tool(name, arguments)

        # Convert result to JSON string for MCP response
        result_json = json.dumps(result, indent=2, default=str)

        logger.info(f"MCP call_tool: {name} completed successfully")
        return [TextContent(type="text", text=result_json)]

    except ValueError as e:
        # Tool not found or validation error
        error_msg = f"Error: {str(e)}"
        logger.warning(f"MCP call_tool error: {error_msg}")
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        # Unexpected error
        error_msg = f"Internal error calling {name}: {str(e)}"
        logger.error(f"MCP call_tool exception: {error_msg}")
        return [TextContent(type="text", text=error_msg)]


def get_mcp_app() -> Server:
    """Get the MCP SDK server instance."""
    return mcp_app


# Entry point for stdio transport (for local MCP clients)
async def run_stdio():
    """Run the MCP server using stdio transport.

    Use this for local integrations where the MCP client spawns
    this server as a subprocess.

    Example usage:
        python -m mcp_server.mcp_protocol
    """
    from mcp.server.stdio import stdio_server

    logger.info("Starting MCP server with stdio transport")

    async with stdio_server() as (read_stream, write_stream):
        await mcp_app.run(
            read_stream,
            write_stream,
            mcp_app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(run_stdio())
