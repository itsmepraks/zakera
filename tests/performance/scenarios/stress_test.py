"""Stress Test Scenario

Pushes system to its limits to find breaking points.
"""

import yaml
import os
from typing import Dict, List


class StressTestScenario:
    """Stress test configuration and execution"""
    
    def __init__(self):
        self.name = "Stress Test"
        self.config_file = "config/stress_test.yaml"
        self.description = "Identifies system breaking points"
    
    def get_config(self) -> Dict:
        """Load scenario configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.config_file
        )
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_load_stages(self) -> List[Dict]:
        """Get load increase stages
        
        Returns:
            List of stage configurations
        """
        config = self.get_config()
        return config.get('stress_options', {}).get('stages', [])
    
    def should_stop(self, current_metrics: Dict) -> bool:
        """Check if test should stop due to system failure
        
        Args:
            current_metrics: Current performance metrics
        
        Returns:
            True if test should stop
        """
        config = self.get_config()
        stop_conditions = config.get('stress_options', {}).get('stop_on', {})
        
        # Check error rate
        if 'error_rate' in current_metrics:
            max_error = stop_conditions.get('error_rate_above', 20.0)
            if current_metrics['error_rate'] > max_error:
                return True
        
        # Check P99 latency
        if 'p99_latency' in current_metrics:
            max_latency = stop_conditions.get('p99_latency_above', 10000) / 1000
            if current_metrics['p99_latency'] > max_latency:
                return True
        
        return False
    
    def analyze_breaking_point(self, results: Dict) -> Dict:
        """Analyze where the system broke
        
        Args:
            results: Test results
        
        Returns:
            Breaking point analysis
        """
        return {
            'max_users_supported': results.get('max_users', 0),
            'breaking_point_metric': 'error_rate',
            'failure_mode': 'gradual_degradation',
            'recommendations': [
                'Add horizontal scaling',
                'Optimize database queries',
                'Implement caching'
            ]
        }
