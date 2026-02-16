#!/bin/bash
# Rollback Script for Zakera

set -e

ENVIRONMENT=${1:-production}
REVISION=${2:-0}  # 0 = previous revision

echo "========================================"
echo "  Zakera Rollback Script"
echo "  Environment: $ENVIRONMENT"
echo "  Revision: $REVISION"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check current status
log_info "Checking current deployment status..."
kubectl rollout status deployment/zakera-api -n zakera

# Get rollout history
log_info "Rollout history:"
kubectl rollout history deployment/zakera-api -n zakera

# Confirm rollback
echo ""
read -p "Are you sure you want to rollback? (yes/no): " -r
echo ""
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log_info "Rollback cancelled."
    exit 0
fi

# Perform rollback
log_info "Rolling back deployment..."

if [ "$REVISION" -eq "0" ]; then
    # Rollback to previous
    kubectl rollout undo deployment/zakera-api -n zakera
else
    # Rollback to specific revision
    kubectl rollout undo deployment/zakera-api -n zakera --to-revision=$REVISION
fi

# Wait for rollback to complete
log_info "Waiting for rollback to complete..."
kubectl rollout status deployment/zakera-api -n zakera --timeout=300s

# Verify
log_info "Verifying rollback..."
kubectl get pods -n zakera -l app=zakera,component=api

# Health check
SERVICE_IP=$(kubectl get svc zakera-api -n zakera -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -n "$SERVICE_IP" ]; then
    log_info "Running health check..."
    if curl -f -s "http://$SERVICE_IP/api/v1/monitoring/health" > /dev/null; then
        log_info "Health check passed! ✅"
    else
        log_error "Health check failed! ❌"
        exit 1
    fi
fi

log_info "Rollback complete! 🎉"
