"""Pydantic schemas for MCP tool validation."""

from .weather import WeatherInput, WeatherOutput
from .mobility import MobilityInput, MobilityOutput
from .calendar import CalendarInput, CalendarOutput
from .todo import TodoInput, TodoOutput
from .financial import FinancialInput, FinancialOutput

__all__ = [
    "WeatherInput", "WeatherOutput",
    "MobilityInput", "MobilityOutput", 
    "CalendarInput", "CalendarOutput",
    "TodoInput", "TodoOutput",
    "FinancialInput", "FinancialOutput"
]
