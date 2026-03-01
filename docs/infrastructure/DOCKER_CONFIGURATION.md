# Docker Configuration Guide

Complete guide to Zakera's Docker setup and configurations.

## Overview

Zakera uses Docker and Docker Compose for:
- Local development
- Testing environments
- CI/CD pipelines
- Production deployment

## Docker Compose Files

### 1. docker-compose.yml (Base)

**Purpose**: Production-ready base configuration
**Use**: `docker-compose up -d`

**Services**:
- postgres
- redis
- backend
- nginx
- jaeger
- prometheus
- grafana

**Features**:
- Health checks
- Restart policies
- Resource limits
- Named volumes
- Bridge networking

### 2. docker-compose.dev.yml (Development)

**Purpose**: Enhanced development environment
**Use**: `docker-compose -f docker-compose.dev.yml up -d`

**Additional Services**:
- pgAdmin (database GUI)
- RedisInsight (cache GUI)
- Loki (log aggregation)
- Promtail (log shipping)
- MailHog (email testing)
- Swagger UI (API docs)

**Features**:
- Volume mounts for hot-reload
- Debug ports exposed
- Development-optimized settings
- All observability tools
- Service profiles for optional tools

**Profiles**:
```bash
# Core services only
docker-compose -f docker-compose.dev.yml up -d

# With development tools
docker-compose -f docker-compose.dev.yml --profile tools up -d

# With full observability
docker-compose -f docker-compose.dev.yml --profile observability up -d

# Everything
docker-compose -f docker-compose.dev.yml --profile tools --profile observability up -d
```

### 3. docker-compose.test.yml (Testing)

**Purpose**: CI/CD testing environment
**Use**: `docker-compose -f docker-compose.test.yml run test-runner`

**Services**:
- test-postgres (isolated test DB)
- test-redis (test cache)
- test-runner (pytest execution)

**Features**:
- Ephemeral containers
- Fast startup
- Parallel test execution
- Coverage reporting

### 4. docker-compose.production.yml (Production)

**Purpose**: Production deployment
**Use**: See production deployment guide

**Differences from base**:
- External secrets
- Resource limits
- Security hardening
- High availability setup
- Backup configurations

## Dockerfile Variants

### Dockerfile (Standard)

**Purpose**: Basic build
**Stages**: development, production

```dockerfile
# Development
FROM python:3.11-slim as development
RUN pip install debugpy
CMD ["uvicorn", "src.api.main:app", "--reload"]

# Production  
FROM python:3.11-slim as production
USER zakera
CMD ["gunicorn", "src.api.main:app"]
```

### Dockerfile.multi-stage (Advanced)

**Purpose**: Optimized multi-target builds
**Stages**: base, development, testing, builder, production, performance-testing

**Advantages**:
- Shared base layer
- Optimized for each use case
- Minimal production image
- Cached dependencies
- Security hardened

**Usage**:
```bash
# Development
docker build --target development -t zakera:dev -f Dockerfile.multi-stage .

# Testing
docker build --target testing -t zakera:test -f Dockerfile.multi-stage .

# Production
docker build --target production -t zakera:prod -f Dockerfile.multi-stage .

# Performance testing
docker build --target performance-testing -t zakera:perf -f Dockerfile.multi-stage .
```

### Dockerfile.production

**Purpose**: Production-optimized build
**Features**:
- Multi-stage build
- Minimal final image
- Non-root user
- Security scanning
- Health checks

## Service Configuration

### PostgreSQL

**Development**:
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: zakera_dev
    POSTGRES_USER: zakera
    POSTGRES_PASSWORD: dev_password
  volumes:
    - postgres_dev_data:/var/lib/postgresql/data
    - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
  ports:
    - "5432:5432"
```

**Production**:
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: zakera
    POSTGRES_USER: zakera
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # From secrets
  volumes:
    - /data/postgres:/var/lib/postgresql/data  # External volume
  # Port not exposed externally
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '2.0'
      reservations:
        memory: 1G
        cpus: '1.0'
```

### Redis

**Development**:
```yaml
redis:
  image: redis:7-alpine
  command: redis-server /usr/local/etc/redis/redis.conf
  volumes:
    - redis_dev_data:/data
    - ./config/redis-dev.conf:/usr/local/etc/redis/redis.conf
  ports:
    - "6379:6379"
```

**Production**:
```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --requirepass ${REDIS_PASSWORD}
    --maxmemory 2gb
    --maxmemory-policy allkeys-lru
    --appendonly yes
  volumes:
    - /data/redis:/data
  deploy:
    resources:
      limits:
        memory: 2.5G
```

### Backend API

