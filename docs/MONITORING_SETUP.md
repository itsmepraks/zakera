# Monitoring and Observability Setup Guide

Complete guide to setting up and using the comprehensive monitoring system for Zakera AI Chat Agent.

## Overview

The monitoring stack provides complete visibility into:
- **Conversation Performance** - Success rates, duration, cost tracking
- **API Performance** - Request rates, latency, error rates
- **Database Health** - Query performance, connection pools, errors
- **Model Performance** - Provider usage, latency, token consumption
- **System Resources** - CPU, memory, disk usage
- **User Activity** - Registrations, logins, active users
- **Search Performance** - Query times, result counts
- **Logs** - Structured logging with correlation IDs

## Quick Start

### Start the Monitoring Stack

```bash
# From project root
cd monitoring

# Start all monitoring services
docker-compose up -d

# Verify all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### Access Dashboards

- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093
- **Node Exporter**: http://localhost:9100/metrics
- **cAdvisor**: http://localhost:8080
- **Loki**: http://localhost:3100

### Start the Application

```bash
# In a new terminal, start the API
cd ..
make dev

# Or with Docker
docker run -p 8000:8000 zakera:latest
```

The application will automatically start sending metrics to Prometheus.

## Components

### 1. Prometheus

**Purpose**: Metrics collection and storage

**Configuration**: `monitoring/prometheus.yml`

**Key Features**:
- Scrapes metrics every 15s
- 30-day retention
- 50GB storage limit
- Alert rule evaluation
- Automatic target discovery

**Metrics Endpoint**: http://localhost:9090

**Query Examples**:
```promql
# Request rate
rate(http_requests_total[5m])

# Success rate
sum(conversation_successful_total) / sum(conversation_started_total)

# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Active conversations
conversations_active_total
```

### 2. Grafana

**Purpose**: Visualization and dashboards

**Configuration**: `monitoring/grafana/`

**Dashboards**:
1. **AI Chat Agent - Overview** 
   - High-level system metrics
   - Request rates and latency
   - Success rates
   - Resource usage

2. **Conversation Performance & Analytics**
   - Conversation lifecycle
   - Message rates by role
   - Cost and token tracking
   - Tag usage analytics
   - Sharing activity

3. **Database Performance & Health**
   - Query performance
   - Connection pool status
   - Slow query detection
   - Error rates

**Default Credentials**:
- Username: `admin`
- Password: `admin`
- **⚠️ Change on first login!**

### 3. AlertManager

**Purpose**: Alert routing and notifications

**Configuration**: `monitoring/alertmanager.yml`

**Notification Channels**:
- Email
- Slack
- Discord
- PagerDuty
- Webhook

**Alert Groups**:
- Critical (immediate notification)
- Warning (5-minute delay)
- Info (15-minute delay)

### 4. Node Exporter

**Purpose**: System-level metrics

**Metrics Collected**:
- CPU usage and load
- Memory usage
- Disk I/O
- Network traffic
- Filesystem usage

### 5. cAdvisor

**Purpose**: Container metrics

**Metrics Collected**:
- Container CPU usage
- Container memory usage
- Container network I/O
- Container filesystem usage

### 6. Loki

**Purpose**: Log aggregation and querying

**Configuration**: `monitoring/loki-config.yml`

**Features**:
- JSON log parsing
- Label extraction
- 30-day retention
- Full-text search
- Integration with Grafana

### 7. Promtail

**Purpose**: Log shipping to Loki

**Configuration**: `monitoring/promtail-config.yml`

**Log Sources**:
- Application logs
- Conversation logs
- Error logs
- Access logs

## Metrics Reference

### Conversation Metrics

```promql
# Conversations created
conversation_created_total

# Active conversations
conversations_active_total

# Success rate
sum(conversation_successful_total) / sum(conversation_started_total)

# Average messages per conversation
avg(conversation_message_count)

# Cost tracking
rate(conversation_cost_total[1h])

# Token usage
rate(conversation_tokens_total[5m])
```

### API Metrics

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status_code=~"5.."}[5m])

# Latency (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Requests by endpoint
sum(rate(http_requests_total[5m])) by (endpoint)
```

### Database Metrics

```promql
# Query rate
rate(db_queries_total[5m])

# Slow queries
rate(db_queries_slow_total[5m])

# Connection pool
db_connection_pool_available

# Query latency
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))
```

### Model Metrics

```promql
# Requests by provider
sum(rate(model_requests_total[5m])) by (provider)

# Token usage
rate(model_tokens_total[5m])

# Cost per hour
rate(model_cost_total[1h])

# Fallback rate
rate(model_fallback_total[5m])
```

