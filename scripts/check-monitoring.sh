#!/bin/bash

# Zakera Monitoring Health Check Script
# Verifies all monitoring components are working

set -e

echo "🔍 Zakera Monitoring Health Check"
echo "==================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

FAILURES=0

# Function to check endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ OK${NC} (HTTP $status)"
    else
        echo -e "${RED}❌ FAILED${NC} (HTTP $status, expected $expected_status)"
        FAILURES=$((FAILURES + 1))
    fi
}

# Function to check service
check_service() {
    local name=$1
    local port=$2
    
    echo -n "Checking $name on port $port... "
    
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✅ OK${NC}"
    else
        echo -e "${RED}❌ NOT RUNNING${NC}"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "📡 Service Availability:"
echo "-------------------------"
check_service "Zakera API" 8000
check_service "Prometheus" 9090
check_service "Grafana" 3001
check_service "AlertManager" 9093
echo ""

echo "🌐 Endpoint Health:"
echo "-------------------"
check_endpoint "API Root" "http://localhost:8000/"
check_endpoint "API Health" "http://localhost:8000/api/v1/monitoring/health"
check_endpoint "API Metrics" "http://localhost:8000/api/v1/monitoring/metrics"
check_endpoint "Liveness Probe" "http://localhost:8000/api/v1/monitoring/health/live"
check_endpoint "Readiness Probe" "http://localhost:8000/api/v1/monitoring/health/ready"
check_endpoint "Prometheus" "http://localhost:9090/-/healthy"
check_endpoint "Grafana" "http://localhost:3001/api/health"
check_endpoint "AlertManager" "http://localhost:9093/-/healthy"
echo ""

echo "📊 Metrics Check:"
echo "-----------------"
metrics=$(curl -s http://localhost:8000/api/v1/monitoring/metrics 2>/dev/null || echo "")
if [ -n "$metrics" ]; then
    metric_count=$(echo "$metrics" | grep -c "^#" || echo "0")
    echo -e "${GREEN}✅ Metrics available${NC} ($metric_count metric types)"
else
    echo -e "${RED}❌ No metrics available${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "🏥 Health Details:"
echo "------------------"
health=$(curl -s "http://localhost:8000/api/v1/monitoring/health?detailed=true" 2>/dev/null || echo "{}")
if [ -n "$health" ] && [ "$health" != "{}" ]; then
    echo "$health" | python3 -m json.tool 2>/dev/null || echo "$health"
else
    echo -e "${RED}❌ Health check failed${NC}"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Summary
echo "==================================="
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "🎉 Monitoring is fully operational"
    echo ""
    echo "📍 Access Points:"
    echo "   Grafana:      http://localhost:3001"
    echo "   Prometheus:   http://localhost:9090"
    echo "   AlertManager: http://localhost:9093"
    echo "   API Docs:     http://localhost:8000/api/docs"
    exit 0
else
    echo -e "${RED}❌ $FAILURES check(s) failed${NC}"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check if services are running: docker-compose ps"
    echo "   2. Check logs: docker-compose logs"
    echo "   3. Restart services: docker-compose restart"
    echo "   4. View detailed logs: make monitoring-logs"
    exit 1
fi
