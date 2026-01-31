"""Pydantic schemas for MCP tool validation."""

from .weather import WeatherInput, WeatherOutput
from .mobility import MobilityInput, MobilityOutput, CommuteInput, CommuteOutput, ShuttleScheduleInput, ShuttleScheduleOutput
from .calendar import CalendarInput, CalendarOutput, CalendarRangeInput, CalendarRangeOutput, CalendarCreateInput, CalendarCreateOutput, CalendarUpdateInput, CalendarUpdateOutput, CalendarDeleteInput, CalendarDeleteOutput, CalendarFindFreeTimeInput, CalendarFindFreeTimeOutput, FreeTimeSlot
from .todo import (
    TodoInput, TodoOutput, TodoCreateInput, TodoCreateOutput,
    TodoUpdateInput, TodoUpdateOutput, TodoCompleteInput, TodoCompleteOutput,
    TodoDeleteInput, TodoDeleteOutput
)
from .financial import FinancialInput, FinancialOutput

__all__ = [
    "WeatherInput", "WeatherOutput",
    "MobilityInput", "MobilityOutput", "CommuteInput", "CommuteOutput", "ShuttleScheduleInput", "ShuttleScheduleOutput",
    "CalendarInput", "CalendarOutput", "CalendarRangeInput", "CalendarRangeOutput", "CalendarCreateInput", "CalendarCreateOutput", "CalendarUpdateInput", "CalendarUpdateOutput", "CalendarDeleteInput", "CalendarDeleteOutput", "CalendarFindFreeTimeInput", "CalendarFindFreeTimeOutput", "FreeTimeSlot",
    "TodoInput", "TodoOutput", "TodoCreateInput", "TodoCreateOutput", 
    "TodoUpdateInput", "TodoUpdateOutput", "TodoCompleteInput", "TodoCompleteOutput",
    "TodoDeleteInput", "TodoDeleteOutput",
    "FinancialInput", "FinancialOutput"
]
