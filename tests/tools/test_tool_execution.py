"""Tests for tool execution."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


class TestToolExecution:
    """Test suite for tool execution."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_success(self, mock_calculator_tool):
        """Test successful tool execution."""
        result = await mock_calculator_tool.execute(operation="add", a=5, b=3)
        
        assert result["success"] is True
        assert "result" in result
        assert mock_calculator_tool.execution_count == 1
    
    @pytest.mark.asyncio
    async def test_tool_execution_failure(self, failing_tool):
        """Test tool execution failure handling."""
        with pytest.raises(Exception) as exc_info:
            await failing_tool.execute()
        
        assert "failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_multiple_tool_executions(self, mock_calculator_tool):
        """Test multiple tool executions."""
        for i in range(5):
            result = await mock_calculator_tool.execute(operation="add", a=i, b=1)
            assert result["execution_count"] == i + 1
        
        assert mock_calculator_tool.execution_count == 5
    
    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self, mock_calculator_tool, mock_search_tool):
        """Test parallel execution of multiple tools."""
        results = await asyncio.gather(
            mock_calculator_tool.execute(operation="add", a=1, b=2),
            mock_search_tool.execute(query="test"),
        )
        
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert mock_calculator_tool.execution_count == 1
        assert mock_search_tool.execution_count == 1
    
    @pytest.mark.asyncio
    async def test_tool_execution_with_retry(self, failing_tool, mock_calculator_tool):
        """Test tool execution with retry logic."""
        tools = [failing_tool, mock_calculator_tool]
        
        result = None
        for tool in tools:
            try:
                result = await tool.execute()
                break
            except Exception:
                continue
        
        assert result is not None
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_tool_caching(self, mock_calculator_tool):
        """Test tool result caching (simulated)."""
        # First execution
        result1 = await mock_calculator_tool.execute(operation="add", a=5, b=3)
        
        # Simulated cached execution (would be the same result)
        result2 = await mock_calculator_tool.execute(operation="add", a=5, b=3)
        
        # Both should succeed
        assert result1["success"] is True
        assert result2["success"] is True
        # Execution count shows both were called (in real impl, cache would prevent second call)
        assert mock_calculator_tool.execution_count == 2
