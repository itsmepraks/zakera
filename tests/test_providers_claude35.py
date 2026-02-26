"""Test suite for Claude-3.5 Sonnet provider.

Comprehensive tests for the Claude35Provider including:
- Rate limiting
- Message conversion
- API calls (mocked)
- Streaming
- Error handling
- Cost calculation
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List

try:
    from src.model.providers_claude35 import (
        Claude35Provider,
        Claude35Config,
        RateLimiter,
    )
    from src.model.providers import Message, ModelResponse
except ImportError:
    # Fallback for different project structures
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from src.model.providers_claude35 import (
        Claude35Provider,
        Claude35Config,
        RateLimiter,
    )
    from src.model.providers import Message, ModelResponse


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000
        )
        
        assert limiter.requests_per_minute == 60
        assert limiter.tokens_per_minute == 100000
        assert limiter.request_tokens == 60
        assert limiter.token_tokens == 100000
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test rate limiter allows requests within limits."""
        limiter = RateLimiter(
            requests_per_minute=10,
            tokens_per_minute=1000
        )
        
        # Should allow immediate acquisition
        await limiter.acquire(token_count=100)
        
        assert limiter.request_tokens < 10
        assert limiter.token_tokens < 1000
    
    @pytest.mark.asyncio
    async def test_rate_limiter_refill(self):
        """Test rate limiter refills tokens over time."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=60000
        )
        
        # Consume all tokens
        for _ in range(60):
            limiter.request_tokens -= 1
        
        assert limiter.request_tokens == 0
        
        # Wait for refill
        await asyncio.sleep(1.1)
        
        # Tokens should be refilled (1 second = 1 request per second for 60/min)
        await limiter.acquire()
        assert limiter.request_tokens >= 0


class TestClaude35Config:
    """Test Claude-3.5 configuration."""
    
    def test_config_initialization(self):
        """Test config initializes with defaults."""
        config = Claude35Config(
            api_key="sk-ant-test-key"
        )
        
        assert config.api_key == "sk-ant-test-key"
        assert config.model_name == "claude-3-5-sonnet-20241022"
        assert config.base_url == "https://api.anthropic.com/v1"
        assert config.max_retries == 3
        assert config.timeout == 120
    
    def test_config_custom_values(self):
        """Test config accepts custom values."""
        config = Claude35Config(
            api_key="sk-ant-test",
            model_name="claude-3-5-sonnet-20240620",
            max_retries=5,
            timeout=180,
            requests_per_minute=100
        )
        
        assert config.model_name == "claude-3-5-sonnet-20240620"
        assert config.max_retries == 5
        assert config.timeout == 180
        assert config.requests_per_minute == 100


class TestClaude35Provider:
    """Test Claude-3.5 provider functionality."""
    
    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        return Claude35Provider(
            api_key="sk-ant-test-key-12345",
            model_name="claude-3-5-sonnet-20241022"
        )
    
    @pytest.fixture
    def sample_messages(self) -> List[Message]:
        """Create sample messages for testing."""
        return [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello, how are you?"),
            Message(role="assistant", content="I'm doing well, thank you!"),
            Message(role="user", content="What's the weather like?")
        ]
    
    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider.config.api_key == "sk-ant-test-key-12345"
        assert provider.config.model_name == "claude-3-5-sonnet-20241022"
        assert provider.rate_limiter is not None
        assert provider.client is not None
    
    def test_provider_initialization_without_api_key(self):
        """Test provider raises error without API key."""
        # Clear environment variable
        old_key = os.environ.get("ANTHROPIC_API_KEY")
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        
        with pytest.raises(ValueError, match="API key required"):
            Claude35Provider()
        
        # Restore environment
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key
    
    def test_message_conversion_with_system(self, provider, sample_messages):
        """Test message conversion handles system messages."""
        system_prompt, claude_messages = provider._convert_messages(sample_messages)
        
        assert system_prompt == "You are a helpful assistant."
        assert len(claude_messages) == 3  # Excludes system message
        assert claude_messages[0]["role"] == "user"
        assert claude_messages[1]["role"] == "assistant"
        assert claude_messages[2]["role"] == "user"
    
    def test_message_conversion_without_system(self, provider):
        """Test message conversion without system message."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!")
        ]
        
        system_prompt, claude_messages = provider._convert_messages(messages)
        
        assert system_prompt is None
        assert len(claude_messages) == 2
    
    def test_token_estimation(self, provider):
        """Test token estimation."""
        text = "This is a test message"
        tokens = provider._estimate_tokens(text)
        
        # Should estimate roughly len(text) / 4
        assert tokens > 0
        assert tokens == len(text) // 4
    
    def test_cost_calculation(self, provider):
        """Test cost calculation."""
        cost = provider._calculate_cost(
            input_tokens=1000,
            output_tokens=500
        )
        
        # Input: 1000 tokens * $0.003/1K = $0.003
        # Output: 500 tokens * $0.015/1K = $0.0075
        # Total: $0.0105
        expected_cost = 0.0105
        assert abs(cost - expected_cost) < 0.0001
    
    def test_headers_generation(self, provider):
        """Test HTTP headers are correctly generated."""
        headers = provider._get_headers()
        
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "sk-ant-test-key-12345"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["content-type"] == "application/json"
    
    @pytest.mark.asyncio
    async def test_generate_with_mock(self, provider, sample_messages):
        """Test generate method with mocked API response."""
        # Mock HTTP response
        mock_response_data = {
            "content": [{"text": "This is a test response from Claude."}],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50
            },
            "stop_reason": "end_turn"
        }
        
        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            response = await provider.generate(
                messages=sample_messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            assert isinstance(response, ModelResponse)
            assert response.content == "This is a test response from Claude."
            assert response.model == "claude-3-5-sonnet-20241022"
            assert response.usage["prompt_tokens"] == 100
            assert response.usage["completion_tokens"] == 50
            assert "cost" in response.usage
    
    @pytest.mark.asyncio
    async def test_generate_empty_messages(self, provider):
        """Test generate raises error with empty messages."""
        with pytest.raises(ValueError, match="At least one user or assistant message required"):
            await provider.generate(messages=[])
    
    @pytest.mark.asyncio
    async def test_stream_generate_with_mock(self, provider, sample_messages):
        """Test streaming generation with mocked response."""
        # Mock SSE stream
        mock_stream_data = [
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}',
            'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":" world"}}',
            'data: {"type":"message_stop"}',
        ]
        
        async def mock_aiter_lines():
            for line in mock_stream_data:
                yield line
        
        with patch.object(provider.client, 'stream') as mock_stream:
            mock_response = AsyncMock()
            mock_response.raise_for_status = Mock()
            mock_response.aiter_lines = mock_aiter_lines
            mock_response.__aenter__.return_value = mock_response
            mock_response.__aexit__.return_value = None
            mock_stream.return_value = mock_response
            
            chunks = []
            async for chunk in provider.stream_generate(
                messages=sample_messages,
                temperature=0.7
            ):
                chunks.append(chunk)
            
            assert len(chunks) == 2
            assert chunks[0] == "Hello"
            assert chunks[1] == " world"
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, provider, sample_messages):
        """Test retry logic on retryable errors."""
        # Mock to fail twice then succeed
        call_count = 0
        
        async def mock_post_with_retries(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count < 3:
                # Simulate 429 rate limit error
                mock_response = Mock()
                mock_response.status_code = 429
                mock_response.text = "Rate limit exceeded"
                from httpx import HTTPStatusError, Request, Response
                raise HTTPStatusError(
                    "Rate limit",
                    request=Mock(spec=Request),
                    response=Mock(spec=Response, status_code=429, text="Rate limit exceeded")
                )
            
            # Success on third try
            mock_response = Mock()
            mock_response.json.return_value = {
                "content": [{"text": "Success after retries"}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "stop_reason": "end_turn"
            }
            mock_response.raise_for_status = Mock()
            return mock_response
        
        with patch.object(provider.client, 'post', side_effect=mock_post_with_retries):
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                response = await provider.generate(messages=sample_messages)
                
                assert call_count == 3
                assert response.content == "Success after retries"
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self, provider, sample_messages):
        """Test non-retryable errors are raised immediately."""
        with patch.object(provider.client, 'post', new_callable=AsyncMock) as mock_post:
            # Simulate 400 bad request (non-retryable)
            from httpx import HTTPStatusError
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_post.side_effect = HTTPStatusError(
                "Bad request",
                request=Mock(),
                response=mock_response
            )
            
            with pytest.raises(Exception):
                await provider.generate(messages=sample_messages)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, provider):
        """Test provider cleanup."""
        await provider.close()
        # Client should be closed (this is a basic check)
        assert provider.client is not None


