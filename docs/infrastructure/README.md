# Infrastructure Documentation Index

Complete infrastructure documentation for Zakera AI Chat Agent.

## Quick Links

### Getting Started
1. [Infrastructure Overview](./INFRASTRUCTURE_OVERVIEW.md) - Start here!
2. [Docker Configuration](./DOCKER_CONFIGURATION.md)
3. [Monitoring Setup](./MONITORING_SETUP.md)

### Deployment
4. [Production Deployment](../PRODUCTION_DEPLOYMENT.md)
5. [Kubernetes Deployment](../DEPLOYMENT_PRODUCTION.md)
6. [Scaling Guide](../SCALING_GUIDE.md)

### API Documentation
7. [API Documentation Guide](../api/API_DOCUMENTATION_GUIDE.md)
8. [OpenAPI Validation](../api/openapi-validator.py)

### Monitoring & Observability
9. [Monitoring Guide](../MONITORING.md)
10. [Distributed Tracing](../DISTRIBUTED_TRACING.md)

## Documentation Structure

```
docs/
├── infrastructure/           # Infrastructure docs (this folder)
│   ├── README.md             # This file
│   ├── INFRASTRUCTURE_OVERVIEW.md
│   ├── DOCKER_CONFIGURATION.md
│   └── MONITORING_SETUP.md
├── api/                      # API documentation
│   ├── API_DOCUMENTATION_GUIDE.md
│   ├── openapi-validator.py
│   ├── openapi.json
│   └── examples/
├── frontend/                 # Frontend documentation
│   ├── CONVERSATION_MANAGEMENT.md
│   ├── KEYBOARD_SHORTCUTS.md
│   └── COMPONENT_API.md
└── ci-cd/                    # CI/CD documentation
    └── PERFORMANCE_TESTING.md
```

## By Role

### For Developers

Start with:
1. [Infrastructure Overview](./INFRASTRUCTURE_OVERVIEW.md)
2. [Docker Configuration](./DOCKER_CONFIGURATION.md)
3. Development Makefile: `make help`

Then:
- [API Documentation Guide](../api/API_DOCUMENTATION_GUIDE.md)
- [Testing Guide](../TESTING.md)

### For DevOps/SRE

Start with:
1. [Monitoring Setup](./MONITORING_SETUP.md)
2. [Production Deployment](../PRODUCTION_DEPLOYMENT.md)
3. [Kubernetes Deployment](../DEPLOYMENT_PRODUCTION.md)

Then:
- [Scaling Guide](../SCALING_GUIDE.md)
- [Security Guide](../SECURITY.md)
- [Troubleshooting](../TROUBLESHOOTING.md)

### For QA/Testing

Start with:
1. [Testing Guide](../TESTING.md)
2. [Performance Testing CI/CD](../ci-cd/PERFORMANCE_TESTING.md)
3. Performance testing: `tests/performance/README.md`

Then:
- [API Documentation](../api/API_DOCUMENTATION_GUIDE.md)
- Test coverage: `make test-coverage`

## Quick Start

### Development Environment

```bash
# 1. Start infrastructure
make quick-start

# 2. Open dashboards
make grafana      # Monitoring
make api-docs     # API documentation
make jaeger       # Distributed tracing

# 3. Run tests
make test

# 4. View logs
make dev-logs
```

### Monitoring Stack

```bash
# Initialize monitoring
./scripts/init-monitoring.sh

# Access services
make prometheus   # Metrics: http://localhost:9090
make grafana      # Dashboards: http://localhost:3001
make jaeger       # Tracing: http://localhost:16686
```

### API Validation

```bash
# Validate OpenAPI schema
python docs/api/openapi-validator.py docs/api/openapi.json

# Or use Make
make api-openapi  # Download schema
make api-docs     # View documentation
```

## Infrastructure Components

### Core Services

