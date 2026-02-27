"""
Normal Load Test Configuration

Simulates typical production load with realistic user behavior patterns.
Use this for baseline performance testing and capacity planning.

Run with:
    locust -f tests/performance/locustfile.py --config tests/performance/config/normal_load.py
"""

# Test configuration
host = "http://localhost:8000"

# User configuration
users = 50              # Number of concurrent users
spawn_rate = 5          # Users spawned per second
run_time = "10m"        # Test duration

# User behavior
wait_time_min = 2       # Minimum wait between requests (seconds)
wait_time_max = 5       # Maximum wait between requests (seconds)

# Monitoring
headless = False        # Run with web UI
print_stats = True
csv = "results/normal_load"
html = "results/normal_load.html"

# Advanced settings
stop_timeout = 10       # Graceful stop timeout
reset_stats = False     # Don't reset stats between test runs

# Tags for filtering tasks
tags = ["api", "chat", "streaming"]

# Custom configuration
test_name = "Normal Load Test"
description = "Baseline performance test with realistic user behavior"

# Expected SLAs (for validation)
expected_avg_response_time = 1000  # ms
expected_max_response_time = 5000  # ms
expected_failure_rate = 1.0        # percent
expected_rps = 10                  # requests per second
