"""Financial tool routes."""

from flask import Blueprint, jsonify, request
from ..server import get_mcp_server
from ..utils.logging import get_logger

financial_bp = Blueprint('financial', __name__)
logger = get_logger("financial_routes")


@financial_bp.route('/tools/financial.get_data', methods=['POST'])
async def financial_get_data():
    """Get financial data for stocks and crypto.
    ---
    tags:
      - Financial
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("financial.get_data", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in financial.get_data: {e}")
        return jsonify({"error": str(e)}), 500
