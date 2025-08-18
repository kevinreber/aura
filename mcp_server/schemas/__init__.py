"""Pydantic schemas for MCP tool validation."""

from .weather import WeatherInput, WeatherOutput
from .mobility import MobilityInput, MobilityOutput
from .calendar import CalendarInput, CalendarOutput, CalendarRangeInput, CalendarRangeOutput
from .todo import TodoInput, TodoOutput
from .financial import FinancialInput, FinancialOutput

__all__ = [
    "WeatherInput", "WeatherOutput",
    "MobilityInput", "MobilityOutput", 
    "CalendarInput", "CalendarOutput", "CalendarRangeInput", "CalendarRangeOutput",
    "TodoInput", "TodoOutput",
    "FinancialInput", "FinancialOutput"
]