**Development with Hot-Reload**:
```yaml
backend:
  build:
    context: .
    target: development
  environment:
    DEBUG: "true"
    RELOAD: "true"
  volumes:
    - ./src:/app/src:ro  # Read-only source mount
    - ./logs:/app/logs   # Writable logs
  ports:
    - "8000:8000"  # API
    - "5678:5678"  # Debugger
  command: >
    python -m debugpy --listen 0.0.0.0:5678
    -m uvicorn src.api.main:app
    --host 0.0.0.0 --port 8000 --reload
```

**Production with Gunicorn**:
```yaml
backend:
  build:
    context: .
    target: production
  environment:
    DEBUG: "false"
    WORKERS: 4
  # No volumes mounted
  # No debug port
  command: >
    gunicorn src.api.main:app
    --worker-class uvicorn.workers.UvicornWorker
    --workers 4
    --bind 0.0.0.0:8000
```

## Networking

### Bridge Network (Default)

```yaml
networks:
  zakera-dev:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

**Service communication**:
- Use service names as hostnames
- Example: `http://backend:8000`
- DNS resolution automatic

### Multiple Networks (Production)

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
  database:
    driver: bridge
    internal: true  # No external access

services:
  nginx:
    networks:
      - frontend
      - backend
  
  backend:
    networks:
      - backend
      - database
  
  postgres:
    networks:
      - database  # Isolated
```

## Volume Management

### Named Volumes

```yaml
volumes:
  postgres_dev_data:
    driver: local
  redis_dev_data:
    driver: local
  grafana_dev_data:
    driver: local
```

**Advantages**:
- Managed by Docker
- Survives container deletion
- Easy backup/restore
- Portable

### Bind Mounts

```yaml
volumes:
  - ./src:/app/src:ro         # Read-only source code
  - ./logs:/app/logs          # Writable logs
  - ./config:/app/config:ro   # Read-only config
```

**Use for**:
- Hot-reload (development)
- Configuration files
- Log collection
- Shared data

### External Volumes (Production)

```yaml
volumes:
  postgres_data:
    external: true
    name: zakera-postgres-prod
```

**Create**:
```bash
docker volume create zakera-postgres-prod
```

## Health Checks

### API Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/monitoring/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### Database Health Check

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U zakera -d zakera_dev"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### Redis Health Check

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Resource Limits

### Development (Generous)

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

### Production (Restricted)

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Environment Variables

### Best Practices

✅ **Good**:
```yaml
environment:
  DATABASE_URL: ${DATABASE_URL}  # From .env file
  SECRET_KEY: ${SECRET_KEY}
  API_KEY: ${API_KEY}
```

❌ **Bad**:
```yaml
environment:
  SECRET_KEY: hardcoded-secret  # Never hardcode secrets!
```

### Using .env Files

**.env**:
```bash
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_redis_password
OPENAI_API_KEY=sk-...
SECRET_KEY=...
```

**docker-compose.yml**:
```yaml
services:
  backend:
    env_file:
      - .env
    environment:
      # Override or add
      DEBUG: "true"
```

## Build Optimization

### Layer Caching

✅ **Good** (copy dependencies first):
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt  # Cached layer

COPY . .  # Changes frequently
```

❌ **Bad** (copy everything first):
```dockerfile
COPY . .  # Invalidates cache often
RUN pip install -r requirements.txt
```

### .dockerignore

```
# Development
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp

# Git
.git/
.gitignore

# Documentation
docs/
*.md

# Tests (for production build)
tests/

# Environment
.env
.env.local

# Logs
logs/
*.log
```

## Common Tasks

### Build Images

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend

# Build with no cache
docker-compose build --no-cache

# Build specific target
docker build --target production -t zakera:prod .
```

### Start Services

```bash
# Start all
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis backend

# Start with logs
docker-compose up

# Start with profiles
docker-compose --profile tools up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Since timestamp
docker-compose logs --since 2026-02-28T10:00:00 backend
```

### Execute Commands

```bash
# Shell in container
docker-compose exec backend /bin/bash

# Run command
docker-compose exec backend python --version

# Run as different user
docker-compose exec -u root backend apt-get update

# Run one-off container
docker-compose run --rm backend python scripts/seed.py
```

### Scale Services

```bash
# Scale to 3 instances
docker-compose up -d --scale backend=3

# With load balancer
docker-compose -f docker-compose.production.yml up -d --scale backend=3
```

### Stop and Remove

```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove with volumes (WARNING: deletes data)
docker-compose down -v

# Remove with images
docker-compose down --rmi all
```

## Debugging

### Python Debugger (debugpy)

**Setup** (already configured in dev compose):

**VS Code launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

**PyCharm**:
1. Run → Edit Configurations
2. Add → Python Remote Debug
3. Host: localhost, Port: 5678
4. Path mappings: Local=./src, Remote=/app/src

### Container Debugging

```bash
# Check container status
docker ps -a

