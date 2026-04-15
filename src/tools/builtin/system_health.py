"""System health tool for monitoring provider availability.

This tool inspects the provider registry and the shared health tracker from
``src.model.model_manager`` to produce a snapshot of provider readiness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from src.model.model_manager import default_health_tracker, list_providers, model_manager
from src.tools.base import Tool, ToolResult


class SystemHealthTool(Tool):
    """Return the current health state of all registered providers."""

    @property
    def name(self) -> str:
        return "system_health"

    @property
    def description(self) -> str:
        return "Inspect registered AI providers and return their current health status."

    @property
    def category(self) -> str:
        return "monitoring"

    @property
    def tags(self) -> List[str]:
        return ["health", "providers", "monitoring", "status"]

    @property
    def parameters(self) -> List[Any]:
        return []

    async def execute(self, **parameters: Any) -> ToolResult:
        """Collect provider health data from the shared model manager."""
        provider_reports: List[Dict[str, Any]] = []

        for provider_name in list_providers():
            tracker_status = default_health_tracker.get_status(provider_name)
            status = "healthy" if default_health_tracker.is_healthy(provider_name) else "degraded"
            configured = False
            provider_class = None
            model_name = None
            message = None

            try:
                provider_instance = model_manager.get_provider(provider_name)
                configured = True
                provider_class = provider_instance.__class__.__name__
                model_name = getattr(provider_instance, "model_name", None) or getattr(
                    getattr(provider_instance, "config", None),
                    "model",
                    None,
                )
            except Exception as exc:  # noqa: BLE001
                status = "unhealthy"
                message = str(exc)

            if status != "unhealthy" and tracker_status.get("cooling_down"):
                status = "degraded"
                message = (
                    "Provider is cooling down; "
                    f"{tracker_status.get('seconds_until_recovery', 0.0)}s until recovery"
                )

            provider_reports.append(
                {
                    "provider": provider_name,
                    "status": status,
                    "configured": configured,
                    "provider_class": provider_class,
                    "model": model_name,
                    "message": message,
                    "health_tracker": tracker_status,
                }
            )

        if any(report["status"] == "unhealthy" for report in provider_reports):
            overall_status = "unhealthy"
        elif any(report["status"] == "degraded" for report in provider_reports):
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return ToolResult.success_result(
            data={
                "status": overall_status,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "checked_providers": len(provider_reports),
                "providers": provider_reports,
            }
        )