### Search Metrics

```promql
# Search requests
rate(search_requests_total[5m])

# Search latency
histogram_quantile(0.95, rate(search_duration_seconds_bucket[5m]))

# No results rate
rate(search_no_results_total[5m]) / rate(search_requests_total[5m])
```

## Alert Rules

### Critical Alerts

**Database Connection Pool Exhausted**
- Trigger: No available connections
- Duration: 1 minute
- Action: Scale up pool or investigate leaks

**API Down**
- Trigger: Service not responding
- Duration: 1 minute
- Action: Restart service, check logs

**High Error Rate**
- Trigger: > 5% error rate
- Duration: 3 minutes
- Action: Check logs, investigate errors

### Warning Alerts

**High Model Latency**
- Trigger: p95 > 10 seconds
- Duration: 5 minutes
- Action: Check provider status, consider fallback

**Slow Database Queries**
- Trigger: p95 > 1 second
- Duration: 5 minutes
- Action: Review query plans, add indexes

**High Conversation Cost**
- Trigger: > $10/hour
- Duration: 5 minutes
- Action: Review usage, check for abuse

### Info Alerts

**No User Activity**
- Trigger: No activity for 30 minutes
- Duration: 30 minutes
- Action: Verify system is operating normally

**Long Conversation Durations**
- Trigger: p95 > 1 hour
- Duration: 10 minutes
- Action: Monitor for user experience issues

## Setting Up Notifications

### Email Notifications

Edit `monitoring/alertmanager.yml`:

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'alerts@example.com'
        from: 'zakera@example.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'
```

### Slack Notifications

```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: 'Zakera Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
```

### Discord Notifications

```yaml
receivers:
  - name: 'discord'
    webhook_configs:
      - url: 'https://discord.com/api/webhooks/YOUR/WEBHOOK'
```

## Dashboard Guide

### AI Chat Agent - Overview

**Purpose**: High-level system health and performance

**Key Panels**:
- Active Conversations (stat)
- Total Messages 24h (stat)
- Success Rate 5m (gauge)
- Average Response Time (stat)
- Requests per Second (graph)
- Response Time Percentiles (graph)
- Model Requests by Provider (graph)
- Token Usage (graph)
- Database Query Performance (graph)
- Error Rate by Type (graph)
- System Resources (graph)

**Use Cases**:
- Quick health check
- Performance at a glance
- Identify issues quickly

### Conversation Performance & Analytics

**Purpose**: Deep dive into conversation metrics

**Key Panels**:
- Conversations Created 24h (stat)
- Average Messages per Conversation (stat)
- Conversation Success Rate (gauge)
- Total Cost 24h (stat with currency)
- Active Users (stat)
- Total Tokens (stat)
- Conversation Duration Distribution (heatmap)
- Message Rate by Role (graph)
- Conversation Lifecycle (graph)
- Top Tags (pie chart)
- Search Performance (graph)
- Sharing Activity (graph)

**Use Cases**:
- Analyze user behavior
- Track costs
- Identify popular features
- Monitor conversation quality

### Database Performance & Health

**Purpose**: Database optimization and troubleshooting

**Key Panels**:
- Query Rate by Operation (graph)
- Query Duration by Table p95 (graph)
- Connection Pool Status (graph)
- Database Errors (graph with alert)
- Conversation Table Queries (graph)
- Message Table Queries (graph)
- Operations Latency Heatmap (heatmap)
- Slow Queries Table (table)

**Use Cases**:
- Identify slow queries
- Monitor connection pool
- Track query patterns
- Optimize database performance

## Using the Monitoring System

### Daily Operations

**Morning Checkup**:
```bash
# 1. Open Overview Dashboard
open http://localhost:3001

# 2. Check for active alerts
open http://localhost:9093

