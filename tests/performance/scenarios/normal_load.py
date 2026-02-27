"""Normal Load Test Scenario

Simulates typical production traffic patterns.
"""

import yaml
import os
from typing import Dict


class NormalLoadScenario:
    """Normal load test configuration and execution"""
    
    def __init__(self):
        self.name = "Normal Load Test"
        self.config_file = "config/normal_load.yaml"
        self.description = "Simulates typical production traffic"
    
    def get_config(self) -> Dict:
        """Load scenario configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.config_file
        )
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def validate_results(self, results: Dict) -> bool:
        """Validate test results against thresholds
        
        Args:
            results: Test results data
        
        Returns:
            True if results meet criteria
        """
        config = self.get_config()
        thresholds = config.get('thresholds', {})
        
        checks = []
        
        # Check error rate
        if 'error_rate' in results:
            error_rate = results['error_rate']
            max_error_rate = thresholds.get('error_rate_percent', 1.0)
            checks.append(error_rate <= max_error_rate)
        
        # Check P95 latency
        if 'p95_latency' in results:
            p95 = results['p95_latency']
            max_p95 = thresholds.get('p95_latency_ms', 1000) / 1000  # Convert to seconds
            checks.append(p95 <= max_p95)
        
        return all(checks)
    
    def get_expected_metrics(self) -> Dict:
        """Get expected performance metrics"""
        return {
            'p95_latency': '<1s',
            'p99_latency': '<2s',
            'error_rate': '<1%',
            'min_throughput': '>5 rps'
        }
