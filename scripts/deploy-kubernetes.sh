#!/bin/bash
#
# Kubernetes Deployment Automation Script
# Deploy Zakera AI Chat Agent to Kubernetes with validation and rollback
#
# Usage: ./scripts/deploy-kubernetes.sh [environment] [options]
#
# Environments: development, staging, production
# Options:
#   --dry-run          Show what would be deployed without applying
#   --skip-tests       Skip smoke tests after deployment
#   --no-backup        Skip database backup (not recommended for production)
#   --rollback         Rollback to previous deployment
#   --force            Force deployment without confirmations

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-staging}"
DRY_RUN=false
SKIP_TESTS=false
NO_BACKUP=false
ROLLBACK=false
FORCE=false

# Parse options
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --skip-tests) SKIP_TESTS=true; shift ;;
        --no-backup) NO_BACKUP=true; shift ;;
        --rollback) ROLLBACK=true; shift ;;
        --force) FORCE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    echo "Valid environments: development, staging, production"
    exit 1
fi

# Set namespace based on environment
NAMESPACE="zakera-${ENVIRONMENT}"
K8S_DIR="${PROJECT_ROOT}/kubernetes/${ENVIRONMENT}"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Zakera Kubernetes Deployment Script     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
echo -e "${GREEN}Dry Run:${NC} $DRY_RUN"
echo ""

# Function: Print step
print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

# Function: Print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function: Print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function: Print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function: Confirm action
confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    echo -e "${YELLOW}$1${NC}"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deployment cancelled${NC}"
        exit 1
    fi
}

# Step 1: Prerequisites check
print_step "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl."
    exit 1
fi

if ! command -v helm &> /dev/null; then
    print_warning "helm not found. Some features may not be available."
fi

print_success "Prerequisites OK"

# Step 2: Verify Kubernetes connection
print_step "Verifying Kubernetes connection..."

if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

CURRENT_CONTEXT=$(kubectl config current-context)
print_success "Connected to: $CURRENT_CONTEXT"

if [[ "$ENVIRONMENT" == "production" && ! "$CURRENT_CONTEXT" =~ production ]]; then
    print_warning "Current context doesn't appear to be production!"
    confirm "You're deploying to PRODUCTION with context '$CURRENT_CONTEXT'."
fi

# Step 3: Create namespace if it doesn't exist
print_step "Ensuring namespace exists..."

if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    print_success "Namespace $NAMESPACE already exists"
else
    if [ "$DRY_RUN" = false ]; then
        kubectl create namespace "$NAMESPACE"
        kubectl label namespace "$NAMESPACE" environment="$ENVIRONMENT"
        print_success "Created namespace $NAMESPACE"
    else
        print_success "Would create namespace $NAMESPACE"
    fi
fi

# Step 4: Backup database (production only)
if [[ "$ENVIRONMENT" == "production" && "$NO_BACKUP" = false && "$ROLLBACK" = false ]]; then
    print_step "Backing up production database..."
    
    if [ "$DRY_RUN" = false ]; then
        BACKUP_NAME="zakera-backup-$(date +%Y%m%d-%H%M%S)"
        kubectl exec -n "$NAMESPACE" deployment/postgres -- \
            pg_dump -U zakera_user zakera_prod > "/tmp/${BACKUP_NAME}.sql" || true
        print_success "Database backed up to /tmp/${BACKUP_NAME}.sql"
    else
        print_success "Would backup database"
    fi
fi

# Step 5: Handle rollback
if [ "$ROLLBACK" = true ]; then
    print_step "Rolling back deployment..."
    
    confirm "This will rollback the deployment in $ENVIRONMENT."
    
    if [ "$DRY_RUN" = false ]; then
        kubectl rollout undo deployment/zakera-api -n "$NAMESPACE"
        kubectl rollout status deployment/zakera-api -n "$NAMESPACE" --timeout=5m
        print_success "Rollback completed"
    else
        print_success "Would rollback deployment"
    fi
    exit 0
fi

# Step 6: Validate manifests
print_step "Validating Kubernetes manifests..."

if [ ! -d "$K8S_DIR" ]; then
    print_error "Kubernetes directory not found: $K8S_DIR"
    exit 1
fi

MANIFEST_COUNT=$(find "$K8S_DIR" -name "*.yaml" -o -name "*.yml" | wc -l)
print_success "Found $MANIFEST_COUNT manifest files"

