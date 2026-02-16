# Kubernetes Deployment

Kubernetes manifests for deploying Zakera to production.

## Quick Start

```bash
# Deploy everything
./scripts/deploy.sh production

# Or manually
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/
```

## Files

### Core Resources
- `namespace.yaml` - Namespace definition
- `deployment.yaml` - Main application deployment
- `service.yaml` - Service definitions
- `ingress.yaml` - Ingress controller configuration

### Configuration
- `configmap.yaml` - Application configuration
- `secrets.yaml.template` - Secrets template (copy and customize)
- `serviceaccount.yaml` - RBAC and service account

### Storage
- `pvc.yaml` - Persistent volume claims
- `postgres.yaml` - PostgreSQL StatefulSet
- `redis.yaml` - Redis deployment

### Scaling
- `hpa.yaml` - Horizontal Pod Autoscaler
- `poddisruptionbudget.yaml` - Pod disruption budgets

### Security
- `networkpolicy.yaml` - Network policies

### Monitoring
- `monitoring-stack.yaml` - Prometheus and Grafana

## Architecture

```
Internet
    ↓
[Ingress] ← SSL/TLS, Rate Limiting
    ↓
[Service] ← Load Balancing
    ↓
[Pods] ← 3-10 replicas, Auto-scaling
    ↓
[PostgreSQL] ← Persistent storage
[Redis] ← Caching
```

## Configuration

### Secrets

```bash
# Copy template
cp secrets.yaml.template secrets.yaml

# Edit with your values
vim secrets.yaml

# Apply
kubectl apply -f secrets.yaml
```

### ConfigMap

Edit `configmap.yaml` for:
- API settings
- Feature flags
- Rate limits
- Model configuration

### Ingress

Edit `ingress.yaml` for:
- Domain name
- SSL certificate
- Rate limiting
- CORS settings

## Scaling

### Horizontal Scaling

```bash
# Manual
kubectl scale deployment/zakera-api --replicas=5 -n zakera

# Automatic (HPA)
kubectl apply -f hpa.yaml
kubectl get hpa -n zakera
```

### Vertical Scaling

```bash
# Update resources
kubectl set resources deployment/zakera-api \
  --limits=cpu=4000m,memory=4Gi \
  --requests=cpu=1000m,memory=1Gi \
  -n zakera
```

## Monitoring

```bash
# Access Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n zakera

# Access Grafana
kubectl port-forward svc/grafana 3000:80 -n zakera
```

## Troubleshooting

```bash
# View pod status
kubectl get pods -n zakera

# Describe pod
kubectl describe pod <pod-name> -n zakera

# View logs
kubectl logs -f <pod-name> -n zakera

# Execute in pod
kubectl exec -it <pod-name> -n zakera -- bash

# View events
kubectl get events -n zakera --sort-by='.lastTimestamp'
```

## Health Checks

```bash
# Test liveness
kubectl exec deployment/zakera-api -n zakera -- \
  curl http://localhost:8000/api/v1/monitoring/health/live

# Test readiness
kubectl exec deployment/zakera-api -n zakera -- \
  curl http://localhost:8000/api/v1/monitoring/health/ready
```

## Updates

```bash
# Rolling update
kubectl set image deployment/zakera-api \
  zakera=zakera:v0.6.1 -n zakera

# Watch rollout
kubectl rollout status deployment/zakera-api -n zakera

# Rollback
kubectl rollout undo deployment/zakera-api -n zakera
```

## Resource Requirements

### Minimum
- 3 nodes (t3.medium or equivalent)
- 6 CPU cores total
- 12GB RAM total
- 100GB storage

### Recommended
- 5 nodes (t3.large)
- 10 CPU cores total
- 20GB RAM total
- 200GB storage

### High Availability
- 3+ availability zones
- 6+ nodes
- Multi-AZ database
- Multiple replicas

## Security

### Network Policies

Network policies restrict pod-to-pod communication:
- API can access database and Redis
- Database and Redis only accessible from API
- Prometheus can scrape all pods

### Pod Security

All pods run as non-root:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
```

### Secrets

Secrets are stored in Kubernetes secrets:
- Base64 encoded
- RBAC protected
- Can be encrypted at rest (enable encryption)

## Backup

```bash
# Backup all configs
kubectl get all,configmap,secret,pvc,ingress -n zakera -o yaml > backup.yaml

# Restore
kubectl apply -f backup.yaml
```

## Support

See `docs/DEPLOYMENT.md` for detailed guide.
