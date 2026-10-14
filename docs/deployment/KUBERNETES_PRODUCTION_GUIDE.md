# Kubernetes Production Deployment Guide

> [!WARNING]
> **Legacy and unsupported.** This guide has not been validated, the associated delivery workflows were removed, and Kubernetes is not part of the Zakera vNext core project.

## 🎯 Overview

Complete guide for deploying Zakera AI Chat Agent to production Kubernetes clusters with enterprise-grade features including auto-scaling, service mesh, comprehensive monitoring, and security hardening.

## ✨ Features

- ✅ **High Availability** - 3+ replicas with pod anti-affinity
- ✅ **Auto-Scaling** - HPA with CPU, memory, and custom metrics
- ✅ **Service Mesh** - Istio integration for traffic management
- ✅ **TLS/SSL** - Automatic certificate management with Let's Encrypt
- ✅ **Monitoring** - Prometheus, Grafana, Alertmanager
- ✅ **Security** - RBAC, Network Policies, Security Contexts
- ✅ **Persistence** - StatefulSets for Redis and PostgreSQL
- ✅ **CI/CD** - Multi-environment deployment pipeline
- ✅ **Observability** - Distributed tracing with Jaeger

## 📁 File Structure

```
kubernetes/production/
├── deployment.yaml           # Main API deployment with HPA and PDB
├── service-ingress.yaml      # Services, Ingress, TLS certificates
├── configmap-secrets.yaml    # Configuration and secrets
├── rbac-security.yaml        # RBAC, NetworkPolicy, Security
├── statefulsets.yaml         # Redis and PostgreSQL
└── README.md                 # This file

monitoring/
├── prometheus/
│   └── prometheus-config.yaml   # Prometheus with alert rules
└── grafana/
    └── dashboards/
        └── zakera-production-dashboard.json  # Grafana dashboard

scripts/
├── deploy-kubernetes.sh      # Deployment automation
├── setup-monitoring.sh       # Monitoring setup
└── health-check.sh           # Health validation

.github/workflows/
└── ci-cd-multi-env.yml       # Multi-environment CI/CD
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install required tools
brew install kubernetes-cli helm

# Configure kubectl context
kubectl config use-context production-cluster

# Verify connection
kubectl cluster-info
```

### 1. Deploy Infrastructure

```bash
# Apply all Kubernetes manifests
kubectl apply -f kubernetes/production/

# Verify deployment
kubectl get all -n zakera-production
```

### 2. Setup Monitoring

```bash
# Install Prometheus and Grafana
./scripts/setup-monitoring.sh

# Access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80
# Open: http://localhost:3000
```

### 3. Run Health Check

```bash
# Comprehensive health check
./scripts/health-check.sh production --detailed

# JSON output for automation
./scripts/health-check.sh production --json
```

## 📋 Detailed Setup

### Step 1: Create Namespace

```bash
kubectl create namespace zakera-production
kubectl label namespace zakera-production \
  environment=production \
  istio-injection=enabled
```

### Step 2: Configure Secrets

```bash
# Create secrets (use proper secret management in production)
kubectl create secret generic zakera-secrets \
  --from-literal=DATABASE_URL="postgresql://user:pass@host:5432/db" \
  --from-literal=JWT_SECRET_KEY="your-secure-jwt-secret" \
  --from-literal=OPENAI_API_KEY="sk-your-key" \
  --from-literal=REDIS_PASSWORD="your-redis-password" \
  -n zakera-production

# For production, use external secret management:
# - AWS Secrets Manager
# - HashiCorp Vault
# - Google Secret Manager
# - Azure Key Vault
```

### Step 3: Deploy Database and Cache

```bash
# Apply StatefulSets for PostgreSQL and Redis
kubectl apply -f kubernetes/production/statefulsets.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod \
  -l app=postgres \
  -n zakera-production \
  --timeout=300s

kubectl wait --for=condition=ready pod \
  -l app=redis \
  -n zakera-production \
  --timeout=300s
```

### Step 4: Deploy Application

```bash
# Apply RBAC and security policies
kubectl apply -f kubernetes/production/rbac-security.yaml

# Apply configuration
kubectl apply -f kubernetes/production/configmap-secrets.yaml

# Deploy application
kubectl apply -f kubernetes/production/deployment.yaml

# Monitor rollout
kubectl rollout status deployment/zakera-api -n zakera-production
```

