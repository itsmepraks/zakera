"""Prometheus metrics for monitoring.

Defines custom metrics for tracking application performance,
model usage, tool execution, and analytics queries.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from contextlib import contextmanager
import time


# Analytics metrics
analytics_request_counter = Counter(
    "analytics_requests_total",
    "Total number of analytics requests",
    ["endpoint", "user_id"],
)

analytics_request_duration = Histogram(
    "analytics_request_duration_seconds",
    "Analytics request duration in seconds",
    ["endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

analytics_query_duration = Histogram(
    "analytics_query_duration_seconds",
    "Database query duration for analytics",
    ["query_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

analytics_cache_hits = Counter(
    "analytics_cache_hits_total",
    "Number of analytics cache hits",
)

analytics_cache_misses = Counter(
    "analytics_cache_misses_total",
    "Number of analytics cache misses",
)

# Model retry and circuit breaker metrics
model_retry_counter = Counter(
    "model_retry_attempts_total",
    "Total number of model request retry attempts",
    ["model", "error_category"],
)

model_circuit_breaker_state = Gauge(
    "model_circuit_breaker_state",
    "Circuit breaker state for model providers (0=closed, 1=open/half-open)",
    ["provider", "state"],
)

model_request_dedup_counter = Counter(
    "model_request_dedup_total",
    "Number of deduplicated model requests",
)

model_provider_health_score = Gauge(
    "model_provider_health_score",
    "Health score of model providers (0.0 to 1.0)",
    ["provider"],
)

model_provider_error_rate = Gauge(
    "model_provider_error_rate",
    "Error rate of model providers",
    ["provider"],
)

# Existing metrics (examples - adjust based on actual implementation)
api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
)

model_requests_total = Counter(
    "model_requests_total",
    "Total model requests",
    ["model", "provider"],
)

model_request_duration_seconds = Histogram(
    "model_request_duration_seconds",
    "Model request duration",
    ["model", "provider"],
)

model_tokens_total = Counter(
    "model_tokens_total",
    "Total tokens used",
    ["model", "token_type"],
)


@contextmanager
def track_analytics_query(query_type: str):
    """Context manager to track analytics query duration.
    
    Usage:
        with track_analytics_query("overview_metrics"):
            # Perform database query
            result = await db.execute(query)
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        analytics_query_duration.labels(query_type=query_type).observe(duration)
