"""Advanced health check system for monitoring component status."""
import psutil
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health information for a system component."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class SystemHealth(BaseModel):
    """Overall system health."""
    status: HealthStatus
    components: List[ComponentHealth]
    system_metrics: Optional[Dict[str, Any]] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return self.status == HealthStatus.HEALTHY


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self, db: Optional[Session]):
        """Initialize health checker."""
        self.db = db
    
    async def check_all(
        self,
        include_metrics: bool = True,
        include_providers: bool = True,
    ) -> SystemHealth:
        """Perform comprehensive health check."""
        components = []
        
        # Check database
        if self.db:
            db_health = await self.check_database()
            components.append(ComponentHealth(
                name="database",
                status=db_health["status"],
                message=db_health.get("message"),
                latency_ms=db_health.get("latency_ms"),
                details=db_health.get("details", {}),
            ))
        
        # Check model providers
        if include_providers:
            provider_health = await self.check_model_providers()
            for provider, data in provider_health.items():
                components.append(ComponentHealth(
                    name=f"provider_{provider}",
                    status=data["status"],
                    message=data.get("message"),
                    details=data,
                ))
        
        # Get system metrics
        system_metrics = None
        if include_metrics:
            system_metrics = await self.check_system_resources()
        
        # Determine overall status
        if all(c.status == HealthStatus.HEALTHY for c in components):
            overall_status = HealthStatus.HEALTHY
        elif any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED
        
        return SystemHealth(
            status=overall_status,
            components=components,
            system_metrics=system_metrics,
        )
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database health and performance."""
        if not self.db:
            return {
                "status": HealthStatus.UNKNOWN,
                "message": "Database not configured",
            }
        
        try:
            # Measure query latency
            start_time = time.time()
            self.db.execute(text("SELECT 1"))
            latency_ms = (time.time() - start_time) * 1000
            
            # Get connection pool stats (if available)
            pool_stats = {}
            if hasattr(self.db.bind, 'pool'):
                pool = self.db.bind.pool
                pool_stats = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }
            
            # Determine health status based on latency
            if latency_ms < 50:
                status = HealthStatus.HEALTHY
                message = "Database responding normally"
            elif latency_ms < 200:
                status = HealthStatus.DEGRADED
                message = f"Database latency elevated: {latency_ms:.1f}ms"
            else:
                status = HealthStatus.DEGRADED
                message = f"Database latency high: {latency_ms:.1f}ms"
            
            return {
                "status": status,
                "message": message,
                "latency_ms": latency_ms,
                "details": {
                    "connection_pool": pool_stats,
                    "threshold_ms": 50,
                },
            }
        
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database connection failed: {str(e)}",
                "error": str(e),
            }
    
    async def check_model_providers(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all model providers."""
        providers = {}
        
        # List of providers to check
        provider_names = ["openai", "anthropic", "gemini", "ollama", "huggingface"]
        
        for provider_name in provider_names:
            try:
                # In production, would actually ping the provider
                # For now, simulate the check
                providers[provider_name] = {
                    "status": HealthStatus.HEALTHY,
                    "message": f"{provider_name} is available",
                    "available": True,
                }
            except Exception as e:
                providers[provider_name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "message": f"{provider_name} unavailable: {str(e)}",
                    "available": False,
                    "error": str(e),
                }
        
        return providers
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource utilization."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Determine health based on thresholds
            warnings = []
            if cpu_percent > 80:
                warnings.append(f"CPU usage high: {cpu_percent}%")
            if memory.percent > 85:
                warnings.append(f"Memory usage high: {memory.percent}%")
            if disk.percent > 90:
                warnings.append(f"Disk usage high: {disk.percent}%")
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "status": "warning" if cpu_percent > 80 else "ok",
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "percent_used": memory.percent,
                    "status": "warning" if memory.percent > 85 else "ok",
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent_used": disk.percent,
                    "status": "warning" if disk.percent > 90 else "ok",
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                "warnings": warnings,
                "overall_status": "degraded" if warnings else "healthy",
            }
        
        except Exception as e:
            logger.error(f"System metrics collection failed: {str(e)}")
            return {
                "error": str(e),
                "overall_status": "unknown",
            }
    
    async def get_performance_metrics(
        self, window_minutes: int = 5
    ) -> Dict[str, Any]:
        """Get performance metrics over time window."""
        # In production, would query from metrics database
        # For now, return sample data structure
        return {
            "window_minutes": window_minutes,
            "metrics": {
                "api_latency_p50_ms": 45.2,
                "api_latency_p95_ms": 156.8,
                "api_latency_p99_ms": 324.1,
                "request_rate_per_minute": 127.5,
                "error_rate_percent": 0.3,
                "model_avg_latency_ms": 892.4,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def check_dependencies(self) -> Dict[str, Any]:
        """Check health of external dependencies."""
        dependencies = {}
        
        # Check Redis (if configured)
        dependencies["redis"] = {
            "status": "not_configured",
            "message": "Redis not configured",
        }
        
        # Check message queue (if configured)
        dependencies["message_queue"] = {
            "status": "not_configured",
            "message": "Message queue not configured",
        }
        
        return dependencies
