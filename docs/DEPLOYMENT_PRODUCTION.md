# Production Deployment Guide

This guide covers deploying Zakera AI Chat Agent to production environments with high availability, scalability, and security.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Architecture](#deployment-architecture)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Docker Compose Production](#docker-compose-production)
- [Cloud Provider Setup](#cloud-provider-setup)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Best Practices](#security-best-practices)
- [Scaling and Performance](#scaling-and-performance)
- [Disaster Recovery](#disaster-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

```bash
# Kubernetes CLI
kubectl version --client

# Helm (optional but recommended)
helm version

# Docker
docker --version

# Cloud CLI (choose one)
aws --version  # AWS
gcloud version  # GCP
az --version   # Azure
```

### Infrastructure Requirements

- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM
- **Storage**: 50GB+ for persistent data
- **Network**: Public IP with HTTPS support
- **Database**: PostgreSQL 13+ or MySQL 8+ (optional, SQLite for development)

## Deployment Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                       │
│                  (Nginx/ALB/GKE LB)                    │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐        ┌──────▼───────┐
│   API Server   │◄──────►│  API Server  │
│   (Replica 1)  │        │  (Replica 2) │
└───────┬────────┘        └──────┬───────┘
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐        ┌──────▼───────┐
│   PostgreSQL   │        │    Redis     │
│   (Primary)    │        │   (Cache)    │
└────────────────┘        └──────────────┘
        │                         
┌───────▼────────┐                
│   PostgreSQL   │                
│   (Replica)    │                
└────────────────┘                
```

### Component Responsibilities

- **Load Balancer**: Traffic distribution, SSL termination
- **API Server**: Request handling, business logic
- **Database**: Persistent data storage
- **Redis**: Session cache, rate limiting
- **Monitoring**: Prometheus, Grafana

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace zakera-prod
kubectl config set-context --current --namespace=zakera-prod
```

### 2. Configure Secrets

```bash
# Create secrets for API keys
kubectl create secret generic zakera-secrets \
  --from-literal=openai-api-key=sk-... \
  --from-literal=anthropic-api-key=sk-ant-... \
  --from-literal=groq-api-key=gsk_... \
  --from-literal=database-url=postgresql://user:pass@host:5432/zakera \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --namespace=zakera-prod

# Verify secrets
kubectl get secrets -n zakera-prod
```

### 3. Apply Kubernetes Manifests

```bash
# Apply all manifests in order
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml
kubectl apply -f kubernetes/hpa.yaml

# Or apply all at once
kubectl apply -f kubernetes/
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n zakera-prod

# Check services
kubectl get svc -n zakera-prod

# Check ingress
kubectl get ingress -n zakera-prod

# View logs
kubectl logs -f deployment/zakera-api -n zakera-prod

# Check pod health
kubectl describe pod <pod-name> -n zakera-prod
```

### 5. Access Application

```bash
# Get external IP
kubectl get ingress zakera-ingress -n zakera-prod

# Or use port forwarding for testing
kubectl port-forward svc/zakera-api 8000:8000 -n zakera-prod

# Test health endpoint
curl http://localhost:8000/api/v1/monitoring/health
```

## Managed Kubernetes Services

### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster \
  --name zakera-cluster \
  --region us-west-2 \
  --nodegroup-name zakera-nodes \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --region us-west-2 --name zakera-cluster

# Deploy application
kubectl apply -f kubernetes/

# Setup ALB Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/v2_4_7_full.yaml
```

### Google GKE

```bash
# Create GKE cluster
gcloud container clusters create zakera-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 5

# Get credentials
gcloud container clusters get-credentials zakera-cluster --zone us-central1-a

# Deploy application
kubectl apply -f kubernetes/
```

### Azure AKS

```bash
# Create resource group
az group create --name zakera-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group zakera-rg \
  --name zakera-cluster \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group zakera-rg --name zakera-cluster

# Deploy application
kubectl apply -f kubernetes/
```

## Docker Compose Production

For smaller deployments without Kubernetes:

```bash
# Use production compose file
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Scale services
docker-compose -f docker-compose.production.yml up -d --scale api=3

# Health check
curl http://localhost:8000/api/v1/monitoring/health
```

## Monitoring and Logging

### Prometheus Setup

```bash
# Install Prometheus using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# Access Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Default credentials: admin / prom-operator
```

### Logging with EFK Stack

```bash
# Install Elasticsearch
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace

# Install Fluentd
kubectl apply -f kubernetes/logging/fluentd-daemonset.yaml

# Install Kibana
helm install kibana elastic/kibana -n logging

# Access Kibana
kubectl port-forward -n logging svc/kibana-kibana 5601:5601
```

## Security Best Practices

### 1. Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zakera-network-policy
spec:
  podSelector:
    matchLabels:
      app: zakera-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: database
    ports:
    - protocol: TCP
      port: 5432
```

### 2. Pod Security Policies

```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: zakera-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### 3. TLS/SSL Configuration

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f kubernetes/cert-issuer.yaml

# SSL will be automatically provisioned via Ingress annotations
```

## Scaling and Performance

### Horizontal Pod Autoscaling

The HPA is configured to scale based on CPU and memory:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: zakera-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: zakera-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Performance Optimization

```bash
# Enable resource quotas
kubectl apply -f kubernetes/resource-quota.yaml

# Configure node affinity for optimal placement
kubectl label nodes node-1 workload=api
kubectl label nodes node-2 workload=database

# Monitor resource usage
kubectl top nodes
kubectl top pods -n zakera-prod
```

## Disaster Recovery

### Backup Strategy

```bash
# Backup database
kubectl exec -n zakera-prod deployment/postgres -- \
  pg_dump -U zakera zakera > backup-$(date +%Y%m%d).sql

# Backup Kubernetes resources
kubectl get all -n zakera-prod -o yaml > k8s-backup-$(date +%Y%m%d).yaml

# Store backups in S3/GCS
aws s3 cp backup-*.sql s3://zakera-backups/
```

### Restore Procedure

```bash
# Restore database
kubectl exec -i -n zakera-prod deployment/postgres -- \
  psql -U zakera zakera < backup-20260218.sql

# Restore Kubernetes resources
kubectl apply -f k8s-backup-20260218.yaml
```

## Cost Optimization

### 1. Right-Size Resources

```bash
# Analyze resource usage
kubectl top pods -n zakera-prod --containers

# Adjust resource requests/limits based on actual usage
# Update deployment.yaml with optimized values
```

### 2. Use Spot/Preemptible Instances

```bash
# AWS EKS with Spot instances
eksctl create nodegroup \
  --cluster=zakera-cluster \
  --name=spot-nodes \
  --node-type=t3.large \
  --nodes=2 \
  --nodes-min=1 \
  --nodes-max=5 \
  --spot

# GKE with Preemptible nodes
gcloud container node-pools create spot-pool \
  --cluster=zakera-cluster \
  --preemptible \
  --num-nodes=2
```

### 3. Enable Cluster Autoscaling

```bash
# AWS EKS
export AWS_REGION=us-west-2
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# GKE (enabled by default with --enable-autoscaling)
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n zakera-prod

# Check logs
kubectl logs <pod-name> -n zakera-prod

# Check resource constraints
kubectl get resourcequota -n zakera-prod
```

#### Service Unavailable

```bash
# Check service endpoints
kubectl get endpoints -n zakera-prod

# Test service connectivity
kubectl run test-pod --rm -it --image=busybox -- wget -O- http://zakera-api:8000/api/v1/monitoring/health

# Check ingress configuration
kubectl describe ingress zakera-ingress -n zakera-prod
```

#### High Memory Usage

```bash
# Monitor memory usage
kubectl top pods -n zakera-prod

# Increase memory limits
kubectl set resources deployment zakera-api --limits=memory=2Gi -n zakera-prod

# Enable memory profiling
kubectl set env deployment/zakera-api ENABLE_PROFILING=true -n zakera-prod
```

### Debug Mode

```bash
# Enable debug logging
kubectl set env deployment/zakera-api LOG_LEVEL=DEBUG -n zakera-prod

# Access shell in running pod
kubectl exec -it <pod-name> -n zakera-prod -- /bin/bash

# Copy files from pod
kubectl cp zakera-prod/<pod-name>:/app/logs/app.log ./local-app.log
```

## Production Checklist

- [ ] Secrets properly configured and encrypted
- [ ] Resource limits and requests set appropriately
- [ ] Health checks (liveness and readiness) configured
- [ ] Horizontal Pod Autoscaler enabled
- [ ] Monitoring and alerting set up
- [ ] Logging configured and centralized
- [ ] Backup strategy implemented
- [ ] SSL/TLS certificates configured
- [ ] Network policies applied
- [ ] Rate limiting enabled
- [ ] Database migrations tested
- [ ] Disaster recovery plan documented
- [ ] Cost monitoring enabled
- [ ] Security scanning automated
- [ ] Performance testing completed

## Support

For production deployment support:
- Email: [email protected]
- Documentation: https://github.com/itsmepraks/zakera/docs
- Issues: https://github.com/itsmepraks/zakera/issues

---

**Last Updated**: February 2026  
**Version**: 1.0.0  
**Status**: Production Ready
