"""Base classes for the plugin system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PluginState(Enum):
    """Plugin lifecycle states."""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


class PluginHook(Enum):
    """Available hooks for plugins."""
    # Lifecycle hooks
    BEFORE_INIT = "before_init"
    AFTER_INIT = "after_init"
    BEFORE_START = "before_start"
    AFTER_START = "after_start"
    BEFORE_STOP = "before_stop"
    AFTER_STOP = "after_stop"
    
    # Application hooks
    BEFORE_REQUEST = "before_request"
    AFTER_REQUEST = "after_request"
    BEFORE_RESPONSE = "before_response"
    AFTER_RESPONSE = "after_response"
    
    # Model hooks
    BEFORE_GENERATE = "before_generate"
    AFTER_GENERATE = "after_generate"
    ON_STREAM_CHUNK = "on_stream_chunk"
    
    # Error hooks
    ON_ERROR = "on_error"
    ON_EXCEPTION = "on_exception"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


class Plugin(ABC):
    """Base class for all plugins.
    
    Plugins extend Zakera's functionality through a well-defined lifecycle
    and hook system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin.
        
        Args:
            config: Plugin configuration dictionary
        """
        self.config = config or {}
        self.state = PluginState.UNLOADED
        self._hooks: Dict[PluginHook, List[Callable]] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.metadata.name}")
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
    
    def register_hook(self, hook: PluginHook, callback: Callable) -> None:
        """Register a callback for a hook.
        
        Args:
            hook: The hook to register for
            callback: The callback function to execute
        """
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        self.logger.debug(f"Registered hook {hook.value} for plugin {self.metadata.name}")
    
    def get_hooks(self, hook: PluginHook) -> List[Callable]:
        """Get all callbacks for a hook.
        
        Args:
            hook: The hook to get callbacks for
            
        Returns:
            List of callback functions
        """
        return self._hooks.get(hook, [])
    
    async def execute_hook(self, hook: PluginHook, *args, **kwargs) -> Any:
        """Execute all callbacks for a hook.
        
        Args:
            hook: The hook to execute
            *args: Positional arguments to pass to callbacks
            **kwargs: Keyword arguments to pass to callbacks
            
        Returns:
            Results from callbacks
        """
        results = []
        for callback in self.get_hooks(hook):
            try:
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(*args, **kwargs)
                else:
                    result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error executing hook {hook.value}: {e}")
                raise
        return results
    
    def validate_config(self) -> bool:
        """Validate plugin configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.metadata.config_schema:
            return True
        
        # Basic validation - can be extended with jsonschema
        required = self.metadata.config_schema.get("required", [])
        for key in required:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")
        
        return True
    
    async def initialize(self) -> None:
        """Initialize the plugin.
        
        Called when the plugin is first loaded. Override to add custom
        initialization logic.
        """
        await self.execute_hook(PluginHook.BEFORE_INIT)
        self.validate_config()
        self.state = PluginState.INITIALIZED
        self.logger.info(f"Plugin {self.metadata.name} initialized")
        await self.execute_hook(PluginHook.AFTER_INIT)
    
    async def start(self) -> None:
        """Start the plugin.
        
        Called when the plugin should begin active operation. Override to
        add custom startup logic.
        """
        await self.execute_hook(PluginHook.BEFORE_START)
        self.state = PluginState.STARTED
        self.logger.info(f"Plugin {self.metadata.name} started")
        await self.execute_hook(PluginHook.AFTER_START)
    
    async def stop(self) -> None:
        """Stop the plugin.
        
        Called when the plugin should cease operation. Override to add
        custom shutdown logic.
        """
        await self.execute_hook(PluginHook.BEFORE_STOP)
        self.state = PluginState.STOPPED
        self.logger.info(f"Plugin {self.metadata.name} stopped")
        await self.execute_hook(PluginHook.AFTER_STOP)
    
    async def cleanup(self) -> None:
        """Cleanup plugin resources.
        
        Called when the plugin is being unloaded. Override to release
        resources, close connections, etc.
        """
        self.logger.info(f"Plugin {self.metadata.name} cleaned up")
    
    async def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle errors.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        self.logger.error(
            f"Error in plugin {self.metadata.name}: {error}",
            extra=context
        )
        await self.execute_hook(PluginHook.ON_ERROR, error, context)


import asyncio
