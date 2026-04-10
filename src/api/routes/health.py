from __future__ import annotations

from datetime import datetime
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "service": "zakera-api",
    }


@router.get("/health/providers")
async def provider_health_check(
    provider: Optional[str] = Query(
        default=None,
        description="Optional provider name to check (e.g. openai, anthropic, ollama)",
    ),
) -> Dict[str, Any]:
    """
    Check provider readiness.

    If ``provider`` is omitted, all registered providers are checked.
    The endpoint verifies provider registration and configuration, and
    surfaces any current cooldown state from the model health tracker.
    """
    from src.model.model_manager import default_health_tracker, list_providers, model_manager

    supported_providers = list_providers()
    provider_names = [provider] if provider else supported_providers

    if provider and provider not in supported_providers:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider '{provider}'. Supported providers: {supported_providers}",
        )

    def _check_single_provider(provider_name: str) -> Dict[str, Any]:
        tracker_status = default_health_tracker.get_status(provider_name)
        status = "healthy" if default_health_tracker.is_healthy(provider_name) else "degraded"
        message = None
        provider_class = None
        model_name = None
        configured = False

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
                f"Provider is cooling down; {tracker_status.get('seconds_until_recovery', 0.0)}s until recovery"
            )

        return {
            "provider": provider_name,
            "status": status,
            "configured": configured,
            "provider_class": provider_class,
            "model": model_name,
            "message": message,
            "health_tracker": tracker_status,
        }

    provider_reports: List[Dict[str, Any]] = [_check_single_provider(name) for name in provider_names]

    if any(report["status"] == "unhealthy" for report in provider_reports):
        overall_status = "unhealthy"
    elif any(report["status"] == "degraded" for report in provider_reports):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checked_providers": len(provider_reports),
        "providers": provider_reports,
    }


@router.get("/status")
async def status():
    """Detailed status information"""
    return {
        "api_version": "0.1.0",
        "status": "operational",
        "uptime": "N/A",  # TODO: Implement uptime tracking
        "features": {
            "chat": True,
            "memory": True,
            "tools": True,
            "streaming": True,
        },
    }
