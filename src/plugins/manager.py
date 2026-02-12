"""Plugin manager for lifecycle management and coordination."""

import asyncio
from typing import Dict, List, Optional, Any
import logging

from .base import Plugin, PluginHook, PluginState
from .registry import PluginRegistry, get_registry

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle and hook execution."""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        """Initialize the plugin manager.
        
        Args:
            registry: Plugin registry to use (uses global if not provided)
        """
        self.registry = registry or get_registry()
        self._load_order: List[str] = []
    
    async def load_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> Plugin:
        """Load and initialize a plugin.
        
        Args:
            name: Plugin class name to load
            config: Plugin configuration
            
        Returns:
            Loaded plugin instance
            
        Raises:
            ValueError: If plugin not found or dependencies missing
        """
        plugin_class = self.registry.get_plugin_class(name)
        if not plugin_class:
            raise ValueError(f"Plugin class not found: {name}")
        
        # Create plugin instance
        plugin = plugin_class(config=config)
        
        # Check dependencies
        missing_deps = self.registry.check_dependencies(plugin)
        if missing_deps:
            raise ValueError(
                f"Plugin {plugin.metadata.name} has missing dependencies: {missing_deps}"
            )
        
        # Initialize plugin
        try:
            await plugin.initialize()
            self.registry.register_plugin(plugin)
            self._load_order.append(plugin.metadata.name)
            logger.info(f"Loaded plugin: {plugin.metadata.name}")
            return plugin
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            plugin.state = PluginState.ERROR
            raise
    
    async def unload_plugin(self, name: str) -> None:
        """Unload a plugin.
        
        Args:
            name: Plugin name to unload
        """
        plugin = self.registry.get_plugin(name)
        if not plugin:
            logger.warning(f"Plugin not found: {name}")
            return
        
        try:
            if plugin.state == PluginState.STARTED:
                await plugin.stop()
            await plugin.cleanup()
            self.registry.unregister_plugin(name)
            if name in self._load_order:
                self._load_order.remove(name)
            logger.info(f"Unloaded plugin: {name}")
        except Exception as e:
            logger.error(f"Error unloading plugin {name}: {e}")
            raise
    
    async def start_plugin(self, name: str) -> None:
        """Start a plugin.
        
        Args:
            name: Plugin name to start
        """
        plugin = self.registry.get_plugin(name)
        if not plugin:
            raise ValueError(f"Plugin not found: {name}")
        
        if plugin.state != PluginState.INITIALIZED:
            raise ValueError(
                f"Plugin {name} must be initialized before starting (current state: {plugin.state})"
            )
        
        await plugin.start()
        logger.info(f"Started plugin: {name}")
    
    async def stop_plugin(self, name: str) -> None:
        """Stop a plugin.
        
        Args:
            name: Plugin name to stop
        """
        plugin = self.registry.get_plugin(name)
        if not plugin:
            raise ValueError(f"Plugin not found: {name}")
        
        if plugin.state != PluginState.STARTED:
            logger.warning(f"Plugin {name} is not started (current state: {plugin.state})")
            return
        
        await plugin.stop()
        logger.info(f"Stopped plugin: {name}")
    
    async def start_all(self) -> None:
        """Start all loaded plugins in load order."""
        for name in self._load_order:
            plugin = self.registry.get_plugin(name)
            if plugin and plugin.state == PluginState.INITIALIZED:
                try:
                    await self.start_plugin(name)
                except Exception as e:
                    logger.error(f"Failed to start plugin {name}: {e}")
    
    async def stop_all(self) -> None:
        """Stop all plugins in reverse load order."""
        for name in reversed(self._load_order):
            plugin = self.registry.get_plugin(name)
            if plugin and plugin.state == PluginState.STARTED:
                try:
                    await self.stop_plugin(name)
                except Exception as e:
                    logger.error(f"Failed to stop plugin {name}: {e}")
    
    async def reload_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> Plugin:
        """Reload a plugin.
        
        Args:
            name: Plugin name to reload
            config: New plugin configuration
            
        Returns:
            Reloaded plugin instance
        """
        await self.unload_plugin(name)
        return await self.load_plugin(name, config)
    
    async def execute_hook(self, hook: PluginHook, *args, **kwargs) -> Dict[str, Any]:
        """Execute a hook across all enabled plugins.
        
        Args:
            hook: Hook to execute
            *args: Positional arguments for hook callbacks
            **kwargs: Keyword arguments for hook callbacks
            
        Returns:
            Dictionary mapping plugin names to their hook results
        """
        results = {}
        
        for name in self._load_order:
            plugin = self.registry.get_plugin(name)
            if not plugin or not plugin.metadata.enabled:
                continue
            
            try:
                result = await plugin.execute_hook(hook, *args, **kwargs)
                results[name] = result
            except Exception as e:
                logger.error(f"Error executing hook {hook.value} in plugin {name}: {e}")
                await plugin.on_error(e, {"hook": hook.value, "args": args, "kwargs": kwargs})
        
        return results
    
    def get_plugins_by_tag(self, tag: str) -> List[Plugin]:
        """Get all plugins with a specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of plugins with the tag
        """
        plugins = []
        for name in self.registry.list_plugins():
            plugin = self.registry.get_plugin(name)
            if plugin and tag in plugin.metadata.tags:
                plugins.append(plugin)
        return plugins
    
    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all plugins.
        
        Returns:
            Dictionary mapping plugin names to their status
        """
        status = {}
        for name in self.registry.list_plugins():
            info = self.registry.get_plugin_info(name)
            if info:
                status[name] = info
        return status
