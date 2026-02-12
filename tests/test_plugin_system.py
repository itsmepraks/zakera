import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.plugins.base import Plugin, PluginMetadata, PluginHook, PluginState
from src.plugins.registry import PluginRegistry
from src.plugins.manager import PluginManager


class MockPlugin(Plugin):
    """Mock plugin for testing."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mock_plugin",
            version="1.0.0",
            description="A mock plugin for testing",
            author="Test Author",
            dependencies=[],
            tags=["test", "mock"]
        )


class DependentPlugin(Plugin):
    """Plugin with dependencies for testing."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dependent_plugin",
            version="1.0.0",
            description="A plugin with dependencies",
            author="Test Author",
            dependencies=["mock_plugin"],
            tags=["test"]
        )


class TestPluginBase:
    """Tests for Plugin base class."""
    
    @pytest.fixture
    def plugin(self):
        """Create a mock plugin instance."""
        return MockPlugin(config={"key": "value"})
    
    def test_initialization(self, plugin):
        """Test plugin initialization."""
        assert plugin.config == {"key": "value"}
        assert plugin.state == PluginState.UNLOADED
        assert plugin.metadata.name == "mock_plugin"
    
    def test_register_hook(self, plugin):
        """Test hook registration."""
        callback = Mock()
        plugin.register_hook(PluginHook.BEFORE_INIT, callback)
        
        hooks = plugin.get_hooks(PluginHook.BEFORE_INIT)
        assert len(hooks) == 1
        assert hooks[0] == callback
    
    @pytest.mark.asyncio
    async def test_execute_hook(self, plugin):
        """Test hook execution."""
        callback = AsyncMock(return_value="result")
        plugin.register_hook(PluginHook.BEFORE_INIT, callback)
        
        results = await plugin.execute_hook(PluginHook.BEFORE_INIT, "arg1", key="value")
        
        assert len(results) == 1
        assert results[0] == "result"
        callback.assert_called_once_with("arg1", key="value")
    
    @pytest.mark.asyncio
    async def test_execute_hook_sync_callback(self, plugin):
        """Test hook execution with synchronous callback."""
        callback = Mock(return_value="sync_result")
        plugin.register_hook(PluginHook.BEFORE_INIT, callback)
        
        results = await plugin.execute_hook(PluginHook.BEFORE_INIT)
        
        assert len(results) == 1
        assert results[0] == "sync_result"
    
    def test_validate_config_success(self, plugin):
        """Test successful config validation."""
        assert plugin.validate_config() is True
    
    def test_validate_config_missing_required(self):
        """Test config validation with missing required fields."""
        
        class RequiredConfigPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="required_config",
                    version="1.0.0",
                    description="Test",
                    author="Test",
                    config_schema={
                        "required": ["api_key"]
                    }
                )
        
        plugin = RequiredConfigPlugin(config={})
        
        with pytest.raises(ValueError, match="Missing required config key: api_key"):
            plugin.validate_config()
    
    @pytest.mark.asyncio
    async def test_initialize(self, plugin):
        """Test plugin initialization."""
        before_hook = AsyncMock()
        after_hook = AsyncMock()
        
        plugin.register_hook(PluginHook.BEFORE_INIT, before_hook)
        plugin.register_hook(PluginHook.AFTER_INIT, after_hook)
        
        await plugin.initialize()
        
        assert plugin.state == PluginState.INITIALIZED
        before_hook.assert_called_once()
        after_hook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start(self, plugin):
        """Test plugin start."""
        await plugin.initialize()
        
        before_hook = AsyncMock()
        after_hook = AsyncMock()
        
        plugin.register_hook(PluginHook.BEFORE_START, before_hook)
        plugin.register_hook(PluginHook.AFTER_START, after_hook)
        
        await plugin.start()
        
        assert plugin.state == PluginState.STARTED
        before_hook.assert_called_once()
        after_hook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop(self, plugin):
        """Test plugin stop."""
        await plugin.initialize()
        await plugin.start()
        
        before_hook = AsyncMock()
        after_hook = AsyncMock()
        
        plugin.register_hook(PluginHook.BEFORE_STOP, before_hook)
        plugin.register_hook(PluginHook.AFTER_STOP, after_hook)
        
        await plugin.stop()
        
        assert plugin.state == PluginState.STOPPED
        before_hook.assert_called_once()
        after_hook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_error(self, plugin):
        """Test error handling."""
        error_hook = AsyncMock()
        plugin.register_hook(PluginHook.ON_ERROR, error_hook)
        
        error = ValueError("Test error")
        context = {"key": "value"}
        
        await plugin.on_error(error, context)
        
        error_hook.assert_called_once_with(error, context)


