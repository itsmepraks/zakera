# Zakera Performance Testing Makefile

.PHONY: help install test-normal test-stress test-spike test-endurance test-api test-websocket test-providers test-mixed test-all report clean

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help:
	@echo "$(GREEN)Zakera Performance Testing$(NC)"
	@echo ""
	@echo "Available targets:"
	@echo "  $(YELLOW)install$(NC)          - Install dependencies"
	@echo "  $(YELLOW)test-normal$(NC)      - Run normal load test"
	@echo "  $(YELLOW)test-stress$(NC)      - Run stress test"
	@echo "  $(YELLOW)test-spike$(NC)       - Run spike test"
	@echo "  $(YELLOW)test-endurance$(NC)   - Run endurance test (24h)"
	@echo "  $(YELLOW)test-api$(NC)         - Test API endpoints"
	@echo "  $(YELLOW)test-websocket$(NC)   - Test WebSocket connections"
	@echo "  $(YELLOW)test-providers$(NC)   - Test model providers"
	@echo "  $(YELLOW)test-mixed$(NC)       - Test mixed scenarios"
	@echo "  $(YELLOW)test-all$(NC)         - Run all tests"
	@echo "  $(YELLOW)report$(NC)           - Generate reports"
	@echo "  $(YELLOW)clean$(NC)            - Clean up reports"
	@echo ""

install:
	@echo "$(GREEN)Installing dependencies...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

test-normal:
	@echo "$(GREEN)Running normal load test...$(NC)"
	./run_tests.sh normal --headless

test-stress:
	@echo "$(YELLOW)Running stress test...$(NC)"
	./run_tests.sh stress --headless

test-spike:
	@echo "$(YELLOW)Running spike test...$(NC)"
	./run_tests.sh spike --headless

test-endurance:
	@echo "$(RED)Running endurance test (24 hours)...$(NC)"
	@echo "$(YELLOW)Warning: This will run for 24 hours!$(NC)"
	./run_tests.sh endurance --headless

test-api:
	@echo "$(GREEN)Testing API endpoints...$(NC)"
	locust -f locustfiles/api_load_test.py --config config/normal_load.yaml --headless

test-websocket:
	@echo "$(GREEN)Testing WebSocket connections...$(NC)"
	locust -f locustfiles/websocket_load_test.py --config config/normal_load.yaml --headless

test-providers:
	@echo "$(GREEN)Testing model providers...$(NC)"
	locust -f locustfiles/model_provider_test.py --config config/normal_load.yaml --headless

test-mixed:
	@echo "$(GREEN)Testing mixed scenarios...$(NC)"
	locust -f locustfiles/mixed_scenario_test.py --config config/normal_load.yaml --headless

test-all:
	@echo "$(GREEN)Running all tests...$(NC)"
	make test-api
	make test-websocket
	make test-providers
	make test-mixed
	@echo "$(GREEN)All tests completed!$(NC)"

report:
	@echo "$(GREEN)Generating reports...$(NC)"
	python utils/report_generator.py --input reports/*.json --output reports/comprehensive_report.html
	@echo "$(GREEN)Reports generated in reports/ directory$(NC)"

clean:
	@echo "$(YELLOW)Cleaning up reports...$(NC)"
	rm -rf reports/*.html reports/*.csv reports/*.json reports/*.pdf
	@echo "$(GREEN)Reports cleaned!$(NC)"

# Docker targets
docker-build:
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker-compose -f docker-compose.performance.yml build

docker-test:
	@echo "$(GREEN)Running tests in Docker...$(NC)"
	docker-compose -f docker-compose.performance.yml up

docker-clean:
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	docker-compose -f docker-compose.performance.yml down -v

# Development targets
dev-ui:
	@echo "$(GREEN)Starting Locust Web UI...$(NC)"
	locust -f locustfiles/api_load_test.py

# Continuous testing
watch:
	@echo "$(GREEN)Running tests continuously...$(NC)"
	while true; do make test-normal; sleep 3600; done
