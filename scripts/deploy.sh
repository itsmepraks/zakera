#!/bin/bash
# Production Deployment Script for Zakera

set -e

ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

echo "========================================"
echo "  Zakera Deployment Script"
echo "  Environment: $ENVIRONMENT"
echo "  Version: $VERSION"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        log_warn "helm not found. Some features may not work."
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_warn "AWS CLI not found. AWS features disabled."
    fi
    
    log_info "Prerequisites check complete."
}

create_namespace() {
    log_info "Creating namespace..."
    kubectl apply -f kubernetes/namespace.yaml
}

create_secrets() {
    log_info "Creating secrets..."
    
    if [ ! -f "kubernetes/secrets.yaml" ]; then
        log_error "secrets.yaml not found. Copy from secrets.yaml.template and configure."
        exit 1
    fi
    
    kubectl apply -f kubernetes/secrets.yaml
}

create_configmaps() {
    log_info "Creating ConfigMaps..."
    kubectl apply -f kubernetes/configmap.yaml
}

create_storage() {
    log_info "Creating persistent volumes..."
    kubectl apply -f kubernetes/pvc.yaml
}

deploy_database() {
    log_info "Deploying PostgreSQL..."
    kubectl apply -f kubernetes/postgres.yaml
    
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=ready pod -l component=postgres -n zakera --timeout=300s
}

deploy_redis() {
    log_info "Deploying Redis..."
    kubectl apply -f kubernetes/redis.yaml
    
    log_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=ready pod -l component=redis -n zakera --timeout=120s
}

deploy_application() {
    log_info "Deploying Zakera API..."
    kubectl apply -f kubernetes/serviceaccount.yaml
    kubectl apply -f kubernetes/deployment.yaml
    kubectl apply -f kubernetes/service.yaml
    
    log_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/zakera-api -n zakera --timeout=300s
}

configure_autoscaling() {
    log_info "Configuring autoscaling..."
    kubectl apply -f kubernetes/hpa.yaml
}

configure_ingress() {
    log_info "Configuring ingress..."
    kubectl apply -f kubernetes/ingress.yaml
}

deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    kubectl apply -f kubernetes/monitoring-stack.yaml
    
    log_info "Waiting for monitoring to be ready..."
    kubectl wait --for=condition=ready pod -l app=prometheus -n zakera --timeout=180s
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    # Get service endpoint
    SERVICE_IP=$(kubectl get svc zakera-api -n zakera -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    
    if [ -z "$SERVICE_IP" ]; then
        SERVICE_IP=$(kubectl get svc zakera-api -n zakera -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    if [ -z "$SERVICE_IP" ]; then
        log_warn "Service endpoint not ready yet. Skipping smoke tests."
        return
    fi
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    if curl -f -s "http://$SERVICE_IP/api/v1/monitoring/health" > /dev/null; then
        log_info "Health check passed!"
    else
        log_error "Health check failed!"
        exit 1
    fi
}

show_status() {
    echo ""
    echo "========================================"
    echo "  Deployment Status"
    echo "========================================"
    echo ""
    
    log_info "Pods:"
    kubectl get pods -n zakera
    
    echo ""
    log_info "Services:"
    kubectl get svc -n zakera
    
    echo ""
    log_info "Ingress:"
    kubectl get ingress -n zakera
    
    echo ""
    log_info "HPA:"
    kubectl get hpa -n zakera
}

show_endpoints() {
    echo ""
    echo "========================================"
    echo "  Access Information"
    echo "========================================"
    echo ""
    
    SERVICE_IP=$(kubectl get svc zakera-api -n zakera -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$SERVICE_IP" ]; then
        SERVICE_IP=$(kubectl get svc zakera-api -n zakera -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    fi
    
    if [ -n "$SERVICE_IP" ]; then
        echo "API Endpoint: http://$SERVICE_IP"
        echo "API Docs: http://$SERVICE_IP/api/docs"
        echo "Health: http://$SERVICE_IP/api/v1/monitoring/health"
    else
        echo "Service endpoint not ready yet. Run 'kubectl get svc -n zakera' to check."
    fi
    
    GRAFANA_IP=$(kubectl get svc grafana -n zakera -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -n "$GRAFANA_IP" ]; then
        echo "Grafana: http://$GRAFANA_IP"
    fi
    
    echo ""
}

# Main deployment flow
main() {
    check_prerequisites
    
    log_info "Starting deployment for environment: $ENVIRONMENT"
    
    create_namespace
    create_secrets
    create_configmaps
    create_storage
    
    deploy_database
    deploy_redis
    deploy_application
    configure_autoscaling
    configure_ingress
    deploy_monitoring
    
    log_info "Deployment complete!"
    
    run_smoke_tests
    show_status
    show_endpoints
    
    echo ""
    log_info "Deployment successful! 🎉"
    echo ""
    log_info "Next steps:"
    echo "  1. Configure DNS to point to the load balancer"
    echo "  2. Set up SSL certificates (cert-manager)"
    echo "  3. Configure monitoring alerts"
    echo "  4. Run integration tests"
    echo "  5. Monitor metrics in Grafana"
    echo ""
}

# Run main function
main