class TestPluginRegistry:
    """Tests for PluginRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create a plugin registry."""
        return PluginRegistry()
    
    def test_register_plugin_class(self, registry):
        """Test registering a plugin class."""
        registry.register_plugin_class("MockPlugin", MockPlugin)
        
        plugin_class = registry.get_plugin_class("MockPlugin")
        assert plugin_class == MockPlugin
    
    def test_register_plugin(self, registry):
        """Test registering a plugin instance."""
        plugin = MockPlugin()
        registry.register_plugin(plugin)
        
        retrieved = registry.get_plugin("mock_plugin")
        assert retrieved == plugin
    
    def test_unregister_plugin(self, registry):
        """Test unregistering a plugin."""
        plugin = MockPlugin()
        registry.register_plugin(plugin)
        
        registry.unregister_plugin("mock_plugin")
        
        assert registry.get_plugin("mock_plugin") is None
    
    def test_list_plugins(self, registry):
        """Test listing plugins."""
        plugin1 = MockPlugin()
        plugin2 = DependentPlugin()
        
        registry.register_plugin(plugin1)
        registry.register_plugin(plugin2)
        
        plugins = registry.list_plugins()
        assert len(plugins) == 2
        assert "mock_plugin" in plugins
        assert "dependent_plugin" in plugins
    
    def test_list_plugins_by_state(self, registry):
        """Test listing plugins by state."""
        plugin = MockPlugin()
        plugin.state = PluginState.INITIALIZED
        registry.register_plugin(plugin)
        
        initialized = registry.list_plugins(PluginState.INITIALIZED)
        assert len(initialized) == 1
        assert "mock_plugin" in initialized
        
        started = registry.list_plugins(PluginState.STARTED)
        assert len(started) == 0
    
    def test_get_plugin_info(self, registry):
        """Test getting plugin info."""
        plugin = MockPlugin()
        registry.register_plugin(plugin)
        
        info = registry.get_plugin_info("mock_plugin")
        
        assert info is not None
        assert info["name"] == "mock_plugin"
        assert info["version"] == "1.0.0"
        assert info["author"] == "Test Author"
        assert "test" in info["tags"]
    
    def test_check_dependencies(self, registry):
        """Test dependency checking."""
        dependent = DependentPlugin()
        
        # Without dependency
        missing = registry.check_dependencies(dependent)
        assert len(missing) == 1
        assert "mock_plugin" in missing
        
        # With dependency
        mock = MockPlugin()
        registry.register_plugin(mock)
        
        missing = registry.check_dependencies(dependent)
        assert len(missing) == 0


class TestPluginManager:
    """Tests for PluginManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a plugin manager with fresh registry."""
        registry = PluginRegistry()
        return PluginManager(registry)
    
    @pytest.mark.asyncio
    async def test_load_plugin(self, manager):
        """Test loading a plugin."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        
        plugin = await manager.load_plugin("MockPlugin", config={"test": "value"})
        
        assert plugin.metadata.name == "mock_plugin"
        assert plugin.state == PluginState.INITIALIZED
        assert plugin.config == {"test": "value"}
    
    @pytest.mark.asyncio
    async def test_load_plugin_missing_dependencies(self, manager):
        """Test loading plugin with missing dependencies."""
        manager.registry.register_plugin_class("DependentPlugin", DependentPlugin)
        
        with pytest.raises(ValueError, match="missing dependencies"):
            await manager.load_plugin("DependentPlugin")
    
    @pytest.mark.asyncio
    async def test_unload_plugin(self, manager):
        """Test unloading a plugin."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        plugin = await manager.load_plugin("MockPlugin")
        
        await manager.unload_plugin("mock_plugin")
        
        assert manager.registry.get_plugin("mock_plugin") is None
    
    @pytest.mark.asyncio
    async def test_start_plugin(self, manager):
        """Test starting a plugin."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        await manager.load_plugin("MockPlugin")
        
        await manager.start_plugin("mock_plugin")
        
        plugin = manager.registry.get_plugin("mock_plugin")
        assert plugin.state == PluginState.STARTED
    
    @pytest.mark.asyncio
    async def test_stop_plugin(self, manager):
        """Test stopping a plugin."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        await manager.load_plugin("MockPlugin")
        await manager.start_plugin("mock_plugin")
        
        await manager.stop_plugin("mock_plugin")
        
        plugin = manager.registry.get_plugin("mock_plugin")
        assert plugin.state == PluginState.STOPPED
    
    @pytest.mark.asyncio
    async def test_start_all(self, manager):
        """Test starting all plugins."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        await manager.load_plugin("MockPlugin")
        
        await manager.start_all()
        
        plugin = manager.registry.get_plugin("mock_plugin")
        assert plugin.state == PluginState.STARTED
    
    @pytest.mark.asyncio
    async def test_stop_all(self, manager):
        """Test stopping all plugins."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        await manager.load_plugin("MockPlugin")
        await manager.start_all()
        
        await manager.stop_all()
        
        plugin = manager.registry.get_plugin("mock_plugin")
        assert plugin.state == PluginState.STOPPED
    
    @pytest.mark.asyncio
    async def test_execute_hook(self, manager):
        """Test executing hooks across plugins."""
        manager.registry.register_plugin_class("MockPlugin", MockPlugin)
        plugin = await manager.load_plugin("MockPlugin")
        
        callback = AsyncMock(return_value="result")
        plugin.register_hook(PluginHook.BEFORE_REQUEST, callback)
        
        results = await manager.execute_hook(PluginHook.BEFORE_REQUEST, "test_arg")
        
        assert "mock_plugin" in results
        callback.assert_called_once_with("test_arg")
    
    def test_get_plugins_by_tag(self, manager):
        """Test filtering plugins by tag."""
        plugin = MockPlugin()
        manager.registry.register_plugin(plugin)
        
        test_plugins = manager.get_plugins_by_tag("test")
        assert len(test_plugins) == 1
        assert test_plugins[0].metadata.name == "mock_plugin"
        
        other_plugins = manager.get_plugins_by_tag("other")
        assert len(other_plugins) == 0
    
    def test_get_plugin_status(self, manager):
        """Test getting plugin status."""
        plugin = MockPlugin()
        manager.registry.register_plugin(plugin)
        
        status = manager.get_plugin_status()
        
        assert "mock_plugin" in status
        assert status["mock_plugin"]["name"] == "mock_plugin"
        assert status["mock_plugin"]["state"] == PluginState.UNLOADED.value
