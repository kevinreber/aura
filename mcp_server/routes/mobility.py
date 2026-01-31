"""Mobility tool routes."""

from flask import Blueprint, jsonify, request
from ..server import get_mcp_server
from ..utils.logging import get_logger

mobility_bp = Blueprint('mobility', __name__)
logger = get_logger("mobility_routes")


@mobility_bp.route('/tools/mobility.get_commute', methods=['POST'])
async def mobility_get_commute():
    """Get commute information.
    ---
    tags:
      - Mobility
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("mobility.get_commute", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in mobility.get_commute: {e}")
        return jsonify({"error": str(e)}), 500


@mobility_bp.route('/tools/mobility.get_commute_options', methods=['POST'])
async def mobility_get_commute_options():
    """Get comprehensive commute analysis.
    ---
    tags:
      - Mobility
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("mobility.get_commute_options", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in mobility.get_commute_options: {e}")
        return jsonify({"error": str(e)}), 500


@mobility_bp.route('/tools/mobility.get_shuttle_schedule', methods=['POST'])
async def mobility_get_shuttle_schedule():
    """Get shuttle schedule information.
    ---
    tags:
      - Mobility
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("mobility.get_shuttle_schedule", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in mobility.get_shuttle_schedule: {e}")
        return jsonify({"error": str(e)}), 500
