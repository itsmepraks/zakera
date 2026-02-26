"""Tests for Claude-3.5 Sonnet provider."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.model.providers_claude import (
    Claude35SonnetProvider,
    TokenBucket,
    RateLimitConfig,
    RequestMetrics
)
from src.model.providers import Message


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""
    
    @pytest.mark.asyncio
    async def test_consume_tokens(self):
        """Test consuming tokens from bucket."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume tokens
        assert await bucket.consume(5) is True
        assert await bucket.consume(5) is True
        
        # Should be empty now
        assert await bucket.consume(1) is False
    
    @pytest.mark.asyncio
    async def test_refill_tokens(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec
        
        # Consume all tokens
        assert await bucket.consume(10) is True
        assert await bucket.consume(1) is False
        
        # Wait for refill
        await asyncio.sleep(0.5)  # Should refill ~5 tokens
        assert await bucket.consume(4) is True
    
    @pytest.mark.asyncio
    async def test_wait_for_tokens(self):
        """Test waiting for token availability."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)
        
        # Consume all tokens
        await bucket.consume(10)
        
        # Wait for tokens to refill
        result = await bucket.wait_for_tokens(1, timeout=2.0)
        assert result is True


class TestRequestMetrics:
    """Tests for RequestMetrics."""
    
    def test_record_request(self):
        """Test recording request metrics."""
        metrics = RequestMetrics()
        
        metrics.record_request(success=True, tokens=100, cost=0.01, latency=1.5)
        
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.total_tokens_used == 100
        assert metrics.total_cost == 0.01
        assert len(metrics.request_latencies) == 1
    
    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = RequestMetrics()
        
        metrics.record_request(True, 100, 0.01, 1.0)
        metrics.record_request(True, 100, 0.01, 1.0)
        metrics.record_request(False, 0, 0.0, 1.0)
        
        assert metrics.get_success_rate() == 2/3
    
    def test_average_latency(self):
        """Test average latency calculation."""
        metrics = RequestMetrics()
        
        metrics.record_request(True, 100, 0.01, 1.0)
        metrics.record_request(True, 100, 0.01, 2.0)
        metrics.record_request(True, 100, 0.01, 3.0)
        
        assert metrics.get_average_latency() == 2.0


class TestClaude35SonnetProvider:
    """Tests for Claude-3.5 Sonnet provider."""
    
    @pytest.fixture
    def provider(self):
        """Create provider instance for testing."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            config = RateLimitConfig(
                requests_per_minute=100,
                requests_per_day=1000
            )
            return Claude35SonnetProvider(rate_limit_config=config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.model_name == "claude-3-5-sonnet-20241022"
        assert provider.api_key == "test-key"
        assert provider.rate_config.requests_per_minute == 100
        assert provider.metrics.total_requests == 0
    
    @pytest.mark.asyncio
    async def test_convert_messages(self, provider):
        """Test message format conversion."""
        messages = [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!")
        ]
        
        system, claude_msgs = provider._convert_messages(messages)
        
        assert system == "You are a helpful assistant"
        assert len(claude_msgs) == 2
        assert claude_msgs[0]["role"] == "user"
        assert claude_msgs[1]["role"] == "assistant"
    
    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        # $3 per 1M input tokens, $15 per 1M output tokens
        cost = provider._calculate_cost(1000, 1000)
        
        expected_cost = (1000 / 1_000_000 * 3.0) + (1000 / 1_000_000 * 15.0)
        assert cost == pytest.approx(expected_cost)
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, provider):
        """Test rate limiting enforcement."""
        # Should allow request within limits
        result = await provider._wait_for_rate_limit()
        assert result is True
        assert provider.daily_requests == 1
    
    @pytest.mark.asyncio
    async def test_generate_with_mock_response(self, provider):
        """Test generate method with mocked API response."""
        messages = [
            Message(role="user", content="What is AI?")
        ]
        
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"text": "AI is artificial intelligence."}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20
            }
        }
        
        with patch.object(provider, '_make_request_with_retry', new=AsyncMock(return_value=mock_response)):
            response = await provider.generate(messages)
            
            assert response.content == "AI is artificial intelligence."
            assert response.model == provider.model_name
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 20
            assert "cost_usd" in response.usage
            
            # Check metrics were updated
            assert provider.metrics.successful_requests == 1
            assert provider.metrics.total_tokens_used == 30
    
    @pytest.mark.asyncio
    async def test_stream_generate_with_mock_response(self, provider):
        """Test streaming generation with mocked API response."""
        messages = [
            Message(role="user", content="Tell me a story")
        ]
        
        # Mock streaming response data
        stream_data = [
            'data: {"type": "message_start", "message": {"usage": {"input_tokens": 10}}}',
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Once "}}',
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "upon "}}',
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "a time"}}',
            'data: {"type": "message_delta", "usage": {"output_tokens": 15}}',
            'data: {"type": "message_stop"}'
        ]
        
        async def mock_aiter_lines():
            for line in stream_data:
                yield line
        
        # Mock the streaming response
        mock_response = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)
        mock_client.stream.return_value = mock_stream_context
        
        with patch.object(provider, '_get_client', new=AsyncMock(return_value=mock_client)):
            chunks = []
            async for chunk in provider.stream_generate(messages):
                chunks.append(chunk)
            
            assert chunks == ["Once ", "upon ", "a time"]
            assert provider.metrics.successful_requests == 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, provider):
        """Test error handling in generate method."""
        messages = [
            Message(role="user", content="Test")
        ]
        
        # Mock a failure
        with patch.object(provider, '_make_request_with_retry', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await provider.generate(messages)
            
            # Check error was tracked
            assert provider.metrics.failed_requests == 1
    
    def test_get_metrics(self, provider):
        """Test metrics retrieval."""
        provider.metrics.total_requests = 10
        provider.metrics.successful_requests = 8
        provider.metrics.failed_requests = 2
        
        metrics = provider.get_metrics()
        
        assert metrics["total_requests"] == 10
        assert metrics["successful_requests"] == 8
        assert metrics["failed_requests"] == 2
        assert metrics["success_rate"] == 0.8
    
    @pytest.mark.asyncio
    async def test_context_manager(self, provider):
        """Test async context manager usage."""
        async with provider as p:
            assert p is not None
            assert p == provider


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