### Step 5: Configure Networking

```bash
# Apply services and ingress
kubectl apply -f kubernetes/production/service-ingress.yaml

# Verify ingress
kubectl get ingress -n zakera-production
kubectl describe ingress zakera-ingress -n zakera-production
```

### Step 6: Verify Deployment

```bash
# Check all resources
kubectl get all -n zakera-production

# Check pod logs
kubectl logs -f deployment/zakera-api -n zakera-production

# Run health check
./scripts/health-check.sh production --detailed
```

## 🔧 Configuration

### ConfigMap Settings

**Application Configuration:**
- Workers: 4 (adjust based on load)
- Log Level: INFO (DEBUG for troubleshooting)
- Resource limits: See deployment.yaml

**Monitoring:**
- Metrics enabled: true
- Tracing enabled: true
- Prometheus scraping: enabled

**Cache:**
- Redis persistence: enabled
- TTL settings: configurable
- Max memory: 1.5GB with LRU eviction

### Secret Management

**Required Secrets:**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - JWT signing key
- `REDIS_PASSWORD` - Redis authentication
- AI Provider API Keys (OpenAI, Anthropic, etc.)
- Alerting credentials (email, Slack, Discord)

**Best Practices:**
```bash
# Use external secret management
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: zakera-secrets
  namespace: zakera-production
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: zakera-secrets
  data:
  - secretKey: DATABASE_URL
    remoteRef:
      key: zakera/prod/database-url
EOF
```

## 📊 Horizontal Pod Autoscaling

### HPA Configuration

**Metrics:**
- CPU: Scale at 70% utilization
- Memory: Scale at 80% utilization
- Custom: HTTP requests per second

**Scaling Behavior:**
- Min replicas: 3
- Max replicas: 20
- Scale up: Fast (100% increase per 30s)
- Scale down: Conservative (50% decrease per 60s)

**Testing HPA:**
```bash
# Generate load
kubectl run -i --tty load-generator \
  --rm --image=busybox \
  --restart=Never \
  -- /bin/sh -c "while sleep 0.01; do wget -q -O- http://zakera-api-service; done"

# Watch HPA
kubectl get hpa zakera-api-hpa -n zakera-production --watch
```

## 🔒 Security Features

### RBAC Configuration

**ServiceAccount:**
- Minimal permissions
- ConfigMap read access
- Secret read access
- Pod information for monitoring

**No permissions for:**
- Creating/deleting resources
- Cluster-wide operations
- Privileged operations

### Network Policies

**Ingress allowed from:**
- Ingress controller
- Monitoring namespace (Prometheus)
- Same namespace pods

**Egress allowed to:**
- DNS (kube-system)
- PostgreSQL
- Redis
- External APIs (HTTPS)
- Jaeger tracing

**Blocked by default:**
- All other traffic

### Pod Security

**Security Contexts:**
- Run as non-root (UID 1000)
- Read-only root filesystem
- Drop all capabilities
- No privilege escalation
- Seccomp profile: RuntimeDefault

### Resource Quotas

**Namespace limits:**
- CPU: 100 cores max
- Memory: 200Gi max
- Pods: 100 max
- PVCs: 10 max
- LoadBalancers: 2 max

## 📈 Monitoring Setup

### Prometheus Configuration

**Scrape jobs:**
- Kubernetes API server
- Kubernetes nodes
- Zakera API pods (every 30s)
- Redis metrics
- PostgreSQL metrics
- Nginx ingress

**Alert rules:**
- High error rate (>5%)
- High API latency (>5s P95)
- Pod restarts
- High memory usage (>90%)
- High CPU usage (>90%)
- Redis/PostgreSQL down
- Low cache hit rate (<60%)
- Model provider errors

### Grafana Dashboards

**Production Dashboard includes:**
- API request rate by endpoint
- Error rate with alerting
- Response time percentiles (P95, P99)
- Active pod count
- Memory and CPU usage
- Redis cache hit rate gauge
- AI model usage distribution
- Database connections
- Token usage and cost tracking
- Auto-refresh every 30s

**Access Grafana:**
```bash
kubectl port-forward -n monitoring svc/grafana 3000:80

# Username: admin
# Password: (from setup-monitoring.sh output)
```

## 🚨 Alerting

### Alert Channels

**Email:**
```yaml
ALERT_EMAIL_SMTP_HOST: smtp.gmail.com
ALERT_EMAIL_TO: admin@zakera.ai
```

