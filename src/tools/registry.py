"""
Tool Registry for managing and discovering tools.

Provides centralized tool registration, discovery, and retrieval
functionality for the Zakera tool ecosystem.
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from src.tools.base import Tool, ToolNotFoundError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all available tools.
    
    The registry manages tool lifecycle, discovery, and retrieval.
    It supports both manual registration and automatic discovery
    of built-in tools.
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._tool_classes: Dict[str, Type[Tool]] = {}
        self._initialized = False
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool instance.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool with same name already exists
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, replacing")
        
        self._tools[tool.name] = tool
        self._tool_classes[tool.name] = type(tool)
        logger.info(f"Registered tool: {tool.name} (v{tool.version})")
    
    def register_class(self, tool_class: Type[Tool]) -> None:
        """
        Register a tool class and instantiate it.
        
        Args:
            tool_class: Tool class to register
        """
        instance = tool_class()
        self.register(instance)
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            del self._tool_classes[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get(self, tool_name: str) -> Tool:
        """
        Get a registered tool by name.
        
        Args:
            tool_name: Name of tool to retrieve
            
        Returns:
            Tool instance
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")
        
        return self._tools[tool_name]
    
    def list_tools(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
        tags: Optional[List[str]] = None
    ) -> List[Tool]:
        """
        List all registered tools with optional filtering.
        
        Args:
            category: Filter by category
            enabled_only: Only return enabled tools
            tags: Filter by tags (tool must have all specified tags)
            
        Returns:
            List of matching tools
        """
        tools = list(self._tools.values())
        
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        if tags:
            tools = [
                t for t in tools
                if all(tag in t.tags for tag in tags)
            ]
        
        return tools
    
    def get_tool_names(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def get_categories(self) -> List[str]:
        """Get list of all tool categories."""
        categories = set(tool.category for tool in self._tools.values())
        return sorted(list(categories))
    
    def search(self, query: str) -> List[Tool]:
        """
        Search for tools by name, description, or tags.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching tools
        """
        query_lower = query.lower()
        results = []
        
        for tool in self._tools.values():
            # Search in name
            if query_lower in tool.name.lower():
                results.append(tool)
                continue
            
            # Search in description
            if query_lower in tool.description.lower():
                results.append(tool)
                continue
            
            # Search in tags
            if any(query_lower in tag.lower() for tag in tool.tags):
                results.append(tool)
                continue
        
        return results
    
    def discover_builtin_tools(self) -> int:
        """
        Automatically discover and register built-in tools.
        
        Scans the builtin tools directory and registers all
        Tool subclasses found.
        
        Returns:
            Number of tools discovered and registered
        """
        try:
            import src.tools.builtin as builtin_module
            
            builtin_path = Path(builtin_module.__file__).parent
            count = 0
            
            # Import all modules in builtin directory
            for _, module_name, _ in pkgutil.iter_modules([str(builtin_path)]):
                try:
                    module = importlib.import_module(
                        f"src.tools.builtin.{module_name}"
                    )
                    
                    # Find Tool subclasses in module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        
                        # Check if it's a Tool subclass (but not Tool itself)
                        if (
                            isinstance(attr, type) and
                            issubclass(attr, Tool) and
                            attr is not Tool and
                            not attr.__name__.startswith('_')
                        ):
                            try:
                                self.register_class(attr)
                                count += 1
                            except Exception as e:
                                logger.error(
                                    f"Failed to register {attr.__name__}: {e}"
                                )
                
                except Exception as e:
                    logger.error(f"Failed to import {module_name}: {e}")
            
            logger.info(f"Discovered and registered {count} built-in tools")
            self._initialized = True
            return count
            
        except Exception as e:
            logger.error(f"Failed to discover built-in tools: {e}")
            return 0
    
    def get_tool_info(self, tool_name: str) -> Dict:
        """
        Get detailed information about a tool.
        
        Args:
            tool_name: Name of tool
            
        Returns:
            Dictionary with tool information
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        tool = self.get(tool_name)
        return tool.to_dict()
    
    def is_available(self, tool_name: str) -> bool:
        """
        Check if a tool is available and enabled.
        
        Args:
            tool_name: Name of tool to check
            
        Returns:
            True if tool exists and is enabled
        """
        try:
            tool = self.get(tool_name)
            return tool.enabled
        except ToolNotFoundError:
            return False
    
    async def initialize_all(self) -> None:
        """Initialize all registered tools."""
        for tool in self._tools.values():
            try:
                await tool.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize {tool.name}: {e}")
    
    async def cleanup_all(self) -> None:
        """Cleanup all registered tools."""
        for tool in self._tools.values():
            try:
                await tool.cleanup()
            except Exception as e:
                logger.error(f"Failed to cleanup {tool.name}: {e}")
    
    def export_schema(self) -> Dict[str, Any]:
        """
        Export tool schemas in OpenAI function calling format.
        
        Returns:
            Dictionary of tool schemas
        """
        schemas = {}
        
        for tool_name, tool in self._tools.items():
            schemas[tool_name] = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            param.name: {
                                "type": param.type.value,
                                "description": param.description,
                                **({"enum": param.enum} if param.enum else {}),
                            }
                            for param in tool.parameters
                        },
                        "required": [
                            param.name
                            for param in tool.parameters
                            if param.required and param.default is None
                        ],
                    },
                },
            }
        
        return schemas
    
    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools
    
    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self._tools)} tools registered>"


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Initializes the registry on first call and discovers built-in tools.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _global_registry.discover_builtin_tools()
        logger.info("Initialized global tool registry")
    
    return _global_registry


def reset_registry() -> None:
    """
    Reset the global registry.
    
    Useful for testing or reinitialization.
    """
    global _global_registry
    _global_registry = None
    logger.info("Reset global tool registry")
