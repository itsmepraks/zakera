# Infrastructure and DevOps Guide

## Overview

This guide covers the complete infrastructure setup, CI/CD pipelines, deployment procedures, and operational best practices for the Zakera AI Chat Agent.

---

## 🏗️ Architecture

### Production Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
│                  (AWS ALB / Nginx)                       │
└──────────────────────┬──────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
    ┌──────▼──────┐        ┌──────▼──────┐
    │   API Pod 1  │        │   API Pod N  │
    │  (Container) │   ...  │  (Container) │
    └──────┬──────┘        └──────┬──────┘
           │                       │
    ┌──────┴───────────────────────┴──────┐
    │                                      │
┌───▼────┐  ┌────────┐  ┌────────┐  ┌───▼─────┐
│Postgres│  │ Redis  │  │ Ollama │  │Monitoring│
│   DB   │  │ Cache  │  │  LLM   │  │  Stack  │
└────────┘  └────────┘  └────────┘  └─────────┘
```

### Monitoring Stack

```
┌──────────┐    ┌────────────┐    ┌───────────┐
│   API    │───▶│ Prometheus │───▶│  Grafana  │
│  Metrics │    │  (Metrics) │    │(Dashboard)│
└──────────┘    └────────────┘    └───────────┘
                      │
                      ▼
                ┌─────────────┐
                │AlertManager │
                │ (Alerting)  │
                └─────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    [Email]      [Slack]      [Discord]
```

---

## 🚀 Deployment

### Prerequisites

- Docker 24+
- kubectl 1.28+
- AWS CLI 2.0+
- Terraform 1.6+ (optional)
- PostgreSQL 15+
- Redis 7+

### Quick Deploy to Staging

```bash
# 1. Set environment
export ENVIRONMENT=staging

# 2. Configure secrets
cp .env.example .env.staging
vim .env.staging  # Add API keys and secrets

# 3. Build and push images
make docker-build
make docker-push

# 4. Deploy to staging
./scripts/deploy.sh staging

# 5. Run migrations
./scripts/migrate.sh staging

# 6. Verify deployment
./scripts/smoke-tests.sh https://staging.zakera.app

# 7. Monitor health
./scripts/health-check.sh https://staging.zakera.app 300
```

### Production Deployment

```bash
# 1. Create backup
./scripts/backup.sh production

# 2. Deploy to production
./scripts/deploy.sh production

# 3. Run migrations
./scripts/migrate.sh production

# 4. Smoke tests
./scripts/smoke-tests.sh https://zakera.app

# 5. Monitor for 10 minutes
./scripts/health-check.sh https://zakera.app 600

# 6. Verify metrics
curl https://zakera.app/api/v1/monitoring/metrics
```

### Kubernetes Deployment

```bash
# 1. Apply configurations
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml

# 2. Verify deployment
kubectl get pods -n zakera
kubectl get svc -n zakera

# 3. Check logs
kubectl logs -f deployment/zakera-api -n zakera

# 4. Scale deployment
kubectl scale deployment/zakera-api --replicas=5 -n zakera
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflows

#### Continuous Integration (ci.yml)

Runs on every push and pull request:

**Backend Tests:**
- Linting (flake8)
- Type checking (mypy)
- Code formatting (black, isort)
- Security scanning (bandit, safety)
- Unit tests with coverage
- Integration tests

**Frontend Tests:**
- ESLint validation
- TypeScript type checking
- Jest unit tests
- Build verification

**Docker:**
- Multi-platform build test
- Image size optimization
- Security scanning (Trivy)

**Quality Gates:**
- Code coverage > 80%
- No critical security issues
- All tests passing
- Build successful

#### Continuous Deployment (cd.yml)

Runs on main branch and tags:

**Staging Deploy:**
- Automatic on main branch push
- Build and push Docker images
- Deploy to ECS staging
- Run database migrations
- Execute smoke tests
- Monitor deployment health
- Slack notification

**Production Deploy:**
- Manual approval required
- Triggered on version tags (v*.*.*)
- Create database backup
- Deploy to ECS production
- Run migrations
- Warm up caches
- Extended smoke tests
- 10-minute health monitoring
- Create GitHub release
- Multi-channel notifications

### Pipeline Status Badges

Add to README.md:
```markdown
[![CI](https://github.com/itsmepraks/zakera/workflows/CI/badge.svg)](https://github.com/itsmepraks/zakera/actions)
[![CD](https://github.com/itsmepraks/zakera/workflows/CD/badge.svg)](https://github.com/itsmepraks/zakera/actions)
[![codecov](https://codecov.io/gh/itsmepraks/zakera/branch/main/graph/badge.svg)](https://codecov.io/gh/itsmepraks/zakera)
```

---

## 🐳 Docker

### Development

```bash
# Build development image
docker build -t zakera:dev .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f api

# Run tests in container
docker-compose exec api pytest

# Stop services
docker-compose down
```

### Production