**Slack:**
```yaml
ALERT_SLACK_WEBHOOK_URL: https://hooks.slack.com/services/YOUR/WEBHOOK
```

**Discord:**
```yaml
ALERT_DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/YOUR/WEBHOOK
```

### Alert Rules

**Critical Alerts:**
- API error rate > 10%
- Database/Redis down
- All pods down
- Disk space > 90%

**Warning Alerts:**
- API error rate > 5%
- High latency > 5s
- Memory usage > 90%
- Cache hit rate < 60%

## 🔄 CI/CD Pipeline

### Workflow Stages

**1. Build and Test**
- Lint checking (Black, Flake8, isort)
- Multi-version testing (Python 3.9-3.12)
- Code coverage analysis
- Security scanning (Bandit, Safety, CodeQL, Trivy)

**2. Build Image**
- Multi-platform build (amd64, arm64)
- Push to GitHub Container Registry
- Vulnerability scanning
- Tag with version and SHA

**3. Deploy Development**
- Automatic on develop branch
- Smoke tests

**4. Deploy Staging**
- Automatic on main branch
- Integration tests
- Performance tests

**5. Deploy Production**
- Manual approval required
- Database backup
- Rollout with monitoring
- Smoke tests
- Slack notifications
- GitHub Release creation

### Triggering Deployments

```bash
# Automatic (push to main)
git push origin main

# Manual (workflow dispatch)
gh workflow run ci-cd-multi-env.yml \
  -f environment=production

# Tag-based release
git tag v1.0.0
git push origin v1.0.0
```

## 🛠️ Operations

### Scaling

```bash
# Manual scaling
kubectl scale deployment/zakera-api --replicas=10 -n zakera-production

# View HPA status
kubectl get hpa -n zakera-production

# Describe HPA
kubectl describe hpa zakera-api-hpa -n zakera-production
```

### Updating

```bash
# Update image
kubectl set image deployment/zakera-api \
  api=ghcr.io/itsmepraks/zakera:v1.1.0 \
  -n zakera-production

# Monitor rollout
kubectl rollout status deployment/zakera-api -n zakera-production

# View rollout history
kubectl rollout history deployment/zakera-api -n zakera-production
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/zakera-api -n zakera-production

# Rollback to specific revision
kubectl rollout undo deployment/zakera-api \
  --to-revision=2 \
  -n zakera-production

# Or use automation script
./scripts/deploy-kubernetes.sh production --rollback
```

### Debugging

```bash
# View logs
kubectl logs -f deployment/zakera-api -n zakera-production

# View logs from all pods
kubectl logs -f -l app=zakera,component=api -n zakera-production

# Exec into pod
kubectl exec -it deployment/zakera-api -n zakera-production -- /bin/bash

# View recent events
kubectl get events -n zakera-production --sort-by='.lastTimestamp'

# Describe deployment
kubectl describe deployment zakera-api -n zakera-production
```

## 🔍 Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n zakera-production

# Describe pod
kubectl describe pod <pod-name> -n zakera-production

# Check logs
kubectl logs <pod-name> -n zakera-production

# Common issues:
# - ImagePullBackOff: Check image name and registry access
# - CrashLoopBackOff: Check application logs and health probes
# - Pending: Check resource availability and node selectors
```

### Service Not Accessible

```bash
# Check service
kubectl get service zakera-api-service -n zakera-production

# Check endpoints
kubectl get endpoints zakera-api-service -n zakera-production

# Test from within cluster
kubectl run test-pod --rm -i --tty --image=busybox -- \
  wget -O- http://zakera-api-service.zakera-production

# Check ingress
kubectl describe ingress zakera-ingress -n zakera-production
```

### High Memory Usage

```bash
# Check current usage
kubectl top pods -n zakera-production

# View memory metrics
kubectl describe pod <pod-name> -n zakera-production | grep -A 5 "Limits:"

# Adjust limits in deployment.yaml and reapply
```

### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -l app=postgres -n zakera-production

# Test connection
kubectl exec -it deployment/zakera-api -n zakera-production -- \
  python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"

# Check PostgreSQL logs
kubectl logs -l app=postgres -n zakera-production
```

## 🎯 Best Practices

### Resource Management

1. **Set appropriate limits and requests**
   - Start conservative, scale based on metrics
   - Monitor actual usage with Prometheus
   - Adjust based on traffic patterns

