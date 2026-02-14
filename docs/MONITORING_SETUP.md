# Monitoring & Observability Setup Guide

Complete guide to setting up and using the Zakera monitoring and observability system.

## Overview

Zakera includes a comprehensive monitoring stack providing:

- **Real-time metrics** via Prometheus
- **Visual dashboards** via Grafana
- **Intelligent alerting** via AlertManager
- **Log aggregation** via Loki
- **System monitoring** via Node Exporter & cAdvisor

## Quick Start

### Start Monitoring Stack

```bash
# Start all monitoring services
cd monitoring
docker-compose up -d

# Verify services
docker-compose ps

# View logs
docker-compose logs -f grafana
```

### Access Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093
- **cAdvisor**: http://localhost:8080

### Default Login

```
Username: admin
Password: admin
```

**⚠️ Change default password in production!**

## Architecture

```
┌─────────────────────────────────────────────────┐
│                Zakera AI Agent                   │
│          (Exposes /metrics endpoint)             │
└────────────────┬────────────────────────────────┘
                 │
                 │ Scrapes metrics every 10s
                 ▼
┌─────────────────────────────────────────────────┐
│              Prometheus                          │
│   - Stores time-series metrics                  │
│   - Evaluates alert rules                       │
│   - Serves PromQL queries                       │
└────┬─────────────────────────┬──────────────────┘
     │                         │
     │ Sends alerts            │ Query metrics
     ▼                         ▼
┌─────────────┐        ┌──────────────────────────┐
│AlertManager │        │       Grafana            │
│- Routes     │        │ - Visualizes metrics     │
│- Deduplicates│       │ - Creates dashboards     │
│- Notifies   │        │ - Sends notifications    │
└─────────────┘        └──────────────────────────┘
     │
     │ Email/Slack/Discord
     ▼
┌─────────────┐
│ Operators   │
└─────────────┘
```

## Grafana Dashboards

### 1. AI Chat Agent Overview

**Purpose**: High-level system health and performance

**Panels**:
- System health status
- Active conversations
- Messages per minute
- Average response time
- API request rate
- Error rate
- Model provider distribution
- Token usage by model
- Database connection pool
- Database query performance
- Cost per hour
- Conversation success rate

**Access**: Default dashboard on login

### 2. Conversation Performance

**Purpose**: Deep dive into conversation metrics

**Panels**:
- Conversation creation rate
- Message throughput
- Conversation duration distribution
- Messages per conversation
- Active users
- Archive/delete rates
- Message success rate
- Top conversations by messages
- Tag distribution

**Use Case**: Optimize conversation handling

### 3. Database Performance

**Purpose**: Database health and optimization

**Panels**:
- Query performance by operation (p95)
- Query rate monitoring
- Connection pool status
- Transaction success/rollback rates
- Database size growth
- Table row counts
- Slow query detection
- Database errors
- Cache hit rate
- Conversation load time
- Message persistence latency

**Use Case**: Identify database bottlenecks

### 4. Model Performance & Cost Analysis

**Purpose**: Track AI model usage and costs

**Panels**:
- Model usage distribution
- Provider response time comparison
- Token usage by provider
- Cost per provider (hourly)
- Model error rates
- Fallback triggers
- Average tokens per request
- Cost efficiency (per 1K tokens)
- Streaming vs non-streaming
- Top models by usage

**Use Case**: Optimize costs and model selection

## Metrics Reference

### Conversation Metrics

```promql
# Active conversations
zakera_conversations_active_total

# Conversation creation rate
rate(zakera_conversations_created_total[5m])

# Success rate
rate(zakera_conversations_completed_total[5m]) / 
rate(zakera_conversations_started_total[5m])

# Duration (p95)
histogram_quantile(0.95, rate(zakera_conversation_duration_seconds_bucket[5m]))

# Messages per conversation (p95)
histogram_quantile(0.95, rate(zakera_conversation_messages_count_bucket[5m]))
```

### Database Metrics

```promql
# Query latency (p95)
histogram_quantile(0.95, rate(zakera_db_query_duration_seconds_bucket[5m]))

# Connection pool usage
zakera_db_connections_active / zakera_db_pool_size

# Transaction success rate
rate(zakera_db_transactions_committed_total[5m]) /
rate(zakera_db_transactions_total[5m])

# Database size
zakera_db_size_bytes

# Query rate by operation
rate(zakera_db_queries_total{operation="select"}[5m])
```

### Model Metrics

```promql
# Cost per hour
rate(zakera_model_cost_total[1h])

# Token usage
rate(zakera_model_tokens_total[5m])

# Error rate
rate(zakera_model_errors_total[5m]) /
rate(zakera_model_requests_total[5m])

# Response time (p95)
histogram_quantile(0.95, rate(zakera_model_response_duration_seconds_bucket[5m]))
```

