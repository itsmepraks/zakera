#!/bin/bash
# Continuous health monitoring script
# Usage: ./health-check.sh <base_url> <duration_seconds>

BASE_URL=${1:-http://localhost:8000}
DURATION=${2:-300}
INTERVAL=10

echo "Monitoring health for ${DURATION} seconds at ${BASE_URL}"

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))

failed_checks=0
successful_checks=0

while [ $(date +%s) -lt $END_TIME ]; do
    response=$(curl -s "${BASE_URL}/api/v1/monitoring/health?detailed=true")
    status=$?
    
    if [ $status -eq 0 ]; then
        # Check if response indicates healthy
        healthy=$(echo $response | jq -r '.status' 2>/dev/null || echo "unknown")
        
        if [ "$healthy" = "healthy" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Service healthy"
            ((successful_checks++))
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ Service unhealthy: $response"
            ((failed_checks++))
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ Health check failed"
        ((failed_checks++))
    fi
    
    # Alert if too many failures
    if [ $failed_checks -gt 5 ]; then
        echo "ERROR: Too many failed health checks. Deployment may have issues."
        exit 1
    fi
    
    sleep $INTERVAL
done

echo ""
echo "Health monitoring completed"
echo "Successful: ${successful_checks}"
echo "Failed: ${failed_checks}"

if [ $failed_checks -gt 0 ]; then
    exit 1
fi

exit 0
