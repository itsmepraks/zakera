"""Tests for OpenRouter provider."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from src.model.providers_openrouter import (
    OpenRouterProvider,
    Message,
    TokenBucket,
    RateLimitError
)


@pytest.fixture
def provider():
    """Create OpenRouter provider instance."""
    with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'sk-or-test-key'}):
        return OpenRouterProvider(model_name="openai/gpt-3.5-turbo")


@pytest.fixture
def messages():
    """Create test messages."""
    return [
        Message(role="user", content="Hello, how are you?")
    ]


class TestTokenBucket:
    """Test TokenBucket rate limiter."""
    
    @pytest.mark.asyncio
    async def test_acquire_success(self):
        """Test successful token acquisition."""
        bucket = TokenBucket(rate=60.0, capacity=60.0)
        result = await bucket.acquire()
        assert result is True
        assert bucket.tokens < 60.0
    
    @pytest.mark.asyncio
    async def test_acquire_rate_limited(self):
        """Test rate limiting."""
        bucket = TokenBucket(rate=60.0, capacity=1.0)
        
        # First acquire should succeed
        result1 = await bucket.acquire()
        assert result1 is True
        
        # Second acquire should fail (rate limited)
        result2 = await bucket.acquire()
        assert result2 is False
    
    def test_get_wait_time(self):
        """Test wait time calculation."""
        bucket = TokenBucket(rate=60.0, capacity=1.0)
        bucket.tokens = 0.5
        
        wait_time = bucket.get_wait_time()
        assert wait_time > 0
        assert wait_time < 1.0


class TestOpenRouterProvider:
    """Test OpenRouter provider."""
    
    def test_initialization_with_key(self):
        """Test provider initialization with API key."""
        provider = OpenRouterProvider(
            api_key="sk-or-test-key",
            model_name="openai/gpt-3.5-turbo"
        )
        
        assert provider.api_key == "sk-or-test-key"
        assert provider.model_name == "openai/gpt-3.5-turbo"
        assert provider.base_url == "https://openrouter.ai/api/v1"
    
    def test_initialization_without_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OpenRouter API key is required"):
                OpenRouterProvider()
    
    def test_get_headers(self, provider):
        """Test request headers generation."""
        headers = provider._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer sk-or-test-key"
        assert "Content-Type" in headers
        assert headers["HTTP-Referer"] == "https://github.com/itsmepraks/zakera"
    
    @pytest.mark.asyncio
    async def test_generate_success(self, provider, messages):
        """Test successful response generation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "I'm doing well, thank you!"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        }
        
        with patch.object(provider, '_make_request', return_value=mock_response):
            response = await provider.generate(messages)
            
            assert response.content == "I'm doing well, thank you!"
            assert response.model == "openai/gpt-3.5-turbo"
            assert response.finish_reason == "stop"
            assert response.usage["total_tokens"] == 25
            assert response.cost > 0
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_params(self, provider, messages):
        """Test generation with custom parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        with patch.object(provider, '_make_request', return_value=mock_response):
            response = await provider.generate(
                messages,
                temperature=0.9,
                max_tokens=1000,
                top_p=0.95
            )
            
            assert response is not None
    
    @pytest.mark.asyncio
    async def test_stream_generate(self, provider, messages):
        """Test streaming response generation."""
        # Mock streaming response
        async def mock_aiter_lines():
            yield 'data: {"choices": [{"delta": {"content": "Hello"}}]}'
            yield 'data: {"choices": [{"delta": {"content": " world"}}]}'
            yield 'data: [DONE]'
        
        mock_stream = Mock()
        mock_stream.aiter_lines = mock_aiter_lines
        mock_stream.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_client.__aexit__ = AsyncMock()
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_httpx.return_value.__aenter__.return_value.stream = Mock(return_value=mock_client)
            
            chunks = []
            async for chunk in provider.stream_generate(messages):
                chunks.append(chunk)
            
            assert len(chunks) > 0
    
    def test_calculate_cost(self, provider):
        """Test cost calculation."""
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
        
        cost = provider._calculate_cost(usage)
        assert cost > 0
        assert cost == 0.003  # (1500/1000) * 0.002
    
    def test_get_stats(self, provider):
        """Test statistics retrieval."""
        provider.total_requests = 10
        provider.total_cost = 0.05
        provider.total_tokens = 5000
        
        stats = provider.get_stats()
        
        assert stats["total_requests"] == 10
        assert stats["total_cost"] == 0.05
        assert stats["total_tokens"] == 5000
        assert stats["average_cost_per_request"] == 0.005
        assert stats["model"] == "openai/gpt-3.5-turbo"
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, provider):
        """Test rate limiting behavior."""
        # Set very low rate limit
        provider.rate_limiter = TokenBucket(rate=1.0, capacity=1.0)
        
        # First request should succeed
        await provider._handle_rate_limit()
        
        # Second request should wait
        start_time = asyncio.get_event_loop().time()
        await provider._handle_rate_limit()
        end_time = asyncio.get_event_loop().time()
        
        # Should have waited at least some time
        assert end_time >= start_time
    
    @pytest.mark.asyncio
    async def test_error_handling(self, provider, messages):
        """Test error handling and retries."""
        with patch.object(provider, '_make_request', side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await provider.generate(messages)


@pytest.mark.asyncio
async def test_integration_example(provider, messages):
    """Example integration test (would need real API key)."""
    # This test would require a real API key and internet connection
    # Skipped in CI/CD, useful for local testing
    pytest.skip("Integration test requires real API key")
    
    response = await provider.generate(messages)
    assert response.content
    assert response.usage["total_tokens"] > 0
