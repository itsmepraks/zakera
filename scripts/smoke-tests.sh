#!/bin/bash
# Smoke tests for deployment validation
# Usage: ./smoke-tests.sh <base_url>

set -e

BASE_URL=${1:-http://localhost:8000}
MAX_RETRIES=10
RETRY_DELAY=5

echo "Running smoke tests against ${BASE_URL}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

test_passed=0
test_failed=0

run_test() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Testing ${name}... "
    
    for i in $(seq 1 $MAX_RETRIES); do
        response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${url}" || echo "000")
        
        if [ "$response" = "$expected_status" ]; then
            echo -e "${GREEN}PASSED${NC}"
            ((test_passed++))
            return 0
        fi
        
        if [ $i -lt $MAX_RETRIES ]; then
            sleep $RETRY_DELAY
        fi
    done
    
    echo -e "${RED}FAILED${NC} (got $response, expected $expected_status)"
    ((test_failed++))
    return 1
}

# Health check endpoints
run_test "Health Check" "/api/v1/monitoring/health"
run_test "Liveness Probe" "/api/v1/monitoring/health/live"
run_test "Readiness Probe" "/api/v1/monitoring/health/ready"

# Metrics endpoint
run_test "Prometheus Metrics" "/api/v1/monitoring/metrics"

# API documentation
run_test "API Docs" "/api/docs"

# Analytics endpoints (should require auth - 401)
run_test "Analytics Overview (Unauthorized)" "/api/v1/analytics/overview" 401

echo ""
echo "========================================"
echo "Smoke Test Results"
echo "========================================"
echo -e "${GREEN}Passed: ${test_passed}${NC}"
echo -e "${RED}Failed: ${test_failed}${NC}"
echo "========================================"

if [ $test_failed -gt 0 ]; then
    exit 1
fi

echo "All smoke tests passed!"
exit 0
