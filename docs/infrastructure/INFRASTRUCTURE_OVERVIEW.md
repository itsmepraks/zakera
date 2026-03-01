# Infrastructure Overview

Comprehensive guide to Zakera's infrastructure components and architecture.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│                    Users / Clients                         │
└────────────────────┬────────────────────────────────┘
                     │
                     │ HTTPS
                     │
          ┌──────────┴──────────┐
          │    Nginx (Reverse    │
          │    Proxy / LB)       │
          └──────────┬──────────┘
                     │
       ┌─────────────┼─────────────┐
       │             │              │
   ┌───┴───┐      ┌──┴──┐      ┌──┴────┐
   │ FastAPI │      │ WS │      │ Static │
   │ Backend │      │    │      │ Assets │
   └───┬───┘      └─────┘      └───────┘
       │
   ┌───┼────────────────────────────────┐
   │   │                                │
   │   └───────────┬─────────────────────┘
   │                │
   │        ┌───────┼────────┐
   │        │       │         │
   │     ┌──┴──┐  ┌─┴──┐  ┌──┴───┐
   │     │ PG  │  │Redis  │ AI   │
   │     │ SQL │  │Cache │ Model │
   │     └─────┘  └─────┘  │ APIs │
   │                         └──────┘
   │
   └───────────────────────────────────────┐
                                       │
            Observability Stack        │
                                       │
   ┌──────────────┬─────────────┼─────────────────┐
   │              │              │                 │
┌──┴───┐      ┌──┴────┐   ┌──┴────┐   ┌────┴────┐
│ Prom- │      │ Grafana│   │ Jaeger │   │ Loki   │
│ etheus│      │        │   │ Tracing│   │ Logs   │
└───────┘      └───────┘   └───────┘   └─────────┘
```

## Components

### Application Layer

#### FastAPI Backend
**Purpose**: Core API server
**Technology**: Python 3.11, FastAPI, Uvicorn
**Port**: 8000 (API), 8001 (Metrics)
**Features**:
- RESTful API endpoints
- WebSocket support
- OpenAPI documentation
- Authentication & authorization
- Rate limiting
- CORS handling

**Health**: http://localhost:8000/api/v1/monitoring/health
**Metrics**: http://localhost:8001/metrics
**Docs**: http://localhost:8000/api/docs

#### React Frontend
**Purpose**: User interface
**Technology**: React 18, TypeScript, Vite
**Port**: 3000 (dev), served via Nginx (prod)
**Features**:
- Modern SPA
- Conversation management UI
- Real-time updates
- Dark mode
- Mobile responsive

**Dev**: `cd src/frontend && npm run dev`
**Build**: `npm run build`

### Data Layer

#### PostgreSQL
**Purpose**: Primary data store
**Version**: 15-alpine
**Port**: 5432
**Features**:
- Conversation history
- User data
- Branch management
- ACID compliance
- Full-text search

**Connection**: `postgresql://zakera:password@localhost:5432/zakera_dev`
**GUI**: pgAdmin at http://localhost:5050

#### Redis
**Purpose**: Caching and session storage
**Version**: 7-alpine
**Port**: 6379
**Features**:
- Conversation cache
- Session management
- Rate limiting
- Model response cache
- Pub/sub for real-time

**Connection**: `redis://:password@localhost:6379/0`
**GUI**: RedisInsight at http://localhost:8001

### Observability Stack

#### Prometheus
**Purpose**: Metrics collection and alerting
**Version**: 2.48.0
**Port**: 9090
**Features**:
- Time-series metrics storage
- PromQL query language
- Alerting rules
- Service discovery
- Recording rules

**UI**: http://localhost:9090
**Targets**: http://localhost:9090/targets
**Alerts**: http://localhost:9090/alerts

#### Grafana
**Purpose**: Metrics visualization
**Version**: 10.2.2
**Port**: 3001
**Features**:
- Pre-built dashboards
- Custom visualizations
- Alert management
- User management
- Dashboard sharing

**UI**: http://localhost:3001
**Credentials**: admin/admin (change in production)

**Dashboards**:
1. Performance Testing
2. Redis Cache Performance
3. API Performance & Health
4. System Metrics
5. Model Provider Comparison

#### Jaeger
**Purpose**: Distributed tracing
**Version**: 1.52
**Port**: 16686 (UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP)
**Features**:
- Request flow visualization
- Performance bottleneck identification
- Error tracking
- Service dependency mapping

**UI**: http://localhost:16686
**Service**: zakera-api-dev

#### Loki + Promtail
**Purpose**: Log aggregation
**Version**: 2.9.3
**Port**: 3100 (Loki)
**Features**:
- Centralized logging
- Log queries (LogQL)
- Integration with Grafana
- Trace correlation

**Query in Grafana**: Explore → Loki

### Supporting Services

#### Nginx
**Purpose**: Reverse proxy and load balancer
**Version**: Alpine
**Port**: 80 (HTTP), 443 (HTTPS)
**Features**:
- SSL termination
- Load balancing
- Static file serving
- Request routing
- Rate limiting

