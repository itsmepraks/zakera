# Performance Testing Suite

Comprehensive performance testing suite for Zakera AI Chat Agent using Locust.

## 🎯 Overview

This suite provides load testing capabilities for:
- **REST API endpoints** - Chat, conversations, search
- **WebSocket connections** - Real-time chat
- **Streaming responses** - Model streaming
- **Model providers** - Multi-provider testing
- **Tool execution** - Tool system performance

## 📦 Installation

```bash
# Install performance testing dependencies
pip install locust websocket-client matplotlib jinja2

# Or install all test dependencies
pip install -r requirements-test.txt
```

## 🚀 Quick Start

### Run Normal Load Test (Baseline)

```bash
# Start Locust with web UI
locust -f tests/performance/locustfile.py --host http://localhost:8000

# Open browser to http://localhost:8089
# Configure: 50 users, 5 users/second spawn rate
```

### Run with Configuration File

```bash
# Normal load test
locust -f tests/performance/locustfile.py \
       --config tests/performance/config/normal_load.py

# Stress test
locust -f tests/performance/locustfile.py \
       --config tests/performance/config/stress_test.py

# Spike test
locust -f tests/performance/locustfile.py \
       --config tests/performance/config/spike_test.py

# Endurance test (2 hours)
locust -f tests/performance/locustfile.py \
       --config tests/performance/config/endurance_test.py
```

### Headless Mode (CI/CD)

```bash
# Run without web UI
locust -f tests/performance/locustfile.py \
       --host http://localhost:8000 \
       --users 100 \
       --spawn-rate 10 \
       --run-time 5m \
       --headless \
       --html results/report.html \
       --csv results/stats
```

## 📊 Test Scenarios

### 1. Normal Load Test
**Purpose**: Baseline performance testing with realistic user behavior

```python
Users: 50
Spawn Rate: 5 users/second
Duration: 10 minutes
Wait Time: 2-5 seconds between requests

Expected SLAs:
- Avg Response Time: < 1000ms
- Max Response Time: < 5000ms
- Failure Rate: < 1%
- Throughput: > 10 req/s
```

**Run**: `make perf-test-normal`

### 2. Stress Test
**Purpose**: Find system breaking points under heavy load

```python
Users: 500
Spawn Rate: 25 users/second
Duration: 15 minutes
Wait Time: 0.5-1 second

Stages:
1. Ramp to 100 users (5 min)
2. Ramp to 300 users (5 min)
3. Peak at 500 users (5 min)

Expected:
- Avg Response Time: < 3000ms
- Failure Rate: < 5%
```

**Run**: `make perf-test-stress`

### 3. Spike Test
**Purpose**: Validate auto-scaling and error handling

```python
Users: 1000 (spike)
Spawn Rate: 100 users/second
Duration: 10 minutes
Wait Time: 0.1-0.5 seconds

Pattern:
1. Baseline: 10 users (1 min)
2. SPIKE: 1000 users (30 sec)
3. Sustain: 1000 users (2 min)
4. Drop: 100 users (1 min)
5. Recovery: 10 users (2 min)

Expected:
- System should handle gracefully
- Failure Rate: < 10% during spike
```

**Run**: `make perf-test-spike`

### 4. Endurance Test (Soak)
**Purpose**: Identify memory leaks and degradation over time

```python
Users: 100
Duration: 2 hours
Wait Time: 2-5 seconds

Monitors:
- Memory growth (alert if > 500MB increase)
- Connection pool exhaustion
- Response time degradation
- CPU usage patterns

Expected:
- Stable performance throughout
- No memory leaks
- Consistent response times
```

**Run**: `make perf-test-endurance`

## 📈 Generating Reports

### HTML Report with Charts

```python
from tests.performance.reporters import HTMLReporter

reporter = HTMLReporter(output_dir="results")
reporter.generate_report(stats, test_config)
```

**Output**: `results/test_report.html`

Features:
- ✅ Key metrics dashboard
- ✅ Response time distribution chart
- ✅ Requests over time graph
- ✅ Endpoint statistics table
- ✅ SLA validation results

### JSON Report (CI/CD)

```python
from tests.performance.reporters import JSONReporter

reporter = JSONReporter(output_dir="results")
reporter.generate_report(stats, test_config)
```

**Output**: `results/test_report.json`

```json
{
  "test_name": "Normal Load Test",
  "timestamp": "2026-02-26T22:00:00",
  "summary": {
    "total_requests": 5000,
    "failure_rate": 0.5,
    "avg_response_time": 850,
    "requests_per_second": 15.2
  },
  "sla_validation": {
    "passed": true,
    "checks": [...]
  }
}
```

### Prometheus Metrics

