# Performance Testing Suite

Comprehensive performance testing framework for Zakera AI Chat Agent using Locust.

## Overview

This testing suite provides load testing, stress testing, and spike testing capabilities for:
- REST API endpoints
- WebSocket connections
- Model provider interactions
- Tool execution system
- Database operations

## Quick Start

### Installation

```bash
# Install performance testing dependencies
pip install locust pytest-benchmark

# Or use the Makefile
make install-perf-test
```

### Running Tests

#### 1. Normal Load Test (Recommended)
```bash
# Command line mode with 50 users
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --tags normal
```

#### 2. Web UI Mode
```bash
# Start Locust web interface
locust -f tests/performance/locustfile.py --host http://localhost:8000

# Open browser: http://localhost:8089
```

#### 3. Stress Test
```bash
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 200 \
  --spawn-rate 20 \
  --run-time 10m \
  --tags stress
```

#### 4. Spike Test
```bash
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 500 \
  --spawn-rate 50 \
  --run-time 3m \
  --tags spike
```

## Test Scenarios

### Normal Load
**Purpose**: Simulate typical production usage
- **Users**: 50 concurrent users
- **Spawn Rate**: 5 users/second
- **Duration**: 5-10 minutes
- **Wait Time**: 1-3 seconds between requests
- **Success Criteria**: <100ms p95 latency, <1% error rate

### Stress Test
**Purpose**: Find system breaking point
- **Users**: 200-500 concurrent users
- **Spawn Rate**: 20 users/second
- **Duration**: 10-15 minutes
- **Wait Time**: 0.5-2 seconds
- **Success Criteria**: Graceful degradation, <5% error rate

### Spike Test
**Purpose**: Test sudden traffic increase
- **Users**: 0 → 500 → 0 users
- **Spawn Rate**: 50 users/second
- **Duration**: 3-5 minutes
- **Wait Time**: 0.1-1 second
- **Success Criteria**: System recovers, no crashes

### Endurance Test
**Purpose**: Long-running stability
- **Users**: 100 concurrent users
- **Spawn Rate**: 10 users/second
- **Duration**: 1-4 hours
- **Wait Time**: 2-5 seconds
- **Success Criteria**: No memory leaks, stable performance

## Test Configuration

### Environment Variables

```bash
# API Configuration
export PERF_TEST_HOST="http://localhost:8000"
export PERF_TEST_API_KEY="your-test-api-key"

# Test Parameters
export PERF_TEST_USERS=50
export PERF_TEST_SPAWN_RATE=5
export PERF_TEST_RUN_TIME="5m"

# Scenario Selection
export PERF_TEST_SCENARIO="normal"  # normal, stress, spike, endurance

# Model Provider
export PERF_TEST_MODEL="gpt-3.5-turbo"
export PERF_TEST_PROVIDER="openai"
```

### Configuration File

Edit `tests/performance/config.py` for advanced settings:

```python
class PerformanceTestConfig:
    # API endpoints to test
    ENDPOINTS = [
        "/api/v1/chat",
        "/api/v1/conversations",
        "/api/v1/monitoring/health"
    ]
    
    # Load distribution (weight)
    TASK_WEIGHTS = {
        "send_message": 70,
        "list_conversations": 20,
        "health_check": 10
    }
    
    # Performance thresholds
    THRESHOLDS = {
        "p95_latency_ms": 100,
        "error_rate_percent": 1.0,
        "throughput_rps": 100
    }
```

## Test Files

### Core Files
- `locustfile.py` - Main entry point, orchestrates all tests
- `config.py` - Configuration and settings
- `test_api_endpoints.py` - REST API load tests
- `test_websocket.py` - WebSocket connection tests
- `test_model_providers.py` - Model provider performance
- `test_tools.py` - Tool execution tests

### Utilities
- `utils/metrics.py` - Custom metrics collection
- `utils/auth.py` - Authentication helpers
- `utils/data_generator.py` - Test data generation
- `utils/report_generator.py` - HTML report generation

### Scenarios
- `scenarios/normal_load.json` - Normal load parameters
- `scenarios/stress_test.json` - Stress test parameters
- `scenarios/spike_test.json` - Spike test parameters
- `scenarios/endurance_test.json` - Endurance test parameters

## Reporting

### Built-in Reports

Locust generates reports automatically:

```bash
# Generate HTML report
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --html reports/performance_report.html

# Generate CSV files
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --csv reports/performance_data
```

### Custom Reports

Generate custom performance reports:

```bash
python tests/performance/utils/report_generator.py \
  --input reports/performance_data_stats.csv \
  --output reports/custom_report.html
```

### Prometheus Integration

Export metrics to Prometheus:

```bash
# Start Locust with Prometheus exporter
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --prometheus-port 8088

# Metrics available at: http://localhost:8088/metrics
```

## Key Metrics

### Response Time Metrics
- **Average Response Time**: Mean latency across all requests
- **Median (p50)**: 50th percentile response time
- **p95**: 95th percentile response time
- **p99**: 99th percentile response time
- **Max**: Maximum observed response time

### Throughput Metrics
- **Requests per Second (RPS)**: Total throughput
- **Failures per Second**: Error rate
- **Current Users**: Active concurrent users

