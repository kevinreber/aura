"""Health check and system status routes."""

from flask import Blueprint, jsonify
from ..config import get_settings
from ..utils.cache import get_cache_service

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """Health check endpoint.
    ---
    tags:
      - System
    responses:
      200:
        description: Service health status
    """
    settings = get_settings()
    return jsonify({
        "status": "healthy",
        "version": "2.1.0",
        "environment": settings.environment
    })


@health_bp.route('/cache/stats')
async def cache_stats():
    """Get cache statistics for monitoring."""
    try:
        cache_service = await get_cache_service()
        stats = await cache_service.get_cache_stats()
        return jsonify({
            "cache_stats": stats,
            "status": "success"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500