# 3. Review error logs
# In Grafana: Explore > Loki > {level="ERROR"}
```

**Troubleshooting Workflow**:

1. **High Latency Detected**
   - Check Overview dashboard
   - Identify slow component (API, Model, Database)
   - Drill down to specific dashboard
   - Review metrics and logs
   - Apply fixes

2. **Error Rate Spike**
   - Check error rate graph
   - Click on spike to see time range
   - Query logs for that time range
   - Identify error patterns
   - Fix and deploy

3. **High Costs**
   - Check Conversation Performance dashboard
   - Review cost by model
   - Identify expensive conversations
   - Analyze usage patterns
   - Optimize model selection

### Custom Queries

**Find Expensive Conversations**:
```promql
topk(10, rate(conversation_cost_total[1h]))
```

**Identify Slow Endpoints**:
```promql
histogram_quantile(0.99, 
  sum(rate(http_request_duration_seconds_bucket[5m])) 
  by (le, endpoint)
) > 1
```

**Database Connection Pressure**:
```promql
(db_connection_pool_size - db_connection_pool_available) / db_connection_pool_size * 100
```

**Most Used Tags**:
```promql
topk(20, sum(conversation_tags_total) by (tag))
```

## Performance Optimization

### Dashboard Best Practices

1. **Use appropriate time ranges**
   - Real-time monitoring: Last 15 minutes
   - Debugging: Last hour
   - Analysis: Last 24 hours
   - Trends: Last 7 days

2. **Set auto-refresh wisely**
   - Critical dashboards: 30 seconds
   - Analysis dashboards: 1-5 minutes
   - Historical dashboards: Manual only

3. **Limit panel queries**
   - Use aggregation where possible
   - Avoid high-cardinality labels
   - Set query timeouts

### Query Optimization

**Good**:
```promql
rate(http_requests_total[5m])
```

**Better**:
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```

**Best**:
```promql
topk(10, sum(rate(http_requests_total[5m])) by (endpoint))
```

## Troubleshooting

### Metrics Not Appearing

```bash
# Check if Prometheus can reach API
curl http://localhost:9090/api/v1/targets

# Check if API is exposing metrics
curl http://localhost:8000/api/v1/monitoring/metrics

# Check Prometheus logs
docker-compose logs prometheus

# Check for scrape errors
# In Prometheus UI: Status > Targets
```

### Dashboards Not Loading

```bash
# Restart Grafana
docker-compose restart grafana

# Check Grafana logs
docker-compose logs grafana

# Verify datasource connection
# In Grafana: Configuration > Data Sources > Test
```

### Alerts Not Firing

```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules

# Check AlertManager status
curl http://localhost:9093/api/v1/status

# Verify AlertManager config
docker-compose exec alertmanager cat /etc/alertmanager/alertmanager.yml
```

### High Resource Usage

```bash
# Check Prometheus disk usage
docker-compose exec prometheus du -sh /prometheus

# Reduce retention if needed
# Edit prometheus.yml: storage.tsdb.retention.time

# Clean up old data
docker-compose restart prometheus
```

## Advanced Configuration

### Production Deployment

**Prometheus**:
```yaml
# Use persistent storage
volumes:
  - /data/prometheus:/prometheus

# Enable remote write for backup
remote_write:
  - url: 'https://remote-storage.example.com/write'
```

**Grafana**:
```yaml
# Use external database
environment:
  - GF_DATABASE_TYPE=postgres
  - GF_DATABASE_HOST=postgres:5432
  - GF_DATABASE_NAME=grafana
  - GF_DATABASE_USER=grafana
  - GF_DATABASE_PASSWORD=secure_password

# Enable HTTPS
  - GF_SERVER_PROTOCOL=https
  - GF_SERVER_CERT_FILE=/etc/grafana/cert.pem
  - GF_SERVER_CERT_KEY=/etc/grafana/cert.key
```

### High Availability

**Prometheus HA**:
```yaml
# Run multiple Prometheus instances
# Use Thanos for long-term storage and querying
```

**AlertManager HA**:
```yaml
# Configure multiple AlertManager instances
# Use gossip protocol for clustering
```

### Custom Dashboards

Create custom dashboards in Grafana:

1. Go to Create > Dashboard
2. Add Panel
3. Write PromQL query
4. Configure visualization
5. Save dashboard
6. Export JSON
7. Place in `monitoring/grafana/dashboards/`

## Metrics Collection in Code

### Recording Conversation Metrics

```python
from src.monitoring.metrics import (
    record_conversation_created,
    record_conversation_message,
    record_conversation_complete
)

# When conversation is created
record_conversation_created(model="gpt-4-turbo", user_type="regular")

# When message is sent
record_conversation_message(role="user", model="gpt-4-turbo", tokens=50)

# When conversation completes
record_conversation_complete(
    model="gpt-4-turbo",
    message_count=10,
    duration=300.5,  # seconds
    total_tokens=500,
    total_cost=0.015  # USD
)
```

### Recording Search Metrics

```python
from src.monitoring.metrics import record_search

start_time = time.time()
# Perform search
results = search_messages(query="test")
duration = time.time() - start_time

record_search(
    search_type="messages",
    duration=duration,
    results_count=len(results),
    status="success"
)
```

### Recording Database Metrics

