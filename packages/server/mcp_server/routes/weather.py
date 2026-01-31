"""Weather tool routes."""

from flask import Blueprint, jsonify, request
from ..server import get_mcp_server
from ..utils.logging import get_logger

weather_bp = Blueprint('weather', __name__)
logger = get_logger("weather_routes")


@weather_bp.route('/tools/weather.get_daily', methods=['POST'])
async def weather_get_daily():
    """Get current weather and daily forecast.
    ---
    tags:
      - Weather
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - location
          properties:
            location:
              type: string
              example: "San Francisco, CA"
    responses:
      200:
        description: Weather data
      400:
        description: Invalid request
      500:
        description: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        mcp_server = get_mcp_server()
        result = await mcp_server.call_tool("weather.get_daily", data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in weather.get_daily: {e}")
        return jsonify({"error": str(e)}), 500