```bash
# Build production image
docker build -f Dockerfile.production -t zakera:prod .

# Run production stack
docker-compose -f docker-compose.production.yml up -d

# Scale API service
docker-compose -f docker-compose.production.yml up -d --scale api=5

# View resource usage
docker stats

# Cleanup
docker-compose -f docker-compose.production.yml down -v
```

### Image Optimization

**Multi-stage Build Benefits:**
- Builder stage: 1.2 GB
- Runtime stage: 450 MB (62% reduction)
- Faster pulls and deployments
- Reduced attack surface

**Security Hardening:**
- Non-root user
- Minimal base image (slim)
- No build tools in runtime
- Security scanning in CI
- Regular base image updates

---

## 🗄️ Database

### Migrations

```bash
# Create new migration
alembic revision -m "Add new feature"

# Run migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Backup and Restore

```bash
# Create backup
./scripts/backup.sh production

# Restore from backup
gunzip < backups/production/db_20260215_030000.sql.gz | \
    psql $DATABASE_URL

# Restore Redis
redis-cli --rdb backups/production/redis_20260215_030000.rdb
```

### Performance Optimization

**Indexes Added:**
- `idx_conversations_created_at` - Date range queries
- `idx_conversations_user_created` - User analytics
- `idx_messages_created_at` - Date range queries
- `idx_messages_model` - Model analytics
- `idx_messages_conversation_created` - Message queries

**Query Optimization:**
- Use `EXPLAIN ANALYZE` for slow queries
- Monitor with `pg_stat_statements`
- Regular `VACUUM ANALYZE`
- Connection pooling (min: 5, max: 20)

---

## 📊 Monitoring

### Accessing Dashboards

**Grafana:**
- URL: http://localhost:3001 (or https://grafana.zakera.app)
- Default credentials: admin/admin
- Dashboards:
  - System Overview
  - API Performance
  - Model Analytics
  - Analytics Metrics

**Prometheus:**
- URL: http://localhost:9090
- Query interface for ad-hoc metrics
- Alert rules viewer

**AlertManager:**
- URL: http://localhost:9093
- View active alerts
- Silence alerts temporarily

### Key Metrics to Monitor

**API Health:**
```promql
# Request rate
rate(api_requests_total[5m])

# Error rate
rate(api_requests_total{status=~"5.."}[5m]) / rate(api_requests_total[5m])

# Response time p95
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))
```

**Analytics Performance:**
```promql
# Query duration
histogram_quantile(0.95, rate(analytics_query_duration_seconds_bucket[5m]))

# Cache hit rate
rate(analytics_cache_hits_total[5m]) / 
(rate(analytics_cache_hits_total[5m]) + rate(analytics_cache_misses_total[5m]))
```

**Model Reliability:**
```promql
# Retry rate
rate(model_retry_attempts_total[5m])

# Provider health
model_provider_health_score

# Circuit breaker state
model_circuit_breaker_state{state="open"}
```

### Alerts

**Critical Alerts:**
- Service down > 2 minutes
- Circuit breaker opened
- Database connection pool exhausted
- High error rate (> 5%)

**Warning Alerts:**
- Slow queries (> 5s)
- Low cache hit rate (< 50%)
- High retry rate
- Low provider health (< 0.7)

**Info Alerts:**
- Request spikes
- Cost threshold exceeded
- Deployment completed

---

## 🧪 Testing

### Running Tests

```bash
# All tests
make test

# Backend only
pytest tests/ -v

# Frontend only
cd src/frontend && npm test

# With coverage
make test-cov

# Integration tests
pytest tests/integration/ -v

# Specific test file
pytest tests/test_analytics.py -v

# Parallel execution
pytest tests/ -n auto
```

### Load Testing

```bash
# Install Locust
pip install locust

# Run load tests
locust -f tests/load/locustfile.py \
    --host http://localhost:8000 \
    --users 100 \
    --spawn-rate 10

# Web UI
open http://localhost:8089
```

### Performance Benchmarking

```bash
# Run benchmarks
pytest tests/benchmarks/ --benchmark-only

# Compare with baseline
pytest tests/benchmarks/ --benchmark-compare

# Generate report
pytest tests/benchmarks/ --benchmark-json=output.json
```

---

## 🔐 Security

### Secret Management

**GitHub Secrets:**
```bash
# Required secrets for CI/CD
GITHUB_TOKEN
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
DOCKER_USERNAME
DOCKER_PASSWORD
SLACK_WEBHOOK
SONAR_TOKEN
CODECOV_TOKEN
```

**Kubernetes Secrets:**
```bash
# Create secrets
kubectl create secret generic zakera-secrets \
  --from-literal=database-url=$DATABASE_URL \
  --from-literal=redis-url=$REDIS_URL \
  --from-literal=secret-key=$SECRET_KEY \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY \
  -n zakera

# Verify
kubectl get secrets -n zakera
```

### Security Scanning

```bash
# Scan dependencies
safety check

# Scan code
bandit -r src/

# Scan Docker image
trivy image zakera:latest

