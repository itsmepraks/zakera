"""
Built-in tools for Zakera AI Chat Agent.

This package contains pre-built tools that come bundled with Zakera,
providing common functionality out of the box.

Available tools:
- Calculator: Mathematical expression evaluation
- WebSearch: Search the internet for information
- CodeExecutor: Execute code in a sandboxed environment
- Weather: Get weather information for locations
- DateTime: Get current date and time information
- FileReader: Read local text files with metadata
"""

from src.tools.builtin.calculator import CalculatorTool
from src.tools.builtin.web_search import WebSearchTool
from src.tools.builtin.code_executor import CodeExecutorTool
from src.tools.builtin.weather import WeatherTool
from src.tools.builtin.datetime_tool import DateTimeTool
from src.tools.builtin.file_reader import FileReaderTool

__all__ = [
    "CalculatorTool",
    "WebSearchTool",
    "CodeExecutorTool",
    "WeatherTool",
    "DateTimeTool",
    "FileReaderTool",
]
