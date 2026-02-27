"""Endurance Test Scenario

Long-running test to detect memory leaks and degradation.
"""

import yaml
import os
from typing import Dict, List
from datetime import datetime, timedelta


class EnduranceTestScenario:
    """Endurance test configuration and execution"""
    
    def __init__(self):
        self.name = "Endurance Test"
        self.config_file = "config/endurance_test.yaml"
        self.description = "24-hour stability test"
        self.checkpoints = []
    
    def get_config(self) -> Dict:
        """Load scenario configuration"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.config_file
        )
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get_checkpoints(self) -> List[Dict]:
        """Get checkpoints for analysis
        
        Returns:
            List of checkpoint configurations
        """
        config = self.get_config()
        return config.get('checkpoints', [])
    
    def analyze_degradation(self, checkpoints_data: List[Dict]) -> Dict:
        """Analyze performance degradation over time
        
        Args:
            checkpoints_data: Performance data at each checkpoint
        
        Returns:
            Degradation analysis
        """
        if len(checkpoints_data) < 2:
            return {'status': 'insufficient_data'}
        
        first = checkpoints_data[0]
        last = checkpoints_data[-1]
        
        # Calculate degradation
        latency_increase = (
            (last['avg_latency'] - first['avg_latency']) / first['avg_latency'] * 100
        )
        
        memory_increase = (
            (last['memory_usage'] - first['memory_usage']) / first['memory_usage'] * 100
        )
        
        return {
            'latency_degradation_percent': latency_increase,
            'memory_growth_percent': memory_increase,
            'error_rate_change': last['error_rate'] - first['error_rate'],
            'has_memory_leak': memory_increase > 20,
            'has_performance_degradation': latency_increase > 15,
            'stability_score': self._calculate_stability_score(checkpoints_data),
            'recommendations': self._get_degradation_recommendations(
                latency_increase,
                memory_increase
            )
        }
    
    def _calculate_stability_score(self, checkpoints: List[Dict]) -> float:
        """Calculate overall stability score (0-100)
        
        Args:
            checkpoints: Checkpoint data
        
        Returns:
            Stability score
        """
        if not checkpoints:
            return 0.0
        
        # Simple scoring based on consistency
        latencies = [cp['avg_latency'] for cp in checkpoints]
        error_rates = [cp['error_rate'] for cp in checkpoints]
        
        # Lower variance = higher stability
        import statistics
        
        latency_variance = statistics.variance(latencies) if len(latencies) > 1 else 0
        error_variance = statistics.variance(error_rates) if len(error_rates) > 1 else 0
        
        # Score inversely proportional to variance
        score = 100 - min(latency_variance * 10 + error_variance * 20, 100)
        
        return max(0, score)
    
    def _get_degradation_recommendations(self, latency_increase: float,
                                        memory_increase: float) -> List[str]:
        """Get recommendations based on degradation"""
        recommendations = []
        
        if memory_increase > 20:
            recommendations.append('Investigate memory leaks')
            recommendations.append('Review object lifecycle management')
            recommendations.append('Add periodic garbage collection')
        
        if latency_increase > 15:
            recommendations.append('Optimize database connection pooling')
            recommendations.append('Review caching strategy')
            recommendations.append('Monitor and clear log files')
        
        if not recommendations:
            recommendations.append('System shows good stability')
        
        return recommendations
    
    def should_continue(self, current_metrics: Dict) -> bool:
        """Check if test should continue
        
        Args:
            current_metrics: Current performance metrics
        
        Returns:
            True if test should continue
        """
        config = self.get_config()
        alerts = config.get('endurance_options', {}).get('alerts', {})
        
        # Stop if critical thresholds exceeded
        if current_metrics.get('memory_usage_percent', 0) > alerts.get('disk_usage_percent', 80):
            return False
        
        if current_metrics.get('error_rate', 0) > 10:
            return False
        
        return True
