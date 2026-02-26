"""Anthropic Claude-3.5 Sonnet provider with streaming and rate limiting.

This module implements a production-ready provider for Anthropic's Claude-3.5 Sonnet model,
including advanced features like streaming responses, rate limiting, and comprehensive error handling.
"""

import asyncio
import time
import logging
from typing import List, Dict, Optional, AsyncIterator, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json

import httpx
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from src.model.providers import ModelProvider, Message, ModelResponse
from src.monitoring.metrics import metrics_collector


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for Claude API."""
    requests_per_minute: int = 50
    requests_per_day: int = 1000
    tokens_per_minute: int = 100000
    max_retries: int = 3
    retry_base_delay: float = 1.0
    max_retry_delay: float = 60.0


class TokenBucket:
    """Token bucket algorithm for rate limiting.
    
    Implements a token bucket that refills at a constant rate,
    allowing burst traffic while maintaining average rate limits.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens in bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        async with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def wait_for_tokens(self, tokens: int = 1, timeout: float = 60.0) -> bool:
        """Wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            timeout: Maximum wait time in seconds
            
        Returns:
            True if tokens acquired, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.consume(tokens):
                return True
            await asyncio.sleep(0.1)
        
        return False


@dataclass
class RequestMetrics:
    """Metrics for tracking API requests."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    rate_limit_hits: int = 0
    request_latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def record_request(self, success: bool, tokens: int, cost: float, latency: float):
        """Record metrics for a request."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_tokens_used += tokens
        self.total_cost += cost
        self.request_latencies.append(latency)
    
    def get_average_latency(self) -> float:
        """Calculate average request latency."""
        if not self.request_latencies:
            return 0.0
        return sum(self.request_latencies) / len(self.request_latencies)
    
    def get_success_rate(self) -> float:
        """Calculate request success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class Claude35SonnetProvider(ModelProvider):
    """Production-ready Claude-3.5 Sonnet provider with streaming and rate limiting.
    
    Features:
    - Streaming responses for real-time output
    - Token bucket rate limiting
    - Automatic retries with exponential backoff
    - Comprehensive metrics and monitoring
    - Cost tracking and usage analytics
    """
    
    # Model pricing (per 1M tokens)
    INPUT_COST_PER_1M = 3.0
    OUTPUT_COST_PER_1M = 15.0
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "claude-3-5-sonnet-20241022",
        rate_limit_config: Optional[RateLimitConfig] = None
    ):
        """Initialize Claude-3.5 Sonnet provider.
        
        Args:
            api_key: Anthropic API key (default: from environment)
            model_name: Model identifier
            rate_limit_config: Rate limiting configuration
        """
        super().__init__(api_key, model_name)
        
        import os
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.base_url = "https://api.anthropic.com/v1"
        self.api_version = "2023-06-01"
        
        # Rate limiting
        self.rate_config = rate_limit_config or RateLimitConfig()
        self.rate_limiter = TokenBucket(
            capacity=self.rate_config.requests_per_minute,
            refill_rate=self.rate_config.requests_per_minute / 60.0
        )
        self.daily_requests = 0
        self.daily_reset_time = datetime.now() + timedelta(days=1)
        
        # Metrics
        self.metrics = RequestMetrics()
        
        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            f"Initialized Claude-3.5 Sonnet provider with model {model_name}, "
            f"rate limits: {self.rate_config.requests_per_minute} RPM, "
            f"{self.rate_config.requests_per_day} RPD"
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
        return self.client
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _check_daily_limit(self) -> bool:
        """Check if daily request limit is reached."""
        # Reset daily counter if needed
        if datetime.now() >= self.daily_reset_time:
            self.daily_requests = 0
            self.daily_reset_time = datetime.now() + timedelta(days=1)
        
        return self.daily_requests < self.rate_config.requests_per_day
    
    async def _wait_for_rate_limit(self) -> bool:
        """Wait for rate limit availability.
        
        Returns:
            True if rate limit acquired, False if daily limit reached
        """
        # Check daily limit
        if not self._check_daily_limit():
            logger.warning(
                f"Daily request limit ({self.rate_config.requests_per_day}) reached"
            )
            self.metrics.rate_limit_hits += 1
            return False
        
        # Wait for token bucket
        if not await self.rate_limiter.wait_for_tokens(1, timeout=60.0):
            logger.warning("Rate limit timeout after 60 seconds")
            self.metrics.rate_limit_hits += 1
            return False
        
        self.daily_requests += 1
        return True
    
    def _convert_messages(self, messages: List[Message]) -> tuple[Optional[str], List[Dict]]:
        """Convert messages to Claude API format.
        
        Args:
            messages: List of messages in our format
            
        Returns:
            Tuple of (system_message, conversation_messages)
        """
        system_message = None
        claude_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                claude_messages.append({
                    "role": msg.role if msg.role != "assistant" else "assistant",
                    "content": msg.content
                })
        
        return system_message, claude_messages
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate request cost.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        return input_cost + output_cost
    
    async def _make_request_with_retry(
        self,
        payload: Dict[str, Any],
        stream: bool = False
    ) -> httpx.Response:
        """Make API request with retry logic.
        
        Args:
            payload: Request payload
            stream: Whether to stream response
            
        Returns:
            HTTP response
            
        Raises:
            Exception: If all retries exhausted
        """
        client = await self._get_client()
        headers = {
            "anthropic-version": self.api_version,
            "x-api-key": self.api_key,
            "content-type": "application/json"
        }
        
        last_exception = None
        delay = self.rate_config.retry_base_delay
        
        for attempt in range(self.rate_config.max_retries):
            try:
                if stream:
                    return await client.post(
                        f"{self.base_url}/messages",
                        json=payload,
                        headers=headers,
                        timeout=120.0
                    )
                else:
                    response = await client.post(
                        f"{self.base_url}/messages",
                        json=payload,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                last_exception = e
                
                # Handle rate limits
                if e.response.status_code == 429:
                    retry_after = float(e.response.headers.get("retry-after", delay))
                    logger.warning(
                        f"Rate limited by API, waiting {retry_after}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(retry_after)
                    delay = min(delay * 2, self.rate_config.max_retry_delay)
                    continue
                
                # Handle server errors (5xx)
                if 500 <= e.response.status_code < 600:
                    logger.warning(
                        f"Server error {e.response.status_code}, retrying (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.rate_config.max_retry_delay)
                    continue
                
                # Don't retry client errors (4xx, except 429)
                raise
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(f"Request error: {e}, retrying (attempt {attempt + 1})")
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.rate_config.max_retry_delay)
        
        raise Exception(
            f"Failed after {self.rate_config.max_retries} retries: {last_exception}"
        )
    
    @tracer.start_as_current_span("claude_generate")
    async def generate(self, messages: List[Message], **kwargs) -> ModelResponse:
        """Generate a response using Claude-3.5 Sonnet.
        
        Args:
            messages: Conversation messages
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            ModelResponse with generated content and metadata
        """
        start_time = time.time()
        span = trace.get_current_span()
        
        try:
            # Wait for rate limit
            if not await self._wait_for_rate_limit():
                raise Exception("Rate limit exceeded")
            
            # Convert messages
            system_message, claude_messages = self._convert_messages(messages)
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "messages": claude_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            }
            
            if system_message:
                payload["system"] = system_message
            
            if "top_p" in kwargs:
                payload["top_p"] = kwargs["top_p"]
            if "top_k" in kwargs:
                payload["top_k"] = kwargs["top_k"]
            
            # Make request
            response = await self._make_request_with_retry(payload, stream=False)
            result = response.json()
            
            # Extract response
            content = result["content"][0]["text"]
            finish_reason = result["stop_reason"]
            
            # Extract usage
            usage_data = result["usage"]
            input_tokens = usage_data["input_tokens"]
            output_tokens = usage_data["output_tokens"]
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost
            cost = self._calculate_cost(input_tokens, output_tokens)
            
            # Record metrics
            latency = time.time() - start_time
            self.metrics.record_request(True, total_tokens, cost, latency)
            
            # Update span attributes
            span.set_attribute("model", self.model_name)
            span.set_attribute("input_tokens", input_tokens)
            span.set_attribute("output_tokens", output_tokens)
            span.set_attribute("cost", cost)
            span.set_attribute("latency", latency)
            span.set_status(Status(StatusCode.OK))
            
            # Update Prometheus metrics
            if metrics_collector:
                metrics_collector.record_model_request(
                    provider="anthropic",
                    model=self.model_name,
                    success=True
                )
                metrics_collector.record_model_tokens(
                    provider="anthropic",
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                metrics_collector.record_model_cost(
                    provider="anthropic",
                    model=self.model_name,
                    cost=cost
                )
            
            return ModelResponse(
                content=content,
                model=self.model_name,
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": cost
                },
                finish_reason=finish_reason
            )
            
        except Exception as e:
            latency = time.time() - start_time
            self.metrics.record_request(False, 0, 0.0, latency)
            
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            
            if metrics_collector:
                metrics_collector.record_model_request(
                    provider="anthropic",
                    model=self.model_name,
                    success=False
                )
            
            logger.error(f"Error generating response from Claude: {e}")
            raise
    
    @tracer.start_as_current_span("claude_stream_generate")
    async def stream_generate(
        self,
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response using Claude-3.5 Sonnet.
        
        Args:
            messages: Conversation messages
            **kwargs: Additional parameters
            
        Yields:
            Chunks of generated text
        """
        start_time = time.time()
        span = trace.get_current_span()
        
        try:
            # Wait for rate limit
            if not await self._wait_for_rate_limit():
                raise Exception("Rate limit exceeded")
            
            # Convert messages
            system_message, claude_messages = self._convert_messages(messages)
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "messages": claude_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": True
            }
            
            if system_message:
                payload["system"] = system_message
            
            # Get client and make streaming request
            client = await self._get_client()
            headers = {
                "anthropic-version": self.api_version,
                "x-api-key": self.api_key,
                "content-type": "application/json"
            }
            
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0
            
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                json=payload,
                headers=headers,
                timeout=120.0
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            
                            # Handle different event types
                            event_type = data.get("type")
                            
                            if event_type == "message_start":
                                # Extract initial usage
                                usage = data.get("message", {}).get("usage", {})
                                input_tokens = usage.get("input_tokens", 0)
                            
                            elif event_type == "content_block_delta":
                                # Extract text delta
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield text
                            
                            elif event_type == "message_delta":
                                # Extract final usage
                                usage = data.get("usage", {})
                                output_tokens = usage.get("output_tokens", 0)
                            
                            elif event_type == "message_stop":
                                # Streaming complete
                                total_tokens = input_tokens + output_tokens
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
            # Record metrics
            cost = self._calculate_cost(input_tokens, output_tokens)
            latency = time.time() - start_time
            self.metrics.record_request(True, total_tokens, cost, latency)
            
            # Update span
            span.set_attribute("model", self.model_name)
            span.set_attribute("input_tokens", input_tokens)
            span.set_attribute("output_tokens", output_tokens)
            span.set_attribute("cost", cost)
            span.set_attribute("streaming", True)
            span.set_status(Status(StatusCode.OK))
            
            # Update metrics
            if metrics_collector:
                metrics_collector.record_model_request(
                    provider="anthropic",
                    model=self.model_name,
                    success=True
                )
                metrics_collector.record_model_tokens(
                    provider="anthropic",
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                metrics_collector.record_model_cost(
                    provider="anthropic",
                    model=self.model_name,
                    cost=cost
                )
            
        except Exception as e:
            latency = time.time() - start_time
            self.metrics.record_request(False, 0, 0.0, latency)
            
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            
            if metrics_collector:
                metrics_collector.record_model_request(
                    provider="anthropic",
                    model=self.model_name,
                    success=False
                )
            
            logger.error(f"Error streaming response from Claude: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get provider metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.get_success_rate(),
            "total_tokens_used": self.metrics.total_tokens_used,
            "total_cost_usd": self.metrics.total_cost,
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "average_latency_seconds": self.metrics.get_average_latency(),
            "daily_requests": self.daily_requests,
            "daily_limit": self.rate_config.requests_per_day
        }
