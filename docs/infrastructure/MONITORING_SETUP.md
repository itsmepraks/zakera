# Monitoring Stack Setup Guide

Comprehensive guide for setting up and using Zakera's observability infrastructure.

## Overview

Zakera includes a complete observability stack:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing
- **Loki**: Log aggregation
- **Promtail**: Log shipping
- **AlertManager**: Alert routing and management

## Quick Start

### One-Command Setup

```bash
# Initialize and start monitoring stack
./scripts/init-monitoring.sh

# Or use Make
make quick-start
```

Access URLs:
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **AlertManager**: http://localhost:9093

### Manual Setup

```bash
# 1. Create directories
mkdir -p data/{prometheus,grafana,loki,jaeger}

# 2. Set permissions
chmod -R 755 monitoring/
sudo chown -R 472:472 data/grafana  # Grafana user

# 3. Start services
docker-compose -f docker-compose.dev.yml up -d prometheus grafana jaeger

# 4. Verify
curl http://localhost:9090/-/healthy
curl http://localhost:3001/api/health
curl http://localhost:16686/
```

## Grafana Dashboards

### Pre-configured Dashboards

#### 1. Performance Testing Dashboard
**Location**: `monitoring/grafana/dashboards/performance-testing.json`

**Panels**:
- 📈 Request rate over time
- 🕒 Response time percentiles (P50, P95, P99)
- 🚨 Failure rate by endpoint
- 👥 Active users by scenario
- 📊 Model provider performance comparison
- 📝 Test scenario status table
- 🎯 Top slowest endpoints

**Use Cases**:
- Monitor ongoing performance tests
- Analyze test results in real-time
- Compare different test scenarios
- Identify performance bottlenecks
- Track improvements over time

**Access**: Grafana → Performance folder → Performance Testing

#### 2. Redis Cache Dashboard
**Location**: `monitoring/grafana/dashboards/redis-cache.json`

**Panels**:
- ✅ Cache hit rate gauge (target: 80%+)
- 🔄 Cache operations rate (hits/misses/sets/deletes)
- 💾 Memory usage tracking
- 🧩 Cache distribution by type (pie chart)
- ⏱️ Cache response time percentiles
- 🗑️ Eviction rate monitoring
- 🔝 Top cached keys analysis
- 🔌 Connection pool metrics

**Use Cases**:
- Monitor cache effectiveness
- Detect memory issues
- Optimize cache configuration
- Identify hot keys
- Track cache performance

**Access**: Grafana → Infrastructure folder → Redis Cache

#### 3. API Performance Dashboard
**Location**: `monitoring/grafana/dashboards/api-performance.json`

**Panels**:
- 💚 Overall API health metrics
- 📉 Request rate by endpoint
- 🌡️ Response time heatmap
- 🚨 Error rate by status code
- 🤖 Model provider usage distribution
- 📊 Database query performance
- 🔌 WebSocket connection metrics
- 💵 AI model cost tracking
- 🐢 Slowest endpoints table

**Use Cases**:
- Monitor API health in real-time
- Identify slow endpoints
- Track error rates
- Analyze usage patterns
- Monitor costs

**Access**: Grafana → Application folder → API Performance

### Creating Custom Dashboards

#### From Grafana UI

