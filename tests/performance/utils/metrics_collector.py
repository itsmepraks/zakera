"""Metrics Collector for Performance Tests

Collects and aggregates:
- Request latencies
- Error rates
- Provider-specific metrics
- WebSocket statistics
- Custom performance metrics
"""

import time
import json
import os
from typing import Dict, List, Optional
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects custom performance metrics during load tests"""
    
    _instance = None
    _metrics = None
    
    def __new__(cls):
        """Singleton pattern to share metrics across all users"""
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
            cls._instance._initialize_metrics()
        return cls._instance
    
    def _initialize_metrics(self):
        """Initialize metrics storage"""
        self._metrics = {
            'chat': [],
            'websocket': [],
            'providers': defaultdict(list),
            'models': defaultdict(list),
            'tools': [],
            'errors': [],
            'costs': []
        }
        self._start_time = time.time()
    
    def record_chat_metrics(self, model: str, duration: float,
                           tokens: int, cost: float):
        """Record chat message metrics
        
        Args:
            model: Model used
            duration: Response time in seconds
            tokens: Total tokens used
            cost: Cost in USD
        """
        self._metrics['chat'].append({
            'timestamp': time.time(),
            'model': model,
            'duration': duration,
            'tokens': tokens,
            'cost': cost
        })
        
        # Also record by model
        self._metrics['models'][model].append({
            'duration': duration,
            'tokens': tokens,
            'cost': cost
        })
        
        self._metrics['costs'].append(cost)
    
    def record_websocket_metrics(self, duration: float, chunks: int,
                                message_length: int, response_length: int):
        """Record WebSocket streaming metrics
        
        Args:
            duration: Total streaming duration
            chunks: Number of chunks received
            message_length: Input message length
            response_length: Output response length
        """
        self._metrics['websocket'].append({
            'timestamp': time.time(),
            'duration': duration,
            'chunks': chunks,
            'message_length': message_length,
            'response_length': response_length,
            'avg_chunk_time': duration / chunks if chunks > 0 else 0
        })
    
    def record_provider_metrics(self, provider: str, model: str,
                               duration: float, tokens: int,
                               cost: float, success: bool):
        """Record provider-specific metrics
        
        Args:
            provider: Provider name
            model: Model name
            duration: Response time
            tokens: Token count
            cost: Cost
            success: Whether request succeeded
        """
        self._metrics['providers'][provider].append({
            'timestamp': time.time(),
            'model': model,
            'duration': duration,
            'tokens': tokens,
            'cost': cost,
            'success': success
        })
        
        if not success:
            self._metrics['errors'].append({
                'timestamp': time.time(),
                'provider': provider,
                'model': model
            })
    
    def record_tool_metrics(self, tool_name: str, duration: float,
                           success: bool, cached: bool = False):
        """Record tool execution metrics
        
        Args:
            tool_name: Name of tool executed
            duration: Execution time
            success: Whether execution succeeded
            cached: Whether result was from cache
        """
        self._metrics['tools'].append({
            'timestamp': time.time(),
            'tool': tool_name,
            'duration': duration,
            'success': success,
            'cached': cached
        })
    
    def get_chat_statistics(self) -> Dict:
        """Get chat metrics statistics"""
        if not self._metrics['chat']:
            return {}
        
        durations = [m['duration'] for m in self._metrics['chat']]
        tokens = [m['tokens'] for m in self._metrics['chat']]
        costs = [m['cost'] for m in self._metrics['chat']]
        
        return {
            'total_requests': len(durations),
            'avg_duration': statistics.mean(durations),
            'p50_duration': statistics.median(durations),
            'p95_duration': self._percentile(durations, 0.95),
            'p99_duration': self._percentile(durations, 0.99),
            'max_duration': max(durations),
            'min_duration': min(durations),
            'total_tokens': sum(tokens),
            'avg_tokens': statistics.mean(tokens),
            'total_cost': sum(costs),
            'avg_cost': statistics.mean(costs)
        }
    
    def get_websocket_statistics(self) -> Dict:
        """Get WebSocket metrics statistics"""
        if not self._metrics['websocket']:
            return {}
        
        durations = [m['duration'] for m in self._metrics['websocket']]
        chunks = [m['chunks'] for m in self._metrics['websocket']]
        
        return {
            'total_messages': len(durations),
            'avg_duration': statistics.mean(durations),
            'p95_duration': self._percentile(durations, 0.95),
            'avg_chunks': statistics.mean(chunks),
            'total_chunks': sum(chunks)
        }
    
    def get_provider_statistics(self) -> Dict:
        """Get provider-specific statistics"""
        stats = {}
        
        for provider, metrics in self._metrics['providers'].items():
            if not metrics:
                continue
            
            durations = [m['duration'] for m in metrics]
            successes = [m['success'] for m in metrics]
            costs = [m['cost'] for m in metrics if m['cost'] > 0]
            
            stats[provider] = {
                'total_requests': len(metrics),
                'success_rate': sum(successes) / len(successes) * 100,
                'avg_duration': statistics.mean(durations),
                'p95_duration': self._percentile(durations, 0.95),
                'total_cost': sum(costs) if costs else 0,
                'avg_cost': statistics.mean(costs) if costs else 0
            }
        
        return stats
    
    def get_model_statistics(self) -> Dict:
        """Get model-specific statistics"""
        stats = {}
        
        for model, metrics in self._metrics['models'].items():
            if not metrics:
                continue
            
            durations = [m['duration'] for m in metrics]
            tokens = [m['tokens'] for m in metrics]
            costs = [m['cost'] for m in metrics if m['cost'] > 0]
            
            stats[model] = {
                'total_requests': len(metrics),
                'avg_duration': statistics.mean(durations),
                'p95_duration': self._percentile(durations, 0.95),
                'total_tokens': sum(tokens),
                'avg_tokens': statistics.mean(tokens),
                'total_cost': sum(costs) if costs else 0
            }
        
        return stats
    
    def get_error_statistics(self) -> Dict:
        """Get error statistics"""
        if not self._metrics['errors']:
            return {'total_errors': 0}
        
        error_by_provider = defaultdict(int)
        for error in self._metrics['errors']:
            error_by_provider[error['provider']] += 1
        
        return {
            'total_errors': len(self._metrics['errors']),
            'errors_by_provider': dict(error_by_provider)
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile
        
        Args:
            data: List of numbers
            percentile: Percentile (0.0 to 1.0)
        
        Returns:
            Percentile value
        """
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def generate_report(self, output_dir: str = './reports'):
        """Generate metrics report
        
        Args:
            output_dir: Directory to save report
        """
        os.makedirs(output_dir, exist_ok=True)
        
        report = {
            'test_duration': time.time() - self._start_time,
            'chat_stats': self.get_chat_statistics(),
            'websocket_stats': self.get_websocket_statistics(),
            'provider_stats': self.get_provider_statistics(),
            'model_stats': self.get_model_statistics(),
            'error_stats': self.get_error_statistics(),
            'total_cost': sum(self._metrics['costs'])
        }
        
        # Save JSON report
        report_file = os.path.join(output_dir, 'custom_metrics.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Custom metrics report saved to {report_file}")
        
        # Print summary
        self.print_summary(report)
    
    def generate_provider_report(self, output_dir: str = './reports'):
        """Generate provider comparison report"""
        stats = self.get_provider_statistics()
        
        if not stats:
            logger.warning("No provider metrics to report")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        report_file = os.path.join(output_dir, 'provider_comparison.json')
        
        with open(report_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Provider comparison report saved to {report_file}")
        
        # Print comparison
        print("\n" + "="*60)
        print("PROVIDER COMPARISON")
        print("="*60)
        
        for provider, data in sorted(stats.items()):
            print(f"\n{provider.upper()}:")
            print(f"  Requests: {data['total_requests']}")
            print(f"  Success Rate: {data['success_rate']:.1f}%")
            print(f"  Avg Duration: {data['avg_duration']:.3f}s")
            print(f"  P95 Duration: {data['p95_duration']:.3f}s")
            print(f"  Total Cost: ${data['total_cost']:.4f}")
    
    def print_summary(self, report: Dict):
        """Print metrics summary"""
        print("\n" + "="*60)
        print("CUSTOM METRICS SUMMARY")
        print("="*60)
        
        if report['chat_stats']:
            print("\nCHAT METRICS:")
            print(f"  Total Requests: {report['chat_stats']['total_requests']}")
            print(f"  Avg Duration: {report['chat_stats']['avg_duration']:.3f}s")
            print(f"  P95 Duration: {report['chat_stats']['p95_duration']:.3f}s")
            print(f"  P99 Duration: {report['chat_stats']['p99_duration']:.3f}s")
            print(f"  Total Tokens: {report['chat_stats']['total_tokens']:,}")
            print(f"  Total Cost: ${report['chat_stats']['total_cost']:.4f}")
        
        if report['error_stats']['total_errors'] > 0:
            print(f"\nERRORS:")
            print(f"  Total: {report['error_stats']['total_errors']}")
        
        print("\n" + "="*60)
