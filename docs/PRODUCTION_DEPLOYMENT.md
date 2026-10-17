# Production Deployment Guide

> [!WARNING]
> **Legacy and unverified.** This is not a supported deployment guide. Zakera does not operate a hosted service, and the referenced deployment workflows and infrastructure have not been validated.

## Overview

This guide covers deploying Zakera AI Chat Agent to production Kubernetes clusters with high availability, autoscaling, and comprehensive monitoring.

## Prerequisites

### Required Tools

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Install helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install terraform
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### Cloud Provider Setup

#### AWS EKS

```bash
# Configure AWS CLI
aws configure

# Create EKS cluster
eksctl create cluster \
  --name zakera-prod \
  --version 1.28 \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed
```

#### GCP GKE

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create GKE cluster
gcloud container clusters create zakera-prod \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 10 \
  --enable-autorepair \
  --enable-autoupgrade
```

#### Azure AKS

```bash
# Login
az login

# Create resource group
az group create --name zakera-prod-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group zakera-prod-rg \
  --name zakera-prod \
  --node-count 3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10 \
  --node-vm-size Standard_D2s_v3 \
  --enable-addons monitoring
```

## Infrastructure Setup

### 1. Terraform Provisioning

```bash
cd terraform/

# Initialize
terraform init

# Plan
terraform plan -var-file="environments/production.tfvars"

# Apply
terraform apply -var-file="environments/production.tfvars"
```

### 2. Create Namespaces

```bash
kubectl create namespace zakera-production
kubectl create namespace zakera-staging
kubectl create namespace zakera-monitoring
```

### 3. Setup Secrets

```bash
# Database credentials
kubectl create secret generic zakera-db-secret \
  --from-literal=username=zakera \
  --from-literal=password=SECURE_PASSWORD \
  --from-literal=database=zakera_prod \
  -n zakera-production

# API keys
kubectl create secret generic zakera-api-keys \
  --from-literal=openai-api-key=sk-... \
  --from-literal=anthropic-api-key=sk-ant-... \
  --from-literal=gemini-api-key=... \
  -n zakera-production

# JWT secret
kubectl create secret generic zakera-jwt \
  --from-literal=secret-key=$(openssl rand -base64 32) \
  -n zakera-production
```

### 4. Deploy Supporting Services

```bash
# PostgreSQL
helm install zakera-postgres bitnami/postgresql \
  --namespace zakera-production \
  --set auth.existingSecret=zakera-db-secret \
  --set primary.persistence.size=50Gi \
  --set metrics.enabled=true

# Redis
helm install zakera-redis bitnami/redis \
  --namespace zakera-production \
  --set architecture=standalone \
  --set master.persistence.size=10Gi \
  --set metrics.enabled=true
```

## Application Deployment

### Using Helm (Recommended)

```bash
# Add helm repo
helm repo add zakera https://charts.zakera.ai
helm repo update

# Install
helm install zakera zakera/zakera \
  --namespace zakera-production \
  --values helm/values-production.yaml \
  --set image.tag=v1.0.0

# Upgrade
helm upgrade zakera zakera/zakera \
  --namespace zakera-production \
  --values helm/values-production.yaml \
  --set image.tag=v1.1.0
```

### Using Kubectl

```bash
# Apply configurations
kubectl apply -f kubernetes/base/
kubectl apply -f kubernetes/production/

# Apply autoscaling
kubectl apply -f kubernetes/autoscaling/

# Apply policies
kubectl apply -f kubernetes/policies/
```

## Deployment Strategies

### Blue-Green Deployment

```bash
# Deploy green version
kubectl apply -f kubernetes/deployments/zakera-api-green.yaml

# Wait for green to be ready
kubectl wait --for=condition=available \
  deployment/zakera-api-green \
  -n zakera-production \
  --timeout=300s

# Run smoke tests
./scripts/smoke-tests.sh green

# Switch traffic
kubectl patch service zakera-api \
  -n zakera-production \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Monitor for 15 minutes
sleep 900

# If successful, remove blue
kubectl delete deployment zakera-api-blue -n zakera-production
```

### Canary Deployment

```bash
# Deploy canary (10% traffic)
kubectl apply -f kubernetes/deployments/zakera-api-canary.yaml

# Monitor metrics
kubectl top pods -n zakera-production -l version=canary

# Check error rates
curl http://prometheus:9090/api/v1/query?query='rate(http_requests_total{status="500",version="canary"}[5m])'

# If stable, increase to 50%
kubectl scale deployment zakera-api-canary --replicas=5 -n zakera-production

# Monitor again
sleep 600

# If still stable, complete rollout
kubectl scale deployment zakera-api-stable --replicas=0 -n zakera-production
kubectl scale deployment zakera-api-canary --replicas=10 -n zakera-production
kubectl patch deployment zakera-api-canary \
  -n zakera-production \
  -p '{"metadata":{"labels":{"version":"stable"}}}'
```

## Database Migrations

### Pre-Deployment

```bash
# Backup database
kubectl exec -it zakera-postgres-0 -n zakera-production -- \
  pg_dump -U zakera zakera_prod > backup-$(date +%Y%m%d-%H%M%S).sql

# Run migrations
kubectl run zakera-migrate \
  --image=zakera/api:v1.1.0 \
  --rm -it \
  --restart=Never \
  --namespace=zakera-production \
  -- alembic upgrade head
```

### Rollback

```bash
# Revert to previous migration
kubectl run zakera-migrate \
  --image=zakera/api:v1.0.0 \
  --rm -it \
  --restart=Never \
  --namespace=zakera-production \
  -- alembic downgrade -1