```python
from tests.performance.reporters import PrometheusReporter

reporter = PrometheusReporter(output_dir="results")
reporter.generate_report(stats, test_config)
```

**Output**: `results/test_metrics.prom`

## 🎯 Task Distribution

### API Endpoint Tasks (50%)
- **Send chat message** (weight: 5) - Most common operation
- **Get conversations** (weight: 3)
- **Get conversation history** (weight: 2)
- **Search conversations** (weight: 2)
- **Execute tool** (weight: 1)
- **Export conversation** (weight: 1)
- **Health check** (weight: 1)

### Streaming Chat Tasks (15%)
- **Streaming chat** - Test SSE/streaming responses

### WebSocket Tasks (15%)
- **WebSocket chat** - Real-time communication testing

### Model Provider Tasks (20%)
- **Test providers** - OpenAI, Anthropic, Gemini, etc.

## 🔍 Monitoring During Tests

### Real-time Metrics
```bash
# Watch Locust web UI
http://localhost:8089

# View API metrics
curl http://localhost:8000/api/v1/monitoring/metrics

# Check Prometheus
http://localhost:9090

# View Grafana dashboards
http://localhost:3001
```

### Key Metrics to Monitor

**Application**:
- Response time (p50, p95, p99)
- Error rate
- Throughput (req/s)
- Active users

**System**:
- CPU usage
- Memory usage
- Database connections
- Network I/O

**Model Providers**:
- Provider latency
- Provider errors
- Token usage
- Cost per request

## 🛠️ Makefile Targets

```bash
# Install dependencies
make perf-test-setup

# Run all performance tests
make perf-test-all

# Individual tests
make perf-test-normal    # Normal load
make perf-test-stress    # Stress test
make perf-test-spike     # Spike test
make perf-test-endurance # Endurance test

# Generate reports
make perf-test-report

# Clean results
make perf-test-clean
```

## 📊 Interpreting Results

### Success Criteria

✅ **PASS** if all conditions met:
- Failure rate < threshold
- Response times within SLA
- No system crashes
- Throughput meets expectations

⚠️ **WARNING** if:
- Response times degrading
- Intermittent failures
- High CPU/memory usage

❌ **FAIL** if:
- Failure rate exceeds threshold
- System crashes
- Response times unacceptable
- Data loss

### Common Issues

**High Response Times**:
- Database query optimization needed
- Add caching layer
- Scale horizontally

**High Failure Rate**:
- Rate limiting too aggressive
- Database connection pool exhausted
- Model provider timeouts

**Memory Leaks**:
- Check connection cleanup
- Review caching strategy
- Monitor object lifecycle

**CPU Spikes**:
- Optimize hot code paths
- Add worker processes
- Review synchronous operations

## 🎯 CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

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
      
      - name: Wait for API
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
      
      - name: Run performance test
        run: |
          locust -f tests/performance/locustfile.py \
                 --host http://localhost:8000 \
                 --users 50 \
                 --spawn-rate 5 \
                 --run-time 5m \
                 --headless \
                 --html results/report.html \
                 --csv results/stats
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: results/
      
      - name: Check SLA
        run: python tests/performance/validate_sla.py results/stats.json
```

## 📚 Best Practices

### 1. Test Environment
- Use dedicated test environment
- Match production specs closely
- Clear data between tests
- Warm up system before testing

### 2. Test Design
- Start with realistic scenarios
- Gradually increase load
- Test one variable at a time
- Document assumptions

### 3. Monitoring
- Monitor all system layers
- Collect detailed metrics
- Save logs for analysis
- Compare with baselines

### 4. Analysis
- Review all metrics
- Identify bottlenecks
- Document findings
- Create action items

## 🔧 Troubleshooting

### Issue: Connection Refused

```bash
# Check if API is running
curl http://localhost:8000/api/v1/monitoring/health

# Start services
docker-compose up -d
```

### Issue: High Failure Rate

```bash
# Check API logs
docker-compose logs api

# Check rate limiting
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/monitoring/metrics | grep rate_limit
```

### Issue: Slow Tests

```bash
# Use FastHttpUser instead of HttpUser
# Reduce logging verbosity
# Disable detailed tracing during tests
```

## 📖 Additional Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://martinfowler.com/articles/performance-testing.html)
- [Load Testing Patterns](https://www.amazon.com/Performance-Testing-Guidance-Web-Applications/dp/1449334857)

## 🤝 Contributing

See main [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

When adding new tests:
1. Follow existing patterns
2. Document expected behavior
3. Add appropriate wait times
4. Update this README

---

**Version**: 1.0.0  
**Last Updated**: February 2026  
**Maintainer**: Zakera Team
