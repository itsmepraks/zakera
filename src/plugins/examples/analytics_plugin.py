"""Example plugin for analytics tracking."""

import time
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime

from ..base import Plugin, PluginMetadata, PluginHook


class AnalyticsPlugin(Plugin):
    """Plugin for tracking usage analytics and metrics."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="analytics_plugin",
            version="1.0.0",
            description="Analytics and metrics tracking",
            author="Zakera Team",
            dependencies=[],
            tags=["analytics", "metrics", "monitoring"],
            config_schema={
                "properties": {
                    "track_requests": {"type": "boolean", "default": True},
                    "track_tokens": {"type": "boolean", "default": True},
                    "track_errors": {"type": "boolean", "default": True}
                }
            }
        )
    
    async def initialize(self) -> None:
        """Initialize analytics tracking."""
        await super().initialize()
        
        # Initialize metrics storage
        self.metrics = {
            "requests": defaultdict(int),
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "errors": defaultdict(int),
            "response_times": [],
            "models_used": defaultdict(int)
        }
        
        # Register hooks
        if self.config.get("track_requests", True):
            self.register_hook(PluginHook.BEFORE_REQUEST, self._start_request_timer)
            self.register_hook(PluginHook.AFTER_RESPONSE, self._track_request)
        
        if self.config.get("track_tokens", True):
            self.register_hook(PluginHook.AFTER_GENERATE, self._track_tokens)
        
        if self.config.get("track_errors", True):
            self.register_hook(PluginHook.ON_ERROR, self._track_error)
        
        self.logger.info("Analytics plugin initialized")
    
    async def _start_request_timer(self, request: Dict[str, Any]) -> None:
        """Start timing a request."""
        request["_start_time"] = time.time()
    
    async def _track_request(self, response: Dict[str, Any]) -> None:
        """Track request metrics."""
        # Track request count by endpoint
        endpoint = response.get("endpoint", "unknown")
        self.metrics["requests"][endpoint] += 1
        
        # Track response time
        if "_start_time" in response:
            duration = time.time() - response["_start_time"]
            self.metrics["response_times"].append(duration)
        
        self.logger.debug(f"Tracked request to {endpoint}")
    
    async def _track_tokens(self, result: Dict[str, Any]) -> None:
        """Track token usage."""
        if "usage" in result:
            usage = result["usage"]
            self.metrics["tokens"]["prompt"] += usage.get("prompt_tokens", 0)
            self.metrics["tokens"]["completion"] += usage.get("completion_tokens", 0)
            self.metrics["tokens"]["total"] += usage.get("total_tokens", 0)
        
        # Track model usage
        if "model" in result:
            self.metrics["models_used"][result["model"]] += 1
    
    async def _track_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Track error occurrences."""
        error_type = type(error).__name__
        self.metrics["errors"][error_type] += 1
        self.logger.debug(f"Tracked error: {error_type}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics.
        
        Returns:
            Dictionary of collected metrics
        """
        avg_response_time = (
            sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
            if self.metrics["response_times"] else 0
        )
        
        return {
            "total_requests": sum(self.metrics["requests"].values()),
            "requests_by_endpoint": dict(self.metrics["requests"]),
            "token_usage": dict(self.metrics["tokens"]),
            "total_errors": sum(self.metrics["errors"].values()),
            "errors_by_type": dict(self.metrics["errors"]),
            "avg_response_time": avg_response_time,
            "models_used": dict(self.metrics["models_used"])
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics = {
            "requests": defaultdict(int),
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "errors": defaultdict(int),
            "response_times": [],
            "models_used": defaultdict(int)
        }
        self.logger.info("Metrics reset")