**Config**: `nginx/nginx.conf`

#### MailHog (Development)
**Purpose**: Email testing
**Port**: 1025 (SMTP), 8025 (UI)
**Features**:
- Catches all outbound emails
- Web interface to view emails
- API access

**UI**: http://localhost:8025

#### pgAdmin (Development)
**Purpose**: PostgreSQL management
**Port**: 5050
**Features**:
- Database browsing
- Query editor
- Schema visualization
- Import/export

**UI**: http://localhost:5050

#### RedisInsight (Development)
**Purpose**: Redis management
**Port**: 8001
**Features**:
- Key browsing
- CLI access
- Memory analysis
- Profiler

**UI**: http://localhost:8001

## Docker Configuration

### Development (docker-compose.dev.yml)

**Purpose**: Local development with hot-reload

**Features**:
- Volume mounts for live code updates
- Debug ports exposed
- Development-optimized settings
- All observability tools
- Database GUIs
- Email testing

**Start**: `make dev` or `docker-compose -f docker-compose.dev.yml up -d`

**Profiles**:
- `default`: Core services (postgres, redis, backend)
- `tools`: Development tools (pgAdmin, RedisInsight)
- `observability`: Full observability (Loki, Promtail)

### Production (docker-compose.production.yml)

**Purpose**: Production deployment

**Features**:
- Multi-stage optimized images
- No development dependencies
- Security hardened
- Health checks
- Resource limits
- Restart policies

**Deploy**: See `docs/DEPLOYMENT_PRODUCTION.md`

### Multi-Stage Dockerfile

**Targets**:
1. **base**: Common dependencies
2. **development**: Dev tools + debugger
3. **testing**: Test dependencies
4. **builder**: Production build
5. **production**: Minimal runtime
6. **performance-testing**: Locust + tools

**Build**:
```bash
# Development
docker build --target development -t zakera:dev .

# Production
docker build --target production -t zakera:prod .

# Testing
docker build --target testing -t zakera:test .
```

## Network Architecture

### Docker Networks

**zakera-dev** (Development):
- Subnet: 172.20.0.0/16
- Bridge network
- All services interconnected

**zakera-prod** (Production):
- Separate networks for security
- Frontend network
- Backend network
- Database network

### Service Communication

```
Nginx:80
  ↓
Backend:8000
  ├──> PostgreSQL:5432 (data)
  ├──> Redis:6379 (cache)
  ├──> Jaeger:4317 (traces)
  └──> Prometheus:9090 (metrics)
```

### Ports Reference

| Service | Port | Purpose |
|---------|------|--------|
| Nginx | 80, 443 | HTTP(S) traffic |
| Backend | 8000 | API endpoints |
| Backend | 8001 | Prometheus metrics |
| Backend | 5678 | Python debugger |
| PostgreSQL | 5432 | Database |
| pgAdmin | 5050 | Database GUI |
| Redis | 6379 | Cache |
| RedisInsight | 8001 | Redis GUI |
| Prometheus | 9090 | Metrics UI |
| Grafana | 3001 | Dashboards |
| Jaeger | 16686 | Tracing UI |
| Jaeger | 4317 | OTLP gRPC |
| Jaeger | 4318 | OTLP HTTP |
| Loki | 3100 | Logs |
| MailHog | 8025 | Email UI |
| MailHog | 1025 | SMTP |

## Data Persistence

### Volumes

**Development**:
```yaml
volumes:
  postgres_dev_data:    # Database data
  redis_dev_data:       # Cache data  
  prometheus_dev_data:  # Metrics data
  grafana_dev_data:     # Dashboards
  jaeger_dev_data:      # Traces
  dev_pip_cache:        # Python packages
```

**Backup**:
```bash
# Backup all volumes
docker run --rm \
  -v zakera_postgres_dev_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar -czf /backup/postgres-$(date +%Y%m%d).tar.gz /data
```

**Restore**:
```bash
# Restore volume
docker run --rm \
  -v zakera_postgres_dev_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar -xzf /backup/postgres-20260228.tar.gz -C /
```

## Configuration Management

### Environment Variables

**Location**: `.env` (local), GitHub Secrets (CI/CD), K8s Secrets (production)

**Required**:
```bash
# Database
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_PASSWORD=secure_redis_password

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Security
SECRET_KEY=generate-with-make-generate-secret
```

**Optional**:
```bash
# Monitoring
GRAFANA_PASSWORD=admin
ENABLE_METRICS=true
ENABLE_TRACING=true
TRACE_SAMPLING_RATE=0.1

# Performance
WORKERS=4
MAX_CONNECTIONS=100
```

### Configuration Files

**Application**:
- `config/settings.py`: Application settings
- `.env`: Environment variables
- `alembic.ini`: Database migrations

**Infrastructure**:
- `monitoring/prometheus.yml`: Prometheus config
- `monitoring/alertmanager.yml`: Alert routing
- `monitoring/grafana/`: Dashboard configs
- `nginx/nginx.conf`: Nginx config
- `config/redis-dev.conf`: Redis config

