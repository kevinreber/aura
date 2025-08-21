"""Pydantic schemas for MCP tool validation."""

from .weather import WeatherInput, WeatherOutput
from .mobility import MobilityInput, MobilityOutput
from .calendar import CalendarInput, CalendarOutput, CalendarRangeInput, CalendarRangeOutput, CalendarCreateInput, CalendarCreateOutput, CalendarUpdateInput, CalendarUpdateOutput, CalendarDeleteInput, CalendarDeleteOutput, CalendarFindFreeTimeInput, CalendarFindFreeTimeOutput, FreeTimeSlot
from .todo import TodoInput, TodoOutput
from .financial import FinancialInput, FinancialOutput

__all__ = [
    "WeatherInput", "WeatherOutput",
    "MobilityInput", "MobilityOutput", 
    "CalendarInput", "CalendarOutput", "CalendarRangeInput", "CalendarRangeOutput", "CalendarCreateInput", "CalendarCreateOutput", "CalendarUpdateInput", "CalendarUpdateOutput", "CalendarDeleteInput", "CalendarDeleteOutput", "CalendarFindFreeTimeInput", "CalendarFindFreeTimeOutput", "FreeTimeSlot",
    "TodoInput", "TodoOutput",
    "FinancialInput", "FinancialOutput"
]
