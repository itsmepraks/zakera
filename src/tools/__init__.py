"""
Zakera Tool Integration System

This module provides a comprehensive plugin system for extending
the AI agent with external tools and capabilities.

The tool system supports:
- Dynamic tool registration and discovery
- Async tool execution
- Parameter validation
- Error handling and retries
- Rate limiting
- Result caching
- Tool chaining

Usage:
    from src.tools import ToolRegistry, get_tool_manager
    
    # Register tools
    registry = ToolRegistry()
    registry.discover_builtin_tools()
    
    # Execute a tool
    manager = get_tool_manager()
    result = await manager.execute_tool("calculator", {"expression": "2 + 2"})
"""

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolResult,
    ToolError,
    ToolExecutionError,
    ToolValidationError,
    ToolNotFoundError,
)
from src.tools.registry import ToolRegistry, get_registry
from src.tools.manager import ToolManager, get_tool_manager

__all__ = [
    # Base classes
    "Tool",
    "ToolParameter",
    "ToolResult",
    # Errors
    "ToolError",
    "ToolExecutionError",
    "ToolValidationError",
    "ToolNotFoundError",
    # Registry
    "ToolRegistry",
    "get_registry",
    # Manager
    "ToolManager",
    "get_tool_manager",
]

__version__ = "1.0.0"
