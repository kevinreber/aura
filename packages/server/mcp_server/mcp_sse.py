"""SSE (Server-Sent Events) transport for MCP protocol using FastAPI.

This module implements the MCP SSE transport specification with proper
async support, enabling MCP clients like Claude Desktop and Cursor to
connect to the server.

Protocol flow:
1. Client connects to GET /sse to establish SSE stream
2. Server sends endpoint URL for client messages
3. Client sends JSON-RPC messages to POST /messages
4. Server responds via SSE stream

Reference: https://modelcontextprotocol.io/docs/concepts/transports#server-sent-events-sse
"""

import json
import asyncio
import uuid
from typing import Optional, AsyncGenerator
from dataclasses import dataclass, field

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .mcp_protocol import get_mcp_app
from .utils.logging import get_logger

logger = get_logger("mcp_sse")

# Create FastAPI router for MCP endpoints
router = APIRouter()


@dataclass
class SSESession:
    """Represents an active SSE client session."""

    session_id: str
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    connected: bool = True


# Active SSE sessions
_sessions: dict[str, SSESession] = {}


def create_session() -> SSESession:
    """Create a new SSE session."""
    session_id = str(uuid.uuid4())
    session = SSESession(session_id=session_id)
    _sessions[session_id] = session
    logger.info(f"Created MCP SSE session: {session_id}")
    return session


def get_session(session_id: str) -> Optional[SSESession]:
    """Get an existing SSE session."""
    return _sessions.get(session_id)


def remove_session(session_id: str) -> None:
    """Remove an SSE session."""
    if session_id in _sessions:
        _sessions[session_id].connected = False
        del _sessions[session_id]
        logger.info(f"Removed MCP SSE session: {session_id}")


async def handle_jsonrpc_message(message: dict, session: SSESession) -> Optional[dict]:
    """Process a JSON-RPC message and return the response.

    Routes messages to the appropriate MCP handlers.
    """
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {})

    try:
        if method == "initialize":
            # Handle initialization
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "aura-mcp-server",
                    "version": "2.0.0"
                },
                "capabilities": {
                    "tools": {"listChanged": False}
                }
            }
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}

        elif method == "tools/list":
            # List available tools
            from .mcp_protocol import handle_list_tools
            tools = await handle_list_tools()
            tools_data = [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema
                }
                for t in tools
            ]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_data}}

        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            from .mcp_protocol import handle_call_tool
            content = await handle_call_tool(tool_name, arguments)

            content_data = [{"type": c.type, "text": c.text} for c in content]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": content_data}}

        elif method == "notifications/initialized":
            # Client acknowledges initialization - no response needed
            return None

        elif method == "ping":
            # Health check
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        else:
            # Unknown method
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    except Exception as e:
        logger.error(f"Error handling JSON-RPC message: {e}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }


async def event_generator(session: SSESession, request: Request) -> AsyncGenerator[dict, None]:
    """Generate SSE events for the MCP protocol.

    Yields events in the format expected by sse-starlette:
    - {"event": "endpoint", "data": "/mcp/messages?session_id=xxx"}
    - {"event": "message", "data": "...json..."}
    """
    try:
        # Send the endpoint URL for client messages
        endpoint_url = f"/mcp/messages?session_id={session.session_id}"
        yield {"event": "endpoint", "data": endpoint_url}
        logger.debug(f"Sent endpoint URL: {endpoint_url}")

        # Keep connection alive and send queued messages
        while session.connected:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(f"Client disconnected: {session.session_id}")
                break

            try:
                # Wait for messages with timeout for keepalive
                message = await asyncio.wait_for(
                    session.message_queue.get(),
                    timeout=30.0
                )
                yield {"event": "message", "data": json.dumps(message)}
                logger.debug(f"Sent message to client: {session.session_id}")

            except asyncio.TimeoutError:
                # Send keepalive comment
                yield {"comment": "keepalive"}

    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled: {session.session_id}")
    except Exception as e:
        logger.error(f"Error in SSE event generator: {e}")
    finally:
        remove_session(session.session_id)


@router.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP protocol clients.

    Establishes an SSE connection for MCP clients like Claude Desktop and Cursor.
    The server sends an 'endpoint' event with the URL for posting messages,
    then streams 'message' events for responses.
    """
    session = create_session()

    return EventSourceResponse(
        event_generator(session, request),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/messages")
async def messages_endpoint(request: Request, session_id: str):
    """Receive JSON-RPC messages from MCP clients.

    Clients POST messages here after connecting via /sse.
    Responses are sent back via the SSE stream.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid or expired session")

    try:
        message = await request.json()
        if not message:
            raise HTTPException(status_code=400, detail="JSON body required")

        logger.debug(f"Received MCP message: {message.get('method', 'unknown')}")

        # Process the message
        response = await handle_jsonrpc_message(message, session)

        if response:
            # Queue response for SSE delivery
            await session.message_queue.put(response)

        # Return 202 Accepted - response will come via SSE
        return JSONResponse(status_code=202, content={})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing MCP message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def mcp_health():
    """Health check for MCP SSE transport.

    Returns health status of the MCP SSE transport layer,
    including number of active sessions.
    """
    return {
        "status": "healthy",
        "transport": "sse",
        "active_sessions": len(_sessions),
        "protocol_version": "2024-11-05"
    }
