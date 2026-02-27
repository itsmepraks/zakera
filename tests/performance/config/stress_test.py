"""
Stress Test Configuration

Tests system behavior under heavy load to identify breaking points.
Use this to find system limits and ensure graceful degradation.

Run with:
    locust -f tests/performance/locustfile.py --config tests/performance/config/stress_test.py
"""

# Test configuration
host = "http://localhost:8000"

# User configuration
users = 500             # High number of concurrent users
spawn_rate = 25         # Rapid user spawn rate
run_time = "15m"        # Extended test duration

# User behavior
wait_time_min = 0.5     # Aggressive request rate
wait_time_max = 1       # Minimal wait time

# Monitoring
headless = False
print_stats = True
csv = "results/stress_test"
html = "results/stress_test.html"

# Advanced settings
stop_timeout = 30       # Longer timeout for cleanup
reset_stats = False

# Tags for filtering
tags = ["api", "stress", "heavy-load"]

# Custom configuration
test_name = "Stress Test"
description = "Heavy load test to identify system breaking points"

# Expected thresholds (should still work under stress)
expected_avg_response_time = 3000   # ms (degraded but acceptable)
expected_max_response_time = 10000  # ms
expected_failure_rate = 5.0         # percent (some failures acceptable)
expected_rps = 50                   # requests per second

# Stress test stages
stages = [
    {"duration": "5m", "users": 100, "spawn_rate": 10},   # Ramp up
    {"duration": "5m", "users": 300, "spawn_rate": 20},   # Increase load
    {"duration": "5m", "users": 500, "spawn_rate": 25},   # Peak load
]
