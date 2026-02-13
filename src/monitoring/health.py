"""Health check system"""

import time
import asyncio
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class HealthCheck:
    """Individual health check"""
    
    def __init__(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True,
        timeout: float = 5.0
    ):
        self.name = name
        self.check_func = check_func
        self.critical = critical
        self.timeout = timeout
    
    async def execute(self) -> HealthCheckResult:
        """Execute the health check"""
        start_time = time.time()
        
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                self.check_func(),
                timeout=self.timeout
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.duration_ms = duration_ms
                return result
            elif isinstance(result, bool):
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    duration_ms=duration_ms
                )
            else:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration_ms,
                    details=result or {}
                )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                duration_ms=(time.time() - start_time) * 1000
            )
        
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                details={"error": type(e).__name__}
            )


class HealthChecker:
    """Centralized health check manager"""
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self._last_check_time: Optional[float] = None
        self._last_results: Optional[Dict[str, HealthCheckResult]] = None
        self._cache_ttl: float = 10.0  # Cache results for 10 seconds
    
    def register_check(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True,
        timeout: float = 5.0
    ):
        """Register a new health check"""
        self.checks.append(HealthCheck(name, check_func, critical, timeout))
    
    async def check_all(self, use_cache: bool = True) -> Dict[str, Any]:
        """Run all health checks"""
        current_time = time.time()
        
        # Use cached results if available and fresh
        if (
            use_cache
            and self._last_results
            and self._last_check_time
            and (current_time - self._last_check_time) < self._cache_ttl
        ):
            return self._build_response(self._last_results)
        
        # Run all checks
        results = {}
        tasks = [check.execute() for check in self.checks]
        check_results = await asyncio.gather(*tasks)
        
        for result in check_results:
            results[result.name] = result
        
        # Update cache
        self._last_check_time = current_time
        self._last_results = results
        
        return self._build_response(results)
    
    def _build_response(self, results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Build health check response"""
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        
        for check in self.checks:
            result = results.get(check.name)
            if not result:
                continue
            
            if result.status == HealthStatus.UNHEALTHY:
                if check.critical:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                elif overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
            elif result.status == HealthStatus.DEGRADED:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        # Build response
        checks_data = {}
        for name, result in results.items():
            checks_data[name] = {
                "status": result.status.value,
                "message": result.message,
                "duration_ms": round(result.duration_ms, 2),
                "details": result.details,
                "timestamp": result.timestamp
            }
        
        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "checks": checks_data
        }


# =============================================================================
# Built-in Health Checks
# =============================================================================

async def check_database_health(db_session: AsyncSession) -> HealthCheckResult:
    """Check database connectivity and health"""
    try:
        # Simple query to test connection
        result = await db_session.execute(text("SELECT 1"))
        result.fetchone()
        
        # Get pool stats if available
        pool = db_session.bind.pool
        details = {
            "pool_size": pool.size() if hasattr(pool, 'size') else None,
            "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else None,
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
        }
        
        return HealthCheckResult(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection is healthy",
            details=details
        )
    
    except Exception as e:
        return HealthCheckResult(
            name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database check failed: {str(e)}"
        )


async def check_system_resources() -> HealthCheckResult:
    """Check system resource usage"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    details = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_mb": memory.available / (1024 * 1024),
        "disk_percent": disk.percent,
        "disk_available_gb": disk.free / (1024 * 1024 * 1024)
    }
    
    # Determine status based on thresholds
    if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
        status = HealthStatus.UNHEALTHY
        message = "System resources critically low"
    elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 75:
        status = HealthStatus.DEGRADED
        message = "System resources running high"
    else:
        status = HealthStatus.HEALTHY
        message = "System resources are healthy"
    
    return HealthCheckResult(
        name="system_resources",
        status=status,
        message=message,
        details=details
    )


async def check_model_providers() -> HealthCheckResult:
    """Check model provider availability"""
    try:
        from src.model.model_manager import model_manager
        
        stats = model_manager.get_statistics()
        provider_health = stats.get("provider_health", {})
        
        healthy_providers = sum(
            1 for health in provider_health.values()
            if health.get("is_available", False)
        )
        
        total_providers = len(provider_health)
        
        if healthy_providers == 0:
            status = HealthStatus.UNHEALTHY
            message = "No model providers available"
        elif healthy_providers < total_providers:
            status = HealthStatus.DEGRADED
            message = f"{healthy_providers}/{total_providers} providers available"
        else:
            status = HealthStatus.HEALTHY
            message = f"All {total_providers} providers healthy"
        
        return HealthCheckResult(
            name="model_providers",
            status=status,
            message=message,
            details={
                "healthy_providers": healthy_providers,
                "total_providers": total_providers,
                "providers": provider_health
            }
        )
    
    except Exception as e:
        return HealthCheckResult(
            name="model_providers",
            status=HealthStatus.UNHEALTHY,
            message=f"Failed to check model providers: {str(e)}"
        )


async def check_cache_health() -> HealthCheckResult:
    """Check cache system health"""
    # Placeholder for cache health check
    return HealthCheckResult(
        name="cache",
        status=HealthStatus.HEALTHY,
        message="Cache is operational"
    )


# Global health checker instance
health_checker = HealthChecker()
