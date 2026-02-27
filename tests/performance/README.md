# Zakera Performance Testing Suite

Comprehensive performance testing infrastructure for the Zakera AI Chat Agent using Locust.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Test Scenarios](#test-scenarios)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Reporting](#reporting)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This performance testing suite provides comprehensive load testing capabilities for:

- **REST API Endpoints**: Chat, conversation management, user operations
- **WebSocket Connections**: Real-time chat streaming
- **Model Provider Interactions**: Testing all 8 LLM providers
- **Mixed Scenarios**: Realistic usage patterns

### Key Metrics Tracked

- Request latency (p50, p95, p99)
- Throughput (requests/second)
- Error rate by endpoint
- WebSocket connection stability
- Model provider response times
- Token consumption rates
- System resource utilization

## ✨ Features

### Test Types

1. **API Load Testing** (`api_load_test.py`)
   - Chat message endpoints
   - Conversation management
   - User authentication
   - Tool execution

2. **WebSocket Testing** (`websocket_load_test.py`)
   - Real-time message streaming
   - Connection stability
   - Concurrent connections
   - Reconnection behavior

3. **Model Provider Testing** (`model_provider_test.py`)
   - All 8 providers (OpenAI, Anthropic, Gemini, etc.)
   - Provider-specific latencies
   - Failover scenarios
   - Cost tracking

4. **Mixed Scenario Testing** (`mixed_scenario_test.py`)
   - Realistic user behavior
   - Combined REST + WebSocket
   - Tool usage patterns
   - Conversation flows

### Test Scenarios

1. **Normal Load** - Typical production traffic
2. **Stress Test** - Find breaking points
3. **Spike Test** - Sudden traffic increases
4. **Endurance Test** - Long-running stability

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.9+
python --version

# Install dependencies
cd tests/performance
pip install -r requirements.txt
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit with your configuration
BASE_URL=http://localhost:8000
API_KEY=your-api-key-here
WS_URL=ws://localhost:8000
```

### Run Your First Test

```bash
# Using Makefile (recommended)
make test-normal

# Or directly with Locust
locust -f locustfiles/api_load_test.py --config config/normal_load.yaml

# With web UI
locust -f locustfiles/api_load_test.py --host http://localhost:8000
# Then open http://localhost:8089
```

## 📊 Test Scenarios

### 1. Normal Load Test

**Purpose**: Simulate typical production traffic

**Configuration** (`config/normal_load.yaml`):
```yaml
users: 50
spawn_rate: 5
run_time: 10m
```

**Expected Results**:
- Avg response time: < 500ms
- 95th percentile: < 1000ms
- Error rate: < 1%

**Run**:
```bash
make test-normal
# or
./run_tests.sh normal
```

### 2. Stress Test

**Purpose**: Find system breaking points

**Configuration** (`config/stress_test.yaml`):
```yaml
users: 500
spawn_rate: 20
run_time: 30m
```

**Goals**:
- Identify maximum capacity
- Find bottlenecks
- Test error handling
- Observe degradation patterns

**Run**:
```bash
make test-stress
# or
./run_tests.sh stress
```

### 3. Spike Test

**Purpose**: Test sudden traffic increases

**Configuration** (`config/spike_test.yaml`):
```yaml
users: 200
spawn_rate: 100  # Rapid ramp-up
run_time: 15m
```

**Scenarios**:
- Sudden user influx
- Auto-scaling trigger
- Recovery behavior

**Run**:
```bash
make test-spike
# or
./run_tests.sh spike
```

### 4. Endurance Test

**Purpose**: Long-running stability test

**Configuration** (`config/endurance_test.yaml`):
```yaml
users: 100
spawn_rate: 10
run_time: 24h
```

**Monitors**:
- Memory leaks
- Connection pool exhaustion
- Database performance degradation
- Log accumulation

**Run**:
```bash
make test-endurance
# or
./run_tests.sh endurance
```

## ⚙️ Configuration

### Configuration Files

All scenarios use YAML configuration in `config/`:

```yaml
# Example: config/normal_load.yaml
users: 50                    # Total concurrent users
spawn_rate: 5                # Users added per second
run_time: 10m                # Test duration
host: http://localhost:8000  # Target host

# Advanced options
stop_timeout: 10
web_port: 8089
headless: false
loglevel: INFO

# Custom tags
tags:
  - api
  - chat
```

### Environment Variables

```bash
# .env file
BASE_URL=http://localhost:8000
API_KEY=your-test-api-key
WS_URL=ws://localhost:8000

# Authentication
JWT_SECRET=your-jwt-secret
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=testpass123

# Model providers (for provider testing)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Test data
TEST_DATA_DIR=./test_data
RESULTS_DIR=./reports

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3001
```

## 🏃 Running Tests

### Using Makefile (Recommended)

```bash
# Run specific scenario
make test-normal      # Normal load test
make test-stress      # Stress test
make test-spike       # Spike test
make test-endurance   # Endurance test

# Run specific test file
make test-api         # API endpoints only
make test-websocket   # WebSocket only
make test-providers   # Model providers only
make test-mixed       # Mixed scenarios

# Run all tests
make test-all

# Generate report
make report

# Clean up
make clean
```

### Using run_tests.sh

```bash
# Basic usage
./run_tests.sh [scenario] [options]

# Examples
./run_tests.sh normal
./run_tests.sh stress --users 1000
./run_tests.sh spike --headless
./run_tests.sh endurance --run-time 48h

# With custom host
./run_tests.sh normal --host https://api.zakera.ai

# With web UI
./run_tests.sh normal --web-ui
```

### Using Docker

```bash
# Build performance testing image
docker-compose -f docker-compose.performance.yml build

# Run tests in container
docker-compose -f docker-compose.performance.yml up

# Run specific scenario
docker-compose -f docker-compose.performance.yml run performance normal

# With custom configuration
docker-compose -f docker-compose.performance.yml run performance stress --users 1000
```

### Direct Locust Usage

```bash
# Web UI mode (interactive)
locust -f locustfiles/api_load_test.py --host http://localhost:8000
# Open http://localhost:8089

# Headless mode (automated)
locust -f locustfiles/api_load_test.py \
  --host http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 10m \
  --headless \
  --html reports/results.html

# Distributed mode (multiple workers)
locust -f locustfiles/api_load_test.py --master &
locust -f locustfiles/api_load_test.py --worker &
locust -f locustfiles/api_load_test.py --worker &
```

## 📈 Reporting

### Built-in Reports

Locust generates several report formats:

```bash
# HTML report (default)
--html reports/results.html

# CSV reports
--csv reports/results
# Generates:
# - results_stats.csv
# - results_stats_history.csv
# - results_failures.csv

# JSON report (for programmatic analysis)
--json reports/results.json
```

### Custom Report Generation

```bash
# Generate comprehensive report
python utils/report_generator.py \
  --input reports/results.json \
  --output reports/analysis.html \
  --format html

# Compare multiple test runs
python utils/report_generator.py \
  --compare reports/run1.json reports/run2.json \
  --output reports/comparison.html

# Export to PDF
python utils/report_generator.py \
  --input reports/results.json \
  --output reports/report.pdf \
  --format pdf
```

### Metrics Collection

```python
# Custom metrics are collected automatically
from utils.metrics_collector import MetricsCollector

metrics = MetricsCollector()
metrics.collect()

# Available metrics:
# - API endpoint performance
# - WebSocket connection stats
# - Model provider latencies
# - Error rates and types
# - Resource utilization
# - Cost estimates
```

### Report Contents

1. **Executive Summary**
   - Test configuration
   - Overall results
   - Pass/fail criteria
   - Recommendations

2. **Performance Metrics**
   - Response time distribution
   - Throughput over time
   - Error rate analysis
   - Latency percentiles

3. **Endpoint Analysis**
   - Per-endpoint statistics
   - Slowest endpoints
   - Most error-prone endpoints
   - Request distribution

4. **Resource Utilization**
   - CPU usage
   - Memory consumption
   - Network bandwidth
   - Database connections

5. **Model Provider Stats**
   - Response times by provider
   - Token consumption
   - Cost analysis
   - Failure rates

6. **Charts and Graphs**
   - Time series plots
   - Distribution histograms
   - Heatmaps
   - Comparison charts

## 🔄 CI/CD Integration

### GitHub Actions

Add to `.github/workflows/performance-tests.yml`:

```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:
    inputs:
      scenario:
        description: 'Test scenario'
        required: true
        default: 'normal'
        type: choice
        options:
          - normal
          - stress
          - spike

jobs:
  performance-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          cd tests/performance
          pip install -r requirements.txt
      
      - name: Run performance tests
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}
          API_KEY: ${{ secrets.TEST_API_KEY }}
        run: |
          cd tests/performance
          ./run_tests.sh ${{ github.event.inputs.scenario || 'normal' }} --headless
      
      - name: Generate report
        run: |
          cd tests/performance
          make report
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: tests/performance/reports/
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('tests/performance/reports/summary.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

### Performance Benchmarks

Set performance benchmarks that fail the build:

```yaml
# tests/performance/benchmarks.yaml
api_endpoints:
  /api/v1/chat/send:
    p95_latency_ms: 1000
    error_rate_percent: 1.0
  /api/v1/conversations:
    p95_latency_ms: 500
    error_rate_percent: 0.5

websocket:
  connection_success_rate: 99.0
  message_latency_ms: 500

model_providers:
  openai:
    p95_latency_ms: 2000
  anthropic:
    p95_latency_ms: 2500
  gemini:
    p95_latency_ms: 1500

system:
  max_error_rate_percent: 2.0
  min_throughput_rps: 100
```

## 📚 Best Practices

### 1. Test Environment

- Use dedicated staging environment
- Match production configuration
- Isolate from production traffic
- Use realistic data volumes

### 2. Test Data

```python
# Use realistic test data
from utils.data_generator import DataGenerator

generator = DataGenerator()

# Generate varied messages
messages = generator.generate_messages(
    count=1000,
    topics=['tech', 'science', 'general'],
    lengths=['short', 'medium', 'long']
)

# Use different user personas
users = generator.generate_users(
    count=100,
    types=['casual', 'power', 'api']
)
```

### 3. Gradual Load Increase

```python
# Don't spike from 0 to 1000 users instantly
spawn_rate = 10  # Add 10 users per second

# Allow warmup period
wait_time = between(1, 5)  # Seconds between requests
```

### 4. Monitor During Tests

```bash
# Watch system metrics
watch -n 1 'docker stats'

# Monitor Prometheus
curl http://localhost:9090/api/v1/query?query=rate(http_requests_total[1m])

# Check logs
tail -f logs/api.log
```

### 5. Interpret Results

- **Look for patterns**: Gradual degradation vs sudden failure
- **Check error types**: Timeouts vs 500 errors vs connection failures
- **Identify bottlenecks**: CPU, memory, database, external APIs
- **Consider costs**: Model API costs during high load

### 6. Iterate and Improve

1. Establish baseline metrics
2. Run tests after changes
3. Compare results
4. Document findings
5. Set alerts for regressions

## 🐛 Troubleshooting

### Common Issues

#### 1. Connection Errors

```bash
# Issue: Cannot connect to host
# Solution: Check if API is running
curl http://localhost:8000/api/v1/health

# Check network
ping localhost
telnet localhost 8000
```

#### 2. Authentication Failures

```bash
# Issue: 401 Unauthorized
# Solution: Check API key
echo $API_KEY

# Test authentication
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/user/me
```

#### 3. High Error Rates

```python
# Issue: Many 500 errors
# Solution: Check API logs
tail -f logs/api.log | grep ERROR

# Check database connections
ps aux | grep postgres

# Monitor system resources
top
free -h
df -h
```

#### 4. WebSocket Connection Issues

```python
# Issue: WebSocket connections failing
# Solution: Check WebSocket endpoint
wscat -c ws://localhost:8000/api/v1/chat/ws

# Check nginx config (if using)
nginx -t

# Verify WebSocket support
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8000/api/v1/chat/ws
```

#### 5. Test Hangs or Stalls

```bash
# Issue: Locust stops responding
# Solution: Check for deadlocks
ps aux | grep locust
kill -9 <pid>

# Restart with debug logging
locust -f locustfiles/api_load_test.py --loglevel DEBUG

# Check system resources
df -h  # Disk space
free -h  # Memory
```

### Debug Mode

```bash
# Run with verbose logging
export LOGLEVEL=DEBUG
./run_tests.sh normal

# Enable Locust debug output
locust -f locustfiles/api_load_test.py --loglevel DEBUG

# Print all HTTP requests/responses
export LOCUST_DEBUG_HTTP=1
```

### Getting Help

1. Check logs in `reports/` directory
2. Review Locust documentation: https://docs.locust.io
3. Open issue on GitHub
4. Check Zakera monitoring dashboards

## 📖 Additional Resources

- [Locust Documentation](https://docs.locust.io)
- [Performance Testing Best Practices](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [Zakera API Documentation](../../docs/API.md)
- [Zakera Architecture](../../docs/ARCHITECTURE.md)

## 🤝 Contributing

To add new test scenarios:

1. Create new locustfile in `locustfiles/`
2. Add configuration in `config/`
3. Update this README
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

---

**Last Updated**: February 2026  
**Version**: 1.0.0  
**Maintained by**: Zakera Team
