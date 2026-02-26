# Kubernetes Deployment Best Practices for Zakera

Comprehensive guide for deploying Zakera to Kubernetes with production-grade reliability.

## Table of Contents

1. [Health Checks](#health-checks)
2. [Resource Management](#resource-management)
3. [High Availability](#high-availability)
4. [Security](#security)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

## Health Checks

### Types of Probes

Zakera uses three types of health probes:

#### 1. Startup Probe

```yaml
startupProbe:
  httpGet:
    path: /api/v1/monitoring/health/startup
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30  # 150 seconds max startup time
```

**Purpose**: Gives the application time to start without being killed by liveness checks.

**Checks**:
- Database connection established
- Redis connection established
- Configuration loaded
- Model providers initialized

#### 2. Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/monitoring/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
```

**Purpose**: Determines if the container should be restarted.

**Checks**:
- Application thread is responsive
- No deadlocks detected
- Memory usage below threshold (90%)
- Critical subsystems functioning

#### 3. Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /api/v1/monitoring/health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3
```

**Purpose**: Determines if the container should receive traffic.

**Checks**:
- Database queries responsive (<1s)
- Redis operations responsive (<500ms)
- Can handle new requests
- Not overwhelmed with existing requests

### Implementing Custom Health Checks

```python
# src/api/health.py

from fastapi import APIRouter, Response, status
import asyncio
import psutil

router = APIRouter()

@router.get("/health/startup")
async def startup_check():
    """Startup probe endpoint."""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "config": check_configuration()
    }
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}
    return Response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "starting", "checks": checks}
    )

@router.get("/health/live")
async def liveness_check():
    """Liveness probe endpoint."""
    memory = psutil.virtual_memory()
    
    if memory.percent > 90:
        return Response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "reason": "memory_pressure"}
        )
    
    return {"status": "alive", "memory_percent": memory.percent}

@router.get("/health/ready")
async def readiness_check():
    """Readiness probe endpoint."""
    checks = await asyncio.gather(
        check_database_responsive(),
        check_redis_responsive(),
        check_request_capacity()
    )
    
    if all(checks):
        return {"status": "ready"}
    return Response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready"}
    )
```

## Resource Management

### QoS Classes

Kubernetes assigns QoS classes based on resource configuration:

#### Guaranteed (Not Recommended for Zakera)

```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 1000m
    memory: 2Gi
```

**Pros**: Highest priority, never evicted
**Cons**: Inflexible, can't handle traffic spikes

#### Burstable (Recommended)

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi
```

**Pros**: Flexible, handles spikes, cost-effective
**Cons**: Can be evicted under node pressure

#### BestEffort (Not Recommended)

No resource specifications. First to be evicted.

### Resource Sizing Guidelines

**Development**:
```yaml
requests:
  cpu: 100m
  memory: 256Mi
limits:
  cpu: 500m
  memory: 512Mi
```

**Staging**:
```yaml
requests:
  cpu: 250m
  memory: 512Mi
limits:
  cpu: 1000m
  memory: 1Gi
```

**Production**:
```yaml
requests:
  cpu: 500m
  memory: 1Gi
limits:
  cpu: 2000m
  memory: 2Gi
```

### Horizontal Pod Autoscaling

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
  minReplicas: 3
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

## High Availability

### Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: zakera-api-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: zakera-api
```

**Ensures**: At least 2 pods always running during voluntary disruptions.

### Anti-Affinity Rules

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values:
          - zakera-api
      topologyKey: kubernetes.io/hostname
```

**Effect**: Pods spread across different nodes.

### Rolling Updates

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

**Result**: Zero-downtime deployments.

## Security

### Pod Security Standards

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

containerSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
    - ALL
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zakera-api-netpol
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
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Monitoring

### Metrics to Monitor

1. **Pod Health**
   - Restart count
   - Probe success rate
   - Pod age

2. **Resource Usage**
   - CPU utilization
   - Memory utilization
   - Disk usage

3. **Application Metrics**
   - Request rate
   - Error rate
   - Latency (p50, p95, p99)

### Prometheus Queries

```promql
# Pod restart rate
rate(kube_pod_container_status_restarts_total{namespace="zakera-prod"}[5m])

# CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="zakera-prod"}[5m])) by (pod)

# Memory usage
sum(container_memory_working_set_bytes{namespace="zakera-prod"}) by (pod)

# Probe failures
sum(rate(prober_probe_failed_total{namespace="zakera-prod"}[5m])) by (probe)
```

## Troubleshooting

### Common Issues

#### 1. CrashLoopBackOff

**Symptoms**: Pod keeps restarting

**Diagnosis**:
```bash
kubectl logs -f zakera-api-xxx --previous
kubectl describe pod zakera-api-xxx
```

**Common Causes**:
- Application crash on startup
- Missing environment variables
- Database connection failure
- Liveness probe too aggressive

**Solutions**:
- Increase `initialDelaySeconds` on probes
- Check application logs
- Verify secrets and configmaps
- Test startup probe locally

#### 2. Pod Not Ready

**Symptoms**: Pod running but not receiving traffic

**Diagnosis**:
```bash
kubectl get pod zakera-api-xxx
kubectl exec -it zakera-api-xxx -- curl localhost:8000/health/ready
```

**Solutions**:
- Check readiness probe configuration
- Verify dependencies (database, redis)
- Check application performance

#### 3. High Memory Usage

**Symptoms**: Pods being OOMKilled

**Diagnosis**:
```bash
kubectl top pod zakera-api-xxx
kubectl exec -it zakera-api-xxx -- ps aux
```

**Solutions**:
- Increase memory limits
- Check for memory leaks
- Optimize application code
- Implement caching strategies

### Debug Commands

```bash
# Check pod status
kubectl get pods -n zakera-prod

# View pod logs
kubectl logs -f zakera-api-xxx -n zakera-prod

# Execute commands in pod
kubectl exec -it zakera-api-xxx -n zakera-prod -- /bin/sh

# Port forward for local testing
kubectl port-forward zakera-api-xxx 8000:8000 -n zakera-prod

# View events
kubectl get events -n zakera-prod --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n zakera-prod

# Describe pod for detailed info
kubectl describe pod zakera-api-xxx -n zakera-prod
```

## Resources

- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Health Checks](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
