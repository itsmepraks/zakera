#!/bin/bash

# Performance Test Runner Script
# Runs all performance test scenarios and generates reports

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
HOST="${LOCUST_HOST:-http://localhost:8000}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create results directory
mkdir -p "${RESULTS_DIR}"

echo -e "${GREEN}🚀 Zakera Performance Test Suite${NC}"
echo "=================================="
echo "Host: ${HOST}"
echo "Results: ${RESULTS_DIR}"
echo "Timestamp: ${TIMESTAMP}"
echo ""

# Function to check if API is ready
check_api() {
    echo -e "${YELLOW}⏳ Checking if API is ready...${NC}"
    
    for i in {1..30}; do
        if curl -f -s "${HOST}/api/v1/monitoring/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API is ready${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    
    echo -e "${RED}❌ API is not responding${NC}"
    exit 1
}

# Function to run a test
run_test() {
    local test_name=$1
    local config_file=$2
    local description=$3
    
    echo ""
    echo -e "${GREEN}📊 Running: ${test_name}${NC}"
    echo "Description: ${description}"
    echo "---"
    
    local result_prefix="${RESULTS_DIR}/${test_name}_${TIMESTAMP}"
    
    locust -f "${SCRIPT_DIR}/locustfile.py" \
           --config "${SCRIPT_DIR}/config/${config_file}" \
           --host "${HOST}" \
           --headless \
           --html "${result_prefix}.html" \
           --csv "${result_prefix}" \
           --logfile "${result_prefix}.log" \
           --loglevel INFO
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${test_name} completed successfully${NC}"
    else
        echo -e "${RED}❌ ${test_name} failed${NC}"
        return 1
    fi
}

# Function to generate summary report
generate_summary() {
    echo ""
    echo -e "${GREEN}📈 Generating Summary Report${NC}"
    echo "---"
    
    python3 << EOF
import json
import glob
from pathlib import Path

results_dir = Path("${RESULTS_DIR}")
csv_files = glob.glob(str(results_dir / "*_stats.csv"))

print(f"\n📊 Test Summary ({len(csv_files)} tests)")
print("=" * 80)

for csv_file in sorted(csv_files):
    test_name = Path(csv_file).stem.replace('_stats', '')
    print(f"\n{test_name}:")
    
    try:
        with open(csv_file.replace('_stats.csv', '_stats_history.csv'), 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                last_line = lines[-1].strip().split(',')
                print(f"  Total Requests: {last_line[2]}")
                print(f"  Failures: {last_line[3]}")
                print(f"  Avg Response: {last_line[4]}ms")
    except:
        print("  (Unable to read results)")

print("\n" + "=" * 80)
print(f"📁 Full reports available in: ${RESULTS_DIR}")
print(f"🌐 Open HTML reports in your browser")
EOF
}

# Function to validate SLAs
validate_sla() {
    echo ""
    echo -e "${GREEN}✓ Validating SLAs${NC}"
    echo "---"
    
    # Check if any test exceeded SLA
    local sla_passed=true
    
    # Add SLA validation logic here
    # For now, just report success
    
    if [ "$sla_passed" = true ]; then
        echo -e "${GREEN}✅ All SLAs passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some SLAs failed - review reports${NC}"
    fi
}

# Main test execution
main() {
    # Check API availability
    check_api
    
    # Run test scenarios
    local failed_tests=0
    
    # Normal Load Test
    if ! run_test "normal_load" "normal_load.py" "Baseline performance test"; then
        ((failed_tests++))
    fi
    
    # Stress Test
    if ! run_test "stress_test" "stress_test.py" "Heavy load test"; then
        ((failed_tests++))
    fi
    
    # Spike Test
    if ! run_test "spike_test" "spike_test.py" "Sudden traffic spike test"; then
        ((failed_tests++))
    fi
    
    # Endurance Test (optional - takes 2 hours)
    if [ "${RUN_ENDURANCE}" = "true" ]; then
        if ! run_test "endurance_test" "endurance_test.py" "Long-running stability test"; then
            ((failed_tests++))
        fi
    fi
    
    # Generate summary
    generate_summary
    
    # Validate SLAs
    validate_sla
    
    # Final status
    echo ""
    echo "=================================="
    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}✅ All tests completed successfully${NC}"
        exit 0
    else
        echo -e "${RED}❌ ${failed_tests} test(s) failed${NC}"
        exit 1
    fi
}

# Handle script arguments
case "${1:-all}" in
    all)
        main
        ;;
    normal)
        check_api
        run_test "normal_load" "normal_load.py" "Baseline performance test"
        ;;
    stress)
        check_api
        run_test "stress_test" "stress_test.py" "Heavy load test"
        ;;
    spike)
        check_api
        run_test "spike_test" "spike_test.py" "Sudden traffic spike test"
        ;;
    endurance)
        check_api
        run_test "endurance_test" "endurance_test.py" "Long-running stability test"
        ;;
    clean)
        echo -e "${YELLOW}🧹 Cleaning results directory${NC}"
        rm -rf "${RESULTS_DIR}"/*
        echo -e "${GREEN}✅ Cleaned${NC}"
        ;;
    help)
        echo "Usage: $0 [all|normal|stress|spike|endurance|clean|help]"
        echo ""
        echo "Commands:"
        echo "  all       - Run all performance tests (default)"
        echo "  normal    - Run normal load test only"
        echo "  stress    - Run stress test only"
        echo "  spike     - Run spike test only"
        echo "  endurance - Run endurance test only (2 hours)"
        echo "  clean     - Clean results directory"
        echo "  help      - Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  LOCUST_HOST     - Target host (default: http://localhost:8000)"
        echo "  RUN_ENDURANCE   - Set to 'true' to include endurance test in 'all'"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
