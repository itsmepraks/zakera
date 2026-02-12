"""Plugin registry for managing plugin discovery and loading."""

import os
import importlib
import inspect
from typing import Dict, List, Optional, Type
from pathlib import Path
import logging

from .base import Plugin, PluginMetadata, PluginState

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for plugin management."""
    
    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_classes: Dict[str, Type[Plugin]] = {}
        self._discovery_paths: List[Path] = []
    
    def add_discovery_path(self, path: str | Path) -> None:
        """Add a path to search for plugins.
        
        Args:
            path: Directory path to search for plugins
        """
        path = Path(path)
        if path.exists() and path.is_dir():
            self._discovery_paths.append(path)
            logger.info(f"Added plugin discovery path: {path}")
        else:
            logger.warning(f"Invalid discovery path: {path}")
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins in discovery paths.
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        for path in self._discovery_paths:
            for file in path.glob("*.py"):
                if file.name.startswith("_"):
                    continue
                
                try:
                    module_name = file.stem
                    spec = importlib.util.spec_from_file_location(
                        f"plugins.{module_name}", file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Find Plugin subclasses in module
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, Plugin) and 
                                obj is not Plugin):
                                self._plugin_classes[obj.__name__] = obj
                                discovered.append(obj.__name__)
                                logger.info(f"Discovered plugin: {obj.__name__}")
                except Exception as e:
                    logger.error(f"Error discovering plugins in {file}: {e}")
        
        return discovered
    
    def register_plugin_class(self, name: str, plugin_class: Type[Plugin]) -> None:
        """Manually register a plugin class.
        
        Args:
            name: Plugin identifier
            plugin_class: Plugin class to register
        """
        if not issubclass(plugin_class, Plugin):
            raise ValueError(f"{plugin_class} must be a subclass of Plugin")
        
        self._plugin_classes[name] = plugin_class
        logger.info(f"Registered plugin class: {name}")
    
    def register_plugin(self, plugin: Plugin) -> None:
        """Register a plugin instance.
        
        Args:
            plugin: Plugin instance to register
        """
        name = plugin.metadata.name
        if name in self._plugins:
            logger.warning(f"Plugin {name} already registered, replacing")
        
        self._plugins[name] = plugin
        logger.info(f"Registered plugin: {name} v{plugin.metadata.version}")
    
    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin.
        
        Args:
            name: Plugin name to unregister
        """
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"Unregistered plugin: {name}")
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a registered plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name)
    
    def get_plugin_class(self, name: str) -> Optional[Type[Plugin]]:
        """Get a plugin class by name.
        
        Args:
            name: Plugin class name
            
        Returns:
            Plugin class or None if not found
        """
        return self._plugin_classes.get(name)
    
    def list_plugins(self, state: Optional[PluginState] = None) -> List[str]:
        """List registered plugins.
        
        Args:
            state: Optional state filter
            
        Returns:
            List of plugin names
        """
        if state is None:
            return list(self._plugins.keys())
        
        return [
            name for name, plugin in self._plugins.items()
            if plugin.state == state
        ]
    
    def get_plugin_info(self, name: str) -> Optional[Dict]:
        """Get information about a plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            Dictionary with plugin information
        """
        plugin = self.get_plugin(name)
        if not plugin:
            return None
        
        metadata = plugin.metadata
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "author": metadata.author,
            "dependencies": metadata.dependencies,
            "tags": metadata.tags,
            "enabled": metadata.enabled,
            "state": plugin.state.value
        }
    
    def check_dependencies(self, plugin: Plugin) -> List[str]:
        """Check if plugin dependencies are satisfied.
        
        Args:
            plugin: Plugin to check dependencies for
            
        Returns:
            List of missing dependencies
        """
        missing = []
        for dep in plugin.metadata.dependencies:
            if dep not in self._plugins:
                missing.append(dep)
        return missing


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry.
    
    Returns:
        Global PluginRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