2. **Use HPA wisely**
   - Don't scale too aggressively
   - Set reasonable min/max replicas
   - Use stabilization windows

3. **Monitor resource quotas**
   - Ensure namespace has sufficient quota
   - Plan for peak traffic

### Security

1. **Always use RBAC**
   - Minimal permissions
   - Service accounts for all pods
   - Regular audit

2. **Enable Network Policies**
   - Default deny all traffic
   - Explicit allow rules
   - Regular review

3. **Use Security Contexts**
   - Run as non-root
   - Read-only filesystem
   - Drop all capabilities

4. **Secret Management**
   - Use external secret stores
   - Rotate secrets regularly
   - Never commit secrets to git

### Monitoring

1. **Set up alerts**
   - Critical: Immediate action needed
   - Warning: Monitor closely
   - Info: Awareness

2. **Create custom dashboards**
   - Application-specific metrics
   - Business metrics
   - Cost tracking

3. **Log aggregation**
   - Centralized logging (ELK, Loki)
   - Structured logs
   - Log retention policy

## 📊 Capacity Planning

### Estimating Resources

**Per Pod:**
- CPU: 500m request, 2000m limit
- Memory: 512Mi request, 2Gi limit

**For 1000 concurrent users:**
- Estimated pods: 5-10
- Total CPU: 2.5-5 cores
- Total Memory: 2.5-5Gi

**Database:**
- Storage: 50Gi (grows with data)
- CPU: 500m-2 cores
- Memory: 1-4Gi

**Redis:**
- Storage: 10Gi per replica
- Memory: 512Mi-2Gi per replica
- Replicas: 3 for HA

### Scaling Recommendations

| Users | Pods | CPU (cores) | Memory (GiB) |
|-------|------|-------------|--------------|
| 100 | 3 | 1.5 | 1.5 |
| 1,000 | 5-10 | 2.5-5 | 2.5-5 |
| 10,000 | 20-40 | 10-20 | 10-20 |
| 100,000 | 50-100 | 25-50 | 25-50 |

## 🔐 Security Hardening

### 1. Enable Pod Security Standards

```bash
kubectl label namespace zakera-production \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### 2. Enable Network Policies

All network policies are defined in `rbac-security.yaml`:
- Default deny all traffic
- Explicit allow rules for required communication
- Separate ingress and egress policies

### 3. Scan for Vulnerabilities

```bash
# Scan images with Trivy
trivy image ghcr.io/itsmepraks/zakera:latest

# Scan Kubernetes manifests
trivy config kubernetes/production/

# Automated scanning in CI/CD
```

### 4. Implement Pod Security Contexts

All pods run with:
- Non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- Dropped capabilities

## 📞 Support

### Useful Commands

```bash
# View all resources
kubectl get all -n zakera-production

# Check HPA status
kubectl get hpa -n zakera-production

# View events
kubectl get events -n zakera-production --sort-by='.lastTimestamp'

# Export logs
kubectl logs -l app=zakera -n zakera-production --tail=1000 > zakera-logs.txt

# Port forward to service
kubectl port-forward svc/zakera-api-service 8000:80 -n zakera-production
```

### Emergency Procedures

**Complete Outage:**
1. Check pod status: `kubectl get pods -n zakera-production`
2. View recent events: `kubectl get events -n zakera-production`
3. Check logs: `kubectl logs -l app=zakera -n zakera-production`
4. Rollback if needed: `kubectl rollout undo deployment/zakera-api -n zakera-production`

**Database Issues:**
1. Check PostgreSQL pod: `kubectl get pods -l app=postgres -n zakera-production`
2. View logs: `kubectl logs -l app=postgres -n zakera-production`
3. Restore from backup if needed

**High Load:**
1. Check HPA: `kubectl get hpa -n zakera-production`
2. Manual scale if needed: `kubectl scale deployment/zakera-api --replicas=20 -n zakera-production`
3. Monitor metrics in Grafana

## 📚 Additional Resources

- **Kubernetes Docs:** https://kubernetes.io/docs/
- **Helm Charts:** `/helm/zakera/`
- **Monitoring Guide:** `/docs/MONITORING.md`
- **Security Guide:** `/docs/SECURITY.md`

---

**Version:** 1.0.0  
**Last Updated:** March 8, 2026  
**Status:** Production Ready
