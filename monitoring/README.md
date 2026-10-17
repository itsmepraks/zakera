# Zakera Monitoring Stack

> [!WARNING]
> **Legacy and unverified.** This stack is not part of the Zakera vNext core project and must not be presented as a supported production capability.

Production-ready monitoring and observability for the Zakera AI Chat Agent.

## Quick Start

```bash
# Start monitoring stack
docker-compose up -d

# Check status
docker-compose ps

# Access Grafana
open http://localhost:3001
# Login: admin/admin
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| **Grafana** | 3001 | Dashboard visualization |
| **Prometheus** | 9090 | Metrics collection & storage |
| **AlertManager** | 9093 | Alert routing & notification |
| **Loki** | 3100 | Log aggregation |
| **Node Exporter** | 9100 | System metrics |
| **cAdvisor** | 8080 | Container metrics |

## Dashboards

### 🎯 AI Chat Agent Overview
**Path**: `grafana/dashboards/ai-chat-agent-overview.json`

**Metrics**:
- System health status
- Active conversations & message rate
- API request & error rates
- Model usage distribution
- Token consumption
- Database performance
- Hourly costs
- Success rates

**When to Use**: Daily health checks, incident response

### 💬 Conversation Performance
**Path**: `grafana/dashboards/conversation-performance.json`

**Metrics**:
- Creation & throughput rates
- Duration distributions
- Messages per conversation
- Archive/delete patterns
- Success rates
- User activity
- Tag distribution

**When to Use**: Optimizing conversation handling, capacity planning

### 🗄️ Database Performance
**Path**: `grafana/dashboards/database-performance.json`

**Metrics**:
- Query performance (all operations)
- Connection pool status
- Transaction rates
- Slow query detection
- Database growth
- Cache performance
- Persistence latency

**When to Use**: Database optimization, troubleshooting slowness

### 🤖 Model Performance & Cost
**Path**: `grafana/dashboards/model-performance.json`

**Metrics**:
- Model usage & distribution
- Response times by provider
- Token usage patterns
- Cost tracking & trends
- Error rates
- Fallback triggers
- Cost efficiency analysis

**When to Use**: Cost optimization, model selection

## Alert Rules

### Configuration Files

- `alerts.yml` - General system alerts
- `alerts-conversations.yml` - Conversation-specific alerts

### Alert Severity Levels

**🔴 Critical** (immediate action):
- High conversation failure rate (>10%)
- Database connection pool exhausted
- Message persistence failures
- Model provider down

**🟡 Warning** (action needed soon):
- High database query latency (>1s)
- High model error rate (>5%)
- Slow search performance (>3s)
- High hourly cost (>$10)

**🔵 Info** (awareness):
- Frequent token limits exceeded
- High cache miss rate (>30%)
- Expensive model overuse (>50%)

## Metrics Collected

### Conversation Metrics (15+)
```
zakera_conversations_created_total
zakera_conversations_active_total
zakera_conversation_duration_seconds
zakera_conversation_messages_count
zakera_conversations_archived_total
zakera_conversations_deleted_total
... and more
```

### Database Metrics (15+)
```
zakera_db_queries_total
zakera_db_query_duration_seconds
zakera_db_connections_active
zakera_db_transactions_total
zakera_db_size_bytes
zakera_db_table_rows
... and more
```

### Model Metrics (10+)
```
zakera_model_requests_total
zakera_model_tokens_total
zakera_model_cost_total
zakera_model_errors_total
zakera_model_fallback_total
... and more
```

### Search Metrics (5+)
```
zakera_search_queries_total
zakera_search_duration_seconds
zakera_search_results_count
zakera_search_no_results_total
... and more
```

## Using the Stack

### View Metrics in Prometheus

```bash
# Open Prometheus
open http://localhost:9090

# Example queries:
zakera_conversations_active_total
rate(zakera_messages_total[5m])
histogram_quantile(0.95, rate(zakera_db_query_duration_seconds_bucket[5m]))
```

### Create Custom Dashboard

1. Open Grafana → Create → Dashboard
2. Add Panel → Select Prometheus datasource
3. Enter PromQL query
4. Configure visualization
5. Save dashboard

### Set Up Alerts

1. **In Grafana** (recommended):
   - Dashboard → Panel → Alert tab
   - Configure conditions
   - Set notification channel

2. **In Prometheus** (for system-wide):
   - Edit `alerts-conversations.yml`
   - Reload Prometheus: `docker-compose restart prometheus`

### Export Data

```bash
# Export Prometheus data
docker exec zakera-prometheus promtool tsdb dump /prometheus

# Export Grafana dashboard
# Grafana UI → Dashboard → Share → Export → Save to file
```

## Integration with Application

### Add Metrics in Code

```python
from src.monitoring.conversation_metrics import (
    conversations_created,
    track_conversation_creation,
    track_message_save
)

# Simple counter
conversations_created.labels(model="gpt-4", has_system_prompt="true").inc()

# With context manager
with track_conversation_creation(model="gpt-4", has_system_prompt=True):
    create_conversation()

with track_message_save(role="user", model="gpt-4"):
    save_message()
```

### Update Gauges

```python
from src.monitoring.conversation_metrics import (
    update_active_conversations,
    update_db_pool_stats
)

# Update active count
update_active_conversations(get_active_count())

# Update connection pool
update_db_pool_stats(
    active=pool.active,
    idle=pool.idle,
    overflow=pool.overflow,
    size=pool.size
)
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop grafana
```

## Useful Commands

```bash
# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana

# Restart service
docker-compose restart prometheus

# Check service health
docker-compose ps

# View resource usage
docker stats

# Execute command in container
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

## Common Issues

**Port already in use**:
```bash
# Change port in docker-compose.yml
ports:
  - "3002:3000"  # Use 3002 instead of 3001
```

**Cannot connect to application**:
```bash
# Use host.docker.internal on Mac/Windows
# Use 172.17.0.1 on Linux
# Or add to same network
```

**Metrics not showing**:
```bash
# Verify endpoint
curl http://localhost:8000/api/v1/monitoring/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

## Directory Structure

```
monitoring/
├── docker-compose.yml           # Service definitions
├── prometheus.yml               # Prometheus config
├── alerts.yml                   # General alerts
├── alerts-conversations.yml     # Conversation alerts
├── alertmanager.yml            # Alert routing
├── loki-config.yml             # Log storage
├── promtail-config.yml         # Log shipping
├── grafana/
│   ├── datasources/
│   │   └── prometheus.yml      # Auto-provision datasources
│   └── dashboards/
│       ├── ai-chat-agent-overview.json
│       ├── conversation-performance.json
│       ├── database-performance.json
│       └── model-performance.json
└── README.md                   # This file
```

## Next Steps

1. **Customize dashboards** for your needs
2. **Set alert thresholds** based on your traffic
3. **Configure notifications** (Email/Slack/Discord)
4. **Set up regular reviews** of metrics
5. **Document incidents** and improvements

---

**For detailed documentation, see**: `docs/MONITORING_SETUP.md`