# Scan infrastructure
trivy config kubernetes/
```

---

## 📦 Releases

### Version Numbering

Follows Semantic Versioning (SemVer):
- **Major**: Breaking changes (v1.0.0)
- **Minor**: New features (v0.6.0)
- **Patch**: Bug fixes (v0.5.1)

### Creating a Release

```bash
# 1. Update version in files
vim pyproject.toml  # Update version
vim src/frontend/package.json  # Update version

# 2. Update CHANGELOG
vim CHANGELOG.md

# 3. Commit changes
git add .
git commit -m "Bump version to v0.6.0"

# 4. Create tag
git tag -a v0.6.0 -m "Release v0.6.0: Analytics and Voice Features"

# 5. Push tag
git push origin v0.6.0

# GitHub Actions will:
# - Run CI tests
# - Build Docker images
# - Deploy to production
# - Create GitHub release
```

### Rollback Procedure

```bash
# 1. Find previous version
aws ecs describe-task-definition \
    --task-definition zakera-production \
    --query 'taskDefinition.revision'

# 2. Update service to previous revision
aws ecs update-service \
    --cluster zakera-production \
    --service zakera-api \
    --task-definition zakera-production:PREVIOUS_REVISION

# 3. Wait for rollback
aws ecs wait services-stable \
    --cluster zakera-production \
    --service zakera-api

# 4. Verify
./scripts/smoke-tests.sh https://zakera.app
```

---

## 🎯 Performance Tuning

### API Optimization

```python
# Gunicorn workers
workers = (2 * cpu_count) + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5

# Request timeouts
timeout = 120
graceful_timeout = 30
```

### Database Connection Pool

```python
# SQLAlchemy pool settings
pool_size = 10
max_overflow = 20
pool_pre_ping = True
pool_recycle = 3600
```

### Redis Configuration

```bash
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

### Caching Strategy

- **Analytics queries**: 5 minutes
- **Model requests**: 5 seconds (deduplication)
- **Static content**: 1 hour
- **User sessions**: 24 hours

---

## 📈 Scaling

### Horizontal Scaling

**Manual Scaling:**
```bash
# Docker Compose
docker-compose up -d --scale api=5

# Kubernetes
kubectl scale deployment/zakera-api --replicas=5 -n zakera

# ECS
aws ecs update-service \
    --cluster zakera-production \
    --service zakera-api \
    --desired-count 5
```

**Auto-scaling (HPA):**
- Min replicas: 3
- Max replicas: 10
- CPU target: 70%
- Memory target: 80%
- Scale up: +100% every 30s
- Scale down: -50% every 60s

### Vertical Scaling

**Resource Allocation:**

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|---------------|
| API | 500m | 2000m | 512Mi | 2Gi |
| Postgres | 500m | 1000m | 512Mi | 1Gi |
| Redis | 250m | 500m | 256Mi | 512Mi |
| Ollama | 2000m | 4000m | 4Gi | 8Gi |
| Monitoring | 500m | 1000m | 512Mi | 1Gi |

---

## 🔧 Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory
docker stats

# Analyze heap
python -m memory_profiler src/api/main.py

# Increase limits
kubectl set resources deployment/zakera-api \
    --limits=memory=4Gi -n zakera
```

#### Database Connection Issues
```bash
# Check connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';"

# Increase pool size
export DB_POOL_SIZE=20
```

#### Circuit Breaker Stuck Open
```bash
# Check provider health
curl http://localhost:8000/api/v1/models/health

# Reset circuit breaker (requires API endpoint)
curl -X POST http://localhost:8000/api/v1/models/circuit-breaker/reset/openai

# Or restart service
kubectl rollout restart deployment/zakera-api -n zakera
```

---

## 🎓 Best Practices

### Development

1. **Always run tests before commit**
   ```bash
   make test
   ```

2. **Check code quality**
   ```bash
   make lint
   make format
   ```

3. **Update dependencies regularly**
   ```bash
   pip-review --auto
   npm audit fix
   ```

4. **Use feature branches**
   ```bash
   git checkout -b feature/my-feature
   ```

### Deployment

1. **Always create backups before production deploy**
2. **Test in staging first**
3. **Monitor health for 10+ minutes after deploy**
4. **Have rollback plan ready**
5. **Deploy during low-traffic hours**
6. **Communicate with team**

### Monitoring

1. **Set up alerts for critical metrics**
2. **Review dashboards daily**
3. **Investigate anomalies promptly**
4. **Keep metrics retention at 30+ days**
5. **Document incident responses**

---

## 📞 Support

### Emergency Contacts

- **On-call Engineer**: Prakriti Bista
- **DevOps Team**: devops@zakera.app
- **Slack Channel**: #zakera-incidents

### Runbooks

- [Service Down](runbooks/service-down.md)
- [Database Issues](runbooks/database-issues.md)
- [High Load](runbooks/high-load.md)
- [Security Incident](runbooks/security-incident.md)

---

**Version**: 1.0.0  
**Last Updated**: February 15, 2026  
**Maintained by**: Prakriti Bista