### Search Metrics

```promql
# Search performance (p95)
histogram_quantile(0.95, rate(zakera_search_duration_seconds_bucket[5m]))

# Search rate
rate(zakera_search_queries_total[5m])

# No results rate
rate(zakera_search_no_results_total[5m]) /
rate(zakera_search_queries_total[5m])
```

## Alert Rules

### Critical Alerts

**High Conversation Failure Rate**
- Trigger: >10% failures over 5 minutes
- Severity: Critical
- Action: Check error logs, verify model providers

**Database Connection Pool Exhausted**
- Trigger: All connections in use
- Severity: Critical
- Action: Increase pool size or investigate slow queries

**Message Persistence Failures**
- Trigger: Any failures over 3 minutes
- Severity: Critical
- Action: Check database connectivity and disk space

**Model Provider Down**
- Trigger: Provider unavailable for 2 minutes
- Severity: Critical
- Action: Verify API keys, check provider status

### Warning Alerts

**High Database Query Latency**
- Trigger: p95 > 1 second
- Severity: Warning
- Action: Optimize queries, add indexes

**High Model Error Rate**
- Trigger: >5% errors
- Severity: Warning
- Action: Check API limits, verify configurations

**Slow Conversation Search**
- Trigger: p95 > 3 seconds
- Severity: Warning
- Action: Optimize search queries, rebuild indexes

**High Hourly Cost**
- Trigger: >$10/hour
- Severity: Warning
- Action: Review model selection, implement rate limiting

### Info Alerts

**Frequent Token Limit Exceeded**
- Trigger: >0.1/second
- Severity: Info
- Action: Consider increasing max_tokens

**High Cache Miss Rate**
- Trigger: >30% misses
- Severity: Info
- Action: Adjust cache configuration

## Setting Up Alerts

### Email Notifications

Edit `monitoring/alertmanager.yml`:

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alertmanager@example.com'
        auth_password: 'your-app-password'
        headers:
          Subject: '[Zakera] {{ .GroupLabels.severity | toUpper }}: {{ .GroupLabels.alertname }}'
```

### Slack Notifications

```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#zakera-alerts'
        title: '{{ .GroupLabels.severity | toUpper }}: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Discord Notifications

```yaml
receivers:
  - name: 'discord'
    webhook_configs:
      - url: 'https://discord.com/api/webhooks/YOUR/WEBHOOK'
        send_resolved: true
```

## Monitoring Best Practices

### 1. Review Dashboards Daily

- Check overview dashboard for anomalies
- Review cost trends
- Monitor error rates
- Check database performance

### 2. Set Appropriate Alert Thresholds

Start conservative and adjust based on your traffic:

```yaml
# Low traffic: more sensitive
- expr: error_rate > 0.01  # 1%

# High traffic: less sensitive
- expr: error_rate > 0.05  # 5%
```

### 3. Use Recording Rules

Pre-calculate common queries for dashboard performance:

```yaml
- record: zakera:conversation_success_rate
  expr: |
    rate(zakera_conversations_completed_total[5m]) /
    rate(zakera_conversations_started_total[5m])
```

### 4. Organize Alerts by Severity

- **Critical**: Immediate action required
- **Warning**: Action needed soon
- **Info**: Awareness only

### 5. Set Up Alert Routing

Route different severities to different channels:

```yaml
routes:
  - match:
      severity: critical
    receiver: pagerduty
  - match:
      severity: warning
    receiver: slack
  - match:
      severity: info
    receiver: email
```

## Custom Queries

### Conversation Analytics

```promql
# Average conversation length (messages)
avg(zakera_conversation_message_count)

# Conversations by hour of day
sum by (hour) (
  hour(timestamp(zakera_conversations_created_total))
)

# Most active users
topk(10, sum by (user_id) (zakera_conversations_created_total))

# Tag popularity
topk(10, zakera_conversations_by_tag)
```

### Cost Analysis

```promql
# Daily cost estimate
sum(rate(zakera_model_cost_total[24h])) * 24

# Cost by model
sum by (model) (zakera_model_cost_total)

# Most expensive conversations
topk(10, zakera_conversation_cost)

# Cost efficiency by provider
(zakera_model_cost_total / zakera_model_tokens_total) * 1000
```

### Performance Analysis

```promql
# Slowest endpoints (p95)
topk(10, histogram_quantile(0.95, 
  rate(zakera_http_request_duration_seconds_bucket[5m])
))

# Database bottlenecks
topk(5, histogram_quantile(0.95,
  rate(zakera_db_query_duration_seconds_bucket[5m])
))

# Model performance comparison
avg by (provider) (
  rate(zakera_model_response_duration_seconds_sum[5m]) /
  rate(zakera_model_response_duration_seconds_count[5m])
)
```

