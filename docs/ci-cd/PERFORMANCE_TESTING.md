# Performance Testing CI/CD Integration

This document describes the comprehensive GitHub Actions workflow for automated performance testing using Locust.

## Overview

The Zakera project includes an enterprise-grade performance testing infrastructure that runs automatically on every push and pull request. The workflow uses Locust to simulate real-world load and provides detailed performance metrics, regression detection, and historical trend analysis.

## Workflow File

**Location**: `.github/workflows/performance-enhanced.yml`

## Features

### 🚀 Automated Testing

- **Trigger Points**:
  - Push to `main` or `develop` branches
  - Pull requests to `main` or `develop`
  - Scheduled nightly runs at 2 AM UTC
  - Manual workflow dispatch with custom parameters

- **Test Scenarios**:
  - **Normal Load**: 50 users, 5 minutes (typical production load)
  - **Stress Test**: 500 users, 10 minutes (finding breaking points)
  - **Spike Test**: 200 users, 15 minutes (sudden traffic spikes)
  - **Endurance Test**: 100 users, 1 hour (memory leak detection)

### 📊 Comprehensive Reporting

- **HTML Reports**: Interactive Locust reports with graphs
- **CSV Data**: Time-series data for custom analysis
- **JSON Output**: Machine-readable results
- **Markdown Summaries**: Human-readable summaries
- **Analysis Reports**: Automated threshold violation detection

### 🔍 Regression Detection

Automatically detects performance regressions by comparing against predefined thresholds:

**Normal Load Thresholds**:
- Chat endpoints: P95 < 2s, P99 < 5s, Error rate < 1%
- Conversation endpoints: P95 < 500ms, P99 < 1s, Error rate < 1%
- Health checks: P95 < 100ms, P99 < 200ms, Error rate < 0.1%

**Stress Test Thresholds**:
- Chat endpoints: P95 < 5s, P99 < 10s, Error rate < 5%
- Overall system: Error rate < 10%, Min throughput > 50 RPS

See `.github/performance-baselines.json` for complete threshold definitions.

### 💬 PR Comments

Automatically posts comprehensive performance results as PR comments:

```markdown
## 🚀 Performance Test Results

**Tested Commit**: `abc1234`
**Test Time**: 2026-02-28 02:15 UTC
**Scenarios Tested**: 3

### 📊 Overall Metrics

| Metric | Value |
|--------|-------|
| Total Requests | 125,487 |
| Total Failures | 234 |
| Failure Rate | 0.19% |

### 📈 Scenario Results

#### ✅ Normal Load Test

All metrics within acceptable thresholds! 🎉

**Top Endpoints:**

| Endpoint | Requests | P95 (ms) | P99 (ms) | Failures |
|----------|----------|----------|----------|----------|
| /api/v1/chat | 52,341 | 1,234 | 3,456 | 23 |
...
```

### 🤖 Model Provider Testing

Separate job matrix tests all 9 model providers in parallel:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google Gemini (1.5 Pro, Flash)
- Perplexity (Sonar)
- Ollama (local models)
- Cohere (Command)
- Groq (ultra-fast)
- Mistral (Mixtral)
- HuggingFace (various)

## Workflow Jobs

### 1. Setup and Validation

Validates test suite structure and configures test scenarios:

```yaml
jobs:
  setup:
    - Validates performance test files exist
    - Configures test scenarios based on trigger
    - Sets up caching strategy
```

### 2. Locust Tests (Matrix)

Runs Locust performance tests for each scenario:

```yaml
locust_tests:
  strategy:
    matrix:
      scenario: [normal, stress, spike]
  steps:
    - Setup PostgreSQL and Redis services
    - Install dependencies with caching
    - Start Zakera application
    - Run Locust tests with scenario config
    - Generate enhanced reports
    - Analyze results for violations
    - Upload artifacts
```

### 3. Model Provider Tests

Benchmarks individual model providers:

```yaml
model_provider_tests:
  strategy:
    matrix:
      provider: [openai, anthropic, gemini, ...]
  steps:
    - Run pytest benchmarks for provider
    - Upload benchmark results
```

### 4. Aggregate Results

Combines results from all scenarios:

```yaml
aggregate_results:
  steps:
    - Download all artifacts
    - Generate comprehensive report
    - Create performance summary
    - Upload final report
```

### 5. PR Comment (PR Only)

Posts results to PR:

```yaml
pr_comment:
  if: github.event_name == 'pull_request'
  steps:
    - Generate formatted comment
    - Update or create PR comment
```

### 6. Regression Check

Fails workflow if regressions detected:

```yaml
regression_check:
  steps:
    - Check for threshold violations
    - Exit with error if violations found
```

## Configuration Files

### Performance Baselines

**File**: `.github/performance-baselines.json`

Defines performance thresholds for all scenarios and endpoints:

```json
{
  "scenarios": {
    "normal": {
      "thresholds": {
        "endpoints": {
          "/api/v1/chat": {
            "p95_ms": 2000,
            "p99_ms": 5000,
            "failure_rate_percent": 1.0
          }
        }
      }
    }
  }
}
```

### CI Configuration

**File**: `tests/performance/ci-config.yml`

CI-specific settings optimized for GitHub Actions:

```yaml
scenarios:
  normal:
    users: 50
    spawn_rate: 5
    duration_seconds: 300

locust:
  tasks:
    chat_message: 5  # Task weight
    get_conversations: 2
  
  wait_time:
    min: 1
    max: 3
```

## Manual Workflow Dispatch

Run custom performance tests manually:

```bash
# Via GitHub UI:
# 1. Go to Actions tab
# 2. Select "Enhanced Performance Testing"
# 3. Click "Run workflow"
# 4. Set parameters:
#    - Scenario: normal/stress/spike/endurance/all
#    - Duration: 300 (seconds)
#    - Users: 50
#    - Workers: 2

# Via GitHub CLI:
gh workflow run performance-enhanced.yml \
  -f scenario=stress \
  -f duration=600 \
  -f users=500 \
  -f workers=4
```

## Artifacts

All test runs produce downloadable artifacts:

### Per-Scenario Artifacts
- `performance-report-{scenario}/`
  - `report.html` - Interactive Locust report
  - `results_stats.csv` - Statistics CSV
  - `results_failures.csv` - Failures CSV  
  - `results.json` - JSON results
  - `analysis.json` - Threshold violation analysis
  - `report.md` - Markdown summary

### Provider Benchmarks
- `benchmark-{provider}.json` - pytest-benchmark results

### Comprehensive Report
- `performance-report-comprehensive/`
  - `performance-report-full.json` - All scenarios aggregated
  - `performance-summary.md` - Executive summary

**Retention**: 30 days for scenario reports, 90 days for comprehensive reports

## Integration with Existing Tools

### Locust Test Suite

The workflow integrates seamlessly with the existing Locust tests:

- **Location**: `tests/performance/`
- **Locustfiles**: `tests/performance/locustfiles/*.py`
- **Configuration**: `tests/performance/config.py`
- **Reporters**: `tests/performance/reporters.py`

### Prometheus & Grafana

While Prometheus/Grafana don't run in CI, the workflow:
- Collects the same metrics
- Generates compatible JSON output
- Can be integrated with monitoring dashboards for production

## Optimization Features

### Caching

- **Python dependencies**: Cached based on requirements.txt hash
- **pip cache**: Speeds up installation
- **Artifacts**: Only changed files uploaded

### Parallel Execution

- **Scenario matrix**: All scenarios run in parallel
- **Provider matrix**: All providers tested simultaneously
- **Worker nodes**: Configurable Locust workers (default: 2)

### Resource Management

- **Services**: PostgreSQL and Redis run as Docker services
- **Application**: Started in background, health-checked
- **Cleanup**: Automatic teardown after tests

## Troubleshooting

### Common Issues

**Application Fails to Start**:
```
Solution: Check health endpoint logs in workflow
- Ensure migrations run successfully
- Verify DATABASE_URL is correct
- Check application logs in workflow output
```

**Tests Timeout**:
```
Solution: Increase duration or reduce users
- Edit workflow inputs
- Modify ci-config.yml
- Check for resource constraints
```

**Threshold Violations**:
```
Solution: Investigate performance regression
- Review detailed CSV reports
- Compare with previous runs
- Check for code changes affecting performance
- Consider adjusting thresholds if legitimate
```

### Debug Mode

Enable debug logging by modifying the workflow:

```yaml
env:
  LOG_LEVEL: DEBUG  # Change from WARNING
```

## Performance Budgets

The workflow enforces performance budgets:

- **Failure on regression**: Workflow fails if thresholds exceeded
- **PR blocking**: Can be configured to block PR merges
- **Notifications**: GitHub issues created for critical regressions

## Future Enhancements

### Planned Features

- [ ] **Historical Trending**: GitHub Pages deployment with trend charts
- [ ] **Comparison Reports**: Automatic baseline comparison
- [ ] **Cost Analysis**: Track API costs per test run
- [ ] **Email Notifications**: Alert on nightly test failures
- [ ] **Slack Integration**: Post results to Slack channel
- [ ] **Performance Badges**: README badges showing current status

### Integration Opportunities

- [ ] **Grafana Cloud**: Upload metrics to Grafana Cloud
- [ ] **DataDog**: Send performance data to DataDog
- [ ] **PagerDuty**: Alert on critical performance degradation

## Best Practices

### For Contributors

1. **Review performance results** before merging PRs
2. **Investigate violations** promptly
3. **Update thresholds** only when justified
4. **Run manual tests** for significant changes
5. **Monitor trends** over time

### For Maintainers

1. **Review baselines** quarterly
2. **Adjust scenarios** based on production patterns
3. **Archive old reports** (automated)
4. **Update documentation** when changing workflows
5. **Monitor CI costs** (GitHub Actions minutes)

## Related Documentation

- [Performance Testing Suite README](../../tests/performance/README.md)
- [Issue #34: Performance Testing Suite](https://github.com/itsmepraks/zakera/issues/34)
- [Locust Documentation](https://docs.locust.io/)
- [GitHub Actions Documentation](https://docs.github.com/actions)

## Support

For issues with the performance testing CI/CD:

1. Check [Troubleshooting](#troubleshooting) section
2. Review [workflow runs](https://github.com/itsmepraks/zakera/actions)
3. Open an issue with:
   - Workflow run URL
   - Error messages
   - Expected vs actual behavior

---

**Last Updated**: 2026-02-28  
**Workflow Version**: 1.0  
**Status**: ✅ Production Ready
