#!/bin/bash
#
# Comprehensive Health Check Script for Zakera Deployment
# Validates all components and generates health report
#
# Usage: ./scripts/health-check.sh [environment] [--detailed] [--json]

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT="${1:-production}"
DETAILED=false
JSON_OUTPUT=false
NAMESPACE="zakera-${ENVIRONMENT}"

# Parse options
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed) DETAILED=true; shift ;;
        --json) JSON_OUTPUT=true; shift ;;
        *) shift ;;
    esac
done

# Health status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

declare -A RESULTS

check_component() {
    local name=$1
    local command=$2
    local critical=${3:-true}
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if eval "$command" &> /dev/null; then
        RESULTS[$name]="PASS"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        [ "$JSON_OUTPUT" = false ] && echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        RESULTS[$name]="FAIL"
        if [ "$critical" = true ]; then
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            [ "$JSON_OUTPUT" = false ] && echo -e "${RED}✗${NC} $name"
        else
            WARNINGS=$((WARNINGS + 1))
            [ "$JSON_OUTPUT" = false ] && echo -e "${YELLOW}⚠${NC} $name"
        fi
        return 1
    fi
}

print_header() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║     Zakera Health Check Report            ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}Environment:${NC} $ENVIRONMENT"
        echo -e "${GREEN}Namespace:${NC} $NAMESPACE"
        echo -e "${GREEN}Timestamp:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
    fi
}

# Start health check
print_header

# 1. Kubernetes Connectivity
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "${BLUE}[1/10] Kubernetes Connectivity${NC}"
fi
check_component "Kubernetes API" "kubectl cluster-info"
check_component "Namespace Exists" "kubectl get namespace $NAMESPACE"

# 2. Deployments
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[2/10] Deployments${NC}"
fi
check_component "API Deployment" "kubectl get deployment zakera-api -n $NAMESPACE"
check_component "API Pods Running" "kubectl get pods -n $NAMESPACE -l app=zakera,component=api --field-selector=status.phase=Running | grep -q Running"

if [ "$DETAILED" = true ]; then
    DESIRED=$(kubectl get deployment zakera-api -n $NAMESPACE -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 0)
    READY=$(kubectl get deployment zakera-api -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
    [ "$JSON_OUTPUT" = false ] && echo -e "  Pods: $READY/$DESIRED ready"
fi

# 3. Services
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[3/10] Services${NC}"
fi
check_component "API Service" "kubectl get service zakera-api-service -n $NAMESPACE"
check_component "Redis Service" "kubectl get service redis-master -n $NAMESPACE" false
check_component "PostgreSQL Service" "kubectl get service postgres-service -n $NAMESPACE" false

# 4. Ingress
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[4/10] Ingress${NC}"
fi
check_component "Ingress Configured" "kubectl get ingress zakera-ingress -n $NAMESPACE" false

if [ "$DETAILED" = true ]; then
    INGRESS_HOST=$(kubectl get ingress zakera-ingress -n $NAMESPACE -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "Not configured")
    [ "$JSON_OUTPUT" = false ] && echo -e "  Host: $INGRESS_HOST"
fi

# 5. Persistent Volumes
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[5/10] Persistent Storage${NC}"
fi
check_component "PVCs Bound" "kubectl get pvc -n $NAMESPACE | grep -q Bound" false

# 6. Health Endpoints
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[6/10] Application Health${NC}"
fi

# Try to get a pod name
API_POD=$(kubectl get pods -n $NAMESPACE -l app=zakera,component=api --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$API_POD" ]; then
    check_component "Health Endpoint" "kubectl exec -n $NAMESPACE $API_POD -- curl -f http://localhost:8000/api/v1/monitoring/health" false
    check_component "Ready Endpoint" "kubectl exec -n $NAMESPACE $API_POD -- curl -f http://localhost:8000/api/v1/monitoring/ready" false
else
    RESULTS["Health Endpoint"]="SKIP"
    RESULTS["Ready Endpoint"]="SKIP"
    [ "$JSON_OUTPUT" = false ] && echo -e "${YELLOW}⚠${NC} No running pods to check"
fi

# 7. Database Connectivity
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[7/10] Database Connectivity${NC}"
fi
check_component "PostgreSQL Running" "kubectl get pods -n $NAMESPACE -l app=postgres --field-selector=status.phase=Running | grep -q Running" false

# 8. Redis Connectivity
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[8/10] Cache Connectivity${NC}"
fi
check_component "Redis Running" "kubectl get pods -n $NAMESPACE -l app=redis --field-selector=status.phase=Running | grep -q Running" false

# 9. Monitoring Stack
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[9/10] Monitoring Stack${NC}"
fi
check_component "Prometheus" "kubectl get deployment prometheus-server -n monitoring" false
check_component "Grafana" "kubectl get deployment grafana -n monitoring" false

# 10. Resource Usage
if [ "$JSON_OUTPUT" = false ]; then
    echo -e "\n${BLUE}[10/10] Resource Usage${NC}"
fi

if [ -n "$API_POD" ] && [ "$DETAILED" = true ]; then
    MEMORY_USAGE=$(kubectl top pod "$API_POD" -n "$NAMESPACE" 2>/dev/null | tail -1 | awk '{print $3}' || echo "N/A")
    CPU_USAGE=$(kubectl top pod "$API_POD" -n "$NAMESPACE" 2>/dev/null | tail -1 | awk '{print $2}' || echo "N/A")
    [ "$JSON_OUTPUT" = false ] && echo -e "  CPU: $CPU_USAGE | Memory: $MEMORY_USAGE"
fi

# Summary
if [ "$JSON_OUTPUT" = true ]; then
    # JSON output
    echo "{"
    echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"environment\": \"$ENVIRONMENT\","
    echo "  \"namespace\": \"$NAMESPACE\","
    echo "  \"total_checks\": $TOTAL_CHECKS,"
    echo "  \"passed\": $PASSED_CHECKS,"
    echo "  \"failed\": $FAILED_CHECKS,"
    echo "  \"warnings\": $WARNINGS,"
    echo "  \"health_score\": $(( PASSED_CHECKS * 100 / TOTAL_CHECKS )),"
    echo "  \"status\": \"$([ $FAILED_CHECKS -eq 0 ] && echo 'healthy' || echo 'unhealthy')\","
    echo "  \"checks\": {"
    
    first=true
    for key in "${!RESULTS[@]}"; do
        [ "$first" = false ] && echo ","
        first=false
        echo -n "    \"$key\": \"${RESULTS[$key]}\""
    done
    echo ""
    echo "  }"
    echo "}"
else
    # Human-readable output
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           Health Check Summary             ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Total Checks:${NC} $TOTAL_CHECKS"
    echo -e "${GREEN}Passed:${NC} $PASSED_CHECKS"
    echo -e "${RED}Failed:${NC} $FAILED_CHECKS"
    echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
    
    HEALTH_SCORE=$(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))
    echo -e "${GREEN}Health Score:${NC} $HEALTH_SCORE%"
    
    echo ""
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}✓ System is healthy${NC}"
        exit 0
    else
        echo -e "${RED}✗ System has issues${NC}"
        exit 1
    fi
fi
