# Zakera AI Chat Agent - Complete Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Methods](#deployment-methods)
5. [Security Best Practices](#security-best-practices)
6. [Monitoring and Health Checks](#monitoring-and-health-checks)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

## Overview

This guide provides comprehensive instructions for deploying Zakera AI Chat Agent in production environments. Whether you're deploying to Docker, Kubernetes, or cloud platforms like AWS, GCP, or Azure, this guide has you covered.

### Architecture Overview

```
┌─────────────────┐
│   Load Balancer │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Nginx  │
    └────┬────┘
         │
┌────────▼────────┐
│  Zakera API     │
│  (FastAPI)      │
└────────┬────────┘
         │
    ┌────▼────┐
    │   DB    │
    │ (SQLite)│
    └─────────┘
```

## Prerequisites

### Required Software

- **Docker**: v20.10+ (for containerized deployment)
- **Docker Compose**: v2.0+ (for local multi-container setup)
- **Kubernetes**: v1.24+ (for K8s deployment)
- **Python**: v3.9+ (for local development)
- **Node.js**: v18+ (for frontend development)

### Required Accounts & API Keys

- OpenAI API Key (optional but recommended)
- Anthropic API Key (optional)
- Google Cloud API Key for Gemini (optional)
- xAI API Key for Grok (optional)
- Domain name (for production deployment)
- SSL Certificate (Let's Encrypt recommended)

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ===========================================
# APPLICATION CONFIGURATION
# ===========================================
APP_NAME=zakera
ENVIRONMENT=production  # development, staging, production
DEBUG=false
LOG_LEVEL=INFO

# ===========================================
# API CONFIGURATION
# ===========================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false

# CORS Configuration
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# ===========================================
# DATABASE CONFIGURATION
# ===========================================
DATABASE_URL=sqlite:///./zakera.db
# For PostgreSQL (recommended for production):
# DATABASE_URL=postgresql://user:password@localhost/zakera

# ===========================================
# AI MODEL PROVIDERS
# ===========================================

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4096

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-opus-20240229

# Google Gemini
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-pro

# xAI Grok
XAI_API_KEY=xai-...
XAI_MODEL=grok-2-latest

# Groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=mixtral-8x7b-32768

# Cohere
COHERE_API_KEY=...
COHERE_MODEL=command

# Mistral
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-large-latest

# DeepSeek
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-chat

# ===========================================
# SECURITY CONFIGURATION
# ===========================================

# JWT Authentication
SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# ===========================================
# MONITORING & OBSERVABILITY
# ===========================================

# OpenTelemetry (Jaeger)
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=zakera-api

# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Sentry (Error Tracking)
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production

# ===========================================
# EMAIL CONFIGURATION (for alerts)
# ===========================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com
ALERT_EMAIL=alerts@yourdomain.com

# ===========================================
# CACHING
# ===========================================
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# ===========================================
# FRONTEND CONFIGURATION
# ===========================================
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com/ws
```

### Environment Templates

We provide templates for different environments:

- `.env.development` - Local development
- `.env.staging` - Staging environment
- `.env.production` - Production environment

Copy the appropriate template and customize for your needs:

```bash
cp .env.example .env.production
# Edit .env.production with your values
```

## Deployment Methods

### Method 1: Docker Compose (Recommended for Getting Started)

**Best for**: Development, small deployments, testing

```bash
# 1. Clone the repository
git clone https://github.com/itsmepraks/zakera.git
cd zakera

# 2. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 3. Build and start services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f zakera-api

# 6. Access the application
# API: http://localhost:8000
# Frontend: http://localhost:3000
# Jaeger: http://localhost:16686
# Grafana: http://localhost:3001
```

### Method 2: Kubernetes (Recommended for Production)

**Best for**: Production, high availability, auto-scaling

#### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### Deployment Steps

```bash
# 1. Create namespace
kubectl create namespace zakera

# 2. Create secrets
kubectl create secret generic zakera-secrets \
  --from-env-file=.env.production \
  -n zakera

# 3. Deploy using Helm
helm install zakera ./helm/zakera \
  --namespace zakera \
  --values helm/zakera/values-production.yaml

# 4. Check deployment status
kubectl get pods -n zakera
kubectl get services -n zakera

# 5. Get external IP (for LoadBalancer)
kubectl get svc zakera-nginx -n zakera
```

#### Scaling

```bash
# Horizontal Pod Autoscaling
kubectl autoscale deployment zakera-api \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n zakera

# Manual scaling
kubectl scale deployment zakera-api --replicas=5 -n zakera
```

### Method 3: Cloud Platforms

#### AWS ECS (Elastic Container Service)

```bash
# 1. Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 2. Configure AWS credentials
aws configure

# 3. Create ECR repository
aws ecr create-repository --repository-name zakera

# 4. Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t zakera .
docker tag zakera:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/zakera:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/zakera:latest

# 5. Deploy to ECS (use terraform/aws/ directory)
cd terraform/aws
terraform init
terraform plan
terraform apply
```

#### Google Cloud Run

```bash
# 1. Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# 2. Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/zakera
gcloud run deploy zakera \
  --image gcr.io/PROJECT_ID/zakera \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars-file .env.production
```

#### Azure Container Instances

```bash
# 1. Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. Login
az login

# 3. Create resource group
az group create --name zakera-rg --location eastus

# 4. Create container registry
az acr create --resource-group zakera-rg --name zakeraacr --sku Basic

# 5. Build and push
az acr build --registry zakeraacr --image zakera:latest .

# 6. Deploy
az container create \
  --resource-group zakera-rg \
  --name zakera \
  --image zakeraacr.azurecr.io/zakera:latest \
  --dns-name-label zakera-app \
  --ports 8000
```

## Security Best Practices

### 1. SSL/TLS Configuration

**Using Let's Encrypt with Certbot:**

```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (add to crontab)
0 0 * * * certbot renew --quiet
```

**Nginx SSL Configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. API Key Management

- **Never commit API keys to version control**
- Use environment variables or secrets management services
- Rotate keys regularly (every 90 days)
- Use different keys for dev/staging/production
- Implement key rotation without downtime

### 3. Database Security

```bash
# For PostgreSQL in production
# 1. Use strong passwords
# 2. Enable SSL connections
# 3. Restrict network access
# 4. Regular backups
# 5. Encryption at rest

# Example PostgreSQL SSL connection
DATABASE_URL=postgresql://user:pass@host:5432/zakera?sslmode=require
```

### 4. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Security groups (AWS)
# - Port 22: SSH (your IP only)
# - Port 80: HTTP (0.0.0.0/0)
# - Port 443: HTTPS (0.0.0.0/0)
```

## Monitoring and Health Checks

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check (includes dependencies)
curl http://localhost:8000/health/detailed

# Metrics endpoint (Prometheus format)
curl http://localhost:8000/metrics
```

### Setting Up Monitoring

**1. Prometheus + Grafana:**

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana: http://localhost:3001
# Default credentials: admin/admin

# Import Zakera dashboard
# Dashboard ID: available in monitoring/grafana/dashboards/
```

**2. Uptime Monitoring:**

- Use services like UptimeRobot, Pingdom, or StatusCake
- Monitor: `/health` endpoint every 1-5 minutes
- Set up alerts for downtime

**3. Log Aggregation:**

```bash
# Using ELK Stack (Elasticsearch, Logstash, Kibana)
docker-compose -f docker-compose.elk.yml up -d

# Or use cloud services:
# - AWS CloudWatch Logs
# - Google Cloud Logging
# - Azure Monitor
# - Datadog
# - New Relic
```

## Backup and Recovery

### Database Backup

```bash
# SQLite backup
cp zakera.db zakera.db.backup.$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
pg_dump -U username -d zakera > backup_$(date +%Y%m%d).sql

# Automated daily backups (crontab)
0 2 * * * /path/to/backup-script.sh
```

### Backup Script Example

```bash
#!/bin/bash
# backup-script.sh

BACKUP_DIR="/backups/zakera"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="zakera.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp $DB_FILE $BACKUP_DIR/zakera_$DATE.db

# Compress backup
gzip $BACKUP_DIR/zakera_$DATE.db

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/zakera_$DATE.db.gz s3://your-backup-bucket/

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.db.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Disaster Recovery Plan

1. **Recovery Time Objective (RTO)**: < 1 hour
2. **Recovery Point Objective (RPO)**: < 24 hours

**Recovery Steps:**

```bash
# 1. Restore from backup
gunzip zakera_20260304.db.gz
cp zakera_20260304.db zakera.db

# 2. Restart services
docker-compose restart

# 3. Verify functionality
curl http://localhost:8000/health

# 4. Check logs
docker-compose logs -f
```

## Troubleshooting

### Common Issues

#### Issue 1: API won't start

```bash
# Check logs
docker-compose logs zakera-api

# Common causes:
# - Port 8000 already in use
# - Invalid environment variables
# - Missing dependencies

# Solutions:
# 1. Change port in docker-compose.yml
# 2. Verify .env file
# 3. Rebuild containers: docker-compose build --no-cache
```

#### Issue 2: High memory usage

```bash
# Check container stats
docker stats

# Solutions:
# 1. Limit container memory in docker-compose.yml:
#    mem_limit: 2g
# 2. Increase swap space
# 3. Scale horizontally instead of vertically
```

#### Issue 3: Slow response times

```bash
# Check metrics
curl http://localhost:8000/metrics | grep response_time

# Solutions:
# 1. Enable caching (Redis)
# 2. Optimize database queries
# 3. Use CDN for static assets
# 4. Scale API workers
```

### Getting Help

- **Documentation**: https://github.com/itsmepraks/zakera/docs
- **Issues**: https://github.com/itsmepraks/zakera/issues
- **Discussions**: https://github.com/itsmepraks/zakera/discussions

## Performance Tuning

### API Workers

```bash
# Calculate optimal workers: (2 x CPU cores) + 1
# For 4 CPU cores: 9 workers
API_WORKERS=9

# With Docker Compose
docker-compose up -d --scale zakera-api=3
```

### Database Optimization

```sql
-- For PostgreSQL
-- 1. Add indexes
CREATE INDEX idx_conversation_user ON conversations(user_id);
CREATE INDEX idx_message_conversation ON messages(conversation_id);

-- 2. Vacuum regularly
VACUUM ANALYZE;

-- 3. Update statistics
ANALYZE;
```

### Caching Strategy

```python
# Redis caching for frequently accessed data
# - User preferences: TTL 1 hour
# - Model configurations: TTL 24 hours
# - Conversation summaries: TTL 30 minutes
```

## Next Steps

After successful deployment:

1. ✅ Set up monitoring and alerts
2. ✅ Configure automated backups
3. ✅ Enable SSL/TLS
4. ✅ Set up CI/CD pipeline
5. ✅ Implement log aggregation
6. ✅ Configure auto-scaling
7. ✅ Document runbooks for common issues
8. ✅ Set up staging environment
9. ✅ Implement blue-green deployment
10. ✅ Schedule regular security audits

---

**Last Updated**: March 2026  
**Version**: 1.0.0  
**Maintained by**: Prakriti Bista (@itsmepraks)