## Makefile Commands

### Quick Reference

```bash
# Development
make dev                # Start environment
make dev-logs           # View logs
make dev-down           # Stop environment
make quick-start        # Start + migrate + seed

# Database
make db-shell           # PostgreSQL shell
make db-migrate         # Run migrations
make db-reset           # Reset database
make db-seed            # Seed test data

# Redis
make redis-cli          # Redis CLI
make redis-flush        # Clear cache
make redis-stats        # Show statistics

# Testing
make test               # Run all tests
make test-unit          # Unit tests
make test-performance   # Performance tests
make test-coverage      # Coverage report

# Code Quality
make lint               # Run linters
make format             # Format code
make type-check         # Type checking
make security-scan      # Security scan

# Monitoring
make grafana            # Open Grafana
make prometheus         # Open Prometheus
make jaeger             # Open Jaeger
make mon-health         # Check all services

# Cleanup
make clean              # Remove temp files
make clean-docker       # Remove containers
make clean-all          # Complete cleanup
```

See `Makefile.dev` for all 50+ commands.

## Deployment

### Local Development

```bash
# Quick start
make quick-start

# Access services
make api-docs      # Open API documentation
make grafana       # Open Grafana dashboards
make jaeger        # Open tracing UI
```

### Staging

```bash
# Deploy to staging
docker-compose -f docker-compose.production.yml up -d

# Run smoke tests
make test-smoke
```

### Production

See dedicated guides:
- [Kubernetes Deployment](./KUBERNETES_DEPLOYMENT.md)
- [AWS Deployment](./AWS_DEPLOYMENT.md)
- [Docker Swarm](./DOCKER_SWARM.md)

## Monitoring Best Practices

### 1. Dashboard Organization

✅ **Good**:
- Group related metrics
- Use consistent colors
- Add descriptions
- Set appropriate refresh rates
- Include thresholds

### 2. Alert Configuration

✅ **Good**:
- Alert on symptoms, not causes
- Set realistic thresholds
- Include runbook links
- Test alerts regularly
- Review and tune

### 3. Metrics Collection

✅ **Good**:
- Follow naming conventions
- Use appropriate metric types
- Add relevant labels
- Document custom metrics
- Avoid high cardinality

### 4. Distributed Tracing

✅ **Good**:
- Sample appropriately (1-10% prod)
- Tag with useful metadata
- Keep traces 7-30 days
- Use for debugging
- Correlate with logs

## Troubleshooting

### Services Won't Start

```bash
# Check status
docker-compose -f docker-compose.dev.yml ps

# View logs
make dev-logs

# Check health
make mon-health

# Restart
make dev-restart
```

### Port Conflicts

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Disk Space Issues

```bash
# Check Docker disk usage
docker system df

# Clean up
docker system prune -a --volumes

# Or selectively
docker volume prune
docker image prune -a
```

### Dashboard Not Loading

```bash
# Check Grafana logs
docker logs zakera-grafana-dev

# Verify data source
curl http://localhost:9090/-/healthy

# Reload provisioning
docker-compose -f docker-compose.dev.yml restart grafana
```

## Security

### Development

⚠️ **Not for production use**:
- Default passwords
- Debug mode enabled
- All ports exposed
- Permissive CORS
- Verbose logging

### Production

✅ **Required**:
- Strong passwords
- TLS/SSL encryption
- Firewall rules
- Secret management
- RBAC enabled
- Audit logging
- Regular updates

See: [Security Guide](../SECURITY.md)

## Performance

### Resource Requirements

**Minimum** (Development):
- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB

**Recommended** (Development):
- CPU: 8 cores
- RAM: 16 GB
- Disk: 50 GB
- SSD storage

**Production** (per instance):
- CPU: 4-8 cores
- RAM: 16-32 GB
- Disk: 100 GB SSD

### Optimization

**Database**:
```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT ...;

-- Add indexes
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
```

**Cache**:
```python
# Optimal TTL settings
CONVERSATION_CACHE_TTL = 3600  # 1 hour
SESSION_CACHE_TTL = 1800       # 30 minutes
MODEL_RESPONSE_TTL = 7200      # 2 hours
```

**Application**:
- Use connection pooling
- Enable async operations
- Implement caching
- Optimize queries
- Use CDN for static assets

## Further Reading

### Infrastructure Guides
- [Monitoring Setup](./MONITORING_SETUP.md)
- [Docker Configuration](./DOCKER_CONFIGURATION.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Scaling Guide](./SCALING_GUIDE.md)

### API Documentation
- [API Documentation Guide](../api/API_DOCUMENTATION_GUIDE.md)
- [OpenAPI Validator](../api/openapi-validator.py)
- [Swagger UI](http://localhost:8000/api/docs)

### Monitoring
- [Grafana Dashboards](../../monitoring/grafana/dashboards/)
- [Prometheus Rules](../../monitoring/prometheus-rules/)
- [Alert Configuration](../../monitoring/alertmanager.yml)

---

**Last Updated**: February 2026  
**Infrastructure Version**: 1.0  
**Status**: Production Ready