| Service | Port | Documentation |
|---------|------|---------------|
| **FastAPI Backend** | 8000 | [API Docs](http://localhost:8000/api/docs) |
| **PostgreSQL** | 5432 | [Docker Config](./DOCKER_CONFIGURATION.md#postgresql) |
| **Redis** | 6379 | [Docker Config](./DOCKER_CONFIGURATION.md#redis) |
| **Nginx** | 80/443 | [Docker Config](./DOCKER_CONFIGURATION.md#nginx) |

### Observability

| Service | Port | Documentation |
|---------|------|---------------|
| **Prometheus** | 9090 | [Monitoring Setup](./MONITORING_SETUP.md#prometheus) |
| **Grafana** | 3001 | [Monitoring Setup](./MONITORING_SETUP.md#grafana) |
| **Jaeger** | 16686 | [Distributed Tracing](../DISTRIBUTED_TRACING.md) |
| **Loki** | 3100 | [Monitoring Setup](./MONITORING_SETUP.md#loki) |

### Development Tools

| Tool | Port | Purpose |
|------|------|--------|
| **pgAdmin** | 5050 | PostgreSQL GUI |
| **RedisInsight** | 8001 | Redis GUI |
| **MailHog** | 8025 | Email testing |
| **Swagger UI** | 8080 | API documentation |

## Configuration Files

### Docker
- `docker-compose.yml` - Base configuration
- `docker-compose.dev.yml` - Development stack
- `docker-compose.production.yml` - Production configuration
- `Dockerfile` - Standard build
- `Dockerfile.multi-stage` - Optimized multi-stage build

### Monitoring
- `monitoring/prometheus.yml` - Prometheus configuration
- `monitoring/alertmanager.yml` - Alert routing
- `monitoring/grafana/provisioning/` - Grafana auto-config
- `monitoring/grafana/dashboards/` - Pre-built dashboards
- `monitoring/prometheus-rules/` - Recording and alerting rules

### Application
- `config/redis-dev.conf` - Redis configuration
- `config/pgadmin-servers.json` - pgAdmin presets
- `.env.example` - Environment variables template

## Dashboards

### Pre-configured Grafana Dashboards

1. **Performance Testing** - Locust test metrics
2. **Redis Cache** - Cache performance and efficiency
3. **API Performance** - Endpoint latency and errors
4. **System Overview** - Overall system health
5. **Model Providers** - AI provider comparison
6. **WebSocket** - Real-time connection metrics
7. **Database** - PostgreSQL performance

**Access**: http://localhost:3001 (admin/admin)

## Automation Scripts

### Monitoring
- `scripts/init-monitoring.sh` - Initialize monitoring stack
- `scripts/validate-infrastructure.sh` - Validate infrastructure

### Database
- `scripts/init-db.sql` - Database initialization
- `scripts/seed-dev-data.sql` - Development test data

### Development
- `Makefile.dev` - 50+ development commands
- `make help` - Show all available commands

## Validation

### Infrastructure Validation

```bash
# Run comprehensive validation
./scripts/validate-infrastructure.sh

# Checks:
# ✓ Docker installed and running
# ✓ Configuration files valid
# ✓ Ports available
# ✓ Disk space sufficient
# ✓ Services healthy
```

### API Validation

```bash
# Validate OpenAPI schema
python docs/api/openapi-validator.py docs/api/openapi.json

# Run in CI/CD
# See: .github/workflows/api-validation.yml
```

## Troubleshooting

### Common Issues

**Services won't start**:
1. Check ports: `./scripts/validate-infrastructure.sh`
2. View logs: `make dev-logs`
3. Check health: `make mon-health`

**Dashboard not loading**:
1. Verify Grafana: `curl http://localhost:3001/api/health`
2. Check Prometheus: `curl http://localhost:9090/-/healthy`
3. Restart: `make dev-restart`

**High resource usage**:
1. Check stats: `docker stats`
2. Review limits: See [Docker Configuration](./DOCKER_CONFIGURATION.md#resource-limits)
3. Optimize: See [Performance Guide](../PERFORMANCE.md)

See detailed troubleshooting in each guide.

## Support

### Getting Help

1. Check documentation (this folder)
2. Run validation: `./scripts/validate-infrastructure.sh`
3. Check logs: `make dev-logs`
4. Open issue on GitHub

### Reporting Issues

Include:
- Output from `./scripts/validate-infrastructure.sh`
- Relevant logs from `make dev-logs`
- Docker version: `docker --version`
- OS and architecture

## Contributing

When adding infrastructure:

1. Update relevant documentation
2. Add to validation script
3. Update Makefile if needed
4. Add Grafana dashboard if applicable
5. Update this index

See [Contributing Guide](../../CONTRIBUTING.md)

---

**Infrastructure Version**: 1.0  
**Last Updated**: February 2026  
**Status**: Production Ready
