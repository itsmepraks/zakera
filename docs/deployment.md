# Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Production Checklist](#production-checklist)
6. [Scaling](#scaling)
7. [Backup and Recovery](#backup-and-recovery)

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space
- Valid API keys for AI providers

## Environment Configuration

### Production Environment Variables

```bash
# Copy and configure
cp .env.example .env.production

# Required variables
ENVIRONMENT=production
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=postgresql://user:pass@db:5432/zakera
REDIS_URL=redis://redis:6379/0

# AI Provider Configuration
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Security
ALLOWED_ORIGINS=https://yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Monitoring
PROMETHEUS_ENABLED=true
LOG_LEVEL=INFO
SENTRY_DSN=https://...@sentry.io/...

# Performance
MAX_WORKERS=4
MAX_CONNECTIONS=100
CONNECTION_TIMEOUT=30
```

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Create production compose file** (`docker-compose.prod.yml`):

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    image: zakera-api:latest
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENV_FILE=.env.production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - zakera-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: zakera
      POSTGRES_USER: zakera_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - zakera-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zakera_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - zakera-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./config/nginx/ssl:/etc/nginx/ssl
      - ./src/frontend/build:/usr/share/nginx/html
    depends_on:
      - api
    networks:
      - zakera-network

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - zakera-network

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - zakera-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  zakera-network:
    driver: bridge
```

2. **Deploy:**

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

3. **Database migrations:**

```bash
docker-compose -f docker-compose.prod.yml exec api \
  alembic upgrade head
```

## Kubernetes Deployment

### Deploy to Kubernetes

1. **Create namespace:**

```bash
kubectl create namespace zakera
```

2. **Create secrets:**

```bash
kubectl create secret generic zakera-secrets \
  --from-literal=secret-key=your-secret-key \
  --from-literal=openai-api-key=sk-... \
  --from-literal=db-password=your-db-password \
  -n zakera
```

3. **Apply manifests:**

```bash
kubectl apply -f k8s/ -n zakera
```

### Sample Kubernetes Manifests

**API Deployment** (`k8s/api-deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zakera-api
  labels:
    app: zakera-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: zakera-api
  template:
    metadata:
      labels:
        app: zakera-api
    spec:
      containers:
      - name: api
        image: your-registry/zakera-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: zakera-secrets
              key: secret-key
        - name: DATABASE_URL
          value: postgresql://$(DB_USER):$(DB_PASSWORD)@postgres:5432/zakera
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: zakera-api
spec:
  selector:
    app: zakera-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Production Checklist

### Security

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY (min 32 characters)
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Enable authentication on all endpoints
- [ ] Review CORS settings
- [ ] Implement API key rotation
- [ ] Enable security headers
- [ ] Set up WAF (Web Application Firewall)

### Performance

- [ ] Enable Redis caching
- [ ] Configure connection pooling
- [ ] Set appropriate worker count
- [ ] Enable compression
- [ ] Configure CDN for static assets
- [ ] Optimize database indexes
- [ ] Enable query caching

### Monitoring

- [ ] Set up Prometheus + Grafana
- [ ] Configure alerting rules
- [ ] Enable error tracking (Sentry)
- [ ] Set up log aggregation
- [ ] Configure uptime monitoring
- [ ] Enable APM

### Backup

- [ ] Configure automated database backups
- [ ] Test backup restoration
- [ ] Set up off-site backup storage
- [ ] Document recovery procedures

### Documentation

- [ ] Document deployment process
- [ ] Create runbooks for common issues
- [ ] Document environment variables
- [ ] Create architecture diagrams

## Scaling

### Horizontal Scaling

**Add more API instances:**

```bash
# Docker Compose
docker-compose -f docker-compose.prod.yml up -d --scale api=5

# Kubernetes
kubectl scale deployment zakera-api --replicas=5 -n zakera
```

### Vertical Scaling

**Increase resources:**

```yaml
# docker-compose.prod.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

### Database Scaling

1. **Read replicas:**

```python
# Configure in settings
DATABASE_REPLICA_URLS = [
    "postgresql://user:pass@replica1:5432/zakera",
    "postgresql://user:pass@replica2:5432/zakera",
]
```

2. **Connection pooling:**

```python
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 40
```

## Backup and Recovery

### Automated Backups

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec -T db pg_dump -U zakera_user zakera \
  | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Data directory backup
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" ./data

# Upload to S3
aws s3 cp "$BACKUP_DIR/" s3://your-bucket/backups/ --recursive

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
```

### Recovery

```bash
# Restore database
gunzip < backup.sql.gz | \
  docker-compose exec -T db psql -U zakera_user zakera

# Restore data
tar -xzf data_backup.tar.gz -C ./
```

## SSL/TLS Configuration

### Using Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## Troubleshooting

See [monitoring.md](monitoring.md) for detailed troubleshooting guides.
