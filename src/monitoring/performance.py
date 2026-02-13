"""Performance monitoring and profiling"""

import time
import functools
import asyncio
from typing import Callable, Optional, Dict, Any
from contextlib import asynccontextmanager, contextmanager
from collections import defaultdict
import threading

from .metrics import (
    model_request_duration_seconds,
    tool_execution_duration_seconds,
    db_query_duration_seconds,
    active_model_requests,
    active_tool_executions
)
from .logging import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """Central performance monitoring"""
    
    def __init__(self):
        self._execution_times = defaultdict(list)
        self._call_counts = defaultdict(int)
        self._lock = threading.Lock()
    
    def record_execution(self, name: str, duration: float):
        """Record function execution time"""
        with self._lock:
            self._execution_times[name].append(duration)
            self._call_counts[name] += 1
    
    def get_statistics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            if name:
                times = self._execution_times.get(name, [])
                if not times:
                    return {}
                
                return {
                    "name": name,
                    "call_count": self._call_counts[name],
                    "avg_duration_ms": sum(times) / len(times) * 1000,
                    "min_duration_ms": min(times) * 1000,
                    "max_duration_ms": max(times) * 1000,
                    "total_duration_ms": sum(times) * 1000
                }
            else:
                # Return all statistics
                stats = {}
                for func_name in self._execution_times.keys():
                    stats[func_name] = self.get_statistics(func_name)
                return stats
    
    def reset(self, name: Optional[str] = None):
        """Reset statistics"""
        with self._lock:
            if name:
                if name in self._execution_times:
                    del self._execution_times[name]
                if name in self._call_counts:
                    del self._call_counts[name]
            else:
                self._execution_times.clear()
                self._call_counts.clear()


# Global performance monitor
performance_monitor = PerformanceMonitor()


def track_execution_time(
    name: Optional[str] = None,
    log_slow: bool = True,
    slow_threshold_ms: float = 1000.0
):
    """
    Decorator to track function execution time
    
    Args:
        name: Custom name for the metric (defaults to function name)
        log_slow: Log if execution is slow
        slow_threshold_ms: Threshold for slow execution warning
    """
    def decorator(func: Callable) -> Callable:
        metric_name = name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    performance_monitor.record_execution(metric_name, duration)
                    
                    duration_ms = duration * 1000
                    if log_slow and duration_ms > slow_threshold_ms:
                        logger.warning(
                            f"Slow execution: {metric_name} took {duration_ms:.2f}ms",
                            function=metric_name,
                            duration_ms=duration_ms,
                            threshold_ms=slow_threshold_ms
                        )
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    performance_monitor.record_execution(metric_name, duration)
                    
                    duration_ms = duration * 1000
                    if log_slow and duration_ms > slow_threshold_ms:
                        logger.warning(
                            f"Slow execution: {metric_name} took {duration_ms:.2f}ms",
                            function=metric_name,
                            duration_ms=duration_ms,
                            threshold_ms=slow_threshold_ms
                        )
            
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def track_model_request(model: str, provider: str):
    """
    Context manager to track model request performance
    
    Usage:
        async with track_model_request("gpt-4", "openai"):
            result = await model_provider.generate(...)
    """
    start_time = time.time()
    active_model_requests.labels(model=model, provider=provider).inc()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        active_model_requests.labels(model=model, provider=provider).dec()
        model_request_duration_seconds.labels(model=model, provider=provider).observe(duration)
        
        logger.debug(
            f"Model request completed",
            model=model,
            provider=provider,
            duration_ms=duration * 1000
        )


@asynccontextmanager
async def track_tool_execution(tool_name: str):
    """
    Context manager to track tool execution performance
    
    Usage:
        async with track_tool_execution("calculator"):
            result = await tool.execute(...)
    """
    start_time = time.time()
    active_tool_executions.labels(tool_name=tool_name).inc()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        active_tool_executions.labels(tool_name=tool_name).dec()
        tool_execution_duration_seconds.labels(tool_name=tool_name).observe(duration)
        
        logger.debug(
            f"Tool execution completed",
            tool_name=tool_name,
            duration_ms=duration * 1000
        )


@contextmanager
def track_db_query(operation: str, table: str):
    """
    Context manager to track database query performance
    
    Usage:
        with track_db_query("SELECT", "users"):
            result = session.execute(query)
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)
        
        logger.debug(
            f"Database query completed",
            operation=operation,
            table=table,
            duration_ms=duration * 1000
        )


class RequestTimer:
    """Timer for tracking request duration"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration_ms = (self.end_time - self.start_time) * 1000
        
        logger.info(
            f"Request timer: {self.name}",
            name=self.name,
            duration_ms=duration_ms,
            success=exc_type is None
        )
    
    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class PerformanceProfiler:
    """
    Simple performance profiler for identifying bottlenecks
    """
    
    def __init__(self, name: str):
        self.name = name
        self.checkpoints = []
        self.start_time = time.time()
        self.last_checkpoint_time = self.start_time
    
    def checkpoint(self, label: str):
        """Add a checkpoint"""
        current_time = time.time()
        duration_from_start = (current_time - self.start_time) * 1000
        duration_from_last = (current_time - self.last_checkpoint_time) * 1000
        
        self.checkpoints.append({
            "label": label,
            "duration_from_start_ms": duration_from_start,
            "duration_from_last_ms": duration_from_last
        })
        
        self.last_checkpoint_time = current_time
        
        logger.debug(
            f"Profiler checkpoint: {label}",
            profiler=self.name,
            label=label,
            duration_from_start_ms=duration_from_start,
            duration_from_last_ms=duration_from_last
        )
    
    def finish(self) -> Dict[str, Any]:
        """Finish profiling and return results"""
        total_duration = (time.time() - self.start_time) * 1000
        
        result = {
            "name": self.name,
            "total_duration_ms": total_duration,
            "checkpoints": self.checkpoints
        }
        
        logger.info(
            f"Profiler finished: {self.name}",
            profiler=self.name,
            total_duration_ms=total_duration,
            checkpoint_count=len(self.checkpoints)
        )
        
        return result
