"""Custom metrics collection for performance tests."""

import time
from typing import Dict, List
from collections import defaultdict
import statistics


class CustomMetrics:
    """Collect custom metrics during performance tests."""
    
    def __init__(self):
        self.model_latencies: Dict[str, List[float]] = defaultdict(list)
        self.token_usage: List[int] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()
    
    def record_model_latency(self, provider: str, latency_ms: float):
        """Record model provider latency.
        
        Args:
            provider: Provider name
            latency_ms: Latency in milliseconds
        """
        self.model_latencies[provider].append(latency_ms)
    
    def record_token_usage(self, tokens: int):
        """Record token usage.
        
        Args:
            tokens: Number of tokens used
        """
        self.token_usage.append(tokens)
    
    def record_error(self, error_type: str):
        """Record an error.
        
        Args:
            error_type: Type of error
        """
        self.error_counts[error_type] += 1
    
    def record_request(self, endpoint: str):
        """Record a request.
        
        Args:
            endpoint: API endpoint
        """
        self.request_counts[endpoint] += 1
    
    def get_provider_stats(self, provider: str) -> Dict[str, float]:
        """Get statistics for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Stats dictionary
        """
        latencies = self.model_latencies.get(provider, [])
        if not latencies:
            return {}
        
        return {
            "count": len(latencies),
            "avg": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "p95": self._percentile(latencies, 0.95),
            "p99": self._percentile(latencies, 0.99),
        }
    
    def get_token_stats(self) -> Dict[str, float]:
        """Get token usage statistics.
        
        Returns:
            Token stats dictionary
        """
        if not self.token_usage:
            return {}
        
        return {
            "total": sum(self.token_usage),
            "avg": statistics.mean(self.token_usage),
            "median": statistics.median(self.token_usage),
            "min": min(self.token_usage),
            "max": max(self.token_usage),
        }
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get error summary.
        
        Returns:
            Error counts by type
        """
        return dict(self.error_counts)
    
    def get_request_summary(self) -> Dict[str, int]:
        """Get request summary.
        
        Returns:
            Request counts by endpoint
        """
        return dict(self.request_counts)
    
    def get_duration(self) -> float:
        """Get test duration in seconds.
        
        Returns:
            Duration in seconds
        """
        return time.time() - self.start_time
    
    def get_summary(self) -> Dict:
        """Get complete metrics summary.
        
        Returns:
            Complete metrics dictionary
        """
        return {
            "duration_seconds": self.get_duration(),
            "providers": {
                provider: self.get_provider_stats(provider)
                for provider in self.model_latencies.keys()
            },
            "tokens": self.get_token_stats(),
            "errors": self.get_error_summary(),
            "requests": self.get_request_summary(),
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile.
        
        Args:
            data: List of values
            percentile: Percentile (0.0 to 1.0)
            
        Returns:
            Percentile value
        """
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_summary(self):
        """Print metrics summary to console."""
        print("\n" + "="*80)
        print("CUSTOM METRICS SUMMARY")
        print("="*80)
        
        print(f"\nTest Duration: {self.get_duration():.2f} seconds")
        
        print("\nProvider Performance:")
        for provider, stats in self.get_summary()["providers"].items():
            print(f"  {provider}:")
            print(f"    Count: {stats['count']}")
            print(f"    Avg: {stats['avg']:.2f}ms")
            print(f"    P95: {stats['p95']:.2f}ms")
            print(f"    P99: {stats['p99']:.2f}ms")
        
        token_stats = self.get_token_stats()
        if token_stats:
            print("\nToken Usage:")
            print(f"  Total: {token_stats['total']:,}")
            print(f"  Average: {token_stats['avg']:.0f}")
        
        errors = self.get_error_summary()
        if errors:
            print("\nErrors:")
            for error_type, count in errors.items():
                print(f"  {error_type}: {count}")
        
        print("\n" + "="*80 + "\n")
