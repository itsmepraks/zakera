"""
Tool Manager for executing tools and managing tool chains.

Provides high-level interface for tool execution with caching,
rate limiting, retries, and result aggregation.
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.tools.base import Tool, ToolResult, ToolExecutionError
from src.tools.registry import ToolRegistry, get_registry

logger = logging.getLogger(__name__)


class ToolManager:
    """
    Manages tool execution with advanced features.
    
    Features:
    - Result caching
    - Rate limiting
    - Automatic retries
    - Parallel execution
    - Tool chaining
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or get_registry()
        self._cache: Dict[str, tuple[ToolResult, datetime]] = {}
        self._rate_limit_tracker: Dict[str, List[datetime]] = defaultdict(list)
        self._execution_history: List[Dict[str, Any]] = []
        self.cache_ttl = 300  # 5 minutes default
        self.enable_cache = True
        self.enable_rate_limiting = True
        self.max_retries = 3
    
    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key from tool name and parameters."""
        param_str = json.dumps(parameters, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{param_str}".encode()).hexdigest()
    
    def _get_cached_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Optional[ToolResult]:
        """Get cached result if available and not expired."""
        if not self.enable_cache:
            return None
        
        cache_key = self._generate_cache_key(tool_name, parameters)
        
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            age = (datetime.utcnow() - timestamp).total_seconds()
            
            if age < self.cache_ttl:
                logger.info(f"Cache hit for {tool_name} (age: {age:.1f}s)")
                return result
            else:
                # Remove expired entry
                del self._cache[cache_key]
        
        return None
    
    def _cache_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: ToolResult
    ) -> None:
        """Cache a tool result."""
        if not self.enable_cache or not result.success:
            return
        
        cache_key = self._generate_cache_key(tool_name, parameters)
        self._cache[cache_key] = (result, datetime.utcnow())
        logger.debug(f"Cached result for {tool_name}")
    
    def _check_rate_limit(self, tool: Tool) -> bool:
        """
        Check if tool is within rate limit.
        
        Args:
            tool: Tool to check
            
        Returns:
            True if within rate limit, False otherwise
        """
        if not self.enable_rate_limiting or tool.rate_limit is None:
            return True
        
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        self._rate_limit_tracker[tool.name] = [
            ts for ts in self._rate_limit_tracker[tool.name]
            if ts > minute_ago
        ]
        
        # Check limit
        call_count = len(self._rate_limit_tracker[tool.name])
        
        if call_count >= tool.rate_limit:
            logger.warning(
                f"Rate limit exceeded for {tool.name}: "
                f"{call_count}/{tool.rate_limit} calls/minute"
            )
            return False
        
        return True
    
    def _record_call(self, tool_name: str) -> None:
        """Record a tool call for rate limiting."""
        self._rate_limit_tracker[tool_name].append(datetime.utcnow())
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        use_cache: bool = True,
        retry_on_failure: bool = True
    ) -> ToolResult:
        """
        Execute a tool with caching and error handling.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            use_cache: Whether to use cached results
            retry_on_failure: Whether to retry on failure
            
        Returns:
            ToolResult containing execution results
        """
        # Check cache first
        if use_cache and self.enable_cache:
            cached_result = self._get_cached_result(tool_name, parameters)
            if cached_result:
                cached_result.metadata["from_cache"] = True
                return cached_result
        
        # Get tool from registry
        tool = self.registry.get(tool_name)
        
        # Check rate limit
        if not self._check_rate_limit(tool):
            return ToolResult.error_result(
                error=f"Rate limit exceeded for tool '{tool_name}'"
            )
        
        # Execute with retries
        retries = self.max_retries if retry_on_failure else 1
        last_error = None
        
        for attempt in range(retries):
            try:
                # Record call
                self._record_call(tool_name)
                
                # Execute tool
                result = await tool.run(parameters)
                
                # Cache successful result
                if result.success:
                    self._cache_result(tool_name, parameters, result)
                
                # Record execution
                self._record_execution(tool_name, parameters, result, attempt + 1)
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Tool execution failed (attempt {attempt + 1}/{retries}): {e}"
                )
                
                if attempt < retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        error_result = ToolResult.error_result(
            error=f"Tool execution failed after {retries} attempts: {last_error}"
        )
        self._record_execution(tool_name, parameters, error_result, retries)
        return error_result
    
    async def execute_tools_parallel(
        self,
        tool_calls: List[tuple[str, Dict[str, Any]]]
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.
        
        Args:
            tool_calls: List of (tool_name, parameters) tuples
            
        Returns:
            List of ToolResults in same order as input
        """
        tasks = [
            self.execute_tool(tool_name, params)
            for tool_name, params in tool_calls
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_name = tool_calls[i][0]
                processed_results.append(
                    ToolResult.error_result(
                        error=f"Execution failed: {str(result)}"
                    )
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def execute_tool_chain(
        self,
        chain: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """
        Execute a chain of tools where each tool's output feeds the next.
        
        Args:
            chain: List of tool configurations with:
                - tool_name: Name of tool
                - parameters: Tool parameters
                - output_mapping: How to map output to next tool's input
                
        Returns:
            List of ToolResults from each step
        """
        results = []
        previous_output = None
        
        for step in chain:
            tool_name = step["tool_name"]
            parameters = step.get("parameters", {}).copy()
            output_mapping = step.get("output_mapping", {})
            
            # Map previous output to current parameters
            if previous_output and output_mapping:
                for source_key, target_key in output_mapping.items():
                    if source_key in previous_output:
                        parameters[target_key] = previous_output[source_key]
            
            # Execute tool
            result = await self.execute_tool(tool_name, parameters)
            results.append(result)
            
            # Stop chain if execution failed
            if not result.success:
                logger.error(f"Tool chain stopped at {tool_name}: {result.error}")
                break
            
            previous_output = result.data
        
        return results
    
    def _record_execution(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: ToolResult,
        attempts: int
    ) -> None:
        """Record tool execution in history."""
        self._execution_history.append({
            "tool_name": tool_name,
            "parameters": parameters,
            "success": result.success,
            "error": result.error,
            "execution_time": result.execution_time,
            "attempts": attempts,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Keep only last 1000 executions
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-1000:]
    
    def get_execution_history(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get tool execution history.
        
        Args:
            tool_name: Filter by tool name (optional)
            limit: Maximum number of entries to return
            
        Returns:
            List of execution records
        """
        history = self._execution_history
        
        if tool_name:
            history = [h for h in history if h["tool_name"] == tool_name]
        
        return history[-limit:]
    
    def get_statistics(
        self,
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            tool_name: Filter by tool name (optional)
            
        Returns:
            Dictionary with statistics
        """
        history = self._execution_history
        
        if tool_name:
            history = [h for h in history if h["tool_name"] == tool_name]
        
        if not history:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "average_execution_time": 0.0,
            }
        
        successful = [h for h in history if h["success"]]
        failed = [h for h in history if not h["success"]]
        
        execution_times = [
            h["execution_time"] for h in history
            if h["execution_time"] is not None
        ]
        
        return {
            "total_executions": len(history),
            "successful_executions": len(successful),
            "failed_executions": len(failed),
            "success_rate": len(successful) / len(history) * 100 if history else 0,
            "average_execution_time": (
                sum(execution_times) / len(execution_times)
                if execution_times else 0
            ),
            "cache_size": len(self._cache),
        }
    
    def clear_cache(self, tool_name: Optional[str] = None) -> int:
        """
        Clear cached results.
        
        Args:
            tool_name: Clear cache for specific tool (or all if None)
            
        Returns:
            Number of cache entries cleared
        """
        if tool_name:
            # Clear cache for specific tool
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(f"{tool_name}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]
            count = len(keys_to_remove)
        else:
            # Clear all cache
            count = len(self._cache)
            self._cache.clear()
        
        logger.info(f"Cleared {count} cache entries")
        return count
    
    async def validate_tool_chain(
        self,
        chain: List[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a tool chain configuration.
        
        Args:
            chain: Tool chain configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        for i, step in enumerate(chain):
            # Check required fields
            if "tool_name" not in step:
                return False, f"Step {i}: Missing 'tool_name'"
            
            tool_name = step["tool_name"]
            
            # Check if tool exists
            if not self.registry.is_available(tool_name):
                return False, f"Step {i}: Tool '{tool_name}' not available"
            
            # Validate parameters if provided
            if "parameters" in step:
                try:
                    tool = self.registry.get(tool_name)
                    params = step["parameters"].copy()
                    tool.validate_parameters(params)
                except Exception as e:
                    return False, f"Step {i}: Parameter validation failed: {e}"
        
        return True, None


# Global manager instance
_global_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    """
    Get the global tool manager instance.
    
    Returns:
        Global ToolManager instance
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = ToolManager()
        logger.info("Initialized global tool manager")
    
    return _global_manager


def reset_manager() -> None:
    """Reset the global manager."""
    global _global_manager
    _global_manager = None
    logger.info("Reset global tool manager")
