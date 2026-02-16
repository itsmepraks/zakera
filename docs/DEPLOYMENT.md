# Production Deployment Guide

## 📖 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [AWS Deployment with Terraform](#aws-deployment-with-terraform)
6. [Docker Compose Deployment](#docker-compose-deployment)
7. [Helm Deployment](#helm-deployment)
8. [CI/CD Setup](#cicd-setup)
9. [Monitoring and Observability](#monitoring-and-observability)
10. [Scaling and Performance](#scaling-and-performance)
11. [Security Hardening](#security-hardening)
12. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
13. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers deploying Zakera to production environments with high availability, scalability, and security.

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Internet                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Load Balancer / Ingress (SSL Termination)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Zakera API (3-10 replicas)                       │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                   │
│  │ Pod1 │  │ Pod2 │  │ Pod3 │  │ ...  │                   │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘                   │
└─────┼────────┼────────┼────────┼──────────────────────────┘
      │        │        │        │
      ▼        ▼        ▼        ▼
┌──────────────────────────────────────────────────┐
│              PostgreSQL (Primary + Standby)      │
└──────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────┐
│              Redis (Cache + Session)             │
└──────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────┐
│      Monitoring (Prometheus + Grafana)           │
└──────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Tools

```bash
# Container runtime
docker --version  # >= 20.10
docker-compose --version  # >= 2.0

# Kubernetes
kubectl version  # >= 1.25
helm version  # >= 3.10

# Cloud providers (choose one)
aws --version  # For AWS
gcloud --version  # For GCP
az --version  # For Azure

# Infrastructure as Code
terraform --version  # >= 1.0
```

### Required Accounts

- Cloud provider account (AWS/GCP/Azure)
- Container registry (Docker Hub, GitHub Container Registry, ECR)
- Domain name and DNS access
- LLM API keys (OpenAI, Anthropic, etc.)

---

## Deployment Options

### Option 1: Kubernetes (Recommended for Production)
- **Best for**: Large scale, high availability
- **Pros**: Auto-scaling, self-healing, declarative
- **Cons**: Complex setup, learning curve

### Option 2: AWS with Terraform
- **Best for**: Enterprise, AWS-native
- **Pros**: Fully managed, automated, scalable
- **Cons**: AWS-specific, costs

### Option 3: Docker Compose
- **Best for**: Small to medium deployments
- **Pros**: Simple, portable, cost-effective
- **Cons**: Limited scaling, manual management

### Option 4: Helm
- **Best for**: Kubernetes with easy config
- **Pros**: Package management, templating, versioning
- **Cons**: Requires Kubernetes knowledge

---

## Kubernetes Deployment

### Step 1: Prepare Configuration

```bash
# Clone repository\ngit clone https://github.com/itsmepraks/zakera.git\ncd zakera\n\n# Create secrets file\ncp kubernetes/secrets.yaml.template kubernetes/secrets.yaml\n\n# Edit secrets (use base64 encoding)\nvim kubernetes/secrets.yaml\n```

**Generate secrets**:
```bash\n# Generate SECRET_KEY\npython -c \"import secrets; print(secrets.token_urlsafe(32))\"\n\n# Base64 encode\necho -n \"your-secret-value\" | base64\n```

### Step 2: Deploy with Script

```bash
# Make script executable\nchmod +x scripts/deploy.sh\n\n# Run deployment\n./scripts/deploy.sh production\n```

**Manual deployment**:
```bash
# Create namespace\nkubectl apply -f kubernetes/namespace.yaml\n\n# Create secrets and configs\nkubectl apply -f kubernetes/secrets.yaml\nkubectl apply -f kubernetes/configmap.yaml\n\n# Deploy storage\nkubectl apply -f kubernetes/pvc.yaml\n\n# Deploy database\nkubectl apply -f kubernetes/postgres.yaml\nkubectl apply -f kubernetes/redis.yaml\n\n# Deploy application\nkubectl apply -f kubernetes/serviceaccount.yaml\nkubectl apply -f kubernetes/deployment.yaml\nkubectl apply -f kubernetes/service.yaml\n\n# Configure scaling\nkubectl apply -f kubernetes/hpa.yaml\n\n# Configure networking\nkubectl apply -f kubernetes/ingress.yaml\nkubectl apply -f kubernetes/networkpolicy.yaml\nkubectl apply -f kubernetes/poddisruptionbudget.yaml\n\n# Deploy monitoring\nkubectl apply -f kubernetes/monitoring-stack.yaml\n```\n\n### Step 3: Verify Deployment\n\n```bash\n# Check pods\nkubectl get pods -n zakera\n\n# Check services\nkubectl get svc -n zakera\n\n# Check ingress\nkubectl get ingress -n zakera\n\n# View logs\nkubectl logs -f deployment/zakera-api -n zakera\n\n# Test health\nkubectl exec -it deployment/zakera-api -n zakera -- \\\n  curl http://localhost:8000/api/v1/monitoring/health\n```\n\n### Step 4: Configure DNS\n\n```bash\n# Get load balancer IP/hostname\nkubectl get svc zakera-api -n zakera\n\n# Add DNS A record:\n# api.zakera.io → LOAD_BALANCER_IP\n```\n\n### Step 5: Configure SSL\n\n```bash\n# Install cert-manager\nkubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml\n\n# Create ClusterIssuer for Let's Encrypt\ncat <<EOF | kubectl apply -f -\napiVersion: cert-manager.io/v1\nkind: ClusterIssuer\nmetadata:\n  name: letsencrypt-prod\nspec:\n  acme:\n    server: https://acme-v02.api.letsencrypt.org/directory\n    email: admin@zakera.io\n    privateKeySecretRef:\n      name: letsencrypt-prod\n    solvers:\n    - http01:\n        ingress:\n          class: nginx\nEOF\n\n# Certificate will be automatically provisioned\n```

---

## AWS Deployment with Terraform

### Step 1: Configure AWS

```bash\n# Configure AWS CLI\naws configure\n# Enter: Access Key, Secret Key, Region, Output format\n\n# Create S3 bucket for Terraform state\naws s3 mb s3://zakera-terraform-state\n\n# Create DynamoDB table for locking\naws dynamodb create-table \\\n  --table-name zakera-terraform-locks \\\n  --attribute-definitions AttributeName=LockID,AttributeType=S \\\n  --key-schema AttributeName=LockID,KeyType=HASH \\\n  --billing-mode PAY_PER_REQUEST\n```\n\n### Step 2: Initialize Terraform\n\n```bash\ncd terraform\n\n# Initialize\nterraform init\n\n# Review plan\nterraform plan -out=tfplan\n\n# Apply (creates VPC, EKS, RDS, etc.)\nterraform apply tfplan\n```\n\n### Step 3: Configure kubectl\n\n```bash\n# Update kubeconfig\naws eks update-kubeconfig --name zakera-production --region us-east-1\n\n# Verify connection\nkubectl get nodes\n```\n\n### Step 4: Deploy Application\n\n```bash\n# Return to root directory\ncd ..\n\n# Run deployment script\n./scripts/deploy.sh production\n```\n\n### Infrastructure Created:\n\n- ✅ VPC with public/private subnets\n- ✅ EKS cluster with managed node groups\n- ✅ RDS PostgreSQL (multi-AZ)\n- ✅ ElastiCache Redis\n- ✅ S3 buckets (data, backups, logs)\n- ✅ CloudWatch monitoring\n- ✅ SNS alerts\n- ✅ Security groups\n- ✅ IAM roles and policies\n\n---\n\n## Docker Compose Deployment\n\n### For Production\n\n```bash\n# Create environment file\ncp .env.example .env\nvim .env  # Configure all settings\n\n# Set passwords\nexport DB_PASSWORD=$(openssl rand -base64 32)\nexport SECRET_KEY=$(python -c \"import secrets; print(secrets.token_urlsafe(32))\")\n\n# Deploy\ndocker-compose -f docker-compose.production.yml up -d\n\n# Check status\ndocker-compose -f docker-compose.production.yml ps\n\n# View logs\ndocker-compose -f docker-compose.production.yml logs -f api\n\n# Initialize database\ndocker-compose -f docker-compose.production.yml exec api \\\n  alembic upgrade head\n\n# Create admin user\ndocker-compose -f docker-compose.production.yml exec api \\\n  python scripts/init_security.py\n```\n\n---\n\n## Helm Deployment\n\n### Step 1: Add Helm Repository (if published)\n\n```bash\nhelm repo add zakera https://charts.zakera.io\nhelm repo update\n```\n\n### Step 2: Install with Helm\n\n```bash\n# Install from local chart\nhelm install zakera ./helm/zakera \\\n  --namespace zakera \\\n  --create-namespace \\\n  --values helm/zakera/values.yaml \\\n  --set postgresql.auth.password=YOUR_DB_PASSWORD \\\n  --set redis.auth.password=YOUR_REDIS_PASSWORD\n\n# Or install from repository\nhelm install zakera zakera/zakera \\\n  --namespace zakera \\\n  --create-namespace\n```\n\n### Step 3: Customize Values\n\n```yaml\n# custom-values.yaml\nreplicaCount: 5\n\nimage:\n  tag: \"v0.6.0\"\n\nresources:\n  limits:\n    cpu: 4000m\n    memory: 4Gi\n  requests:\n    cpu: 1000m\n    memory: 1Gi\n\nautoscaling:\n  minReplicas: 3\n  maxReplicas: 20\n\ningress:\n  hosts:\n    - host: api.yourdomain.com\n  tls:\n    - secretName: your-tls-secret\n```\n\n```bash\n# Deploy with custom values\nhelm install zakera ./helm/zakera -f custom-values.yaml\n```\n\n### Step 4: Upgrade\n\n```bash\n# Upgrade deployment\nhelm upgrade zakera ./helm/zakera -f custom-values.yaml\n\n# Rollback if needed\nhelm rollback zakera 1\n```\n\n---\n\n## CI/CD Setup\n\n### GitHub Actions\n\n**Automatic triggers**:\n- Push to `main` → Deploy to production\n- Push to `develop` → Deploy to staging\n- Create tag `v*` → Create release and deploy\n\n**Required Secrets**:\n```bash\n# GitHub repository settings → Secrets\nAWS_ACCESS_KEY_ID\nAWS_SECRET_ACCESS_KEY\nDOCKER_USERNAME\nDOCKER_PASSWORD\nOPENAI_API_KEY\nANTHROPIC_API_KEY\n```\n\n**Workflow files**:\n- `.github/workflows/ci.yaml` - CI pipeline\n- `.github/workflows/cd.yaml` - CD pipeline\n\n### Manual Deploy\n\n```bash\n# Build and push image\ndocker build -f Dockerfile.production -t zakera:v0.6.0 .\ndocker tag zakera:v0.6.0 ghcr.io/itsmepraks/zakera:v0.6.0\ndocker push ghcr.io/itsmepraks/zakera:v0.6.0\n\n# Deploy to Kubernetes\nkubectl set image deployment/zakera-api \\\n  zakera=ghcr.io/itsmepraks/zakera:v0.6.0 \\\n  -n zakera\n\n# Watch rollout\nkubectl rollout status deployment/zakera-api -n zakera\n```\n\n---\n\n## Monitoring and Observability\n\n### Access Monitoring\n\n```bash\n# Port forward Prometheus\nkubectl port-forward svc/prometheus 9090:9090 -n zakera\n# Access: http://localhost:9090\n\n# Port forward Grafana\nkubectl port-forward svc/grafana 3000:80 -n zakera\n# Access: http://localhost:3000\n```\n\n### Key Metrics to Monitor\n\n**Application**:\n- Request rate and latency\n- Error rates (4xx, 5xx)\n- Active connections\n- Memory usage\n\n**Database**:\n- Connection pool usage\n- Query performance\n- Replication lag\n- Storage usage\n\n**Infrastructure**:\n- CPU and memory utilization\n- Network I/O\n- Disk I/O\n- Pod restarts\n\n### Alerts Configuration\n\n**Critical Alerts**:\n- API down (no healthy pods)\n- Database connection failure\n- High error rate (>5%)\n- Memory exhaustion (>90%)\n\n**Warning Alerts**:\n- High latency (p95 > 2s)\n- High CPU (>70%)\n- Scaling events\n- Certificate expiring\n\n---\n\n## Scaling and Performance\n\n### Horizontal Pod Autoscaling\n\n**Automatic scaling** based on:\n- CPU utilization (target: 70%)\n- Memory utilization (target: 80%)\n- Custom metrics (requests per second)\n\n```bash\n# Check HPA status\nkubectl get hpa -n zakera\n\n# View scaling events\nkubectl describe hpa zakera-api-hpa -n zakera\n```\n\n### Manual Scaling\n\n```bash\n# Scale to specific replica count\nkubectl scale deployment/zakera-api --replicas=5 -n zakera\n\n# Scale node group (AWS)\neksctl scale nodegroup --cluster=zakera-production \\\n  --name=general --nodes=5 --nodes-min=3 --nodes-max=10\n```\n\n### Performance Tuning\n\n**Application**:\n```yaml\n# Increase workers\ncommand: [\"uvicorn\", \"src.api.main:app\", \"--workers\", \"8\"]\n\n# Increase resources\nresources:\n  limits:\n    cpu: 4000m\n    memory: 4Gi\n```\n\n**Database**:\n```sql\n-- Optimize connections\nALTER SYSTEM SET max_connections = 200;\nALTER SYSTEM SET shared_buffers = '2GB';\nALTER SYSTEM SET effective_cache_size = '6GB';\n```\n\n**Redis**:\n```bash\n# Increase memory\nmaxmemory 1gb\nmaxmemory-policy allkeys-lru\n```\n\n---\n\n## Security Hardening\n\n### Pre-Deployment Checklist\n\n- [x] Change all default passwords\n- [x] Generate strong SECRET_KEY (32+ chars)\n- [x] Enable HTTPS/TLS everywhere\n- [x] Configure network policies\n- [x] Enable audit logging\n- [x] Configure rate limiting\n- [x] Set up Web Application Firewall (WAF)\n- [x] Enable encryption at rest\n- [x] Configure backup encryption\n- [x] Set up security scanning\n- [x] Review RBAC permissions\n- [x] Enable MFA for admins\n\n### Security Best Practices\n\n**1. Secrets Management**\n```bash\n# Use external secrets operator\nkubectl apply -f https://raw.githubusercontent.com/external-secrets/external-secrets/main/deploy/crds/bundle.yaml\n\n# Or use sealed-secrets\nhelm install sealed-secrets sealed-secrets/sealed-secrets\n```\n\n**2. Network Security**\n```bash\n# Apply network policies\nkubectl apply -f kubernetes/networkpolicy.yaml\n\n# Verify policies\nkubectl get networkpolicies -n zakera\n```\n\n**3. Pod Security**\n```yaml\n# Enable Pod Security Standards\napiVersion: v1\nkind: Namespace\nmetadata:\n  name: zakera\n  labels:\n    pod-security.kubernetes.io/enforce: restricted\n    pod-security.kubernetes.io/audit: restricted\n    pod-security.kubernetes.io/warn: restricted\n```\n\n---\n\n## Backup and Disaster Recovery\n\n### Database Backups\n\n**Automated backups** (AWS RDS):\n```bash\n# Configured in Terraform\nbackup_retention_period = 7  # days\nbackup_window = \"03:00-04:00\"\n```\n\n**Manual backup**:\n```bash\n# PostgreSQL\nkubectl exec -it statefulset/zakera-postgres -n zakera -- \\\n  pg_dump -U zakera zakera > backup-$(date +%Y%m%d).sql\n\n# Upload to S3\naws s3 cp backup-$(date +%Y%m%d).sql \\\n  s3://zakera-production-backups/database/\n```\n\n### Application State Backup\n\n```bash\n# Backup PVCs\nkubectl get pvc -n zakera -o yaml > pvc-backup.yaml\n\n# Backup configs\nkubectl get configmap -n zakera -o yaml > configmap-backup.yaml\n\n# Backup secrets (encrypted)\nkubectl get secrets -n zakera -o yaml > secrets-backup.yaml.enc\n```\n\n### Disaster Recovery Procedure\n\n**RTO (Recovery Time Objective)**: < 1 hour  \n**RPO (Recovery Point Objective)**: < 15 minutes\n\n```bash\n# 1. Restore infrastructure\nterraform apply\n\n# 2. Restore database\npsql -U zakera -h DB_HOST < backup-latest.sql\n\n# 3. Deploy application\n./scripts/deploy.sh production\n\n# 4. Verify\ncurl https://api.zakera.io/api/v1/monitoring/health\n```\n\n---\n\n## Troubleshooting\n\n### Pod Crashes\n\n```bash\n# Check pod status\nkubectl get pods -n zakera\n\n# Describe pod\nkubectl describe pod <pod-name> -n zakera\n\n# View logs\nkubectl logs <pod-name> -n zakera --previous\n\n# Check events\nkubectl get events -n zakera --sort-by='.lastTimestamp'\n```\n\n### Database Connection Issues\n\n```bash\n# Test connectivity\nkubectl exec -it deployment/zakera-api -n zakera -- \\\n  psql postgresql://zakera:PASSWORD@zakera-postgres:5432/zakera\n\n# Check database logs\nkubectl logs statefulset/zakera-postgres -n zakera\n```\n\n### High Memory Usage\n\n```bash\n# Check resource usage\nkubectl top pods -n zakera\nkubectl top nodes\n\n# Increase limits\nkubectl set resources deployment/zakera-api \\\n  --limits=memory=4Gi -n zakera\n```\n\n### SSL Certificate Issues\n\n```bash\n# Check certificate\nkubectl describe certificate zakera-tls -n zakera\n\n# Check cert-manager logs\nkubectl logs -n cert-manager deployment/cert-manager\n\n# Manually trigger renewal\nkubectl delete certificate zakera-tls -n zakera\nkubectl apply -f kubernetes/ingress.yaml\n```\n\n---\n\n## Production Checklist\n\n### Pre-Deployment\n- [ ] Review and update all configurations\n- [ ] Generate secure secrets\n- [ ] Configure OAuth2 providers\n- [ ] Set up DNS records\n- [ ] Obtain SSL certificates\n- [ ] Configure monitoring alerts\n- [ ] Set up log aggregation\n- [ ] Plan backup strategy\n- [ ] Document runbooks\n- [ ] Test disaster recovery\n\n### Post-Deployment\n- [ ] Verify all pods are running\n- [ ] Test all API endpoints\n- [ ] Verify database connectivity\n- [ ] Check monitoring dashboards\n- [ ] Test alert notifications\n- [ ] Verify SSL certificates\n- [ ] Run load tests\n- [ ] Check autoscaling\n- [ ] Review security scans\n- [ ] Update documentation\n\n### Ongoing Maintenance\n- [ ] Monitor metrics daily\n- [ ] Review logs weekly\n- [ ] Update dependencies monthly\n- [ ] Rotate secrets quarterly\n- [ ] Review access logs\n- [ ] Test backups monthly\n- [ ] Update runbooks\n- [ ] Security audits quarterly\n\n---\n\n## Cost Optimization\n\n### AWS Cost Estimates\n\n| Component | Configuration | Monthly Cost |\n|-----------|---------------|-------------|\n| EKS Cluster | 1 cluster | $73 |\n| EC2 Nodes | 3x t3.medium | $100 |\n| RDS PostgreSQL | db.t3.medium, multi-AZ | $120 |\n| ElastiCache | cache.t3.micro | $15 |\n| Load Balancer | NLB | $20 |\n| Data Transfer | ~100GB | $10 |\n| **Total** | | **~$338/month** |\n\n### Cost Optimization Tips\n\n1. **Use Spot Instances**: 50-70% savings on compute\n2. **Right-size resources**: Monitor and adjust\n3. **Use S3 Lifecycle**: Archive old data to Glacier\n4. **Reserved Instances**: Save 30-60% on long-term\n5. **Enable autoscaling**: Scale down during low traffic\n\n---\n\n## Quick Reference\n\n### Common Commands\n\n```bash\n# Deploy\n./scripts/deploy.sh production\n\n# Rollback\n./scripts/rollback.sh production\n\n# Scale\nkubectl scale deployment/zakera-api --replicas=5 -n zakera\n\n# Update image\nkubectl set image deployment/zakera-api \\\n  zakera=ghcr.io/itsmepraks/zakera:v0.6.1 -n zakera\n\n# View logs\nkubectl logs -f deployment/zakera-api -n zakera\n\n# Execute command in pod\nkubectl exec -it deployment/zakera-api -n zakera -- bash\n\n# Port forward\nkubectl port-forward svc/zakera-api 8000:8000 -n zakera\n```\n\n---\n\n**Version**: 1.0.0  \n**Last Updated**: February 2026  \n**Status**: Production Ready 🚀\n