# Monitoring Setup

Zakera includes built-in monitoring with Prometheus metrics, OpenTelemetry tracing, and structured logging. This guide covers how to set it up.

## What's included

- **Request metrics** — count, latency, and status code for every API request (Prometheus)
- **System metrics** — CPU, memory, and disk usage sampled every 15 seconds
- **Distributed tracing** — OpenTelemetry spans exported to Jaeger
- **Structured logging** — JSON logs with request IDs and rotation via loguru
- **Health probes** — liveness and readiness endpoints for Kubernetes
- **Alerts** — configurable rules that notify via Slack, Discord, or email

## Quick start

Start the full monitoring stack with Docker Compose:

```bash
docker-compose up -d
```

This starts:
- **Prometheus** at http://localhost:9090
- **Grafana** at http://localhost:3001
- **Jaeger** at http://localhost:16686
- **AlertManager** at http://localhost:9093

The Zakera API exposes metrics at `GET /api/v1/monitoring/metrics` in Prometheus text format.

## Endpoints

| Endpoint | What it does |
|----------|-------------|
| `/api/v1/monitoring/metrics` | Prometheus-format metrics |
| `/api/v1/monitoring/health` | Full health check (db, system resources, providers) |
| `/api/v1/monitoring/health/live` | Kubernetes liveness probe |
| `/api/v1/monitoring/health/ready` | Kubernetes readiness probe |
| `/api/v1/monitoring/performance` | Execution time stats for tracked functions |
| `/api/v1/monitoring/alerts` | Active and historical alerts |
| `/api/v1/monitoring/system` | Current CPU, memory, disk, network stats |

## Metrics tracked

The `metrics_middleware` in `src/monitoring/metrics.py` automatically records:

- `api_requests_total` — counter by method, endpoint, status code
- `api_request_duration_seconds` — histogram by method, endpoint
- `system_cpu_percent`, `system_memory_percent`, `system_disk_percent` — gauges updated every 15s
- `model_requests_total` — counter by provider, model, status
- `tool_executions_total` — counter by tool name, status
- `tool_execution_duration_seconds` — histogram by tool name

## Tracing

OpenTelemetry is initialized at startup in `main.py`. It instruments:
- FastAPI requests
- SQLAlchemy database queries
- HTTP clients (httpx, aiohttp, requests)

Traces are exported to Jaeger via OTLP gRPC. View them at http://localhost:16686.

Configuration via environment variables:
- `TRACING_ENABLED` — true/false (default: true)
- `OTLP_ENDPOINT` — Jaeger collector URL (default: http://localhost:4318)
- `TRACING_SAMPLING_RATE` — 0.0 to 1.0 (default: 1.0)

## Alerts

Alert rules are registered at startup via `register_default_alerts()`. Built-in rules:
- High error rate (>10%)
- High CPU usage (>90%)
- High memory usage (>90%)
- Database connection failure
- All model providers down
- Slow response time (>5s average)

Add alert channels (Slack, Discord, email) by configuring the `AlertManager` in `src/monitoring/alerts.py`.

## Configuration files

The `monitoring/` directory at the project root contains:
- `prometheus.yml` — scrape targets and recording rules
- `alertmanager.yml` — alert routing
- `grafana/` — pre-built dashboard JSON files
