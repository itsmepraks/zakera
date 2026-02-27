"""
Endurance Test Configuration (Soak Test)

Tests system stability over extended periods to identify memory leaks,
resource exhaustion, and degradation over time.

Run with:
    locust -f tests/performance/locustfile.py --config tests/performance/config/endurance_test.py
"""

# Test configuration
host = "http://localhost:8000"

# User configuration
users = 100             # Moderate sustained load
spawn_rate = 10         # Gradual ramp-up
run_time = "2h"         # Extended duration (2 hours)

# User behavior
wait_time_min = 2       # Normal user behavior
wait_time_max = 5

# Monitoring
headless = True         # Run headless for long tests
print_stats = True
csv = "results/endurance_test"
html = "results/endurance_test.html"

# Advanced settings
stop_timeout = 30
reset_stats = False

# Tags for filtering
tags = ["api", "endurance", "soak"]

# Custom configuration
test_name = "Endurance Test"
description = "Long-running test to identify memory leaks and degradation"

# Expected thresholds (should remain stable over time)
expected_avg_response_time = 1000   # ms (should not increase)
expected_max_response_time = 5000   # ms
expected_failure_rate = 0.5         # percent (very low)
expected_rps = 20                   # requests per second

# Memory monitoring thresholds
max_memory_increase_mb = 500        # Alert if memory grows by 500MB
max_connection_pool_size = 50       # Alert if connection pool exhausted
max_cpu_usage_percent = 80          # Alert if CPU consistently high

# Checkpoints for analysis
checkpoints = [
    "30m",  # 30 minutes - first checkpoint
    "1h",   # 1 hour - mid-point
    "1h30m",# 1.5 hours - late stage
    "2h",   # 2 hours - completion
]
