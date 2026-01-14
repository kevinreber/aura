"""Flask route blueprints for the MCP server."""

from .health import health_bp
from .weather import weather_bp
from .mobility import mobility_bp
from .calendar import calendar_bp
from .todo import todo_bp
from .financial import financial_bp

__all__ = [
    'health_bp',
    'weather_bp',
    'mobility_bp',
    'calendar_bp',
    'todo_bp',
    'financial_bp'
]
