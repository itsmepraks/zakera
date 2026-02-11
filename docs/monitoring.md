# Monitoring and Observability Guide

## Overview

Zakera includes comprehensive monitoring capabilities using Prometheus, Grafana, and custom logging.

## Metrics Collection

### Prometheus Metrics

The application exposes metrics at `/metrics` endpoint.

#### Available Metrics

**Request Metrics:**
```
# Total HTTP requests
http_requests_total{method="POST", endpoint="/chat/message", status="200"}

# Request duration histogram
http_request_duration_seconds{method="POST", endpoint="/chat/message"}

# Active requests
http_requests_in_progress{endpoint="/chat/message"}
```

**AI Model Metrics:**
```
# Total AI model calls
ai_model_calls_total{provider="openai", model="gpt-4"}

# Token usage
ai_tokens_used_total{provider="openai", model="gpt-4", type="prompt|completion"}

# Model latency
ai_model_latency_seconds{provider="openai", model="gpt-4"}

# Model errors
ai_model_errors_total{provider="openai", model="gpt-4", error_type="timeout"}
```

**Database Metrics:**
```
# Database query duration
db_query_duration_seconds{operation="select", table="conversations"}

# Connection pool status
db_connection_pool_size{status="active|idle"}

# Query errors
db_errors_total{operation="insert", table="messages"}
```

**Application Metrics:**
```
# Active conversations
active_conversations_gauge

# Message queue length
message_queue_length

# Cache hit rate
cache_hit_rate{cache="conversation"}
```

### Setting Up Prometheus

1. **Add Prometheus configuration** (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'zakera-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

2. **Run Prometheus:**

```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

3. **Access Prometheus UI:** http://localhost:9090

## Grafana Dashboards

### Setup

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana
```

Default credentials: `admin/admin`

### Import Dashboard

Import the pre-configured dashboard from `config/grafana/zakera-dashboard.json`

### Key Panels

1. **Request Rate**
   - Total requests per second
   - Breakdown by endpoint
   - Success/error rates

2. **Response Time**
   - P50, P95, P99 latencies
   - Per-endpoint breakdown

3. **AI Model Performance**
   - Calls per second by provider
   - Token usage trends
   - Error rates

4. **Database Performance**
   - Query duration
   - Connection pool status
   - Slow query alerts

5. **System Resources**
   - CPU usage
   - Memory usage
   - Disk I/O

## Logging

### Log Levels

```python
# config/logging.py
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/zakera.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'DEBUG'
        }
    },
    'loggers': {
        'zakera': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}
```

### Structured Logging Example

```python
import logging
import structlog

logger = structlog.get_logger()

logger.info(
    "message_sent",
    conversation_id="conv_123",
    user_id="user_456",
    tokens_used=245,
    latency_ms=850
)
```

## Health Checks

### Endpoints

#### Basic Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T22:00:00Z",
  "version": "1.0.0"
}
```

#### Detailed Health Check
```http
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T22:00:00Z",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12
    },
    "ai_provider": {
      "status": "healthy",
      "provider": "openai",
      "response_time_ms": 234
    },
    "cache": {
      "status": "healthy",
      "hit_rate": 0.87
    },
    "disk_space": {
      "status": "healthy",
      "free_gb": 45.3,
      "total_gb": 100
    }
  },
  "metrics": {
    "uptime_seconds": 86400,
    "requests_per_minute": 1250,
    "active_conversations": 42
  }
}
```

## Alerting

### Prometheus Alert Rules

Create `alerts.yml`:

```yaml
groups:
  - name: zakera_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/sec"
      
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, 
            rate(http_request_duration_seconds_bucket[5m])
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "P95 latency is {{ $value }}s"
      
      - alert: AIModelErrors
        expr: |
          rate(ai_model_errors_total[5m]) > 0.1
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "AI model errors detected"
          description: "Error rate: {{ $value }} errors/sec"
      
      - alert: DatabaseConnectionPool
        expr: |
          db_connection_pool_size{status="active"} 
          / db_connection_pool_size{status="total"} > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool nearly exhausted"
```

### AlertManager Configuration

```yaml
# alertmanager.yml
route:
  receiver: 'team-email'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@zakera.ai'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@zakera.ai'
        auth_password: 'password'
  
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: 'Zakera Alert: {{ .GroupLabels.alertname }}'
```

## Performance Monitoring

### Application Performance Monitoring (APM)

Integrate with tools like:

1. **New Relic**
2. **Datadog**
3. **Sentry** (for error tracking)

### Custom Performance Tracking

```python
from src.api.monitoring import track_performance

@track_performance("chat_message")
async def send_message(message: str):
    # Your code here
    pass
```

## Tracing

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_message")
async def process_message(message: str):
    with tracer.start_as_current_span("ai_call"):
        response = await ai_provider.generate(message)
    return response
```

## Best Practices

1. **Set up alerts for critical metrics**
   - Error rates > 1%
   - Latency P95 > 2s
   - Database connection pool > 80%

2. **Monitor business metrics**
   - Active users
   - Conversation starts
   - Message volume

3. **Track costs**
   - AI API token usage
   - Infrastructure costs

4. **Regular dashboard reviews**
   - Daily: Quick health check
   - Weekly: Performance trends
   - Monthly: Capacity planning

5. **Log retention**
   - Keep 30 days locally
   - Archive to S3 for compliance

## Troubleshooting

### High Memory Usage

```bash
# Check memory usage
docker stats zakera-api

# Check for memory leaks
python -m memory_profiler src/api/main.py
```

### Database Connection Issues

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND query_start < now() - interval '5 minutes';
```

### AI Provider Timeouts

```python
# Adjust timeout settings in config
AI_PROVIDER_TIMEOUT = 30  # seconds
AI_PROVIDER_RETRIES = 3
```
