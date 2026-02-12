# Plugin Development Guide

This guide explains how to develop plugins for Zakera, extending its functionality through a well-defined plugin system.

## Table of Contents

- [Overview](#overview)
- [Plugin Architecture](#plugin-architecture)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Lifecycle](#plugin-lifecycle)
- [Hooks System](#hooks-system)
- [Configuration](#configuration)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

Zakera's plugin system provides:

- ✅ Flexible plugin architecture with base classes
- ✅ Comprehensive lifecycle management
- ✅ Event hooks for extensibility
- ✅ Configuration validation
- ✅ Dependency resolution
- ✅ Automatic plugin discovery
- ✅ State management
- ✅ Error handling

## Plugin Architecture

### Core Components

1. **Plugin Base Class** - Abstract base class all plugins inherit from
2. **PluginRegistry** - Manages plugin discovery and registration
3. **PluginManager** - Handles plugin lifecycle and coordination
4. **PluginHooks** - Predefined extension points
5. **PluginMetadata** - Plugin information and dependencies

### Plugin States

Plugins progress through these states:

```
UNLOADED → LOADED → INITIALIZED → STARTED → STOPPED
                                      ↓
                                    ERROR
```

## Creating a Plugin

### Basic Plugin Structure

```python
from src.plugins.base import Plugin, PluginMetadata, PluginHook
from typing import Dict, Any

class MyPlugin(Plugin):
    """My custom plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="my_plugin",
            version="1.0.0",
            description="Description of what the plugin does",
            author="Your Name",
            dependencies=[],  # List of required plugins
            tags=["category", "feature"],
            config_schema={
                "required": ["api_key"],
                "properties": {
                    "api_key": {"type": "string"},
                    "enabled": {"type": "boolean", "default": True}
                }
            }
        )
    
    async def initialize(self) -> None:
        """Initialize the plugin."""
        await super().initialize()
        
        # Your initialization code here
        self.api_key = self.config.get("api_key")
        
        # Register hooks
        self.register_hook(PluginHook.BEFORE_REQUEST, self.on_request)
        
        self.logger.info("My plugin initialized")
    
    async def on_request(self, request: Dict[str, Any]) -> None:
        """Handle request hook."""
        self.logger.debug(f"Processing request: {request}")
        # Your request handling code
```

### With Dependencies

```python
class AdvancedPlugin(Plugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="advanced_plugin",
            version="1.0.0",
            description="Plugin that depends on others",
            author="Your Name",
            dependencies=["logging_plugin", "analytics_plugin"],
            tags=["advanced"]
        )
```

## Plugin Lifecycle

### Lifecycle Methods

```python
class MyPlugin(Plugin):
    async def initialize(self) -> None:
        """Called when plugin is first loaded."""
        await super().initialize()
        # Setup resources, validate config
    
    async def start(self) -> None:
        """Called when plugin should begin operation."""
        await super().start()
        # Start background tasks, open connections
    
    async def stop(self) -> None:
        """Called when plugin should cease operation."""
        await super().stop()
        # Stop background tasks, flush buffers
    
    async def cleanup(self) -> None:
        """Called when plugin is being unloaded."""
        await super().cleanup()
        # Release resources, close connections
```

### Using the Plugin Manager

```python
from src.plugins.manager import PluginManager
from src.plugins.registry import get_registry

# Get plugin manager
manager = PluginManager()

# Register plugin class
manager.registry.register_plugin_class("MyPlugin", MyPlugin)

# Load plugin
plugin = await manager.load_plugin(
    "MyPlugin",
    config={"api_key": "your-key"}
)

# Start plugin
await manager.start_plugin("my_plugin")

# Use plugin
# ...

# Stop plugin
await manager.stop_plugin("my_plugin")

# Unload plugin
await manager.unload_plugin("my_plugin")
```

## Hooks System

### Available Hooks

#### Lifecycle Hooks
- `BEFORE_INIT` - Before plugin initialization
- `AFTER_INIT` - After plugin initialization
- `BEFORE_START` - Before plugin starts
- `AFTER_START` - After plugin starts
- `BEFORE_STOP` - Before plugin stops
- `AFTER_STOP` - After plugin stops

#### Application Hooks
- `BEFORE_REQUEST` - Before processing a request
- `AFTER_REQUEST` - After request processed
- `BEFORE_RESPONSE` - Before sending response
- `AFTER_RESPONSE` - After response sent

#### Model Hooks
- `BEFORE_GENERATE` - Before model generation
- `AFTER_GENERATE` - After model generation
- `ON_STREAM_CHUNK` - On streaming chunk received

#### Error Hooks
- `ON_ERROR` - When an error occurs
- `ON_EXCEPTION` - When exception is raised

### Registering Hooks

```python
class MyPlugin(Plugin):
    async def initialize(self) -> None:
        await super().initialize()
        
        # Register synchronous callback
        self.register_hook(
            PluginHook.BEFORE_REQUEST,
            self.log_request
        )
        
        # Register async callback
        self.register_hook(
            PluginHook.AFTER_GENERATE,
            self.track_tokens
        )
    
    def log_request(self, request: Dict) -> None:
        """Synchronous hook handler."""
        print(f"Request: {request}")
    
    async def track_tokens(self, result: Dict) -> None:
        """Async hook handler."""
        tokens = result.get("usage", {}).get("total_tokens", 0)
        await self.save_token_count(tokens)
```

### Executing Hooks

```python
# Execute hooks from application code
await manager.execute_hook(
    PluginHook.BEFORE_REQUEST,
    request={"method": "POST", "path": "/chat"}
)
```

## Configuration

### Config Schema

```python
config_schema = {
    "required": ["api_key"],  # Required fields
    "properties": {
        "api_key": {
            "type": "string",
            "description": "API key for service"
        },
        "timeout": {
            "type": "number",
            "default": 30.0,
            "description": "Request timeout in seconds"
        },
        "enabled": {
            "type": "boolean",
            "default": True
        },
        "log_level": {
            "type": "string",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR"],
            "default": "INFO"
        }
    }
}
```

### Accessing Configuration

```python
class MyPlugin(Plugin):
    async def initialize(self) -> None:
        await super().initialize()
        
        # Access config values
        api_key = self.config.get("api_key")
        timeout = self.config.get("timeout", 30.0)
        
        # Config is validated automatically
        # Missing required fields will raise ValueError
```

## Examples

See `src/plugins/examples/` for complete examples:

### 1. Logging Plugin

Logs all requests, responses, and token usage:

```python
from src.plugins.examples.logging_plugin import LoggingPlugin

plugin = LoggingPlugin(config={
    "log_level": "INFO",
    "log_requests": True,
    "log_responses": True,
    "log_tokens": True
})
```

### 2. Analytics Plugin

Tracks metrics and usage statistics:

```python
from src.plugins.examples.analytics_plugin import AnalyticsPlugin

plugin = AnalyticsPlugin(config={
    "track_requests": True,
    "track_tokens": True,
    "track_errors": True
})

# Get metrics
metrics = plugin.get_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Token usage: {metrics['token_usage']}")
```

### 3. Custom Tool Plugin

Adds external API tools:

```python
from src.plugins.examples.custom_tool_plugin import WeatherToolPlugin

plugin = WeatherToolPlugin(config={
    "api_key": "your-weather-api-key",
    "units": "metric"
})

# Use tool
weather = await plugin.get_weather("Boston")
print(f"Temperature: {weather['temperature']}°C")

# Get OpenAI function definition
function_def = plugin.get_tool_definition()
```

## Best Practices

### 1. Error Handling

```python
class MyPlugin(Plugin):
    async def on_request(self, request: Dict) -> None:
        try:
            # Process request
            result = await self.process(request)
        except Exception as e:
            # Handle error
            await self.on_error(e, {"request": request})
            raise
```

### 2. Resource Management

```python
class MyPlugin(Plugin):
    async def start(self) -> None:
        await super().start()
        # Open connections
        self.client = httpx.AsyncClient()
    
    async def cleanup(self) -> None:
        await super().cleanup()
        # Close connections
        if hasattr(self, 'client'):
            await self.client.aclose()
```

### 3. Logging

```python
class MyPlugin(Plugin):
    async def initialize(self) -> None:
        await super().initialize()
        
        # Use plugin logger
        self.logger.info("Plugin initialized")
        self.logger.debug(f"Config: {self.config}")
        self.logger.error("Error occurred", exc_info=True)
```

### 4. State Checking

```python
class MyPlugin(Plugin):
    async def do_something(self) -> None:
        if self.state != PluginState.STARTED:
            self.logger.warning("Plugin not started")
            return
        
        # Proceed with operation
```

### 5. Dependency Management

```python
class MyPlugin(Plugin):
    async def initialize(self) -> None:
        await super().initialize()
        
        # Get dependent plugin
        registry = get_registry()
        dep_plugin = registry.get_plugin("dependency_name")
        
        if dep_plugin:
            # Use dependency
            pass
```

## Testing

### Unit Tests

```python
import pytest
from your_plugin import MyPlugin

@pytest.mark.asyncio
async def test_plugin_initialization():
    """Test plugin initializes correctly."""
    plugin = MyPlugin(config={"api_key": "test-key"})
    await plugin.initialize()
    
    assert plugin.state == PluginState.INITIALIZED
    assert plugin.config["api_key"] == "test-key"

@pytest.mark.asyncio
async def test_hook_execution():
    """Test hook execution."""
    plugin = MyPlugin(config={"api_key": "test-key"})
    await plugin.initialize()
    
    result = await plugin.execute_hook(
        PluginHook.BEFORE_REQUEST,
        {"method": "GET"}
    )
    
    assert result is not None
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_plugin_with_manager():
    """Test plugin with manager."""
    manager = PluginManager()
    manager.registry.register_plugin_class("MyPlugin", MyPlugin)
    
    # Load and start
    await manager.load_plugin("MyPlugin", config={"api_key": "test"})
    await manager.start_plugin("my_plugin")
    
    # Verify
    plugin = manager.registry.get_plugin("my_plugin")
    assert plugin.state == PluginState.STARTED
    
    # Cleanup
    await manager.stop_plugin("my_plugin")
    await manager.unload_plugin("my_plugin")
```

## Troubleshooting

### Plugin Not Loading

```python
# Check if plugin class is registered
registry = get_registry()
plugin_class = registry.get_plugin_class("MyPlugin")
if not plugin_class:
    print("Plugin class not registered")

# Check dependencies
plugin = MyPlugin()
missing = registry.check_dependencies(plugin)
if missing:
    print(f"Missing dependencies: {missing}")
```

### Configuration Errors

```python
try:
    plugin = MyPlugin(config={})
    await plugin.initialize()
except ValueError as e:
    print(f"Config error: {e}")
```

### State Issues

```python
plugin = registry.get_plugin("my_plugin")
print(f"Current state: {plugin.state}")
print(f"Can start: {plugin.state == PluginState.INITIALIZED}")
```

### Hook Not Executing

```python
# Check if hook is registered
hooks = plugin.get_hooks(PluginHook.BEFORE_REQUEST)
print(f"Registered hooks: {len(hooks)}")

# Check if plugin is enabled
if not plugin.metadata.enabled:
    print("Plugin is disabled")
```

## API Reference

For complete API documentation, see the docstrings in:
- `src/plugins/base.py` - Plugin base class
- `src/plugins/registry.py` - Plugin registry
- `src/plugins/manager.py` - Plugin manager

## Support

For issues or questions:
- Check examples in `src/plugins/examples/`
- Review tests in `tests/test_plugin_system.py`
- File an issue: https://github.com/itsmepraks/zakera/issues
