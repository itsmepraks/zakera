"""Advanced health check endpoints with detailed system monitoring."""
import psutil
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ...monitoring.health_checks import (
    HealthChecker,
    ComponentHealth,
    SystemHealth,
    HealthStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring/health", tags=["health"])


@router.get(
    "/advanced",
    response_model=SystemHealth,
    summary="Advanced health check",
    description="""
    Comprehensive health check with detailed component status.
    
    Checks:
    - Database health (connection pool, query performance)
    - Model provider availability (OpenAI, Anthropic, Ollama, etc.)
    - System resources (CPU, memory, disk usage)
    - External dependencies (Redis, message queues)
    - Performance metrics and latency
    
    Returns overall system health status with detailed component breakdown.
    """,
)
async def advanced_health_check(
    include_metrics: bool = Query(default=True, description="Include system metrics"),
    include_providers: bool = Query(default=True, description="Check model providers"),
    db: Session = Depends(get_db),
) -> SystemHealth:
    """Perform advanced health check with detailed monitoring."""
    health_checker = HealthChecker(db)
    
    # Gather all health checks
    health_data = await health_checker.check_all(
        include_metrics=include_metrics,
        include_providers=include_providers,
    )
    
    return health_data


@router.get(
    "/database",
    summary="Database health check",
    description="Detailed database health including connection pool and query performance",
)
async def database_health(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Check database health and performance."""
    health_checker = HealthChecker(db)
    return await health_checker.check_database()


@router.get(
    "/providers",
    summary="Model provider health",
    description="Check availability and status of all model providers",
)
async def providers_health() -> Dict[str, Any]:
    """Check health of all model providers."""
    health_checker = HealthChecker(None)
    return await health_checker.check_model_providers()


@router.get(
    "/system",
    summary="System metrics",
    description="Current system resource utilization (CPU, memory, disk, network)",
)
async def system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    health_checker = HealthChecker(None)
    return await health_checker.check_system_resources()


@router.get(
    "/performance",
    summary="Performance metrics",
    description="Performance benchmarks and latency measurements",
)
async def performance_metrics(
    window_minutes: int = Query(default=5, ge=1, le=60),
) -> Dict[str, Any]:
    """Get performance metrics over time window."""
    health_checker = HealthChecker(None)
    return await health_checker.get_performance_metrics(window_minutes=window_minutes)


@router.get(
    "/dependencies",
    summary="Dependency health",
    description="Check health of external dependencies (Redis, message queues, etc.)",
)
async def dependencies_health() -> Dict[str, Any]:
    """Check health of external dependencies."""
    health_checker = HealthChecker(None)
    return await health_checker.check_dependencies()


@router.get(
    "/live",
    summary="Liveness probe",
    description="Kubernetes liveness probe - is the application running?",
)
async def liveness_probe() -> Dict[str, str]:
    """Simple liveness check for Kubernetes."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe - is the application ready to serve traffic?",
)
async def readiness_probe(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Readiness check for Kubernetes."""
    try:
        # Quick database check
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "status": "not_ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get(
    "/startup",
    summary="Startup probe",
    description="Kubernetes startup probe - has the application finished starting?",
)
async def startup_probe(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Startup check for Kubernetes."""
    health_checker = HealthChecker(db)
    
    # Check critical components
    checks = await asyncio.gather(
        health_checker.check_database(),
        health_checker.check_model_providers(),
        return_exceptions=True,
    )
    
    # Determine if startup is complete
    db_ok = not isinstance(checks[0], Exception) and checks[0].get("status") == "healthy"
    providers_ok = not isinstance(checks[1], Exception)
    
    if db_ok and providers_ok:
        return {
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
        }
    else:
        return {
            "status": "starting",
            "database_ready": db_ok,
            "providers_ready": providers_ok,
            "timestamp": datetime.utcnow().isoformat(),
        }