1. Login to Grafana (http://localhost:3001)
2. Click **+** → **Dashboard**
3. Click **Add visualization**
4. Select **Prometheus** data source
5. Enter PromQL query
6. Customize visualization
7. Save dashboard

#### From JSON

1. Create JSON file in `monitoring/grafana/dashboards/`
2. Use existing dashboards as templates
3. Restart Grafana or wait 30s for auto-reload
4. Dashboard appears in Grafana UI

#### Dashboard JSON Structure

```json
{
  "dashboard": {
    "id": null,
    "uid": "unique-dashboard-id",
    "title": "My Custom Dashboard",
    "tags": ["custom"],
    "panels": [
      {
        "id": 1,
        "title": "Panel Title",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "your_promql_query",
            "legendFormat": "{{label}}"
          }
        ]
      }
    ]
  }
}
```

## Prometheus Configuration

### Scrape Configurations

**Location**: `monitoring/prometheus.yml`

Targets:
- Zakera API (port 8001)
- Redis Exporter
- PostgreSQL Exporter
- Node Exporter (system metrics)
- Locust (performance tests)

### Adding New Metrics

1. **Expose metrics in Python**:
   ```python
   from prometheus_client import Counter, Histogram
   
   REQUEST_COUNT = Counter(
       'http_requests_total',
       'Total HTTP requests',
       ['method', 'endpoint', 'status']
   )
   
   REQUEST_LATENCY = Histogram(
       'http_request_duration_seconds',
       'HTTP request latency',
       ['method', 'endpoint']
   )
   
   # Use in code
   REQUEST_COUNT.labels(method='POST', endpoint='/chat', status='200').inc()
   REQUEST_LATENCY.labels(method='POST', endpoint='/chat').observe(0.234)
   ```

2. **Query in Prometheus**:
   ```promql
   # Total requests
   sum(rate(http_requests_total[5m]))
   
   # Error rate
   sum(rate(http_requests_total{status=~"5.."}[5m])) 
     / sum(rate(http_requests_total[5m]))
   
   # P95 latency
   histogram_quantile(0.95, 
     rate(http_request_duration_seconds_bucket[5m])
   )
   ```

3. **Visualize in Grafana**:
   - Create new panel
   - Enter PromQL query
   - Choose visualization type
   - Configure thresholds
   - Save

### Recording Rules

**Location**: `monitoring/prometheus-rules/*.yml`

Pre-calculate expensive queries:

```yaml
groups:
  - name: my_rules
    interval: 30s
    rules:
      - record: job:request_rate:5m
        expr: sum by (job) (rate(http_requests_total[5m]))
```

Use in queries: `job:request_rate:5m` instead of full expression.

### Alerting Rules

**Existing Rules**:
- `performance-testing.yml`: Performance test alerts
- `redis-cache.yml`: Cache performance alerts
- `alerts.yml`: General system alerts
- `alerts-conversations.yml`: Conversation-specific alerts

**Creating New Alerts**:

```yaml
groups:
  - name: my_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
          component: api
        annotations:
          summary: "High API error rate"
          description: "Error rate is {{ $value | humanizePercentage }}"
```

## Jaeger Tracing

### Viewing Traces

1. Open Jaeger UI: http://localhost:16686
2. Select service: **zakera-api-dev**
3. Set time range
4. Click **Find Traces**
5. Click trace to view details

### Trace Details

Each trace shows:
- Request flow through services
- Database queries
- Model API calls
- Cache operations
- Error details
- Performance bottlenecks

### Linking Logs to Traces

Grafana automatically links:
- Logs in Loki with trace IDs
- Click trace ID in logs → opens in Jaeger
- Click "Logs" in trace → shows related logs

## Alerting

### Alert Manager

**Configuration**: `monitoring/alertmanager.yml`

**Channels**:
- Email
- Slack
- Discord
- PagerDuty
- Webhook

### Configuring Email Alerts

```yaml
route:
  receiver: 'email-team'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'email-team'
    email_configs:
      - to: 'team@zakera.ai'
        from: 'alerts@zakera.ai'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@zakera.ai'
        auth_password: 'password'
```

### Configuring Slack Alerts

```yaml
receivers:
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#zakera-alerts'
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
```

## Performance Monitoring

### Performance Test Metrics

Automatically collected during tests:

- `locust_requests_total`: Total requests
- `locust_failures_total`: Failed requests
- `locust_users`: Active simulated users
- `locust_response_time_*`: Response time percentiles
- `locust_model_response_time`: Per-model latency

### Viewing Test Results

**During Test**:
1. Start test: `make perf-test-normal`
2. Open Grafana: http://localhost:3001
3. Go to: Performance → Performance Testing
4. Watch real-time metrics

**After Test**:
1. View in Grafana (7-day retention)
2. Export dashboard as PDF/PNG
3. Download CSV data
4. Analyze trends

## Redis Cache Monitoring

### Key Metrics

**Hit Rate**:
- Target: >80%
- Warning: <60%
- Critical: <40%

**Memory**:
- Limit: 512 MB (dev)
- Warning: >80% usage
- Critical: >95% usage

**Latency**:
- Target: P95 <10ms
- Warning: P95 >50ms
- Critical: P99 >100ms

### Optimizing Cache Performance

**Low Hit Rate**:
1. Check Grafana → Redis Cache → Top Cached Keys
2. Identify frequently missed keys
3. Adjust TTL settings
4. Implement cache warming

**High Memory**:
1. Check cache distribution pie chart
2. Identify large cache types
3. Reduce TTL for less important data
4. Increase maxmemory if needed
5. Review eviction policy

**Slow Operations**:
1. Check operation latency panel
2. Identify slow operations
3. Review network latency
4. Check Redis slow log
5. Optimize queries

### RedisInsight

**Access**: http://localhost:8001

**Features**:
- Browse keys
- View memory usage
- Monitor commands
- Analyze slow queries
- CLI access
- Profiler

## Distributed Tracing

### Understanding Traces

**Trace**: End-to-end request flow
**Span**: Individual operation within trace
**Tags**: Metadata (endpoint, model, user_id)
**Logs**: Events within span

### Trace Example

```
HTTP Request /api/v1/chat (450ms total)
  ├─ Validate request (5ms)
  ├─ Check cache (10ms)
  │  └─ Redis GET (8ms)
  ├─ Load conversation (50ms)
  │  └─ PostgreSQL query (45ms)
  ├─ Call AI model (350ms)
  │  ├─ Prepare prompt (10ms)
  │  ├─ OpenAI API call (330ms)
  │  └─ Parse response (10ms)
  ├─ Save to database (20ms)
  └─ Update cache (15ms)
```

### Finding Performance Issues

1. Open Jaeger: http://localhost:16686
2. Filter by slow traces: Min Duration >1s
3. Sort by duration (longest first)
4. Click trace to analyze
5. Identify bottleneck spans
6. Optimize identified operations

## Log Aggregation (Loki)

### Viewing Logs

**In Grafana**:
1. Explore → Select Loki
2. Query: `{job="zakera-api"} |= "error"`
3. View log stream
4. Click trace ID to jump to Jaeger

**Log Queries**:

```logql
# All API logs
{job="zakera-api"}

# Errors only
{job="zakera-api"} |= "ERROR"

# Specific endpoint
{job="zakera-api"} | json | endpoint="/api/v1/chat"

# With trace ID
{job="zakera-api"} | json | trace_id="abc123"

# Rate of errors
sum(rate({job="zakera-api"} |= "ERROR" [5m]))
```

### Structured Logging

Ensure logs are JSON formatted:

```python
import structlog

logger = structlog.get_logger()
logger.info(
    "chat_request_processed",
    conversation_id=conv_id,
    model=model,
    tokens=tokens,
    latency_ms=latency,
    trace_id=trace_id,
)
```

## Alerting

### Alert Lifecycle

```
Prometheus
  ↓ Evaluates rules every 15-30s
Alert Fires
  ↓ Sends to AlertManager
AlertManager
  ↓ Groups and routes
Notification
  ↓ Slack/Email/PagerDuty
Team Responds
```

### Alert Severity Levels

**Info**: FYI, no action needed
**Warning**: Investigate soon (within 24h)
**Critical**: Investigate immediately (<1h)
**Emergency**: Page on-call engineer

### Silencing Alerts

**Temporary**:
1. Open AlertManager: http://localhost:9093
2. Click alert
3. Click **Silence**
4. Set duration
5. Add comment

**Permanent**:
1. Update alerting rules
2. Adjust thresholds
3. Remove rule if not needed

## Integration with CI/CD

### Performance Test Integration

GitHub Actions automatically:
1. Runs Locust tests
2. Exposes metrics to Prometheus
3. Grafana dashboards update
4. Alerts fire if thresholds exceeded
5. Results in PR comments

See: `.github/workflows/performance-enhanced.yml`

### Monitoring in CI/CD

```yaml
- name: Check Prometheus Targets
  run: |
    curl -s http://localhost:9090/api/v1/targets | \
      jq '.data.activeTargets[] | select(.health != "up")'

- name: Validate Dashboards
  run: |
    for dashboard in monitoring/grafana/dashboards/*.json; do
      cat $dashboard | jq . > /dev/null || exit 1
    done
```

## Backup and Restore

### Backup Grafana

```bash
# Backup dashboards
mkdir -p backups/grafana
docker cp zakera-grafana-dev:/var/lib/grafana backups/grafana/$(date +%Y%m%d)

# Or use API
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:3001/api/search?query=& > backups/dashboards.json
```

### Restore Grafana

```bash
# Restore from backup
docker cp backups/grafana/20260228 zakera-grafana-dev:/var/lib/grafana
docker-compose -f docker-compose.dev.yml restart grafana
```

### Backup Prometheus Data

```bash
# Snapshot
curl -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Backup data directory
tar -czf backups/prometheus-$(date +%Y%m%d).tar.gz data/prometheus/
```

## Performance Tuning

### Prometheus

**Retention**:
```yaml
command:
  - '--storage.tsdb.retention.time=15d'  # Keep 15 days
  - '--storage.tsdb.retention.size=50GB'  # Or 50GB max
```

**Scrape Interval**:
```yaml
global:
  scrape_interval: 15s     # Balance between granularity and load
  evaluation_interval: 15s
```

### Grafana

**Query Optimization**:
- Use recording rules for complex queries
- Set appropriate time ranges
- Limit data points with `$__interval`
- Use table panels for large datasets

**Resource Limits**:
```yaml
grafana:
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '1.0'
```

### Jaeger

**Sampling**:
```python
# Development: 100% sampling
TRACE_SAMPLING_RATE = 1.0

# Production: 10% sampling
TRACE_SAMPLING_RATE = 0.1
```

**Storage**:
```yaml
jaeger:
  environment:
    SPAN_STORAGE_TYPE: elasticsearch  # For production
```

## Troubleshooting

### Prometheus Not Scraping

**Check targets**:
1. Open http://localhost:9090/targets
2. Look for DOWN targets
3. Check error message

**Common issues**:
- Service not exposing metrics
- Wrong port in config
- Network connectivity
- Authentication required

**Solution**:
```bash
# Test metrics endpoint
curl http://localhost:8001/metrics

# Check Prometheus logs
docker logs zakera-prometheus-dev
```

### Grafana Dashboard Not Loading

**Symptoms**: Dashboard blank or shows "No data"

**Solutions**:
1. Check data source connection (Grafana → Connections)
2. Verify Prometheus has data: `curl http://localhost:9090/api/v1/query?query=up`
3. Check dashboard queries in panel editor
4. Verify time range
5. Check Grafana logs: `docker logs zakera-grafana-dev`

### Alerts Not Firing

**Check**:
1. Prometheus → Alerts page
2. Verify rule is loaded
3. Check evaluation interval
4. Test expression in Prometheus
5. Check AlertManager config

### High Resource Usage

**Prometheus**:
- Reduce retention time
- Decrease scrape frequency
- Use recording rules
- Archive old data

**Grafana**:
- Limit dashboard auto-refresh
- Reduce query frequency
- Use shorter time ranges
- Optimize panel queries

## Production Considerations

### Scaling

**Prometheus**:
- Use remote storage (Thanos, Cortex)
- Federation for multiple instances
- Horizontal scaling with sharding

**Grafana**:
- External database (PostgreSQL/MySQL)
- Load balancer for multiple instances
- Shared storage for dashboards

**Jaeger**:
- Elasticsearch/Cassandra backend
- Kafka for buffering
- Sampling strategy

### Security

**Grafana**:
- Change default password
- Enable HTTPS
- Configure LDAP/OAuth
- Set up RBAC

**Prometheus**:
- Enable authentication
- Use TLS for scraping
- Restrict access with firewall

**Jaeger**:
- Enable authentication
- Use TLS
- Restrict UI access

### High Availability

**Prometheus**:
```yaml
prometheus-1:
  # Primary instance
prometheus-2:
  # Secondary instance (same config)
```

**Grafana**:
```yaml
grafana:
  replicas: 2
  environment:
    GF_DATABASE_TYPE: postgres
    GF_DATABASE_HOST: postgres:5432
```

## Best Practices

### 1. Dashboard Design
- Group related metrics
- Use clear titles and descriptions
- Set appropriate time ranges
- Add threshold markers
- Use color coding wisely
- Include links to runbooks

### 2. Alert Configuration
- Alert on symptoms, not causes
- Set appropriate thresholds
- Include runbook links
- Test alerts regularly
- Review and tune alerts

### 3. Metrics Naming
- Follow Prometheus naming conventions
- Use consistent labels
- Document custom metrics
- Avoid high cardinality

### 4. Tracing
- Sample appropriately (1-10% in prod)
- Tag spans with useful metadata
- Keep trace data 7-30 days
- Use for debugging, not monitoring

## Resources

### Documentation
- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [Jaeger Docs](https://www.jaegertracing.io/docs/)
- [Loki Docs](https://grafana.com/docs/loki/)

### Zakera Monitoring
- Setup Script: `scripts/init-monitoring.sh`
- Makefile Commands: `make help`
- Dashboard JSONs: `monitoring/grafana/dashboards/`
- Alert Rules: `monitoring/prometheus-rules/`

---

**Last Updated**: February 2026  
**Stack Version**: Prometheus 2.48, Grafana 10.2, Jaeger 1.52  
**Status**: Production Ready
