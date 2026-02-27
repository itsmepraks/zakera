"""Spike Test Scenario

Tests system behavior under sudden traffic increases.
"""

import yaml
import os
from typing import Dict, List


class SpikeTestScenario:
    """Spike test configuration and execution"""
    
    def __init__(self):
        self.name = "Spike Test"
        self.config_file = "config/spike_test.yaml"
        self.description = "Tests sudden traffic spikes"
    
    def get_config(self) -> Dict:
        """Load scenario configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.config_file
        )
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_spike_pattern(self) -> List[Dict]:
        """Get spike test phases
        
        Returns:
            List of test phases
        """
        config = self.get_config()
        return config.get('spike_options', {}).get('pattern', [])
    
    def analyze_recovery(self, results: Dict) -> Dict:
        """Analyze system recovery after spike
        
        Args:
            results: Test results
        
        Returns:
            Recovery analysis
        """
        config = self.get_config()
        expectations = config.get('spike_options', {}).get('expectations', {})
        
        return {
            'scale_up_time': results.get('scale_up_time', 0),
            'expected_scale_up': expectations.get('scale_up_time_max', '30s'),
            'recovery_time': results.get('recovery_time', 0),
            'expected_recovery': expectations.get('recovery_time_max', '120s'),
            'error_spike_handled': results.get('error_rate_during_spike', 0) < 10.0,
            'recommendations': self._get_recommendations(results)
        }
    
    def _get_recommendations(self, results: Dict) -> List[str]:
        """Get recommendations based on results"""
        recommendations = []
        
        if results.get('scale_up_time', 0) > 30:
            recommendations.append('Improve auto-scaling response time')
        
        if results.get('error_rate_during_spike', 0) > 5:
            recommendations.append('Add request queuing')
            recommendations.append('Implement circuit breakers')
        
        if results.get('recovery_time', 0) > 120:
            recommendations.append('Optimize connection pool management')
        
        return recommendations