```python
from src.monitoring.metrics import record_db_query

start_time = time.time()
# Execute query
result = db.query(Conversation).all()
duration = time.time() - start_time

record_db_query(
    operation="select",
    table="conversations",
    duration=duration,
    status="success"
)
```

## Alert Configuration

### Email Setup

1. Edit `monitoring/alertmanager.yml`
2. Configure SMTP settings
3. Add email addresses
4. Restart AlertManager

```bash
docker-compose restart alertmanager
```

### Slack Setup

1. Create Slack webhook
2. Edit `monitoring/alertmanager.yml`
3. Add webhook URL
4. Configure channel
5. Restart AlertManager

### Testing Alerts

```bash
# Trigger test alert
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "warning"},
    "annotations": {"summary": "Test alert"}
  }]'

# Check AlertManager UI
open http://localhost:9093
```

## Log Analysis

### Using Loki in Grafana

1. Go to Explore
2. Select Loki datasource
3. Write LogQL query:

```logql
# All error logs
{job="zakera"} |= "ERROR"

# Logs for specific conversation
{job="conversations"} | json | conversation_id="conv-123"

# Slow requests
{job="zakera"} | json | duration > 1000

# Authentication failures
{job="zakera"} | json | message =~ "login failed"
```

### Log Patterns

```logql
# Rate of errors
rate({level="ERROR"}[5m])

# Top error types
topk(10, sum by (error_type) (rate({job="errors"}[5m])))

# User activity timeline
{job="zakera"} | json | user_id != ""
```

## Maintenance

### Regular Tasks

**Daily**:
- Review active alerts
- Check dashboard anomalies
- Monitor resource usage

**Weekly**:
- Review alert noise
- Update dashboard panels
- Check disk usage

**Monthly**:
- Review retention policies
- Archive old dashboards
- Update alert thresholds
- Review metric cardinality

### Data Cleanup

```bash
# Clean up old Prometheus data
docker-compose exec prometheus promtool tsdb clean-tombstones /prometheus

# Clean up Loki data (older than 30 days done automatically)

# Clean up Grafana unused dashboards
# Via UI: Dashboards > Manage > Delete unused
```

## Security

### Securing Grafana

```yaml
# In docker-compose.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
  - GF_AUTH_ANONYMOUS_ENABLED=false
  - GF_AUTH_BASIC_ENABLED=true
  - GF_AUTH_DISABLE_LOGIN_FORM=false
  - GF_USERS_ALLOW_SIGN_UP=false
```

### Securing Prometheus

```yaml
# Add basic auth
# In prometheus.yml
basic_auth:
  username: admin
  password_file: /etc/prometheus/password
```

### Network Security

```yaml
# Expose only necessary ports
# Use reverse proxy (nginx/traefik)
# Enable TLS/SSL
# Restrict access with firewall rules
```

## Backup and Recovery

### Backup Metrics

```bash
# Backup Prometheus data
docker-compose exec prometheus tar -czf /backup/prometheus.tar.gz /prometheus

# Backup Grafana dashboards
curl -u admin:admin http://localhost:3001/api/search | \
  jq -r '.[] | .uri' | \
  xargs -I {} curl -u admin:admin http://localhost:3001/api/dashboards/{} > dashboards_backup.json
```

### Restore

```bash
# Restore Prometheus data
docker-compose down
tar -xzf prometheus.tar.gz -C /data/
docker-compose up -d

# Import Grafana dashboards
# Via UI: Create > Import > Upload JSON
```

## Performance Tuning

### Prometheus

```yaml
# Adjust scrape interval
scrape_interval: 30s  # Reduce load

# Adjust retention
retention.time: 15d  # Save disk space

# Adjust query timeout
query.timeout: 2m
```

### Grafana

```yaml
# Enable caching
GF_RENDERING_SERVER_URL: http://renderer:8081/render
GF_RENDERING_CALLBACK_URL: http://grafana:3000/

# Optimize queries
GF_DATABASE_CACHE_MODE: shared
```

## Makefile Commands

```bash
# Start monitoring
make monitoring-start

# Stop monitoring
make monitoring-stop

# Restart monitoring
make monitoring-restart

# View logs
make monitoring-logs

# Check health
make monitoring-health

# Access Grafana
make monitoring-dashboard
```

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Guide](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## Support

For issues or questions:
1. Check this documentation
2. Review dashboard annotations
3. Check service logs
4. Consult Prometheus/Grafana docs
5. Open GitHub issue

---

**Your monitoring system is production-ready and provides complete visibility into your AI chat agent!** 📊🚀
