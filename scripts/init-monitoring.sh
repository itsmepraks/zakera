#!/bin/bash
# Initialize monitoring stack for Zakera
# Sets up Prometheus, Grafana, Jaeger, and associated services

set -e

COLOR_RESET="\033[0m"
COLOR_BLUE="\033[34m"
COLOR_GREEN="\033[32m"
COLOR_YELLOW="\033[33m"
COLOR_RED="\033[31m"

echo -e "${COLOR_BLUE}Initializing Zakera Monitoring Stack${COLOR_RESET}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${COLOR_RED}Error: Docker is not running${COLOR_RESET}"
    exit 1
fi

echo -e "${COLOR_GREEN}✓ Docker is running${COLOR_RESET}"

# Create directories
echo -e "${COLOR_BLUE}Creating directories...${COLOR_RESET}"
mkdir -p monitoring/grafana/dashboards/{performance,infrastructure,application}
mkdir -p monitoring/grafana/provisioning/{dashboards,datasources,notifiers}
mkdir -p monitoring/prometheus/rules
mkdir -p logs
mkdir -p data/{prometheus,grafana,loki,jaeger}

echo -e "${COLOR_GREEN}✓ Directories created${COLOR_RESET}"

# Set permissions
echo -e "${COLOR_BLUE}Setting permissions...${COLOR_RESET}"
chmod -R 755 monitoring/
chown -R 472:472 data/grafana 2>/dev/null || true  # Grafana user

echo -e "${COLOR_GREEN}✓ Permissions set${COLOR_RESET}"

# Validate configuration files
echo -e "${COLOR_BLUE}Validating configurations...${COLOR_RESET}"

# Validate Prometheus config
if docker run --rm -v "$(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml" \
    prom/prometheus:latest \
    promtool check config /etc/prometheus/prometheus.yml > /dev/null 2>&1; then
    echo -e "${COLOR_GREEN}✓ Prometheus configuration is valid${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Prometheus configuration is invalid${COLOR_RESET}"
    exit 1
fi

# Start monitoring stack
echo ""
echo -e "${COLOR_BLUE}Starting monitoring stack...${COLOR_RESET}"
docker-compose -f docker-compose.dev.yml up -d prometheus grafana jaeger

echo ""
echo -e "${COLOR_GREEN}Waiting for services to be healthy...${COLOR_RESET}"
sleep 10

# Check service health
echo ""
echo -e "${COLOR_BLUE}Checking service health:${COLOR_RESET}"

# Check Prometheus
if curl -sf http://localhost:9090/-/healthy > /dev/null; then
    echo -e "${COLOR_GREEN}✓ Prometheus is healthy${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ Prometheus health check failed${COLOR_RESET}"
fi

# Check Grafana
if curl -sf http://localhost:3001/api/health > /dev/null; then
    echo -e "${COLOR_GREEN}✓ Grafana is healthy${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ Grafana health check failed${COLOR_RESET}"
fi

# Check Jaeger
if curl -sf http://localhost:16686/ > /dev/null; then
    echo -e "${COLOR_GREEN}✓ Jaeger is healthy${COLOR_RESET}"
else
    echo -e "${COLOR_YELLOW}⚠ Jaeger health check failed${COLOR_RESET}"
fi

echo ""
echo -e "${COLOR_GREEN}========================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}Monitoring Stack Initialized!${COLOR_RESET}"
echo -e "${COLOR_GREEN}========================================${COLOR_RESET}"
echo ""
echo "Access URLs:"
echo -e "  Prometheus:  ${COLOR_BLUE}http://localhost:9090${COLOR_RESET}"
echo -e "  Grafana:     ${COLOR_BLUE}http://localhost:3001${COLOR_RESET} (admin/admin)"
echo -e "  Jaeger:      ${COLOR_BLUE}http://localhost:16686${COLOR_RESET}"
echo ""
echo "Grafana Dashboards:"
echo "  • Performance Testing"
echo "  • Redis Cache Performance"
echo "  • API Performance & Health"
echo ""
echo "Next Steps:"
echo "  1. Start the application: make dev"
echo "  2. Generate some traffic"
echo "  3. View metrics in Grafana"
echo "  4. Run performance tests: make perf-test-normal"
echo ""
