"""Prometheus metrics collection with comprehensive conversation tracking"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY, Summary
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
# Conversation Metrics
# =============================================================================

conversation_created_total = Counter(
    "conversation_created_total",
    "Total number of conversations created",
    ["model", "user_type"]
)

conversation_started_total = Counter(
    "conversation_started_total",
    "Total number of conversation sessions started",
    ["model"]
)

conversation_successful_total = Counter(
    "conversation_successful_total",
    "Total number of successful conversations (>= 1 message exchange)",
    ["model"]
)

conversations_active_total = Gauge(
    "conversations_active_total",
    "Number of currently active conversations",
    ["model"]
)

conversation_messages_total = Counter(
    "conversation_messages_total",
    "Total number of messages in conversations",
    ["role", "model"]
)

conversation_message_count = Histogram(
    "conversation_message_count",
    "Number of messages per conversation",
    ["model"],
    buckets=(1, 5, 10, 20, 50, 100, 200, 500, 1000)
)

conversation_duration_seconds = Histogram(
    "conversation_duration_seconds",
    "Conversation duration in seconds",
    ["model"],
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400, 28800)
)

conversation_tokens_total = Counter(
    "conversation_tokens_total",
    "Total tokens used in conversations",
    ["model", "token_type"]
)

conversation_cost_total = Counter(
    "conversation_cost_total",
    "Total cost of conversations in USD",
    ["model"]
)

conversation_archived_total = Counter(
    "conversation_archived_total",
    "Total number of archived conversations"
)

conversation_deleted_total = Counter(
    "conversation_deleted_total",
    "Total number of deleted conversations",
    ["delete_type"]  # soft, hard
)

conversation_tags_total = Counter(
    "conversation_tags_total",
    "Total usage of conversation tags",
    ["tag"]
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

model_response_quality = Histogram(
    "model_response_quality",
    "Quality score of model responses (user feedback)",
    ["model", "provider"],
    buckets=(1, 2, 3, 4, 5)
)

# =============================================================================
# Search Metrics
# =============================================================================

search_requests_total = Counter(
    "search_requests_total",
    "Total number of search requests",
    ["search_type", "status"]  # search_type: messages, conversations, all
)

search_duration_seconds = Histogram(
    "search_duration_seconds",
    "Search request duration in seconds",
    ["search_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

search_results_count = Histogram(
    "search_results_count",
    "Number of search results returned",
    ["search_type"],
    buckets=(0, 1, 5, 10, 20, 50, 100, 200)
)

search_no_results_total = Counter(
    "search_no_results_total",
    "Total number of searches with no results",
    ["search_type"]
)

# =============================================================================
# Sharing Metrics
# =============================================================================

conversation_shares_created_total = Counter(
    "conversation_shares_created_total",
    "Total number of conversation shares created",
    ["share_type"]  # public, private
)

conversation_shares_accessed_total = Counter(
    "conversation_shares_accessed_total",
    "Total number of times shared conversations were accessed",
    ["share_type"]
)

active_shares = Gauge(
    "active_shares",
    "Number of active conversation shares",
    ["share_type"]
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
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

db_queries_slow_total = Counter(
    "db_queries_slow_total",
    "Total number of slow queries (> 1s)",
    ["operation", "table"]
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
    "Total number of database connection errors",
    ["error_type"]
)

db_transaction_total = Counter(
    "db_transaction_total",
    "Total number of database transactions",
    ["status"]  # committed, rolled_back
)

# =============================================================================
# User Activity Metrics
# =============================================================================

user_registrations_total = Counter(
    "user_registrations_total",
    "Total number of user registrations"
)

user_logins_total = Counter(
    "user_logins_total",
    "Total number of user logins",
    ["status"]  # success, failed
)

active_users = Gauge(
    "active_users",
    "Number of active users in the last hour"
)

user_sessions_total = Counter(
    "user_sessions_total",
    "Total number of user sessions",
    ["status"]  # started, ended, expired
)

user_activity_total = Counter(
    "user_activity_total",
    "Total user activity events",
    ["activity_type"]  # message_sent, conversation_created, search_performed
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
# Export Metrics
# =============================================================================

export_requests_total = Counter(
    "export_requests_total",
    "Total number of export requests",
    ["format", "status"]
)

export_duration_seconds = Histogram(
    "export_duration_seconds",
    "Export generation duration in seconds",
    ["format"],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

export_messages_total = Counter(
    "export_messages_total",
    "Total number of messages exported",
    ["format"]
)

export_errors_total = Counter(
    "export_errors_total",
    "Total number of export errors",
    ["format", "error_type"]
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

def record_conversation_created(model: str, user_type: str = "regular"):
    """Record conversation creation"""
    conversation_created_total.labels(
        model=model,
        user_type=user_type
    ).inc()
    conversation_started_total.labels(model=model).inc()

def record_conversation_message(role: str, model: str, tokens: int = 0):
    """Record conversation message"""
    conversation_messages_total.labels(
        role=role,
        model=model
    ).inc()
    
    if tokens > 0:
        conversation_tokens_total.labels(
            model=model,
            token_type="message"
        ).inc(tokens)

def record_conversation_complete(model: str, message_count: int, duration: float, total_tokens: int, total_cost: float):
    """Record conversation completion"""
    conversation_successful_total.labels(model=model).inc()
    conversation_message_count.labels(model=model).observe(message_count)
    conversation_duration_seconds.labels(model=model).observe(duration)
    
    if total_tokens > 0:
        conversation_tokens_total.labels(
            model=model,
            token_type="conversation"
        ).inc(total_tokens)
    
    if total_cost > 0:
        conversation_cost_total.labels(model=model).inc(total_cost)

def record_conversation_archived():
    """Record conversation archival"""
    conversation_archived_total.inc()

def record_conversation_deleted(delete_type: str = "soft"):
    """Record conversation deletion"""
    conversation_deleted_total.labels(delete_type=delete_type).inc()

def record_conversation_tag(tag: str):
    """Record conversation tag usage"""
    conversation_tags_total.labels(tag=tag).inc()

def record_search(search_type: str, duration: float, results_count: int, status: str = "success"):
    """Record search operation"""
    search_requests_total.labels(
        search_type=search_type,
        status=status
    ).inc()
    
    search_duration_seconds.labels(
        search_type=search_type
    ).observe(duration)
    
    search_results_count.labels(
        search_type=search_type
    ).observe(results_count)
    
    if results_count == 0:
        search_no_results_total.labels(search_type=search_type).inc()

def record_share_created(share_type: str = "public"):
    """Record share creation"""
    conversation_shares_created_total.labels(share_type=share_type).inc()

def record_share_accessed(share_type: str = "public"):
    """Record share access"""
    conversation_shares_accessed_total.labels(share_type=share_type).inc()

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
    
    # Track slow queries
    if duration > 1.0:
        db_queries_slow_total.labels(
            operation=operation,
            table=table
        ).inc()

def record_db_transaction(status: str):
    """Record database transaction"""
    db_transaction_total.labels(status=status).inc()

def record_user_activity(activity_type: str):
    """Record user activity"""
    user_activity_total.labels(activity_type=activity_type).inc()

def record_export(format: str, duration: float, status: str, messages_count: int = 0):
    """Record export operation"""
    export_requests_total.labels(
        format=format,
        status=status
    ).inc()
    
    export_duration_seconds.labels(format=format).observe(duration)
    
    if messages_count > 0:
        export_messages_total.labels(format=format).inc(messages_count)
