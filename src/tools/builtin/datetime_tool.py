"""
DateTime tool for date and time operations.

Provides current date/time information, timezone conversions,
and date calculations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import pytz

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
)

logger = logging.getLogger(__name__)


class DateTimeTool(Tool):
    """
    Tool for date and time operations.
    
    Features:
    - Get current date and time
    - Timezone conversion
    - Date formatting
    - Date arithmetic
    - Timezone information
    """
    
    @property
    def name(self) -> str:
        return "datetime"
    
    @property
    def description(self) -> str:
        return (
            "Get current date and time information, convert between timezones, "
            "and perform date calculations."
        )
    
    @property
    def category(self) -> str:
        return "utility"
    
    @property
    def tags(self) -> List[str]:
        return ["date", "time", "timezone", "clock", "calendar"]
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="Operation to perform",
                required=False,
                default="current",
                enum=["current", "convert", "format", "calculate"],
            ),
            ToolParameter(
                name="timezone",
                type=ToolParameterType.STRING,
                description="Timezone name (e.g., 'America/New_York', 'Europe/London')",
                required=False,
                default="UTC",
            ),
            ToolParameter(
                name="format",
                type=ToolParameterType.STRING,
                description="Output format string (Python strftime format)",
                required=False,
                default="%Y-%m-%d %H:%M:%S %Z",
            ),
        ]
    
    def _get_current_time(self, tz_name: str) -> Dict[str, Any]:
        """Get current time in specified timezone."""
        try:
            tz = pytz.timezone(tz_name)
            now = datetime.now(tz)
            
            return {
                "datetime": now.isoformat(),
                "date": now.date().isoformat(),
                "time": now.time().isoformat(),
                "timezone": tz_name,
                "timezone_offset": now.strftime("%z"),
                "timestamp": now.timestamp(),
                "weekday": now.strftime("%A"),
                "day_of_year": now.timetuple().tm_yday,
                "week_number": now.isocalendar()[1],
            }
        except pytz.exceptions.UnknownTimeZoneError:
            raise ToolExecutionError(f"Unknown timezone: {tz_name}")
    
    def _format_datetime(self, tz_name: str, fmt: str) -> str:
        """Format current datetime with custom format."""
        try:
            tz = pytz.timezone(tz_name)
            now = datetime.now(tz)
            return now.strftime(fmt)
        except Exception as e:
            raise ToolExecutionError(f"Formatting error: {str(e)}")
    
    async def execute(
        self,
        operation: str = "current",
        timezone: str = "UTC",
        format: str = "%Y-%m-%d %H:%M:%S %Z",
        **kwargs
    ) -> ToolResult:
        """
        Execute datetime operation.
        
        Args:
            operation: Operation to perform
            timezone: Timezone name
            format: Format string for output
            
        Returns:
            ToolResult with datetime information
        """
        try:
            if operation == "current":
                # Get current date/time
                time_info = self._get_current_time(timezone)
                
                return ToolResult.success_result(
                    data=time_info,
                    metadata={"operation": "current"}
                )
            
            elif operation == "format":
                # Get formatted datetime
                formatted = self._format_datetime(timezone, format)
                
                return ToolResult.success_result(
                    data={"formatted": formatted, "timezone": timezone},
                    metadata={"operation": "format", "format": format}
                )
            
            elif operation == "convert":
                # Timezone conversion (placeholder)
                return ToolResult.error_result(
                    "Timezone conversion not yet implemented. Use operation='current' with target timezone."
                )
            
            elif operation == "calculate":
                # Date calculations (placeholder)
                return ToolResult.error_result(
                    "Date calculations not yet implemented."
                )
            
            else:
                return ToolResult.error_result(f"Unknown operation: {operation}")
        
        except ToolExecutionError as e:
            return ToolResult.error_result(str(e))
        except Exception as e:
            logger.exception("Unexpected error in datetime tool")
            return ToolResult.error_result(f"DateTime operation failed: {str(e)}")
