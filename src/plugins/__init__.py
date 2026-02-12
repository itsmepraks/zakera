"""Plugin system for Zakera.

Provides a flexible plugin architecture for extending functionality.
"""

from .base import Plugin, PluginMetadata, PluginHook
from .registry import PluginRegistry, get_registry
from .manager import PluginManager

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginHook",
    "PluginRegistry",
    "PluginManager",
    "get_registry",
]
