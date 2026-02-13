"""Prometheus metrics collection"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import Request, Response
import time
import psutil
import platform
from typing import Callable
import asyncio

# =============================================================================
# API Metrics
# =============================================================================

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"]
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"]
)

# =============================================================================
# Model Metrics
# =============================================================================

model_requests_total = Counter(
    "model_requests_total",
    "Total number of model requests",
    ["model", "provider", "status"]
)

model_request_duration_seconds = Histogram(
    "model_request_duration_seconds",
    "Model request duration in seconds",
    ["model", "provider"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
)

model_tokens_total = Counter(
    "model_tokens_total",
    "Total number of tokens processed",
    ["model", "provider", "type"]  # type: input or output
)

model_cost_total = Counter(
    "model_cost_total",
    "Total cost of model requests in USD",
    ["model", "provider"]
)

model_fallback_total = Counter(
    "model_fallback_total",
    "Total number of model fallbacks",
    ["primary_model", "fallback_model", "reason"]
)

active_model_requests = Gauge(
    "active_model_requests",
    "Number of active model requests",
    ["model", "provider"]
)

# =============================================================================
# Tool Metrics
# =============================================================================

tool_executions_total = Counter(
    "tool_executions_total",
    "Total number of tool executions",
    ["tool_name", "status"]
)

tool_execution_duration_seconds = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

tool_cache_hits_total = Counter(
    "tool_cache_hits_total",
    "Total number of tool cache hits",
    ["tool_name"]
)

tool_cache_misses_total = Counter(
    "tool_cache_misses_total",
    "Total number of tool cache misses",
    ["tool_name"]
)

active_tool_executions = Gauge(
    "active_tool_executions",
    "Number of active tool executions",
    ["tool_name"]
)

# =============================================================================
# Database Metrics
# =============================================================================

db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["operation", "table", "status"]
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current size of the database connection pool"
)

db_connection_pool_available = Gauge(
    "db_connection_pool_available",
    "Number of available connections in the pool"
)

db_connection_errors_total = Counter(
    "db_connection_errors_total",
    "Total number of database connection errors"
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

websocket_connections_total = Counter(
    "websocket_connections_total",
    "Total number of WebSocket connections",
    ["status"]  # connected, disconnected, error
)

active_websocket_connections = Gauge(
    "active_websocket_connections",
    "Number of active WebSocket connections"
)

websocket_messages_total = Counter(
    "websocket_messages_total",
    "Total number of WebSocket messages",
    ["direction"]  # sent, received
)

# =============================================================================
# System Metrics
# =============================================================================

system_cpu_usage_percent = Gauge(
    "system_cpu_usage_percent",
    "Current CPU usage percentage"
)

system_memory_usage_percent = Gauge(
    "system_memory_usage_percent",
    "Current memory usage percentage"
)

system_memory_available_bytes = Gauge(
    "system_memory_available_bytes",
    "Available memory in bytes"
)

system_disk_usage_percent = Gauge(
    "system_disk_usage_percent",
    "Current disk usage percentage",
    ["mount_point"]
)

system_disk_available_bytes = Gauge(
    "system_disk_available_bytes",
    "Available disk space in bytes",
    ["mount_point"]
)

# =============================================================================
# Application Metrics
# =============================================================================

app_info = Info(
    "app",
    "Application information"
)

app_errors_total = Counter(
    "app_errors_total",
    "Total number of application errors",
    ["error_type", "severity"]
)

app_uptime_seconds = Gauge(
    "app_uptime_seconds",
    "Application uptime in seconds"
)

active_users = Gauge(
    "active_users",
    "Number of active users"
)

user_sessions_total = Counter(
    "user_sessions_total",
    "Total number of user sessions",
    ["status"]  # started, ended
)

# =============================================================================
# Cache Metrics
# =============================================================================

cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type"]
)

cache_size_bytes = Gauge(
    "cache_size_bytes",
    "Current cache size in bytes",
    ["cache_type"]
)

# =============================================================================
# Rate Limiting Metrics
# =============================================================================

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total number of rate limit exceeded events",
    ["endpoint", "user_id"]
)

# =============================================================================
# Middleware
# =============================================================================

def metrics_middleware(app):
    """Add metrics middleware to FastAPI app"""
    
    # Use prometheus-fastapi-instrumentator for automatic metrics
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    
    instrumentator.instrument(app)
    
    # Add custom middleware for additional metrics
    @app.middleware("http")
    async def add_custom_metrics(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get request size
        request_size = int(request.headers.get("content-length", 0))
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract endpoint info
        method = request.method
        endpoint = request.url.path
        status_code = response.status_code
        
        # Update metrics
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        # Get response size if available
        if hasattr(response, "body"):
            response_size = len(response.body)
            http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
        
        return response
    
    return instrumentator


def get_metrics_handler():
    """Get metrics endpoint handler"""
    def metrics_endpoint():
        return Response(content=generate_latest(REGISTRY), media_type="text/plain")
    return metrics_endpoint


# =============================================================================
# System Metrics Updater
# =============================================================================

class SystemMetricsCollector:
    """Background task to collect system metrics"""
    
    def __init__(self, interval: int = 15):
        self.interval = interval
        self._task = None
        self._start_time = time.time()
    
    async def start(self):
        """Start collecting system metrics"""
        self._task = asyncio.create_task(self._collect_loop())
    
    async def stop(self):
        """Stop collecting system metrics"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _collect_loop(self):
        """Continuous collection loop"""
        while True:
            try:
                self._collect_metrics()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                await asyncio.sleep(self.interval)
    
    def _collect_metrics(self):
        """Collect system metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage_percent.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        system_memory_usage_percent.set(memory.percent)
        system_memory_available_bytes.set(memory.available)
        
        # Disk usage
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                system_disk_usage_percent.labels(
                    mount_point=partition.mountpoint
                ).set(usage.percent)
                system_disk_available_bytes.labels(
                    mount_point=partition.mountpoint
                ).set(usage.free)
            except PermissionError:
                continue
        
        # App uptime
        uptime = time.time() - self._start_time
        app_uptime_seconds.set(uptime)


# Initialize system metrics collector
system_metrics_collector = SystemMetricsCollector()


# =============================================================================
# Helper Functions
# =============================================================================

def record_model_request(
    model: str,
    provider: str,
    duration: float,
    status: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: float = 0.0
):
    """Record model request metrics"""
    model_requests_total.labels(
        model=model,
        provider=provider,
        status=status
    ).inc()
    
    model_request_duration_seconds.labels(
        model=model,
        provider=provider
    ).observe(duration)
    
    if input_tokens > 0:
        model_tokens_total.labels(
            model=model,
            provider=provider,
            type="input"
        ).inc(input_tokens)
    
    if output_tokens > 0:
        model_tokens_total.labels(
            model=model,
            provider=provider,
            type="output"
        ).inc(output_tokens)
    
    if cost > 0:
        model_cost_total.labels(
            model=model,
            provider=provider
        ).inc(cost)


def record_tool_execution(
    tool_name: str,
    duration: float,
    status: str,
    cache_hit: bool = False
):
    """Record tool execution metrics"""
    tool_executions_total.labels(
        tool_name=tool_name,
        status=status
    ).inc()
    
    tool_execution_duration_seconds.labels(
        tool_name=tool_name
    ).observe(duration)
    
    if cache_hit:
        tool_cache_hits_total.labels(tool_name=tool_name).inc()
    else:
        tool_cache_misses_total.labels(tool_name=tool_name).inc()


def record_db_query(
    operation: str,
    table: str,
    duration: float,
    status: str
):
    """Record database query metrics"""
    db_queries_total.labels(
        operation=operation,
        table=table,
        status=status
    ).inc()
    
    db_query_duration_seconds.labels(
        operation=operation,
        table=table
    ).observe(duration)
