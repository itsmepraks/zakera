#!/bin/bash
# Zakera Performance Testing Runner Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SCENARIO="normal"
HEADLESS=false
WEB_UI=false
HOST="${BASE_URL:-http://localhost:8000}"
USERS=""
SPAWN_RATE=""
RUN_TIME=""
REPORT=true

# Help message
show_help() {
    echo -e "${GREEN}Zakera Performance Testing Runner${NC}"
    echo ""
    echo "Usage: ./run_tests.sh [scenario] [options]"
    echo ""
    echo "Scenarios:"
    echo "  normal       - Normal load test (default)"
    echo "  stress       - Stress test"
    echo "  spike        - Spike test"
    echo "  endurance    - Endurance test (24h)"
    echo ""
    echo "Options:"
    echo "  --headless           Run without web UI"
    echo "  --web-ui             Run with web UI (default: false)"
    echo "  --host HOST          Target host (default: \$BASE_URL or localhost:8000)"
    echo "  --users NUM          Number of users"
    echo "  --spawn-rate NUM     Users spawned per second"
    echo "  --run-time TIME      Test duration (e.g., 10m, 1h)"
    echo "  --no-report          Don't generate report"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh normal"
    echo "  ./run_tests.sh stress --headless"
    echo "  ./run_tests.sh spike --users 200 --run-time 15m"
    echo "  ./run_tests.sh normal --host https://api.zakera.ai"
    echo ""
}

# Parse arguments
if [ $# -eq 0 ]; then
    SCENARIO="normal"
else
    SCENARIO="$1"
    shift
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --headless)
            HEADLESS=true
            shift
            ;;
        --web-ui)
            WEB_UI=true
            HEADLESS=false
            shift
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --users)
            USERS="$2"
            shift 2
            ;;
        --spawn-rate)
            SPAWN_RATE="$2"
            shift 2
            ;;
        --run-time)
            RUN_TIME="$2"
            shift 2
            ;;
        --no-report)
            REPORT=false
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Validate scenario
if [[ ! "$SCENARIO" =~ ^(normal|stress|spike|endurance)$ ]]; then
    echo -e "${RED}Invalid scenario: $SCENARIO${NC}"
    echo "Valid scenarios: normal, stress, spike, endurance"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    echo -e "${BLUE}Loading environment variables...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${RED}Locust is not installed!${NC}"
    echo "Install it with: pip install -r requirements.txt"
    exit 1
fi

# Create reports directory
mkdir -p reports

# Select configuration file
CONFIG_FILE="config/${SCENARIO}_load.yaml"
if [ "$SCENARIO" = "normal" ]; then
    CONFIG_FILE="config/normal_load.yaml"
elif [ "$SCENARIO" = "stress" ]; then
    CONFIG_FILE="config/stress_test.yaml"
elif [ "$SCENARIO" = "spike" ]; then
    CONFIG_FILE="config/spike_test.yaml"
elif [ "$SCENARIO" = "endurance" ]; then
    CONFIG_FILE="config/endurance_test.yaml"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Select locustfile (default to mixed scenario for comprehensive testing)
LOCUSTFILE="locustfiles/mixed_scenario_test.py"

# Build Locust command
CMD="locust -f $LOCUSTFILE --config $CONFIG_FILE --host $HOST"

# Add custom parameters if provided
if [ -n "$USERS" ]; then
    CMD="$CMD --users $USERS"
fi

if [ -n "$SPAWN_RATE" ]; then
    CMD="$CMD --spawn-rate $SPAWN_RATE"
fi

if [ -n "$RUN_TIME" ]; then
    CMD="$CMD --run-time $RUN_TIME"
fi

# Add headless mode
if [ "$HEADLESS" = true ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    CMD="$CMD --headless --html reports/${SCENARIO}_${TIMESTAMP}.html --csv reports/${SCENARIO}_${TIMESTAMP}"
fi

# Print test information
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Zakera Performance Test${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Scenario:${NC} $SCENARIO"
echo -e "${BLUE}Target:${NC} $HOST"
echo -e "${BLUE}Config:${NC} $CONFIG_FILE"
echo -e "${BLUE}Headless:${NC} $HEADLESS"
if [ "$SCENARIO" = "endurance" ]; then
    echo -e "${YELLOW}⚠ Warning: Endurance test will run for 24 hours!${NC}"
fi
echo -e "${GREEN}========================================${NC}"
echo ""

# Run the test
echo -e "${GREEN}Starting test...${NC}"
echo "Command: $CMD"
echo ""

if eval "$CMD"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Test completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Generate additional reports if requested
    if [ "$REPORT" = true ] && [ "$HEADLESS" = true ]; then
        echo ""
        echo -e "${BLUE}Generating additional reports...${NC}"
        
        # Generate markdown summary
        LATEST_JSON=$(ls -t reports/${SCENARIO}_*.json 2>/dev/null | head -n 1)
        if [ -f "$LATEST_JSON" ]; then
            python -c "
import json
import sys
with open('$LATEST_JSON', 'r') as f:
    data = json.load(f)
    print('\\n## Test Summary')
    print(f'\\n**Scenario:** $SCENARIO')
    print(f'**Timestamp:** $(date)')
    print('\\n### Results')
    if 'stats' in data:
        for stat in data['stats']:
            if stat['name'] != 'Aggregated':
                print(f'- {stat[\"name\"]}: {stat[\"num_requests\"]} requests, avg: {stat[\"avg_response_time\"]:.2f}ms')
" > reports/${SCENARIO}_summary.md
            echo -e "${GREEN}Summary generated: reports/${SCENARIO}_summary.md${NC}"
        fi
    fi
    
    # Print summary
    echo ""
    echo -e "${BLUE}Reports saved in: ${NC}reports/"
    echo -e "${BLUE}Open HTML report: ${NC}reports/${SCENARIO}_${TIMESTAMP}.html"
    
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Test failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
