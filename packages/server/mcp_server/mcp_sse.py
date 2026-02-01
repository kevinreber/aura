"""SSE (Server-Sent Events) transport for MCP protocol over Flask.

This module implements the MCP SSE transport specification, allowing
MCP clients to connect to the server over HTTP using Server-Sent Events.

Protocol flow:
1. Client connects to GET /mcp/sse to establish SSE stream
2. Server sends endpoint URL for client messages
3. Client sends JSON-RPC messages to POST /mcp/messages
4. Server responds via SSE stream

Reference: https://modelcontextprotocol.io/docs/concepts/transports#server-sent-events-sse
"""

import json
import asyncio
import uuid
from typing import Optional
from dataclasses import dataclass, field
from queue import Queue

from flask import Blueprint, Response, request, jsonify, stream_with_context

from .mcp_protocol import get_mcp_app
from .utils.logging import get_logger

logger = get_logger("mcp_sse")

# Blueprint for MCP SSE endpoints
mcp_sse_bp = Blueprint("mcp_sse", __name__, url_prefix="/mcp")


@dataclass
class SSESession:
    """Represents an active SSE client session."""

    session_id: str
    message_queue: Queue = field(default_factory=Queue)
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


def format_sse_message(event: str, data: str) -> str:
    """Format a message for SSE transmission."""
    return f"event: {event}\ndata: {data}\n\n"


async def handle_jsonrpc_message(message: dict, session: SSESession) -> dict:
    """Process a JSON-RPC message and return the response.

    Routes messages to the appropriate MCP handlers.
    """
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {})

    mcp_server = get_mcp_app()

    try:
        if method == "initialize":
            # Handle initialization
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "aura-mcp-server",
                    "version": "1.0.0"
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


@mcp_sse_bp.route("/sse", methods=["GET"])
def sse_endpoint():
    """SSE endpoint for MCP clients.

    Clients connect here to establish the SSE stream. The server
    immediately sends the endpoint URL for posting messages.
    """
    session = create_session()

    def generate():
        try:
            # Send the endpoint URL for client messages
            # Include session_id so we can route responses back
            endpoint_url = f"/mcp/messages?session_id={session.session_id}"
            yield format_sse_message("endpoint", endpoint_url)

            # Keep connection alive and send queued messages
            while session.connected:
                try:
                    # Check for messages to send (non-blocking with timeout)
                    try:
                        message = session.message_queue.get(timeout=30)
                        yield format_sse_message("message", json.dumps(message))
                    except Exception:
                        # Timeout - send keepalive
                        yield ": keepalive\n\n"
                except GeneratorExit:
                    break

        finally:
            remove_session(session.session_id)

    response = Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
    return response


@mcp_sse_bp.route("/messages", methods=["POST"])
async def messages_endpoint():
    """Endpoint for receiving JSON-RPC messages from MCP clients.

    Clients POST messages here, and responses are sent back via
    the SSE stream.
    """
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Invalid or expired session"}), 404

    try:
        message = request.get_json()
        if not message:
            return jsonify({"error": "JSON body required"}), 400

        logger.debug(f"Received MCP message: {message.get('method', 'unknown')}")

        # Process the message
        response = await handle_jsonrpc_message(message, session)

        if response:
            # Queue response for SSE delivery
            session.message_queue.put(response)

        # Return 202 Accepted - response will come via SSE
        return "", 202

    except Exception as e:
        logger.error(f"Error processing MCP message: {e}")
        return jsonify({"error": str(e)}), 500


@mcp_sse_bp.route("/health", methods=["GET"])
def mcp_health():
    """Health check endpoint for MCP SSE transport."""
    return jsonify({
        "status": "healthy",
        "transport": "sse",
        "active_sessions": len(_sessions),
        "protocol_version": "2024-11-05"
    })


def get_mcp_sse_blueprint() -> Blueprint:
    """Get the Flask blueprint for MCP SSE endpoints."""
    return mcp_sse_bp