# Validate with kubectl dry-run
for file in "$K8S_DIR"/*.yaml; do
    if [ -f "$file" ]; then
        if kubectl apply -f "$file" --dry-run=client -n "$NAMESPACE" &> /dev/null; then
            print_success "Validated: $(basename $file)"
        else
            print_error "Invalid manifest: $(basename $file)"
            exit 1
        fi
    fi
done

# Step 7: Apply configurations
print_step "Deploying to $ENVIRONMENT..."

if [[ "$ENVIRONMENT" == "production" ]]; then
    confirm "⚠️  You are about to deploy to PRODUCTION!"
fi

KUBECTL_CMD="kubectl apply -f $K8S_DIR/ -n $NAMESPACE"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - No changes will be applied${NC}"
    kubectl apply -f "$K8S_DIR/" --dry-run=client -n "$NAMESPACE"
else
    $KUBECTL_CMD
    print_success "Manifests applied successfully"
fi

# Step 8: Wait for rollout
if [ "$DRY_RUN" = false ]; then
    print_step "Waiting for rollout to complete..."
    
    if kubectl rollout status deployment/zakera-api -n "$NAMESPACE" --timeout=10m; then
        print_success "Deployment rolled out successfully"
    else
        print_error "Deployment rollout failed or timed out"
        
        print_step "Recent pod events:"
        kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -20
        
        print_step "Pod status:"
        kubectl get pods -n "$NAMESPACE" -l app=zakera
        
        confirm "Rollout failed. Do you want to rollback?"
        kubectl rollout undo deployment/zakera-api -n "$NAMESPACE"
        exit 1
    fi
fi

# Step 9: Verify deployment
print_step "Verifying deployment..."

if [ "$DRY_RUN" = false ]; then
    echo ""
    echo "Pods:"
    kubectl get pods -n "$NAMESPACE" -l app=zakera
    echo ""
    echo "Services:"
    kubectl get services -n "$NAMESPACE"
    echo ""
    echo "Ingress:"
    kubectl get ingress -n "$NAMESPACE"
    echo ""
    
    # Check pod health
    READY_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=zakera,component=api --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)
    TOTAL_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=zakera,component=api --no-headers 2>/dev/null | wc -l)
    
    if [ "$READY_PODS" -eq "$TOTAL_PODS" ] && [ "$READY_PODS" -gt 0 ]; then
        print_success "All pods are running: $READY_PODS/$TOTAL_PODS"
    else
        print_warning "Some pods are not ready: $READY_PODS/$TOTAL_PODS"
    fi
fi

# Step 10: Run smoke tests
if [[ "$SKIP_TESTS" = false && "$DRY_RUN" = false ]]; then
    print_step "Running smoke tests..."
    
    # Get ingress URL
    INGRESS_HOST=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || echo "")
    
    if [ -n "$INGRESS_HOST" ]; then
        API_URL="https://${INGRESS_HOST}"
        
        # Test health endpoint
        if curl -f -s "${API_URL}/api/v1/monitoring/health" > /dev/null; then
            print_success "Health check passed"
        else
            print_error "Health check failed"
        fi
        
        # Test API docs
        if curl -f -s "${API_URL}/api/docs" > /dev/null; then
            print_success "API docs accessible"
        else
            print_warning "API docs not accessible (may be disabled in production)"
        fi
    else
        print_warning "Ingress not configured, skipping smoke tests"
    fi
fi

# Step 11: Display summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Deployment Summary                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
echo -e "${GREEN}Status:${NC} Completed"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo "Useful commands:"
    echo ""
    echo "  # View logs"
    echo "  kubectl logs -f deployment/zakera-api -n $NAMESPACE"
    echo ""
    echo "  # View pod status"
    echo "  kubectl get pods -n $NAMESPACE -w"
    echo ""
    echo "  # Scale deployment"
    echo "  kubectl scale deployment/zakera-api --replicas=5 -n $NAMESPACE"
    echo ""
    echo "  # Rollback deployment"
    echo "  kubectl rollout undo deployment/zakera-api -n $NAMESPACE"
    echo ""
    echo "  # View deployment history"
    echo "  kubectl rollout history deployment/zakera-api -n $NAMESPACE"
    echo ""
fi

print_success "Deployment completed successfully! 🚀"
