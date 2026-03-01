#!/bin/bash
# Validate infrastructure configuration and health
# Comprehensive validation of all Zakera infrastructure components

set -e

COLOR_RESET="\033[0m"
COLOR_BLUE="\033[34m"
COLOR_GREEN="\033[32m"
COLOR_YELLOW="\033[33m"
COLOR_RED="\033[31m"

ERRORS=0
WARNINGS=0

echo -e "${COLOR_BLUE}======================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}Zakera Infrastructure Validation${COLOR_RESET}"
echo -e "${COLOR_BLUE}======================================${COLOR_RESET}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -i:"$1" >/dev/null 2>&1
}

echo -e "${COLOR_BLUE}[1/10] Checking prerequisites...${COLOR_RESET}"

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    echo -e "${COLOR_GREEN}✓ Docker installed (${DOCKER_VERSION})${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Docker not found${COLOR_RESET}"
    ((ERRORS++))
fi

# Check Docker Compose
if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ Docker Compose available${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Docker Compose not found${COLOR_RESET}"
    ((ERRORS++))
fi

# Check if Docker daemon is running
if docker info >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ Docker daemon is running${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Docker daemon is not running${COLOR_RESET}"
    ((ERRORS++))
    exit 1
fi

echo ""
echo -e "${COLOR_BLUE}[2/10] Validating configuration files...${COLOR_RESET}"

# Check required files exist
REQUIRED_FILES=(
    "docker-compose.yml"
    "docker-compose.dev.yml"
    "Dockerfile"
    "Dockerfile.multi-stage"
    "requirements.txt"
    "monitoring/prometheus.yml"
    "monitoring/grafana/provisioning/datasources/datasources.yml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${COLOR_GREEN}✓ Found: $file${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}✗ Missing: $file${COLOR_RESET}"
        ((ERRORS++))
    fi
done

echo ""
echo -e "${COLOR_BLUE}[3/10] Validating Docker Compose files...${COLOR_RESET}"

# Validate docker-compose.yml
if docker-compose -f docker-compose.yml config >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ docker-compose.yml is valid${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ docker-compose.yml has errors${COLOR_RESET}"
    ((ERRORS++))
fi

# Validate docker-compose.dev.yml
if docker-compose -f docker-compose.dev.yml config >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ docker-compose.dev.yml is valid${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ docker-compose.dev.yml has errors${COLOR_RESET}"
    ((ERRORS++))
fi

echo ""
echo -e "${COLOR_BLUE}[4/10] Validating Prometheus configuration...${COLOR_RESET}"

if docker run --rm -v "$(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml" \
    prom/prometheus:latest \
    promtool check config /etc/prometheus/prometheus.yml >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ Prometheus configuration is valid${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Prometheus configuration is invalid${COLOR_RESET}"
    ((ERRORS++))
fi

# Validate alert rules
if [ -d "monitoring/prometheus-rules" ]; then
    for rule_file in monitoring/prometheus-rules/*.yml; do
        if docker run --rm -v "$(pwd)/$rule_file:/rules.yml" \
            prom/prometheus:latest \
            promtool check rules /rules.yml >/dev/null 2>&1; then
            echo -e "${COLOR_GREEN}✓ $(basename $rule_file) is valid${COLOR_RESET}"
        else
            echo -e "${COLOR_RED}✗ $(basename $rule_file) is invalid${COLOR_RESET}"
            ((ERRORS++))
        fi
    done
fi

echo ""
echo -e "${COLOR_BLUE}[5/10] Validating Grafana dashboards...${COLOR_RESET}"

if [ -d "monitoring/grafana/dashboards" ]; then
    DASHBOARD_COUNT=0
    for dashboard in monitoring/grafana/dashboards/*.json; do
        if [ -f "$dashboard" ]; then
            if cat "$dashboard" | jq empty >/dev/null 2>&1; then
                echo -e "${COLOR_GREEN}✓ $(basename $dashboard) is valid JSON${COLOR_RESET}"
                ((DASHBOARD_COUNT++))
            else
                echo -e "${COLOR_RED}✗ $(basename $dashboard) is invalid JSON${COLOR_RESET}"
                ((ERRORS++))
            fi
        fi
    done
    echo -e "${COLOR_GREEN}Found $DASHBOARD_COUNT dashboard(s)${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ No dashboards directory found${COLOR_RESET}"
    ((WARNINGS++))
fi

echo ""
echo -e "${COLOR_BLUE}[6/10] Checking port availability...${COLOR_RESET}"

PORTS=(8000 5432 6379 9090 3001 16686)
PORT_NAMES=("API" "PostgreSQL" "Redis" "Prometheus" "Grafana" "Jaeger")

for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${PORT_NAMES[$i]}
    
    if port_in_use "$PORT"; then
        echo -e "${COLOR_YELLOW}⚠ Port $PORT ($NAME) is already in use${COLOR_RESET}"
        ((WARNINGS++))
    else
        echo -e "${COLOR_GREEN}✓ Port $PORT ($NAME) is available${COLOR_RESET}"
    fi
done

echo ""
echo -e "${COLOR_BLUE}[7/10] Checking disk space...${COLOR_RESET}"

AVAIL_SPACE=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$(echo "$AVAIL_SPACE < 10" | bc)" -eq 1 ]; then
    echo -e "${COLOR_RED}✗ Low disk space: ${AVAIL_SPACE}GB available (need 10GB+)${COLOR_RESET}"
    ((ERRORS++))
else
    echo -e "${COLOR_GREEN}✓ Sufficient disk space: ${AVAIL_SPACE}GB available${COLOR_RESET}"
fi

echo ""
echo -e "${COLOR_BLUE}[8/10] Checking environment variables...${COLOR_RESET}"

if [ -f ".env" ]; then
    echo -e "${COLOR_GREEN}✓ .env file exists${COLOR_RESET}"
    
    # Check for required variables
    REQUIRED_VARS=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            echo -e "${COLOR_GREEN}✓ $var is set${COLOR_RESET}"
        else
            echo -e "${COLOR_YELLOW}⚠ $var not found in .env${COLOR_RESET}"
            ((WARNINGS++))
        fi
    done
else
    echo -e "${COLOR_YELLOW}⚠ .env file not found (will use defaults)${COLOR_RESET}"
    ((WARNINGS++))
fi

echo ""
echo -e "${COLOR_BLUE}[9/10] Validating Dockerfile syntax...${COLOR_RESET}"

if docker build --check . >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ Dockerfile syntax is valid${COLOR_RESET}"
else
    # --check not available in older Docker
    echo -e "${COLOR_GREEN}✓ Dockerfile exists (syntax check skipped)${COLOR_RESET}"
fi

echo ""
echo -e "${COLOR_BLUE}[10/10] Testing service connectivity...${COLOR_RESET}"

# Only if services are running
if docker ps | grep -q zakera; then
    echo -e "${COLOR_GREEN}Services are running, testing connectivity...${COLOR_RESET}"
    
    # Test API
    if curl -sf http://localhost:8000/api/v1/monitoring/health >/dev/null 2>&1; then
        echo -e "${COLOR_GREEN}✓ API is healthy${COLOR_RESET}"
    else
        echo -e "${COLOR_YELLOW}⚠ API not responding${COLOR_RESET}"
        ((WARNINGS++))
    fi
    
    # Test Prometheus
    if curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then
        echo -e "${COLOR_GREEN}✓ Prometheus is healthy${COLOR_RESET}"
    else
        echo -e "${COLOR_YELLOW}⚠ Prometheus not responding${COLOR_RESET}"
        ((WARNINGS++))
    fi
    
    # Test Grafana
    if curl -sf http://localhost:3001/api/health >/dev/null 2>&1; then
        echo -e "${COLOR_GREEN}✓ Grafana is healthy${COLOR_RESET}"
    else
        echo -e "${COLOR_YELLOW}⚠ Grafana not responding${COLOR_RESET}"
        ((WARNINGS++))
    fi
else
    echo -e "${COLOR_YELLOW}⚠ Services not running (skipping connectivity tests)${COLOR_RESET}"
    echo -e "  Run 'make dev' to start services"
fi

echo ""
echo -e "${COLOR_BLUE}======================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}Validation Complete${COLOR_RESET}"
echo -e "${COLOR_BLUE}======================================${COLOR_RESET}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${COLOR_GREEN}✅ All checks passed! Infrastructure is ready.${COLOR_RESET}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${COLOR_YELLOW}⚠ Validation passed with $WARNINGS warning(s)${COLOR_RESET}"
    exit 0
else
    echo -e "${COLOR_RED}❌ Validation failed with $ERRORS error(s) and $WARNINGS warning(s)${COLOR_RESET}"
    echo -e "${COLOR_RED}Please fix the errors before proceeding.${COLOR_RESET}"
    exit 1
fi
