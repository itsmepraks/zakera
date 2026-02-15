"""Enhanced Model Manager with robust error handling and retry logic.

Extends the base ModelManager with:
- Exponential backoff retry mechanism
- Circuit breaker pattern for failing providers
- Request deduplication
- Comprehensive error categorization
- Provider health tracking
"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import random

from src.model.model_manager import ModelManager
from src.monitoring.metrics import (
    model_retry_counter,
    model_circuit_breaker_state,
    model_request_dedup_counter,
)


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry mechanism."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes to close circuit
    timeout: float = 60.0  # Seconds before trying half-open state
    window_size: int = 100  # Number of recent requests to consider


class CircuitBreakerState:
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class ProviderHealth:
    """Track health metrics for a model provider."""
    provider_name: str
    state: str = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    recent_requests: deque = field(default_factory=lambda: deque(maxlen=100))
    total_requests: int = 0
    total_failures: int = 0
    
    def record_success(self):
        """Record a successful request."""
        self.success_count += 1
        self.total_requests += 1
        self.last_success_time = datetime.utcnow()
        self.recent_requests.append(("success", datetime.utcnow()))
        
        # Reset failure count on success in half-open state
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed request."""
        self.failure_count += 1
        self.total_requests += 1
        self.total_failures += 1
        self.last_failure_time = datetime.utcnow()
        self.recent_requests.append(("failure", datetime.utcnow()))
    
    def get_error_rate(self) -> float:
        """Calculate recent error rate."""
        if not self.recent_requests:
            return 0.0
        failures = sum(1 for status, _ in self.recent_requests if status == "failure")
        return failures / len(self.recent_requests)
    
    def get_health_score(self) -> float:
        """Calculate health score (0.0 to 1.0)."""
        if self.state == CircuitBreakerState.OPEN:
            return 0.0
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return 0.5
        return 1.0 - self.get_error_rate()