### Error Metrics
- **Total Failures**: Number of failed requests
- **Failure Rate**: Percentage of failed requests
- **Error Types**: Breakdown by error type

### Model Provider Metrics
- **Provider Latency**: Response time by provider
- **Token Usage**: Tokens consumed per request
- **Cost per Request**: Estimated cost
- **Fallback Rate**: Provider failover frequency

## Best Practices

### 1. Baseline First
```bash
# Run baseline test to establish performance profile
locust -f tests/performance/locustfile.py \
  --host http://localhost:8000 \
  --users 10 \
  --spawn-rate 1 \
  --run-time 2m \
  --html reports/baseline.html
```

### 2. Gradual Load Increase
```bash
# Start with low load, increase gradually
for users in 10 50 100 200; do
  locust -f tests/performance/locustfile.py \
    --host http://localhost:8000 \
    --users $users \
    --spawn-rate 5 \
    --run-time 3m \
    --html reports/load_$users.html
done
```

### 3. Monitor System Resources
```bash
# Monitor CPU, memory, disk during tests
watch -n 1 'docker stats'

# Monitor application logs
tail -f logs/app.log

# Check Grafana dashboards
open http://localhost:3001
```

### 4. Test in Isolation
- Run tests in a dedicated environment
- Disable unnecessary services
- Use consistent test data
- Clear caches between runs

### 5. Warm Up Period
```python
# In locustfile.py
class MyUser(HttpUser):
    @task
    def my_task(self):
        # Skip first 30 seconds for warm-up
        if time.time() - self.start_time < 30:
            return
        # ... rest of test
```

## Troubleshooting

### Issue: High Error Rate

**Symptoms**: >5% error rate during tests

**Solutions**:
1. Check API logs for errors
2. Verify API keys and authentication
3. Reduce load (users/spawn rate)
4. Increase server resources
5. Check rate limiting settings

### Issue: Slow Response Times

**Symptoms**: p95 > 1000ms

**Solutions**:
1. Check database query performance
2. Review model provider latency
3. Enable caching (Redis)
4. Optimize database indexes
5. Scale horizontally

### Issue: WebSocket Disconnections

**Symptoms**: Frequent WebSocket errors

**Solutions**:
1. Increase connection timeout
2. Check network stability
3. Review WebSocket handler code
4. Monitor server resources
5. Implement reconnection logic

### Issue: Inconsistent Results

**Symptoms**: Large variance between runs

**Solutions**:
1. Run longer tests (10+ minutes)
2. Increase sample size
3. Use consistent test data
4. Eliminate external dependencies
5. Test at same time of day

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

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
          pip install -r requirements.txt
          pip install locust
      
      - name: Start services
        run: docker-compose up -d
      
      - name: Wait for services
        run: sleep 30
      
      - name: Run performance tests
        run: |
          locust -f tests/performance/locustfile.py \
            --host http://localhost:8000 \
            --users 50 \
            --spawn-rate 5 \
            --run-time 5m \
            --headless \
            --html reports/performance.html \
            --csv reports/performance
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: performance-reports
          path: reports/
      
      - name: Check thresholds
        run: python tests/performance/utils/check_thresholds.py
```

## Advanced Usage

### Custom User Behavior

```python
from locust import HttpUser, task, between

class CustomUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before starting tasks"""
        self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_pass"
        })
    
    @task(3)  # Weight: 3x more likely
    def send_message(self):
        self.client.post("/api/v1/chat", json={
            "message": "Hello, AI!",
            "model": "gpt-3.5-turbo"
        })
    
    @task(1)
    def list_conversations(self):
        self.client.get("/api/v1/conversations")
```

### Sequential Task Flow

```python
from locust import HttpUser, TaskSet, task

class ConversationFlow(TaskSet):
    @task
    def flow(self):
        # 1. Create conversation
        resp = self.client.post("/api/v1/conversations")
        conv_id = resp.json()["id"]
        
        # 2. Send messages
        for i in range(5):
            self.client.post(f"/api/v1/conversations/{conv_id}/messages", json={
                "message": f"Message {i}"
            })
        
        # 3. Export conversation
        self.client.get(f"/api/v1/conversations/{conv_id}/export")
        
        # 4. Delete conversation
        self.client.delete(f"/api/v1/conversations/{conv_id}")
```

## Performance Targets

### Production Requirements

| Metric | Target | Critical |
|--------|--------|----------|
| p95 Latency | < 100ms | < 500ms |
| p99 Latency | < 200ms | < 1000ms |
| Error Rate | < 0.1% | < 1% |
| Throughput | > 100 RPS | > 50 RPS |
| Uptime | > 99.9% | > 99% |

### Scalability Targets

| Users | Expected RPS | Max Latency |
|-------|--------------|-------------|
| 10 | 10 | 50ms |
| 50 | 50 | 100ms |
| 100 | 100 | 200ms |
| 500 | 300 | 500ms |
| 1000 | 500 | 1000ms |

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://www.softwaretestinghelp.com/performance-testing-best-practices/)
- [API Load Testing Guide](https://www.blazemeter.com/blog/api-load-testing)

## Support

For issues or questions:
- GitHub Issues: https://github.com/itsmepraks/zakera/issues
- Discussions: https://github.com/itsmepraks/zakera/discussions

---

**Last Updated**: February 2026  
**Version**: 1.0.0
