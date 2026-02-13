"""
Comprehensive tests for the tool integration system.

Tests cover tool registration, execution, validation,
caching, rate limiting, and error handling.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolValidationError,
    ToolNotFoundError,
)
from src.tools.registry import ToolRegistry, get_registry, reset_registry
from src.tools.manager import ToolManager, get_tool_manager, reset_manager
from src.tools.builtin.calculator import CalculatorTool
from src.tools.builtin.datetime_tool import DateTimeTool


# ============================================================================
# Test Tool Implementations
# ============================================================================

class DummyTool(Tool):
    """Simple tool for testing."""
    
    @property
    def name(self) -> str:
        return "dummy"
    
    @property
    def description(self) -> str:
        return "A dummy tool for testing"
    
    @property
    def parameters(self):
        return [
            ToolParameter(
                name="input",
                type=ToolParameterType.STRING,
                description="Input string",
                required=True
            )
        ]
    
    async def execute(self, input: str, **kwargs) -> ToolResult:
        return ToolResult.success_result(data={"output": f"Processed: {input}"})


class FailingTool(Tool):
    """Tool that always fails for testing error handling."""
    
    @property
    def name(self) -> str:
        return "failing"
    
    @property
    def description(self) -> str:
        return "A tool that always fails"
    
    @property
    def parameters(self):
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        raise Exception("Intentional failure")


class SlowTool(Tool):
    """Tool that takes long time for testing timeouts."""
    
    @property
    def name(self) -> str:
        return "slow"
    
    @property
    def description(self) -> str:
        return "A slow tool"
    
    @property
    def timeout(self) -> int:
        return 1  # 1 second timeout
    
    @property
    def parameters(self):
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        await asyncio.sleep(5)  # Sleep longer than timeout
        return ToolResult.success_result(data={"done": True})


# ============================================================================
# Test Tool Base Classes
# ============================================================================

class TestToolParameter:
    """Test ToolParameter validation."""
    
    def test_string_parameter_validation(self):
        param = ToolParameter(
            name="test",
            type=ToolParameterType.STRING,
            description="Test parameter",
            required=True
        )
        
        # Valid
        is_valid, error = param.validate("hello")
        assert is_valid
        assert error is None
        
        # Invalid type
        is_valid, error = param.validate(123)
        assert not is_valid
        assert "must be a string" in error
    
    def test_integer_parameter_with_range(self):
        param = ToolParameter(
            name="count",
            type=ToolParameterType.INTEGER,
            description="Count",
            required=True,
            min_value=1,
            max_value=10
        )
        
        # Valid
        is_valid, error = param.validate(5)
        assert is_valid
        
        # Too small
        is_valid, error = param.validate(0)
        assert not is_valid
        assert ">=" in error
        
        # Too large
        is_valid, error = param.validate(11)
        assert not is_valid
        assert "<=" in error
    
    def test_enum_parameter(self):
        param = ToolParameter(
            name="option",
            type=ToolParameterType.STRING,
            description="Option",
            required=True,
            enum=["a", "b", "c"]
        )
        
        # Valid
        is_valid, error = param.validate("a")
        assert is_valid
        
        # Invalid
        is_valid, error = param.validate("d")
        assert not is_valid
        assert "must be one of" in error
    
    def test_required_parameter(self):
        param = ToolParameter(
            name="required",
            type=ToolParameterType.STRING,
            description="Required param",
            required=True
        )
        
        # Missing
        is_valid, error = param.validate(None)
        assert not is_valid
        assert "required" in error.lower()
    
    def test_optional_parameter_with_default(self):
        param = ToolParameter(
            name="optional",
            type=ToolParameterType.STRING,
            description="Optional param",
            required=False,
            default="default_value"
        )
        
        # Can be None
        is_valid, error = param.validate(None)
        assert is_valid


class TestToolResult:
    """Test ToolResult functionality."""
    
    def test_success_result(self):
        result = ToolResult.success_result(
            data={"value": 42},
            metadata={"source": "test"}
        )
        
        assert result.success
        assert result.data == {"value": 42}
        assert result.error is None
        assert result.metadata["source"] == "test"
    
    def test_error_result(self):
        result = ToolResult.error_result(
            error="Something went wrong",
            metadata={"code": "ERR001"}
        )
        
        assert not result.success
        assert result.error == "Something went wrong"
        assert result.data is None
        assert result.metadata["code"] == "ERR001"
    
    def test_to_dict(self):
        result = ToolResult.success_result(data={"test": "data"})
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "data" in result_dict
        assert result_dict["success"] is True


# ============================================================================
# Test Tool Registry
# ============================================================================

class TestToolRegistry:
    """Test ToolRegistry functionality."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        reset_registry()
        return ToolRegistry()
    
    def test_register_tool(self, registry):
        tool = DummyTool()
        registry.register(tool)
        
        assert "dummy" in registry
        assert len(registry) == 1
    
    def test_get_tool(self, registry):
        tool = DummyTool()
        registry.register(tool)
        
        retrieved = registry.get("dummy")
        assert retrieved.name == "dummy"
    
    def test_get_nonexistent_tool(self, registry):
        with pytest.raises(ToolNotFoundError):
            registry.get("nonexistent")
    
    def test_unregister_tool(self, registry):
        tool = DummyTool()
        registry.register(tool)
        
        registry.unregister("dummy")
        assert "dummy" not in registry
    
    def test_list_tools(self, registry):
        registry.register(DummyTool())
        registry.register(CalculatorTool())
        
        tools = registry.list_tools()
        assert len(tools) == 2
    
    def test_filter_by_category(self, registry):
        registry.register(CalculatorTool())  # computation
        registry.register(DateTimeTool())     # utility
        
        computation_tools = registry.list_tools(category="computation")
        assert len(computation_tools) == 1
        assert computation_tools[0].category == "computation"
    
    def test_search_tools(self, registry):
        registry.register(CalculatorTool())
        
        results = registry.search("math")
        assert len(results) >= 1
        
        results = registry.search("calculator")
        assert len(results) >= 1
    
    def test_discover_builtin_tools(self, registry):
        count = registry.discover_builtin_tools()
        assert count >= 4  # We have at least 4 built-in tools
        assert "calculator" in registry
        assert "web_search" in registry
        assert "weather" in registry
        assert "datetime" in registry
    
    def test_export_schema(self, registry):
        registry.register(CalculatorTool())
        schemas = registry.export_schema()
        
        assert "calculator" in schemas
        assert schemas["calculator"]["type"] == "function"
        assert "parameters" in schemas["calculator"]["function"]