# Restore database
kubectl exec -it zakera-postgres-0 -n zakera-production -- \
  psql -U zakera zakera_prod < backup-20260222-120000.sql
```

## Monitoring Setup

### Prometheus & Grafana

```bash
# Install Prometheus stack
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace zakera-monitoring \
  --values monitoring/prometheus/values.yaml

# Import Zakera dashboards
kubectl create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/ \
  -n zakera-monitoring
```

### Jaeger (Distributed Tracing)

```bash
# Install Jaeger operator
kubectl create namespace observability
kubectl create -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.50.0/jaeger-operator.yaml -n observability

# Deploy Jaeger instance
kubectl apply -f monitoring/jaeger/instance.yaml
```

### Log Aggregation (ELK Stack)

```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace zakera-monitoring \
  --set replicas=3 \
  --set volumeClaimTemplate.resources.requests.storage=100Gi

# Install Kibana
helm install kibana elastic/kibana \
  --namespace zakera-monitoring

# Install Filebeat
kubectl apply -f monitoring/filebeat/
```

## Autoscaling Configuration

### Enable Metrics Server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Install Cluster Autoscaler

```bash
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=zakera-prod \
  --set awsRegion=us-east-1
```

### Apply HPA & VPA

```bash
kubectl apply -f kubernetes/autoscaling/hpa.yaml
kubectl apply -f kubernetes/autoscaling/vpa.yaml
```

## Security Hardening

### Network Policies

```bash
kubectl apply -f kubernetes/policies/network-policy.yaml
```

### Pod Security Standards

```bash
kubectl label namespace zakera-production \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### RBAC

```bash
kubectl apply -f kubernetes/rbac/
```

### Image Scanning

```bash
# Scan images with Trivy
trivy image zakera/api:v1.0.0

# Deploy admission controller
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/trivy-operator/main/deploy/static/trivy-operator.yaml
```

## Disaster Recovery

### Backup Strategy

```bash
# Install Velero
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket zakera-backups \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1

# Create backup schedule
velero schedule create zakera-daily \
  --schedule="0 2 * * *" \
  --include-namespaces zakera-production
```

### Restore Procedure

```bash
# List backups
velero backup get

# Restore from backup
velero restore create --from-backup zakera-daily-20260222020000

# Monitor restore
velero restore describe zakera-daily-20260222020000
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- Vacuum and analyze
VACUUM ANALYZE;
```

### Redis Tuning

```bash
# Increase memory
kubectl set resources statefulset zakera-redis \
  --limits=memory=2Gi \
  --requests=memory=1Gi \
  -n zakera-production

# Enable persistence
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### Application Tuning

```yaml
# Update deployment
env:
  - name: WORKERS
    value: "4"  # Number of Uvicorn workers
  - name: MAX_CONNECTIONS
    value: "1000"
  - name: CONNECTION_TIMEOUT
    value: "30"
```

## Cost Optimization

### Right-Sizing

```bash
# Analyze resource usage
kubectl top pods -n zakera-production
kubectl top nodes

# Use VPA recommendations
kubectl describe vpa zakera-api-vpa -n zakera-production
```

### Spot Instances

```bash
# AWS
eksctl create nodegroup \
  --cluster=zakera-prod \
  --name=spot-workers \
  --node-type=t3.large \
  --nodes=3 \
  --nodes-min=3 \
  --nodes-max=10 \
  --spot

# GCP
gcloud container node-pools create spot-pool \
  --cluster=zakera-prod \
  --preemptible \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=3 \
  --max-nodes=10
```

## Monitoring & Alerts

### Key Metrics to Monitor

1. **API Performance**
   - Response time (p50, p95, p99)
   - Request rate
   - Error rate
   - Throughput

2. **Resource Usage**
   - CPU utilization
   - Memory usage
   - Disk I/O
   - Network traffic

3. **Application Metrics**
   - Active connections
   - Queue length
   - Cache hit rate
   - Model API latency

4. **Business Metrics**
   - Active users
   - Messages per second
   - Token usage
   - Cost per request

### Alert Rules

```yaml
# prometheus-rules.yaml
groups:
  - name: zakera
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: High error rate detected
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        annotations:
          summary: High latency detected
      
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        annotations:
          summary: Pod is crash looping
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n zakera-production

# Describe pod
kubectl describe pod <pod-name> -n zakera-production

# Check logs
kubectl logs <pod-name> -n zakera-production --previous
```

#### Database Connection Issues

```bash
# Test connectivity
kubectl run test-db --rm -it --restart=Never \
  --image=postgres:15 \
  --namespace=zakera-production \
  -- psql -h zakera-postgres -U zakera -d zakera_prod
```

#### High Memory Usage

```bash
# Get top consumers
kubectl top pods -n zakera-production --sort-by=memory

# Check OOM kills
kubectl get events -n zakera-production | grep OOMKilled
```

## Maintenance

### Regular Tasks

- **Daily**: Check monitoring dashboards
- **Weekly**: Review logs and alerts
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and optimize resource allocation

### Upgrade Procedure

```bash
# 1. Test in staging
helm upgrade zakera zakera/zakera \
  --namespace zakera-staging \
  --set image.tag=v1.1.0

# 2. Run integration tests
./scripts/integration-tests.sh staging

# 3. Deploy to production (canary)
./scripts/deploy-canary.sh v1.1.0

# 4. Monitor for 1 hour
sleep 3600

# 5. Complete rollout
./scripts/complete-rollout.sh
```

## References

- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [12-Factor App Methodology](https://12factor.net/)
- [Production Readiness Checklist](https://srcco.de/posts/production-readiness-checklist.html)
- [Site Reliability Engineering](https://sre.google/books/)
