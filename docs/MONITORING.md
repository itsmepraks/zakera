# Monitoring and Observability Guide

Comprehensive guide for monitoring, observability, and alerting in Zakera AI Chat Agent.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Metrics](#metrics)
- [Logging](#logging)
- [Health Checks](#health-checks)
- [Alerts](#alerts)
- [Dashboards](#dashboards)
- [Production Setup](#production-setup)
- [Troubleshooting](#troubleshooting)

## Overview

Zakera includes a comprehensive monitoring stack:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notifications
- **Structured Logging**: JSON logs with correlation IDs
- **Health Checks**: Readiness and liveness probes
- **Performance Tracking**: Execution time monitoring

### Architecture

```
┌─────────────┐
│   Zakera    │
│   API       │
│             │
│  - Metrics  │──────┐
│  - Logs     │      │
│  - Health   │      │
└─────────────┘      │
                     ▼
              ┌─────────────┐      ┌──────────────┐
              │ Prometheus  │─────▶│ AlertManager │
              │             │      │              │
              └─────────────┘      └──────────────┘
                     │                     │
                     ▼                     ▼
              ┌─────────────┐      ┌──────────────┐
              │   Grafana   │      │  Email/Slack │
              │ Dashboards  │      │   Webhooks   │
              └─────────────┘      └──────────────┘
```

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start Prometheus, Grafana, and AlertManager
cd monitoring
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### 3. Configure Alerts

```bash
# Edit alert configuration
vim monitoring/alertmanager.yml

# Add your email or Slack webhook
# Reload AlertManager
docker-compose restart alertmanager
```

### 4. View Metrics

```bash
# API metrics endpoint
curl http://localhost:8000/api/v1/monitoring/metrics

# Health check
curl http://localhost:8000/api/v1/monitoring/health

# System info
curl http://localhost:8000/api/v1/monitoring/system
```

## Metrics

### Available Metrics

#### API Metrics
```prometheus
# Total requests
http_requests_total{method, endpoint, status_code}

# Request duration
http_request_duration_seconds{method, endpoint}

# Request/response size
http_request_size_bytes{method, endpoint}
http_response_size_bytes{method, endpoint}

# Active requests
http_requests_inprogress{method, endpoint}
```

#### Model Metrics
```prometheus
# Model requests
model_requests_total{model, provider, status}

# Request duration
model_request_duration_seconds{model, provider}

# Token usage
model_tokens_total{model, provider, type}  # type: input|output

# Cost tracking
model_cost_total{model, provider}

# Fallback tracking
model_fallback_total{primary_model, fallback_model, reason}

# Active requests
active_model_requests{model, provider}
```

#### Tool Metrics
```prometheus
# Tool executions
tool_executions_total{tool_name, status}

# Execution duration
tool_execution_duration_seconds{tool_name}

# Cache performance
tool_cache_hits_total{tool_name}
tool_cache_misses_total{tool_name}

# Active executions
active_tool_executions{tool_name}
```

#### Database Metrics
```prometheus
# Query metrics
db_queries_total{operation, table, status}
db_query_duration_seconds{operation, table}

# Connection pool
db_connection_pool_size
db_connection_pool_available
db_connection_errors_total
```

#### System Metrics
```prometheus
# Resource usage
system_cpu_usage_percent
system_memory_usage_percent
system_memory_available_bytes
system_disk_usage_percent{mount_point}
system_disk_available_bytes{mount_point}

# Application
app_uptime_seconds
active_users
user_sessions_total{status}
```

### Example Queries

#### Request Rate (last 5 minutes)
```prometheus
sum(rate(http_requests_total[5m])) by (method, status_code)
```

#### Error Rate
```prometheus
sum(rate(http_requests_total{status_code=~"5.."}[5m])) /
sum(rate(http_requests_total[5m]))
```

#### 95th Percentile Response Time
```prometheus
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)
```

#### Model Cost (last hour)
```prometheus
sum(increase(model_cost_total[1h])) by (model, provider)
```

#### Top Used Tools
```prometheus
topk(10,
  sum(rate(tool_executions_total[1h])) by (tool_name)
)
```

## Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error events that might still allow the app to continue
- **CRITICAL**: Critical events that may cause the app to abort

### Log Format

Structured JSON logs with correlation:

```json
{
  "timestamp": "2026-02-13T03:15:30.123456",
  "level": "INFO",
  "logger": "src.api.routes.chat",
  "message": "Chat message processed",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user123",
  "duration_ms": 245.67,
  "model": "llama3:8b",
  "tokens": 156
}
```

### Configuration

```env
# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=logs/zakera.log
JSON_LOGS=true
LOG_ROTATION=true
LOG_MAX_SIZE=10485760  # 10MB
LOG_RETENTION_DAYS=7
```

### Usage in Code

```python
from src.monitoring.logging import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Processing request")

# With context
logger.info(
    "Model request completed",
    model="gpt-4",
    tokens=150,
    duration_ms=234.5
)

# Error logging
logger.error(
    "Model request failed",
    model="gpt-4",
    error=str(e),
    exc_info=True
)
```

### Log Queries

```bash
# View recent logs
tail -f logs/zakera.log | jq .

# Filter by level
cat logs/zakera.log | jq 'select(.level=="ERROR")'

# Filter by request ID
cat logs/zakera.log | jq 'select(.request_id=="abc-123")'

# Find slow requests
cat logs/zakera.log | jq 'select(.duration_ms > 1000)'
```

## Health Checks

### Endpoints

#### Detailed Health Check
```bash
GET /api/v1/monitoring/health?detailed=true
```

Response:
```json
{
  "status": "healthy",
  "timestamp": 1707789123.456,
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection is healthy",
      "duration_ms": 5.23,
      "details": {
        "pool_size": 10,
        "checked_out": 2
      }
    },
    "system_resources": {
      "status": "healthy",
      "message": "System resources are healthy",
      "duration_ms": 2.15,
      "details": {
        "cpu_percent": 45.2,
        "memory_percent": 62.8,
        "disk_percent": 58.3
      }
    },
    "model_providers": {
      "status": "healthy",
      "message": "All 3 providers healthy",
      "duration_ms": 12.45,
      "details": {
        "healthy_providers": 3,
        "total_providers": 3
      }
    }
  }
}
```

#### Liveness Probe (Kubernetes)
```bash
GET /api/v1/monitoring/health/live
```

#### Readiness Probe (Kubernetes)
```bash
GET /api/v1/monitoring/health/ready
```

### Custom Health Checks

```python
from src.monitoring.health import health_checker, HealthCheckResult, HealthStatus

# Register custom check
async def check_custom_service():
    try:
        # Your health check logic
        is_healthy = await my_service.ping()
        
        return HealthCheckResult(
            name="custom_service",
            status=HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY,
            message="Service is responsive"
        )
    except Exception as e:
        return HealthCheckResult(
            name="custom_service",
            status=HealthStatus.UNHEALTHY,
            message=str(e)
        )

health_checker.register_check(
    "custom_service",
    check_custom_service,
    critical=False,
    timeout=5.0
)
```

## Alerts

### Built-in Alert Rules

1. **HighErrorRate**: >5% error rate for 5 minutes
2. **CriticalErrorRate**: >10% error rate for 2 minutes
3. **SlowResponseTime**: p95 > 2s for 10 minutes
4. **HighModelFailureRate**: >20% model failures for 5 minutes
5. **AllModelProvidersDown**: No successful requests for 5 minutes
6. **HighCPUUsage**: >80% CPU for 5 minutes
7. **CriticalMemoryUsage**: >95% memory for 2 minutes
8. **DatabaseConnectionFailures**: Connection errors detected
9. **ZakeraDown**: Application not responding for 1 minute

### Alert Channels

#### Email Alerts

```python
from src.monitoring.alerts import alert_manager, EmailAlertChannel

email_channel = EmailAlertChannel(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="alerts@example.com",
    password="app-password",
    from_addr="zakera@example.com",
    to_addrs=["team@example.com", "oncall@example.com"]
)

alert_manager.add_channel(email_channel)
```

#### Slack Alerts

```python
from src.monitoring.alerts import WebhookAlertChannel

slack_channel = WebhookAlertChannel(
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    format="slack"
)

alert_manager.add_channel(slack_channel)
```

#### Discord Alerts

```python
discord_channel = WebhookAlertChannel(
    webhook_url="https://discord.com/api/webhooks/YOUR/WEBHOOK",
    format="discord"
)

alert_manager.add_channel(discord_channel)
```

### Custom Alert Rules

```python
from src.monitoring.alerts import alert_manager, AlertSeverity
from datetime import timedelta

alert_manager.register_rule(
    name="custom_business_rule",
    check_func=lambda ctx: ctx.get("revenue_drop", 0) > 0.20,
    severity=AlertSeverity.WARNING,
    message_func=lambda ctx: f"Revenue dropped {ctx['revenue_drop']*100:.1f}%",
    cooldown=timedelta(hours=1)
)
```

## Dashboards

### Grafana Setup

1. **Access Grafana**: http://localhost:3001
2. **Login**: admin/admin (change on first login)
3. **Import Dashboard**: 
   - Click "+" → Import
   - Upload `monitoring/grafana/dashboards/zakera-overview.json`
   - Select Prometheus datasource

### Key Dashboard Panels

1. **API Request Rate**: Requests per second by method and status
2. **Response Time**: p95 latency by endpoint
3. **Model Requests**: Requests by provider and status
4. **Model Response Time**: Latency by model
5. **Token Usage**: Input/output tokens by model
6. **Tool Executions**: Tool usage and performance
7. **System Resources**: CPU, memory, disk usage
8. **Database Performance**: Query latency and throughput
9. **Error Rate**: 5xx errors over time
10. **Active Connections**: WebSocket and HTTP

### Custom Dashboards

```python
# Create custom dashboard in Grafana UI or via API
import requests

grafana_url = "http://localhost:3001"
api_key = "your-grafana-api-key"

dashboard_json = {
    "dashboard": {
        "title": "Custom Dashboard",
        "panels": [...]
    }
}

requests.post(
    f"{grafana_url}/api/dashboards/db",
    headers={"Authorization": f"Bearer {api_key}"},
    json=dashboard_json
)
```

## Production Setup

### 1. Environment Configuration

```env
# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
ENABLE_HEALTH_CHECKS=true

# Logging
LOG_LEVEL=INFO
JSON_LOGS=true
LOG_FILE=/var/log/zakera/app.log

# Alerts
ENABLE_ALERTS=true
ALERT_EMAIL_ENABLED=true
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_FROM_EMAIL=zakera@example.com
ALERT_TO_EMAILS=team@example.com,oncall@example.com
```

### 2. Prometheus Production Config

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    environment: 'prod'

scrape_configs:
  - job_name: 'zakera-api'
    static_configs:
      - targets: ['zakera-api:8000']
    
    # Use service discovery in production
    # consul_sd_configs:
    #   - server: 'consul:8500'
```

### 3. AlertManager Production Config

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.sendgrid.net:587'
  smtp_from: 'alerts@zakera.example.com'
  smtp_auth_username: 'apikey'
  smtp_auth_password: '${SENDGRID_API_KEY}'

receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@example.com'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#critical-alerts'
```

### 4. Kubernetes Deployment

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: zakera-api
spec:
  containers:
    - name: zakera
      image: zakera:latest
      livenessProbe:
        httpGet:
          path: /api/v1/monitoring/health/live
          port: 8000
        initialDelaySeconds: 30
        periodSeconds: 10
      readinessProbe:
        httpGet:
          path: /api/v1/monitoring/health/ready
          port: 8000
        initialDelaySeconds: 10
        periodSeconds: 5
```

### 5. Log Aggregation

```yaml
# fluent-bit.conf
[INPUT]
    Name              tail
    Path              /var/log/zakera/*.log
    Parser            json
    Tag               zakera

[OUTPUT]
    Name              es
    Match             *
    Host              elasticsearch
    Port              9200
    Index             zakera-logs
```

## Performance Tracking

### Decorator Usage

```python
from src.monitoring.performance import track_execution_time

@track_execution_time(name="custom_function", slow_threshold_ms=500)
async def my_function():
    # Function logic
    pass
```

### Context Manager Usage

```python
from src.monitoring.performance import track_model_request

async with track_model_request("gpt-4", "openai"):
    response = await model.generate(...)
```

### Profiling

```python
from src.monitoring.performance import PerformanceProfiler

profiler = PerformanceProfiler("complex_operation")

profiler.checkpoint("loaded_data")
# ... do work ...

profiler.checkpoint("processed_data")
# ... more work ...

profiler.checkpoint("saved_results")

results = profiler.finish()
print(results)  # Shows duration of each step
```

## Troubleshooting

### Common Issues

#### 1. Metrics Not Appearing

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check if metrics endpoint is accessible
curl http://localhost:8000/api/v1/monitoring/metrics

# Verify Prometheus scrape config
cat monitoring/prometheus.yml
```

#### 2. Alerts Not Firing

```bash
# Check AlertManager status
curl http://localhost:9093/api/v1/status

# View active alerts
curl http://localhost:9093/api/v1/alerts

# Check Prometheus alerts
curl http://localhost:9090/api/v1/alerts
```

#### 3. High Memory Usage

```bash
# Check metrics retention
# Reduce retention period in prometheus.yml:
storage:
  tsdb:
    retention.time: 15d  # Reduce from 30d
```

#### 4. Missing Logs

```bash
# Check log file permissions
ls -la logs/zakera.log

# Check disk space
df -h

# Verify logging configuration
echo $LOG_LEVEL
echo $LOG_FILE
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export ENABLE_SQL_ECHO=true

# Restart application
python -m uvicorn src.api.main:app --reload
```

## Best Practices

### 1. Metric Naming
- Use descriptive names
- Follow Prometheus naming conventions
- Include units in metric names (e.g., `_seconds`, `_bytes`)

### 2. Label Cardinality
- Avoid high-cardinality labels (e.g., user IDs, request IDs)
- Use labels for dimensions you need to filter/group by
- Limit number of label combinations

### 3. Alert Fatigue
- Set appropriate thresholds
- Use alert grouping and inhibition
- Implement cooldown periods
- Route alerts to right teams

### 4. Log Management
- Use structured logging
- Include correlation IDs
- Implement log rotation
- Set appropriate retention periods
- Index logs for searchability

### 5. Dashboard Design
- Start with overview dashboard
- Create focused dashboards per component
- Use consistent time ranges
- Add annotations for deployments
- Include SLO/SLA indicators

## Monitoring Checklist

- [ ] Prometheus scraping metrics
- [ ] Grafana dashboard accessible
- [ ] Alerts configured and tested
- [ ] Log rotation enabled
- [ ] Health checks responding
- [ ] Metrics retention configured
- [ ] Alert channels tested
- [ ] Runbooks documented
- [ ] On-call rotation set up
- [ ] Backup monitoring configured

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Guide](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)

## Next Steps

1. Review and customize alert thresholds
2. Set up alert notification channels
3. Create custom dashboards for your use cases
4. Configure log aggregation (ELK, Loki, etc.)
5. Set up distributed tracing (Jaeger, Zipkin)
6. Implement SLO/SLA tracking
7. Create runbooks for common alerts