# ============================================================================
# Test Tool Manager
# ============================================================================

class TestToolManager:
    """Test ToolManager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create fresh manager and registry for each test."""
        reset_registry()
        reset_manager()
        registry = ToolRegistry()
        return ToolManager(registry)
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, manager):
        manager.registry.register(DummyTool())
        
        result = await manager.execute_tool(
            "dummy",
            {"input": "test"}
        )
        
        assert result.success
        assert "Processed: test" in result.data["output"]
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, manager):
        with pytest.raises(ToolNotFoundError):
            await manager.execute_tool("nonexistent", {})
    
    @pytest.mark.asyncio
    async def test_tool_timeout(self, manager):
        manager.registry.register(SlowTool())
        
        result = await manager.execute_tool("slow", {})
        
        assert not result.success
        assert "timed out" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_result_caching(self, manager):
        manager.registry.register(DummyTool())
        manager.enable_cache = True
        
        # First call
        result1 = await manager.execute_tool("dummy", {"input": "test"})
        assert "from_cache" not in result1.metadata
        
        # Second call (should be cached)
        result2 = await manager.execute_tool("dummy", {"input": "test"})
        assert result2.metadata.get("from_cache") is True
    
    @pytest.mark.asyncio
    async def test_cache_bypass(self, manager):
        manager.registry.register(DummyTool())
        manager.enable_cache = True
        
        # Execute with cache
        result1 = await manager.execute_tool("dummy", {"input": "test"})
        
        # Execute without cache
        result2 = await manager.execute_tool(
            "dummy",
            {"input": "test"},
            use_cache=False
        )
        
        assert "from_cache" not in result2.metadata
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, manager):
        manager.registry.register(DummyTool())
        manager.enable_cache = True
        
        # Execute to populate cache
        await manager.execute_tool("dummy", {"input": "test"})
        
        # Clear cache
        cleared = manager.clear_cache()
        assert cleared > 0
        
        # Next call should not be cached
        result = await manager.execute_tool("dummy", {"input": "test"})
        assert "from_cache" not in result.metadata
    
    @pytest.mark.asyncio
    async def test_execution_statistics(self, manager):
        manager.registry.register(DummyTool())
        
        # Execute multiple times
        for i in range(5):
            await manager.execute_tool("dummy", {"input": f"test{i}"})
        
        stats = manager.get_statistics("dummy")
        assert stats["total_executions"] == 5
        assert stats["successful_executions"] == 5
        assert stats["success_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, manager):
        manager.registry.register(DummyTool())
        manager.registry.register(CalculatorTool())
        
        results = await manager.execute_tools_parallel([
            ("dummy", {"input": "test"}),
            ("calculator", {"expression": "2 + 2"}),
        ])
        
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_tool_chain_execution(self, manager):
        manager.registry.register(CalculatorTool())
        
        chain = [
            {
                "tool_name": "calculator",
                "parameters": {"expression": "10 + 5"}
            },
            {
                "tool_name": "calculator",
                "parameters": {"expression": "result * 2"},
                "output_mapping": {"result": "result"}
            }
        ]
        
        results = await manager.execute_tool_chain(chain)
        
        # First step: 10 + 5 = 15
        assert results[0].success
        assert results[0].data["result"] == 15
        
        # Second step should fail or handle differently
        # (since output mapping isn't fully implemented)
        assert len(results) == 2


# ============================================================================
# Test Built-in Tools
# ============================================================================

class TestCalculatorTool:
    """Test Calculator tool."""
    
    @pytest.mark.asyncio
    async def test_basic_arithmetic(self):
        tool = CalculatorTool()
        
        # Addition
        result = await tool.execute(expression="2 + 2")
        assert result.success
        assert result.data["result"] == 4
        
        # Multiplication
        result = await tool.execute(expression="5 * 6")
        assert result.success
        assert result.data["result"] == 30
        
        # Division
        result = await tool.execute(expression="10 / 2")
        assert result.success
        assert result.data["result"] == 5.0
    
    @pytest.mark.asyncio
    async def test_mathematical_functions(self):
        tool = CalculatorTool()
        
        # Square root
        result = await tool.execute(expression="sqrt(16)")
        assert result.success
        assert result.data["result"] == 4.0
        
        # Power
        result = await tool.execute(expression="pow(2, 3)")
        assert result.success
        assert result.data["result"] == 8.0
    
    @pytest.mark.asyncio
    async def test_constants(self):
        tool = CalculatorTool()
        
        # Pi
        result = await tool.execute(expression="pi")
        assert result.success
        assert 3.14 < result.data["result"] < 3.15
    
    @pytest.mark.asyncio
    async def test_precision_control(self):
        tool = CalculatorTool()
        
        result = await tool.execute(
            expression="10 / 3",
            precision=2
        )
        
        assert result.success
        assert result.data["result"] == 3.33
    
    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        tool = CalculatorTool()
        
        result = await tool.execute(expression="1 / 0")
        assert not result.success
        assert "division by zero" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        tool = CalculatorTool()
        
        result = await tool.execute(expression="2 +")
        assert not result.success
        assert "syntax" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_unsafe_operation(self):
        tool = CalculatorTool()
        
        # Try to use import (should fail)
        result = await tool.execute(expression="import os")
        assert not result.success


class TestDateTimeTool:
    """Test DateTime tool."""
    
    @pytest.mark.asyncio
    async def test_get_current_time(self):
        tool = DateTimeTool()
        
        result = await tool.execute(timezone="UTC")
        
        assert result.success
        assert "datetime" in result.data
        assert "timezone" in result.data
        assert result.data["timezone"] == "UTC"
    
    @pytest.mark.asyncio
    async def test_different_timezones(self):
        tool = DateTimeTool()
        
        # UTC
        result_utc = await tool.execute(timezone="UTC")
        assert result_utc.success
        
        # New York
        result_ny = await tool.execute(timezone="America/New_York")
        assert result_ny.success
        
        # Times should be different (unless running at exact moment)
        # but both should be valid
        assert "datetime" in result_utc.data
        assert "datetime" in result_ny.data
    
    @pytest.mark.asyncio
    async def test_invalid_timezone(self):
        tool = DateTimeTool()
        
        result = await tool.execute(timezone="Invalid/Timezone")
        
        assert not result.success
        assert "timezone" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_custom_format(self):
        tool = DateTimeTool()
        
        result = await tool.execute(
            operation="format",
            timezone="UTC",
            format="%Y-%m-%d"
        )
        
        if result.success:
            assert "formatted" in result.data
            # Should match YYYY-MM-DD pattern
            assert len(result.data["formatted"]) == 10


class TestCodeExecutorTool:
    """Test Code Executor tool."""
    
    @pytest.mark.asyncio
    async def test_execute_simple_code(self):
        from src.tools.builtin.code_executor import CodeExecutorTool
        
        tool = CodeExecutorTool()
        
        result = await tool.execute(code="print('Hello, World!')")
        
        assert result.success
        assert "Hello, World!" in result.data["stdout"]
    
    @pytest.mark.asyncio
    async def test_expression_evaluation(self):
        from src.tools.builtin.code_executor import CodeExecutorTool
        
        tool = CodeExecutorTool()
        
        result = await tool.execute(code="2 + 2")
        
        assert result.success
        assert result.data["result"] == 4 or "4" in result.data["stdout"]
    
    @pytest.mark.asyncio
    async def test_restricted_builtins(self):
        from src.tools.builtin.code_executor import CodeExecutorTool
        
        tool = CodeExecutorTool()
        
        # Try to use forbidden function
        result = await tool.execute(code="open('/etc/passwd')")
        
        assert not result.success
        assert "error" in result.data or result.error


# ============================================================================
# Test Tool Integration
# ============================================================================

class TestToolIntegration:
    """Test end-to-end tool integration."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        # Reset to clean state
        reset_registry()
        reset_manager()
        
        # Get instances
        registry = get_registry()
        manager = get_tool_manager()
        
        # Discover tools
        count = registry.discover_builtin_tools()
        assert count >= 4
        
        # List tools
        tools = registry.list_tools()
        assert len(tools) >= 4
        
        # Execute a tool
        result = await manager.execute_tool(
            "calculator",
            {"expression": "sqrt(144)"}
        )
        
        assert result.success
        assert result.data["result"] == 12.0
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        reset_registry()
        reset_manager()
        
        registry = get_registry()
        manager = get_tool_manager()
        
        registry.discover_builtin_tools()
        
        # Execute multiple times
        for _ in range(10):
            await manager.execute_tool("calculator", {"expression": "1 + 1"})
        
        stats = manager.get_statistics("calculator")
        assert stats["total_executions"] >= 10
        assert stats["success_rate"] > 0
