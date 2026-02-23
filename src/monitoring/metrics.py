"""Prometheus metrics for monitoring."""
from prometheus_client import Counter, Histogram, Gauge, Info

# Existing metrics (placeholder - extend as needed)
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"]
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"]
)

model_requests_total = Counter(
    "model_requests_total",
    "Total model API requests",
    ["provider", "model", "status"]
)

model_tokens_total = Counter(
    "model_tokens_total",
    "Total tokens used",
    ["provider", "model", "type"]
)

model_cost_total = Counter(
    "model_cost_total",
    "Total cost in USD",
    ["provider", "model"]
)

# Rate limiting metrics
rate_limit_counter = Counter(
    "rate_limit_requests_total",
    "Total rate limit checks",
    ["identifier", "endpoint", "status"]
)

rate_limit_exceeded_counter = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["endpoint", "user_tier"]
)

active_rate_limits = Gauge(
    "active_rate_limits",
    "Number of active rate limit entries",
    ["backend"]
)

# System metrics
active_connections = Gauge(
    "active_connections",
    "Number of active connections",
    ["type"]
)

conversation_messages_total = Counter(
    "conversation_messages_total",
    "Total conversation messages",
    ["conversation_id", "role"]
)

tool_executions_total = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"]
)

tool_execution_duration = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"]
)

# Application info
app_info = Info("app_info", "Application information")
