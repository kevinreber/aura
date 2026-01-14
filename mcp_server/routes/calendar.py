"""Calendar tool routes."""

from flask import Blueprint, jsonify, request
from ..server import get_mcp_server
from ..utils.logging import get_logger
from ..utils.audit import audit_log

calendar_bp = Blueprint('calendar', __name__)
logger = get_logger("calendar_routes")


@calendar_bp.route('/tools/calendar.list_events', methods=['POST'])
async def calendar_list_events():
    """List calendar events for a date.
    ---
    tags:
      - Calendar
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("calendar.list_events", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in calendar.list_events: {e}")
        return jsonify({"error": str(e)}), 500


@calendar_bp.route('/tools/calendar.list_events_range', methods=['POST'])
async def calendar_list_events_range():
    """List calendar events for a date range.
    ---
    tags:
      - Calendar
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("calendar.list_events_range", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in calendar.list_events_range: {e}")
        return jsonify({"error": str(e)}), 500


@calendar_bp.route('/tools/calendar.create_event', methods=['POST'])
async def calendar_create_event():
    """Create a new calendar event.
    ---
    tags:
      - Calendar
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("calendar.create_event", data)

        # Audit log for write operation
        audit_log("calendar.create_event", data, result, request.remote_addr)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in calendar.create_event: {e}")
        return jsonify({"error": str(e)}), 500


@calendar_bp.route('/tools/calendar.update_event', methods=['POST'])
async def calendar_update_event():
    """Update an existing calendar event.
    ---
    tags:
      - Calendar
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        if not data.get('event_id'):
            return jsonify({"error": "event_id is required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("calendar.update_event", data)

        # Audit log for write operation
        audit_log("calendar.update_event", data, result, request.remote_addr)

        if not result.get('success') and 'not found' in result.get('message', '').lower():
            return jsonify({"error": result.get('message', 'Event not found')}), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in calendar.update_event: {e}")
        return jsonify({"error": str(e)}), 500


@calendar_bp.route('/tools/calendar.delete_event', methods=['POST'])
async def calendar_delete_event():
    """Delete a calendar event.
    ---
    tags:
      - Calendar
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        if not data.get('event_id'):
            return jsonify({"error": "event_id is required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("calendar.delete_event", data)

        # Audit log for write operation
        audit_log("calendar.delete_event", data, result, request.remote_addr)

        if not result.get('success') and 'not found' in result.get('message', '').lower():
            return jsonify({"error": result.get('message', 'Event not found')}), 404

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in calendar.delete_event: {e}")
        return jsonify({"error": str(e)}), 500


@calendar_bp.route('/tools/calendar.find_free_time', methods=['POST'])
async def calendar_find_free_time():
    """Find available time slots.
    ---
    tags:
      - Calendar
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("calendar.find_free_time", data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in calendar.find_free_time: {e}")
        return jsonify({"error": str(e)}), 500
