"""Provider-specific metrics collection and tracking.

Comprehensive metrics for tracking AI provider performance, costs, and usage.
"""

import time
import logging
from typing import Dict, Optional, Any
from contextlib import contextmanager
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry
)

logger = logging.getLogger(__name__)


class ProviderMetrics:
    """Metrics collector for AI model providers.
    
    Tracks requests, latency, tokens, costs, errors, and availability
    for all AI model providers in the system.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize provider metrics.
        
        Args:
            registry: Prometheus registry (uses default if not provided)
        """
        self.registry = registry
        
        # Request metrics
        self.requests_total = Counter(
            'zakera_provider_requests_total',
            'Total number of requests to AI providers',
            ['provider', 'model', 'status'],
            registry=registry
        )
        
        self.request_duration = Histogram(
            'zakera_provider_request_duration_seconds',
            'Request duration in seconds',
            ['provider', 'model'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=registry
        )
        
        # Token metrics
        self.tokens_total = Counter(
            'zakera_provider_tokens_total',
            'Total tokens processed',
            ['provider', 'model', 'type'],
            registry=registry
        )
        
        # Cost metrics
        self.cost_total = Counter(
            'zakera_provider_cost_total',
            'Total cost in USD',
            ['provider', 'model'],
            registry=registry
        )
        
        self.cost_per_request = Histogram(
            'zakera_provider_cost_per_request',
            'Cost per request in USD',
            ['provider', 'model'],
            buckets=[0.0001, 0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'zakera_provider_errors_total',
            'Total number of errors',
            ['provider', 'error_type'],
            registry=registry
        )
        
        self.rate_limits_hit = Counter(
            'zakera_provider_rate_limits_hit_total',
            'Number of times rate limit was hit',
            ['provider'],
            registry=registry
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'zakera_provider_cache_hits_total',
            'Number of cache hits',
            ['provider', 'cache_type'],
            registry=registry
        )
        
        self.cache_misses = Counter(
            'zakera_provider_cache_misses_total',
            'Number of cache misses',
            ['provider', 'cache_type'],
            registry=registry
        )
        
        # Availability metrics
        self.provider_available = Gauge(
            'zakera_provider_available',
            'Provider availability (1=available, 0=unavailable)',
            ['provider'],
            registry=registry
        )
        
        # Active requests gauge
        self.active_requests = Gauge(
            'zakera_provider_active_requests',
            'Number of active requests',
            ['provider', 'model'],
            registry=registry
        )
        
        # Provider info
        self.provider_info = Info(
            'zakera_provider_info',
            'Provider information',
            registry=registry
        )
        
        logger.info("Provider metrics initialized")
    
    @contextmanager
    def track_request(
        self, 
        provider: str, 
        model: str,
        track_cost: bool = True
    ):
        """Context manager for tracking provider requests.
        
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            model: Model name
            track_cost: Whether to track cost metrics
            
        Yields:
            RequestTracker object with methods to record metrics
            
        Example:
            with metrics.track_request('openai', 'gpt-4') as tracker:
                response = await provider.generate(messages)
                tracker.record_tokens(response.usage)
                tracker.record_cost(response.cost)
        """
        start_time = time.time()
        self.active_requests.labels(provider=provider, model=model).inc()
        
        tracker = RequestTracker(
            metrics=self,
            provider=provider,
            model=model,
            track_cost=track_cost
        )
        
        try:
            yield tracker
            
            duration = time.time() - start_time
            self.request_duration.labels(
                provider=provider, 
                model=model
            ).observe(duration)
            
            self.requests_total.labels(
                provider=provider,
                model=model,
                status='success'
            ).inc()
            
        except Exception as e:
            self.requests_total.labels(
                provider=provider,
                model=model,
                status='error'
            ).inc()
            
            error_type = type(e).__name__
            self.errors_total.labels(
                provider=provider,
                error_type=error_type
            ).inc()
            
            logger.error(
                f"Request failed: {provider}/{model}",
                extra={
                    'provider': provider,
                    'model': model,
                    'error_type': error_type,
                    'error': str(e)
                }
            )
            raise
            
        finally:
            self.active_requests.labels(provider=provider, model=model).dec()
    
    def record_tokens(
        self, 
        provider: str, 
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ):
        """Record token usage.
        
        Args:
            provider: Provider name
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        if input_tokens > 0:
            self.tokens_total.labels(
                provider=provider,
                model=model,
                type='input'
            ).inc(input_tokens)
        
        if output_tokens > 0:
            self.tokens_total.labels(
                provider=provider,
                model=model,
                type='output'
            ).inc(output_tokens)
        
        total_tokens = input_tokens + output_tokens
        if total_tokens > 0:
            self.tokens_total.labels(
                provider=provider,
                model=model,
                type='total'
            ).inc(total_tokens)
    
    def record_cost(
        self,
        provider: str,
        model: str,
        cost: float
    ):
        """Record request cost.
        
        Args:
            provider: Provider name
            model: Model name
            cost: Cost in USD
        """
        if cost > 0:
            self.cost_total.labels(
                provider=provider,
                model=model
            ).inc(cost)
            
            self.cost_per_request.labels(
                provider=provider,
                model=model
            ).observe(cost)
    
    def record_rate_limit_hit(self, provider: str):
        """Record rate limit hit.
        
        Args:
            provider: Provider name
        """
        self.rate_limits_hit.labels(provider=provider).inc()
        logger.warning(
            f"Rate limit hit: {provider}",
            extra={'provider': provider}
        )
    
    def record_cache_hit(
        self,
        provider: str,
        cache_type: str = 'response'
    ):
        """Record cache hit.
        
        Args:
            provider: Provider name
            cache_type: Type of cache (e.g., 'response', 'embedding')
        """
        self.cache_hits.labels(
            provider=provider,
            cache_type=cache_type
        ).inc()
    
    def record_cache_miss(
        self,
        provider: str,
        cache_type: str = 'response'
    ):
        """Record cache miss.
        
        Args:
            provider: Provider name
            cache_type: Type of cache
        """
        self.cache_misses.labels(
            provider=provider,
            cache_type=cache_type
        ).inc()
    
    def set_provider_availability(
        self,
        provider: str,
        available: bool
    ):
        """Set provider availability status.
        
        Args:
            provider: Provider name
            available: Whether provider is available
        """
        self.provider_available.labels(provider=provider).set(
            1 if available else 0
        )
        
        log_level = logging.INFO if available else logging.WARNING
        logger.log(
            log_level,
            f"Provider availability: {provider} = {available}",
            extra={'provider': provider, 'available': available}
        )
    
    def set_provider_info(
        self,
        provider: str,
        version: str,
        **kwargs
    ):
        """Set provider information.
        
        Args:
            provider: Provider name
            version: Provider version
            **kwargs: Additional provider metadata
        """
        info = {
            'provider': provider,
            'version': version,
            **kwargs
        }
        self.provider_info.info(info)


class RequestTracker:
    """Helper class for tracking individual request metrics."""
    
    def __init__(
        self,
        metrics: ProviderMetrics,
        provider: str,
        model: str,
        track_cost: bool
    ):
        self.metrics = metrics
        self.provider = provider
        self.model = model
        self.track_cost = track_cost
    
    def record_tokens(
        self,
        usage: Dict[str, int]
    ):
        """Record token usage from response.
        
        Args:
            usage: Dictionary with token counts (prompt_tokens, completion_tokens, etc.)
        """
        input_tokens = usage.get('prompt_tokens', 0) or usage.get('input_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0) or usage.get('output_tokens', 0)
        
        self.metrics.record_tokens(
            self.provider,
            self.model,
            input_tokens,
            output_tokens
        )
        
        logger.debug(
            f"Tokens recorded: {self.provider}/{self.model}",
            extra={
                'provider': self.provider,
                'model': self.model,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens
            }
        )
    
    def record_cost(self, cost: float):
        """Record request cost.
        
        Args:
            cost: Cost in USD
        """
        if self.track_cost and cost > 0:
            self.metrics.record_cost(self.provider, self.model, cost)
            logger.debug(
                f"Cost recorded: {self.provider}/{self.model} = ${cost:.6f}",
                extra={
                    'provider': self.provider,
                    'model': self.model,
                    'cost': cost
                }
            )
    
    def record_rate_limit_hit(self):
        """Record that rate limit was hit."""
        self.metrics.record_rate_limit_hit(self.provider)


# Global metrics instance
_metrics: Optional[ProviderMetrics] = None


def get_provider_metrics() -> ProviderMetrics:
    """Get global provider metrics instance.
    
    Returns:
        ProviderMetrics instance
    """
    global _metrics
    if _metrics is None:
        _metrics = ProviderMetrics()
    return _metrics
