"""Example plugin that adds comprehensive logging."""

import time
from typing import Dict, Any
import logging
from datetime import datetime

from ..base import Plugin, PluginMetadata, PluginHook


class LoggingPlugin(Plugin):
    """Plugin for logging requests, responses, and model interactions."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="logging_plugin",
            version="1.0.0",
            description="Comprehensive logging for Zakera",
            author="Zakera Team",
            dependencies=[],
            tags=["logging", "monitoring"],
            config_schema={
                "properties": {
                    "log_level": {"type": "string", "default": "INFO"},
                    "log_requests": {"type": "boolean", "default": True},
                    "log_responses": {"type": "boolean", "default": True},
                    "log_tokens": {"type": "boolean", "default": True}
                }
            }
        )
    
    async def initialize(self) -> None:
        """Initialize logging configuration."""
        await super().initialize()
        
        # Configure logging level
        log_level = self.config.get("log_level", "INFO")
        self.logger.setLevel(getattr(logging, log_level))
        
        # Register hooks
        if self.config.get("log_requests", True):
            self.register_hook(PluginHook.BEFORE_REQUEST, self._log_request)
        
        if self.config.get("log_responses", True):
            self.register_hook(PluginHook.AFTER_RESPONSE, self._log_response)
        
        if self.config.get("log_tokens", True):
            self.register_hook(PluginHook.AFTER_GENERATE, self._log_token_usage)
        
        self.logger.info("Logging plugin initialized")
    
    async def _log_request(self, request: Dict[str, Any]) -> None:
        """Log incoming requests."""
        self.logger.info(
            f"Request received: {request.get('method')} {request.get('path')}",
            extra={
                "timestamp": datetime.now().isoformat(),
                "request_id": request.get("id"),
                "user": request.get("user")
            }
        )
    
    async def _log_response(self, response: Dict[str, Any]) -> None:
        """Log outgoing responses."""
        self.logger.info(
            f"Response sent: {response.get('status_code')}",
            extra={
                "timestamp": datetime.now().isoformat(),
                "request_id": response.get("request_id"),
                "duration_ms": response.get("duration_ms")
            }
        )
    
    async def _log_token_usage(self, result: Dict[str, Any]) -> None:
        """Log token usage from model responses."""
        if "usage" in result:
            usage = result["usage"]
            self.logger.info(
                f"Token usage - Prompt: {usage.get('prompt_tokens')}, "
                f"Completion: {usage.get('completion_tokens')}, "
                f"Total: {usage.get('total_tokens')}",
                extra={
                    "model": result.get("model"),
                    "timestamp": datetime.now().isoformat()
                }
            )
