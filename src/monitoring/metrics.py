"""Prometheus metrics and middleware for request tracking."""

import asyncio
import time
from typing import Callable

import psutil
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    generate_latest, CONTENT_TYPE_LATEST,
)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
)

model_requests_total = Counter(
    "model_requests_total",
    "Total model API requests",
    ["provider", "model", "status"],
)

model_tokens_total = Counter(
    "model_tokens_total",
    "Total tokens used",
    ["provider", "model", "type"],
)

active_connections = Gauge(
    "active_connections",
    "Number of active connections",
    ["type"],
)

tool_executions_total = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
)

tool_execution_duration_seconds = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
)
tool_execution_duration = tool_execution_duration_seconds  # alias

# System resource gauges
system_cpu_percent = Gauge("system_cpu_percent", "CPU usage percent")
system_memory_percent = Gauge("system_memory_percent", "Memory usage percent")
system_disk_percent = Gauge("system_disk_percent", "Disk usage percent")

# Performance tracking (used by performance.py)
model_request_duration_seconds = Histogram(
    "model_request_duration_seconds",
    "Model request duration",
    ["provider", "model"],
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"],
)

active_model_requests = Gauge(
    "active_model_requests",
    "Currently active model requests",
    ["provider"],
)

active_tool_executions = Gauge(
    "active_tool_executions",
    "Currently active tool executions",
    ["tool_name"],
)

app_info = Info("app_info", "Application information")


# ---------------------------------------------------------------------------
# Metrics middleware — records request count and latency per endpoint
# ---------------------------------------------------------------------------

def metrics_middleware(app: FastAPI) -> None:
    """Add Prometheus metrics middleware to a FastAPI app."""

    @app.middleware("http")
    async def _record_request_metrics(request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        # Collapse path params to reduce cardinality (e.g. /api/v1/conversations/abc -> /api/v1/conversations/{id})
        path = request.url.path
        method = request.method

        api_requests_total.labels(
            method=method,
            endpoint=path,
            status_code=response.status_code,
        ).inc()

        api_request_duration_seconds.labels(
            method=method,
            endpoint=path,
        ).observe(duration)

        return response


# ---------------------------------------------------------------------------
# System metrics collector — periodically samples CPU / memory / disk
# ---------------------------------------------------------------------------

class SystemMetricsCollector:
    """Background task that updates system-resource gauges."""

    def __init__(self, interval: float = 15.0):
        self.interval = interval
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                system_cpu_percent.set(psutil.cpu_percent(interval=0))
                system_memory_percent.set(psutil.virtual_memory().percent)
                system_disk_percent.set(psutil.disk_usage("/").percent)
            except Exception:
                pass
            await asyncio.sleep(self.interval)


system_metrics_collector = SystemMetricsCollector()


# ---------------------------------------------------------------------------
# Handler for the /metrics endpoint
# ---------------------------------------------------------------------------

def get_metrics_handler() -> Callable:
    """Return a callable that produces Prometheus text-format output."""

    def _handler() -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return _handler
