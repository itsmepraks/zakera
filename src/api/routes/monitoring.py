"""Monitoring and observability API routes"""

from fastapi import APIRouter, Response, HTTPException, Query
from typing import Optional
import psutil

from src.monitoring.metrics import get_metrics_handler
from src.monitoring.health import health_checker
from src.monitoring.performance import performance_monitor
from src.monitoring.alerts import alert_manager, AlertSeverity

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics")
async def get_metrics():
    """
    Get Prometheus metrics
    
    Returns metrics in Prometheus text format for scraping.
    """
    handler = get_metrics_handler()
    return handler()


@router.get("/health")
async def health_check(detailed: bool = Query(False, description="Include detailed health checks")):
    """
    Get application health status
    
    Returns overall health status and optionally detailed check results.
    """
    try:
        health_result = await health_checker.check_all(use_cache=not detailed)
        return health_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe
    
    Returns 200 if application is alive.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe
    
    Returns 200 if application is ready to serve requests.
    """
    health_result = await health_checker.check_all(use_cache=True)
    
    if health_result["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready"}


@router.get("/performance")
async def get_performance_stats(
    function_name: Optional[str] = Query(None, description="Get stats for specific function")
):
    """
    Get performance statistics
    
    Returns execution time statistics for tracked functions.
    """
    try:
        stats = performance_monitor.get_statistics(function_name)
        return {"statistics": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/performance")
async def reset_performance_stats(
    function_name: Optional[str] = Query(None, description="Reset stats for specific function")
):
    """
    Reset performance statistics
    
    Clears collected performance data.
    """
    try:
        performance_monitor.reset(function_name)
        return {"message": "Performance statistics reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(True, description="Get only active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity")
):
    """
    Get alerts
    
    Returns active or historical alerts.
    """
    try:
        if active_only:
            alerts = alert_manager.get_active_alerts()
        else:
            sev = AlertSeverity(severity) if severity else None
            alerts = alert_manager.get_alert_history(severity=sev)
        
        return {
            "alerts": [
                {
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "details": alert.details,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved,
                    "resolution_time": alert.resolution_time.isoformat() if alert.resolution_time else None
                }
                for alert in alerts
            ],
            "count": len(alerts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system")
async def get_system_info():
    """
    Get system information and resource usage
    
    Returns current system metrics.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network stats if available
        try:
            net_io = psutil.net_io_counters()
            network = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except:
            network = None
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_mb": memory.total / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
                "used_mb": memory.used / (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "used_gb": disk.used / (1024 * 1024 * 1024),
                "free_gb": disk.free / (1024 * 1024 * 1024),
                "percent": disk.percent
            },
            "network": network
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