class ErrorCategory:
    """Categorize errors for appropriate handling."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    INVALID_REQUEST = "invalid_request"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


class EnhancedModelManager(ModelManager):
    """Enhanced model manager with robust error handling."""

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        """Initialize enhanced model manager.
        
        Args:
            retry_config: Retry mechanism configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__()
        
        self.retry_config = retry_config or RetryConfig()
        self.cb_config = circuit_breaker_config or CircuitBreakerConfig()
        
        # Provider health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}
        
        # Request deduplication cache
        self.request_cache: Dict[str, Tuple[Any, float]] = {}
        self.cache_ttl = 5.0  # seconds
        
        # Pending requests for deduplication
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        self.logger.info(
            "Enhanced model manager initialized",
            extra={
                "retry_config": vars(self.retry_config),
                "circuit_breaker_config": vars(self.cb_config),
            },
        )

    def _get_provider_health(self, provider_name: str) -> ProviderHealth:
        """Get or create provider health tracker."""
        if provider_name not in self.provider_health:
            self.provider_health[provider_name] = ProviderHealth(provider_name=provider_name)
        return self.provider_health[provider_name]

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for appropriate handling."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "429" in error_str:
            return ErrorCategory.RATE_LIMIT
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorCategory.TIMEOUT
        elif "authentication" in error_str or "401" in error_str or "403" in error_str:
            return ErrorCategory.AUTHENTICATION
        elif "invalid" in error_str or "400" in error_str:
            return ErrorCategory.INVALID_REQUEST
        elif "connection" in error_str or "network" in error_str:
            return ErrorCategory.NETWORK_ERROR
        elif "api error" in error_str or "500" in error_str or "503" in error_str:
            return ErrorCategory.API_ERROR
        else:
            return ErrorCategory.UNKNOWN

    def _should_retry(self, error_category: str, attempt: int) -> bool:
        """Determine if request should be retried based on error category."""
        if attempt >= self.retry_config.max_retries:
            return False
        
        # Don't retry authentication or invalid request errors
        if error_category in [ErrorCategory.AUTHENTICATION, ErrorCategory.INVALID_REQUEST]:
            return False
        
        return True

    async def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = min(
            self.retry_config.initial_delay
            * (self.retry_config.exponential_base ** attempt),
            self.retry_config.max_delay,
        )
        
        if self.retry_config.jitter:
            # Add random jitter (0% to 25% of delay)
            jitter = delay * random.random() * 0.25
            delay += jitter
        
        return delay

    def _check_circuit_breaker(self, provider_name: str) -> bool:
        """Check if circuit breaker allows request.
        
        Returns:
            True if request should proceed, False if circuit is open
        """
        health = self._get_provider_health(provider_name)
        
        # Update circuit breaker state
        if health.state == CircuitBreakerState.CLOSED:
            if health.failure_count >= self.cb_config.failure_threshold:
                health.state = CircuitBreakerState.OPEN
                self.logger.warning(
                    f"Circuit breaker opened for provider {provider_name}",
                    extra={
                        "provider": provider_name,
                        "failure_count": health.failure_count,
                    },
                )
                model_circuit_breaker_state.labels(
                    provider=provider_name, state="open"
                ).set(1)
                return False
        
        elif health.state == CircuitBreakerState.OPEN:
            # Check if timeout has elapsed
            if health.last_failure_time:
                elapsed = (datetime.utcnow() - health.last_failure_time).total_seconds()
                if elapsed >= self.cb_config.timeout:
                    health.state = CircuitBreakerState.HALF_OPEN
                    health.failure_count = 0
                    health.success_count = 0
                    self.logger.info(
                        f"Circuit breaker half-open for provider {provider_name}",
                        extra={"provider": provider_name},
                    )
                    model_circuit_breaker_state.labels(
                        provider=provider_name, state="half_open"
                    ).set(1)
                else:
                    return False
            else:
                return False
        
        elif health.state == CircuitBreakerState.HALF_OPEN:
            if health.success_count >= self.cb_config.success_threshold:
                health.state = CircuitBreakerState.CLOSED
                health.failure_count = 0
                self.logger.info(
                    f"Circuit breaker closed for provider {provider_name}",
                    extra={"provider": provider_name},
                )
                model_circuit_breaker_state.labels(
                    provider=provider_name, state="closed"
                ).set(1)
        
        return True

    def _create_request_hash(self, model: str, messages: List[Dict], **kwargs) -> str:
        """Create hash for request deduplication."""
        # Create a deterministic hash of the request
        content = f"{model}:{str(messages)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(content.encode()).hexdigest()

    async def _get_cached_response(self, request_hash: str) -> Optional[Any]:
        """Get cached response if available and not expired."""
        if request_hash in self.request_cache:
            response, timestamp = self.request_cache[request_hash]
            if time.time() - timestamp < self.cache_ttl:
                model_request_dedup_counter.inc()
                self.logger.debug(f"Returning cached response for hash {request_hash[:8]}")
                return response
            else:
                del self.request_cache[request_hash]
        return None

    async def generate_with_retry(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate response with retry logic and circuit breaker.
        
        Args:
            model: Model name
            messages: Conversation messages
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response
            
        Raises:
            Exception: If all retries exhausted or circuit breaker open
        """
        # Check request deduplication
        request_hash = self._create_request_hash(model, messages, **kwargs)
        
        # Check cache
        cached_response = await self._get_cached_response(request_hash)
        if cached_response is not None:
            return cached_response
        
        # Check if same request is pending
        if request_hash in self.pending_requests:
            self.logger.debug(f"Waiting for pending request {request_hash[:8]}")
            return await self.pending_requests[request_hash]
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[request_hash] = future
        
        try:
            # Get provider name from model
            provider_name = self._get_provider_name(model)
            
            # Check circuit breaker
            if not self._check_circuit_breaker(provider_name):
                raise Exception(
                    f"Circuit breaker open for provider {provider_name}. "
                    "Service temporarily unavailable."
                )
            
            attempt = 0
            last_error = None
            
            while attempt < self.retry_config.max_retries:
                try:
                    self.logger.info(
                        f"Attempt {attempt + 1}/{self.retry_config.max_retries} "
                        f"for model {model}",
                        extra={"model": model, "attempt": attempt + 1},
                    )
                    
                    # Call base class generate method
                    response = await super().generate(model, messages, **kwargs)
                    
                    # Record success
                    health = self._get_provider_health(provider_name)
                    health.record_success()
                    
                    # Cache response
                    self.request_cache[request_hash] = (response, time.time())
                    
                    # Set future result
                    if not future.done():
                        future.set_result(response)
                    
                    self.logger.info(
                        f"Successfully generated response with {model}",
                        extra={"model": model, "attempts": attempt + 1},
                    )
                    
                    return response
                
                except Exception as e:
                    last_error = e
                    error_category = self._categorize_error(e)
                    
                    self.logger.warning(
                        f"Error on attempt {attempt + 1}: {str(e)}",
                        extra={
                            "model": model,
                            "attempt": attempt + 1,
                            "error_category": error_category,
                        },
                    )
                    
                    # Record failure
                    health = self._get_provider_health(provider_name)
                    health.record_failure()
                    
                    # Increment retry counter
                    model_retry_counter.labels(
                        model=model,
                        error_category=error_category,
                    ).inc()
                    
                    # Check if should retry
                    if not self._should_retry(error_category, attempt):
                        self.logger.error(
                            f"Not retrying due to error category: {error_category}",
                            extra={"model": model, "error_category": error_category},
                        )
                        break
                    
                    attempt += 1
                    
                    if attempt < self.retry_config.max_retries:
                        # Calculate backoff delay
                        delay = await self._calculate_backoff_delay(attempt - 1)
                        
                        self.logger.info(
                            f"Retrying in {delay:.2f} seconds...",
                            extra={"model": model, "delay": delay},
                        )
                        
                        await asyncio.sleep(delay)
            
            # All retries exhausted
            error_msg = (
                f"Failed to generate response after {self.retry_config.max_retries} attempts. "
                f"Last error: {str(last_error)}"
            )
            self.logger.error(error_msg, extra={"model": model})
            
            if not future.done():
                future.set_exception(Exception(error_msg))
            
            raise Exception(error_msg)
        
        finally:
            # Clean up pending request
            if request_hash in self.pending_requests:
                del self.pending_requests[request_hash]

    def _get_provider_name(self, model: str) -> str:
        """Extract provider name from model string."""
        if model.startswith("gpt"):
            return "openai"
        elif model.startswith("claude"):
            return "anthropic"
        elif model.startswith("gemini"):
            return "google"
        elif ":" in model:  # Ollama format (model:tag)
            return "ollama"
        else:
            return "unknown"

    def get_provider_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers.
        
        Returns:
            Dictionary mapping provider name to health metrics
        """
        return {
            name: {
                "state": health.state,
                "health_score": health.get_health_score(),
                "error_rate": health.get_error_rate(),
                "total_requests": health.total_requests,
                "total_failures": health.total_failures,
                "last_success": (
                    health.last_success_time.isoformat() if health.last_success_time else None
                ),
                "last_failure": (
                    health.last_failure_time.isoformat() if health.last_failure_time else None
                ),
            }
            for name, health in self.provider_health.items()
        }

    async def cleanup_old_cache_entries(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        expired = [
            key
            for key, (_, timestamp) in self.request_cache.items()
            if current_time - timestamp >= self.cache_ttl
        ]
        
        for key in expired:
            del self.request_cache[key]
        
        if expired:
            self.logger.debug(f"Cleaned up {len(expired)} expired cache entries")
