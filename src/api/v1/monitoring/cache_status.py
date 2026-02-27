"""FastAPI endpoint for cache monitoring."""

from fastapi import APIRouter, Depends
from typing import Dict, Any

from ....utils.cache_manager import cache_manager
from ....utils.cache_services import (
    ConversationCache,
    ModelResponseCache,
    ToolResultCache,
)

router = APIRouter(prefix="/cache", tags=["cache", "monitoring"])


@router.get("/status")
async def get_cache_status() -> Dict[str, Any]:
    """Get cache status and statistics.

    Returns:
        Cache status information
    """
    is_healthy = await cache_manager.is_healthy()
    stats = await cache_manager.get_stats()

    return {
        "healthy": is_healthy,
        "connected": cache_manager._is_connected,
        "statistics": stats,
        "circuit_breaker": {
            "is_open": cache_manager.circuit_breaker["is_open"],
            "failures": cache_manager.circuit_breaker["failures"],
            "threshold": cache_manager.circuit_breaker["threshold"],
        },
    }


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get detailed cache statistics.

    Returns:
        Detailed cache statistics
    """
    return await cache_manager.get_stats()


@router.post("/clear/{pattern}")
async def clear_cache_pattern(pattern: str) -> Dict[str, Any]:
    """Clear cache entries matching pattern.

    Args:
        pattern: Cache key pattern (e.g., "conversation:*")

    Returns:
        Number of keys deleted
    """
    deleted = await cache_manager.clear_pattern(pattern)
    return {
        "pattern": pattern,
        "deleted": deleted,
    }


@router.post("/warm")
async def warm_cache(priority: str = "normal") -> Dict[str, Any]:
    """Trigger cache warming.

    Args:
        priority: Warming priority ("low", "normal", "high")

    Returns:
        Warming results
    """
    # This would typically import and use the CacheWarmer
    # For now, return a placeholder
    return {
        "status": "warming_initiated",
        "priority": priority,
    }


@router.get("/health")
async def check_cache_health() -> Dict[str, Any]:
    """Check cache health.

    Returns:
        Health status
    """
    is_healthy = await cache_manager.is_healthy()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "connected": cache_manager._is_connected,
        "circuit_breaker_open": cache_manager.circuit_breaker["is_open"],
    }
