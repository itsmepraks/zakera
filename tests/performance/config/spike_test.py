"""
Spike Test Configuration

Tests system behavior under sudden traffic spikes.
Use this to validate auto-scaling and error handling under rapid load changes.

Run with:
    locust -f tests/performance/locustfile.py --config tests/performance/config/spike_test.py
"""

# Test configuration
host = "http://localhost:8000"

# User configuration
users = 1000            # Very high user count for spike
spawn_rate = 100        # Extremely rapid spawn (simulates spike)
run_time = "10m"        # Shorter duration

# User behavior
wait_time_min = 0.1     # Minimal wait (aggressive)
wait_time_max = 0.5     # Very short wait times

# Monitoring
headless = False
print_stats = True
csv = "results/spike_test"
html = "results/spike_test.html"

# Advanced settings
stop_timeout = 60       # Longer timeout for spike recovery
reset_stats = False

# Tags for filtering
tags = ["api", "spike", "burst"]

# Custom configuration
test_name = "Spike Test"
description = "Sudden traffic spike test to validate auto-scaling"

# Expected thresholds (should handle gracefully)
expected_avg_response_time = 5000   # ms (can be high during spike)
expected_max_response_time = 15000  # ms
expected_failure_rate = 10.0        # percent (some failures expected)
expected_rps = 100                  # requests per second

# Spike test pattern
spike_pattern = [
    {"duration": "1m", "users": 10, "spawn_rate": 5},      # Baseline
    {"duration": "30s", "users": 1000, "spawn_rate": 100}, # SPIKE
    {"duration": "2m", "users": 1000, "spawn_rate": 0},    # Sustain spike
    {"duration": "1m", "users": 100, "spawn_rate": -50},   # Rapid drop
    {"duration": "30s", "users": 10, "spawn_rate": -10},   # Return to baseline
    {"duration": "2m", "users": 10, "spawn_rate": 0},      # Recovery observation
]