## Troubleshooting

### Metrics Not Appearing

1. **Check Prometheus targets**:
   - Go to http://localhost:9090/targets
   - Ensure Zakera API target is UP
   - Check scrape errors

2. **Verify metrics endpoint**:
   ```bash
   curl http://localhost:8000/api/v1/monitoring/metrics
   ```

3. **Check Prometheus logs**:
   ```bash
   docker-compose logs prometheus
   ```

### Dashboards Not Loading

1. **Check Grafana datasource**:
   - Configuration → Data Sources
   - Test Prometheus connection

2. **Verify dashboard files**:
   ```bash
   ls -la monitoring/grafana/dashboards/
   ```

3. **Check Grafana logs**:
   ```bash
   docker-compose logs grafana
   ```

### Alerts Not Firing

1. **Check AlertManager**:
   - Go to http://localhost:9093
   - Verify alert rules loaded

2. **Test alert expression**:
   - Go to Prometheus
   - Run alert query in PromQL
   - Check if condition is met

3. **Verify notification config**:
   - Check `alertmanager.yml`
   - Test receiver configuration

## Advanced Configuration

### High-Availability Setup

For production, run multiple instances:

```yaml
# docker-compose.yml
prometheus-1:
  image: prom/prometheus
  # ... configuration

prometheus-2:
  image: prom/prometheus
  # ... configuration

# Use Thanos for long-term storage
thanos:
  image: thanosio/thanos
  # ... configuration
```

### Custom Metrics

Add your own metrics in application code:

```python
from src.monitoring.conversation_metrics import (
    conversations_created,
    track_message_save
)

# Increment counter
conversations_created.labels(
    model="gpt-4",
    has_system_prompt="true"
).inc()

# Use context manager
with track_message_save(role="user", model="gpt-4"):
    save_message_to_database()
```

### Dashboard Customization

1. **Clone existing dashboard** in Grafana
2. **Modify panels** as needed
3. **Export JSON**:
   - Settings → JSON Model
   - Copy to `monitoring/grafana/dashboards/`
4. **Restart Grafana** to load new dashboard

## Maintenance

### Regular Tasks

**Daily**:
- Review overview dashboard
- Check for active alerts
- Monitor cost trends

**Weekly**:
- Review alert effectiveness
- Check dashboard accuracy
- Clean up old data

**Monthly**:
- Optimize slow queries
- Review retention policies
- Update alert thresholds
- Archive old dashboards

### Data Retention

**Prometheus**:
- Default: 30 days
- Configured in `prometheus.yml`
- Increase: `--storage.tsdb.retention.time=90d`

**Grafana**:
- Dashboards: Persistent
- Annotations: 90 days default

**Loki**:
- Default: 30 days
- Configured in `loki-config.yml`

### Backup

```bash
# Backup Prometheus data
docker run -v prometheus-data:/prometheus \
  -v $(pwd)/backup:/backup \
  busybox tar -czf /backup/prometheus.tar.gz /prometheus

# Backup Grafana data
docker run -v grafana-data:/grafana \
  -v $(pwd)/backup:/backup \
  busybox tar -czf /backup/grafana.tar.gz /grafana
```

## Production Deployment

### Scaling Prometheus

For high-traffic deployments:

```yaml
# prometheus.yml
global:
  scrape_interval: 30s  # Increase for less load
  evaluation_interval: 30s

# Use remote storage
remote_write:
  - url: "http://your-remote-storage/api/v1/write"
```

### Securing Grafana

```yaml
# docker-compose.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
  - GF_AUTH_DISABLE_LOGIN_FORM=false
  - GF_AUTH_ANONYMOUS_ENABLED=false
```

### SSL/TLS

Add reverse proxy (nginx/traefik) for SSL:

```yaml
# docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./certs:/etc/nginx/certs
```

## Monitoring Checklist

Before going to production:

- [ ] All dashboards loading correctly
- [ ] Metrics being collected (check Prometheus targets)
- [ ] Alerts configured and tested
- [ ] Notification channels configured
- [ ] Alert thresholds appropriate for your load
- [ ] Data retention configured
- [ ] Backup strategy in place
- [ ] SSL/TLS configured
- [ ] Default passwords changed
- [ ] Access controls configured
- [ ] Documentation updated
- [ ] Team trained on dashboards

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Guide](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## Support

For issues with monitoring:

1. Check logs: `docker-compose logs [service]`
2. Verify configuration files
3. Test metrics endpoint: `/api/v1/monitoring/metrics`
4. Review Prometheus targets: http://localhost:9090/targets
5. Check AlertManager status: http://localhost:9093
