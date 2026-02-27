"""Check performance thresholds and fail if not met."""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class ThresholdChecker:
    """Check performance test results against thresholds."""
    
    def __init__(self, stats_file: str, thresholds: Dict[str, float]):
        """Initialize threshold checker.
        
        Args:
            stats_file: Path to Locust stats CSV file
            thresholds: Dictionary of metric thresholds
        """
        self.stats_file = Path(stats_file)
        self.thresholds = thresholds
        self.failures: List[str] = []
    
    def check(self) -> bool:
        """Check all thresholds.
        
        Returns:
            True if all thresholds met, False otherwise
        """
        if not self.stats_file.exists():
            print(f"❌ Stats file not found: {self.stats_file}")
            return False
        
        # Load stats
        with open(self.stats_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Find aggregated row
        aggregated = next((row for row in rows if row.get('Name') == 'Aggregated'), None)
        
        if not aggregated:
            print("❌ No aggregated stats found")
            return False
        
        # Check p95 latency
        p95 = float(aggregated.get('95%', 0))
        if p95 > self.thresholds.get('p95_latency_ms', float('inf')):
            self.failures.append(
                f"P95 latency ({p95:.2f}ms) exceeds threshold ({self.thresholds['p95_latency_ms']}ms)"
            )
        
        # Check p99 latency
        p99 = float(aggregated.get('99%', 0))
        if p99 > self.thresholds.get('p99_latency_ms', float('inf')):
            self.failures.append(
                f"P99 latency ({p99:.2f}ms) exceeds threshold ({self.thresholds['p99_latency_ms']}ms)"
            )
        
        # Check error rate
        total_requests = int(aggregated.get('Request Count', 1))
        total_failures = int(aggregated.get('Failure Count', 0))
        error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        
        if error_rate > self.thresholds.get('error_rate_percent', float('inf')):
            self.failures.append(
                f"Error rate ({error_rate:.2f}%) exceeds threshold ({self.thresholds['error_rate_percent']}%)"
            )
        
        # Check throughput
        rps = float(aggregated.get('Requests/s', 0))
        if rps < self.thresholds.get('throughput_rps', 0):
            self.failures.append(
                f"Throughput ({rps:.2f} RPS) below threshold ({self.thresholds['throughput_rps']} RPS)"
            )
        
        return len(self.failures) == 0
    
    def print_results(self):
        """Print check results."""
        if self.failures:
            print("\n❌ PERFORMANCE THRESHOLD FAILURES:")
            for failure in self.failures:
                print(f"  - {failure}")
            print()
        else:
            print("\n✅ All performance thresholds met!\n")


if __name__ == "__main__":
    # Default thresholds
    thresholds = {
        "p95_latency_ms": 200.0,
        "p99_latency_ms": 500.0,
        "error_rate_percent": 1.0,
        "throughput_rps": 50.0,
    }
    
    stats_file = "reports/performance_stats.csv"
    
    checker = ThresholdChecker(stats_file, thresholds)
    passed = checker.check()
    checker.print_results()
    
    sys.exit(0 if passed else 1)