class TestModelLimits:
    """Test model-specific limits and configurations."""
    
    def test_model_limits_exist(self):
        """Test model limits are defined for supported models."""
        assert "claude-3-5-sonnet-20241022" in Claude35Provider.MODEL_LIMITS
        assert "claude-3-5-sonnet-20240620" in Claude35Provider.MODEL_LIMITS
    
    def test_model_limits_values(self):
        """Test model limit values are correct."""
        limits = Claude35Provider.MODEL_LIMITS["claude-3-5-sonnet-20241022"]
        
        assert limits["max_tokens"] == 8192
        assert limits["context_window"] == 200000
        assert limits["cost_per_1k_input"] == 0.003
        assert limits["cost_per_1k_output"] == 0.015


class TestIntegration:
    """Integration tests (require API key)."""
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_real_api_call(self):
        """Test real API call (requires valid API key)."""
        provider = Claude35Provider(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        messages = [
            Message(role="user", content="Say 'Hello, World!' and nothing else.")
        ]
        
        response = await provider.generate(
            messages=messages,
            max_tokens=50,
            temperature=0
        )
        
        assert response.content
        assert "Hello" in response.content or "hello" in response.content
        assert response.usage["total_tokens"] > 0
        assert response.usage["cost"] > 0
        
        await provider.close()
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set"
    )
    @pytest.mark.asyncio
    async def test_real_streaming(self):
        """Test real streaming API call."""
        provider = Claude35Provider(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        messages = [
            Message(role="user", content="Count from 1 to 5, one number per word.")
        ]
        
        chunks = []
        async for chunk in provider.stream_generate(
            messages=messages,
            max_tokens=50
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0
        
        await provider.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