# Inspect container
docker inspect zakera-backend-dev

# View container logs
docker logs zakera-backend-dev --tail 100 -f

# Check resource usage
docker stats zakera-backend-dev

# Execute shell
docker exec -it zakera-backend-dev /bin/bash
```

## Performance

### Build Performance

**Use BuildKit**:
```bash
export DOCKER_BUILDKIT=1
docker build .
```

**Parallel builds**:
```bash
docker-compose build --parallel
```

**Layer caching**:
```bash
# Use cache from registry
docker build --cache-from zakera:latest .
```

### Runtime Performance

**Resource limits**:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

**Logging drivers**:
```yaml
services:
  backend:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

## Security

### Non-Root User

```dockerfile
# Create user
RUN useradd -m -u 1000 -s /bin/bash zakera

# Switch to user
USER zakera

# Run as user
CMD ["python", "app.py"]
```

### Secret Management

**Development** (.env file):
```bash
SECRET_KEY=dev-secret
```

**Production** (Docker secrets):
```yaml
secrets:
  db_password:
    external: true

services:
  backend:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
```

**Create secret**:
```bash
echo "secure_password" | docker secret create db_password -
```

### Read-Only Filesystem

```yaml
services:
  backend:
    read_only: true
    tmpfs:
      - /tmp
      - /app/cache
```

### Security Scanning

```bash
# Scan image for vulnerabilities
docker scan zakera:latest

# Or use Trivy
trivy image zakera:latest
```

## Troubleshooting

### Container Won't Start

**Check logs**:
```bash
docker logs zakera-backend-dev
```

**Check health**:
```bash
docker inspect --format='{{json .State.Health}}' zakera-backend-dev | jq
```

**Try manually**:
```bash
docker run --rm -it zakera:dev /bin/bash
```

### Network Issues

**List networks**:
```bash
docker network ls
```

**Inspect network**:
```bash
docker network inspect zakera-dev
```

**Test connectivity**:
```bash
# From one container to another
docker exec zakera-backend-dev ping postgres
docker exec zakera-backend-dev curl http://redis:6379
```

### Volume Issues

**List volumes**:
```bash
docker volume ls
```

**Inspect volume**:
```bash
docker volume inspect zakera_postgres_dev_data
```

**Backup volume**:
```bash
docker run --rm \
  -v zakera_postgres_dev_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar -czf /backup/data.tar.gz /data
```

### Build Failures

**Clear build cache**:
```bash
docker builder prune -a
```

**Build with verbose output**:
```bash
docker-compose build --progress=plain backend
```

**Check Dockerfile syntax**:
```bash
docker build --check .
```

## Best Practices

### 1. Use Multi-Stage Builds

✅ Reduces final image size  
✅ Separates build and runtime dependencies  
✅ Improves security  
✅ Faster deployments

### 2. Minimize Layers

✅ **Good**:
```dockerfile
RUN apt-get update && \\
    apt-get install -y curl git && \\
    rm -rf /var/lib/apt/lists/*
```

❌ **Bad**:
```dockerfile
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git
RUN rm -rf /var/lib/apt/lists/*
```

### 3. Use Specific Versions

✅ **Good**:
```yaml
image: postgres:15-alpine
```

❌ **Bad**:
```yaml
image: postgres:latest  # Unpredictable
```

### 4. Health Checks

Always include health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### 5. Resource Limits

Prevent resource exhaustion:
```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Build Docker image
  run: |
    docker build \
      --target production \
      --tag zakera:${{ github.sha }} \
      --tag zakera:latest \
      .

- name: Test image
  run: |
    docker run --rm zakera:${{ github.sha }} pytest

- name: Push image
  run: |
    docker push zakera:${{ github.sha }}
    docker push zakera:latest
```

### Docker Hub

```bash
# Login
docker login

# Tag
docker tag zakera:latest username/zakera:0.8.0

# Push
docker push username/zakera:0.8.0
```

## Production Deployment

### Docker Swarm

See: [Docker Swarm Guide](./DOCKER_SWARM.md)

### Kubernetes

See: [Kubernetes Deployment](./KUBERNETES_DEPLOYMENT.md)

### Cloud Platforms

- [AWS ECS](./AWS_ECS.md)
- [Google Cloud Run](./GCP_CLOUD_RUN.md)
- [Azure Container Instances](./AZURE_ACI.md)

## Maintenance

### Updates

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build
```

### Cleanup

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

### Monitoring

```bash
# Check disk usage
docker system df

# Detailed view
docker system df -v
```

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)

---

**Last Updated**: February 2026  
**Docker Version**: 24.0+  
**Compose Version**: 2.0+
