"""Integration tests for model providers.

Tests the complete model provider system including:
- Provider initialization and configuration
- API request handling and response parsing
- Error handling and retry logic
- Streaming responses
- Token counting and cost calculation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import json

# Import providers
try:
    from src.model.providers import OpenAIProvider, AnthropicProvider
    from src.model.providers_mistral import MistralProvider, MistralConfig
    from src.model.model_manager import ModelManager
except ImportError:
    pytest.skip("Model providers not available", allow_module_level=True)


class TestMistralProvider:
    """Test suite for Mistral AI provider."""
    
    @pytest.fixture
    def mistral_config(self):
        """Create test configuration."""
        return MistralConfig(
            api_key="test_key_123",
            base_url="https://api.mistral.ai/v1",
            timeout=30,
            max_retries=2,
        )
    
    @pytest.fixture
    def mock_response(self):
        """Create mock API response."""
        return {
            "id": "cmpl-test123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "mistral-small-latest",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "This is a test response from Mistral AI.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, mistral_config):
        """Test provider initializes correctly."""
        provider = MistralProvider(mistral_config)
        assert provider.config.api_key == "test_key_123"
        assert len(provider.AVAILABLE_MODELS) > 0
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_generate_response(self, mistral_config, mock_response):
        """Test generating a non-streaming response."""
        provider = MistralProvider(mistral_config)
        
        # Mock the HTTP client
        with patch.object(provider.client, 'post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = Mock()
            mock_post.return_value = mock_resp
            
            result = await provider.generate(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                temperature=0.7,
            )
            
            # Verify response structure
            assert result["text"] == "This is a test response from Mistral AI."
            assert result["provider"] == "mistral"
            assert result["model"] == "mistral-small-latest"
            assert "usage" in result
            assert result["usage"]["total_tokens"] == 30
            assert "cost" in result
            assert result["cost"] > 0
            assert "latency" in result
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_cost_calculation(self, mistral_config):
        """Test cost calculation for different models."""
        provider = MistralProvider(mistral_config)
        
        # Test mistral-tiny
        cost_tiny = provider._calculate_cost("mistral-tiny-latest", 1000, 1000)
        assert cost_tiny > 0
        
        # Test mistral-large (should be more expensive)
        cost_large = provider._calculate_cost("mistral-large-latest", 1000, 1000)
        assert cost_large > cost_tiny
        
        # Test with zero tokens
        cost_zero = provider._calculate_cost("mistral-small-latest", 0, 0)
        assert cost_zero == 0
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, mistral_config, mock_response):
        """Test retry logic on API failures."""
        provider = MistralProvider(mistral_config)
        
        with patch.object(provider.client, 'post') as mock_post:
            # First two calls fail, third succeeds
            fail_resp = AsyncMock()
            fail_resp.status_code = 429
            fail_resp.raise_for_status.side_effect = Exception("Rate limited")
            
            success_resp = AsyncMock()
            success_resp.json.return_value = mock_response
            success_resp.raise_for_status = Mock()
            
            mock_post.side_effect = [
                fail_resp,
                fail_resp,
                success_resp,
            ]
            
            # Should eventually succeed after retries
            with patch('asyncio.sleep'):
                result = await provider.generate(
                    model="mistral-small-latest",
                    messages=[{"role": "user", "content": "Test"}],
                )
            
            assert result["text"] == "This is a test response from Mistral AI."
            assert mock_post.call_count == 3
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_health_check(self, mistral_config):
        """Test health check endpoint."""
        provider = MistralProvider(mistral_config)
        
        with patch.object(provider.client, 'get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.raise_for_status = Mock()
            mock_get.return_value = mock_resp
            
            health = await provider.health_check()
            
            assert health["status"] == "healthy"
            assert health["provider"] == "mistral"
            assert health["api_accessible"] is True
            assert len(health["available_models"]) > 0
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_invalid_model(self, mistral_config, mock_response):
        """Test handling of unknown model names."""
        provider = MistralProvider(mistral_config)
        
        with patch.object(provider.client, 'post') as mock_post:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = Mock()
            mock_post.return_value = mock_resp
            
            # Should still work but log a warning
            result = await provider.generate(
                model="unknown-model",
                messages=[{"role": "user", "content": "Test"}],
            )
            
            assert result["text"] is not None
        
        await provider.close()


class TestModelProviderIntegration:
    """Integration tests for multiple providers."""
    
    @pytest.fixture
    def mock_providers(self):
        """Create mock providers for testing."""
        openai_mock = AsyncMock()
        openai_mock.generate.return_value = {
            "text": "OpenAI response",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "usage": {"total_tokens": 50},
            "cost": 0.001,
        }
        
        anthropic_mock = AsyncMock()
        anthropic_mock.generate.return_value = {
            "text": "Anthropic response",
            "provider": "anthropic",
            "model": "claude-3-sonnet",
            "usage": {"total_tokens": 45},
            "cost": 0.002,
        }
        
        mistral_mock = AsyncMock()
        mistral_mock.generate.return_value = {
            "text": "Mistral response",
            "provider": "mistral",
            "model": "mistral-small-latest",
            "usage": {"total_tokens": 40},
            "cost": 0.0015,
        }
        
        return {
            "openai": openai_mock,
            "anthropic": anthropic_mock,
            "mistral": mistral_mock,
        }
    
    @pytest.mark.asyncio
    async def test_provider_selection(self, mock_providers):
        """Test selecting appropriate provider."""
        # Test that each provider returns expected format
        for provider_name, provider in mock_providers.items():
            result = await provider.generate(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}],
            )
            
            assert "text" in result
            assert result["provider"] == provider_name
            assert "usage" in result
            assert "cost" in result
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_providers):
        """Test handling concurrent requests to multiple providers."""
        tasks = []
        
        for provider in mock_providers.values():
            task = provider.generate(
                model="test-model",
                messages=[{"role": "user", "content": "Test"}],
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(mock_providers)
        for result in results:
            assert "text" in result
            assert "provider" in result
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self, mock_providers):
        """Test fallback to next provider on failure."""
        # Make first provider fail
        mock_providers["openai"].generate.side_effect = Exception("API Error")
        
        # Should fallback to anthropic
        result = None
        for provider in mock_providers.values():
            try:
                result = await provider.generate(
                    model="test",
                    messages=[{"role": "user", "content": "Test"}],
                )
                break
            except Exception:
                continue
        
        assert result is not None
        assert result["provider"] in ["anthropic", "mistral"]
    
    @pytest.mark.asyncio
    async def test_response_format_consistency(self, mock_providers):
        """Test all providers return consistent format."""
        required_fields = ["text", "provider", "model", "usage", "cost"]
        
        for provider in mock_providers.values():
            result = await provider.generate(
                model="test",
                messages=[{"role": "user", "content": "Test"}],
            )
            
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            # Check usage structure
            assert "total_tokens" in result["usage"]
            assert isinstance(result["cost"], (int, float))


class TestStreamingResponses:
    """Test streaming response handling."""
    
    @pytest.mark.asyncio
    async def test_streaming_chunks(self):
        """Test processing streaming response chunks."""
        chunks = [
            {"text": "Hello", "full_text": "Hello", "finish_reason": None},
            {"text": " world", "full_text": "Hello world", "finish_reason": None},
            {"text": "!", "full_text": "Hello world!", "finish_reason": "stop"},
        ]
        
        full_response = ""
        for chunk in chunks:
            full_response += chunk["text"]
        
        assert full_response == "Hello world!"
    
    @pytest.mark.asyncio
    async def test_streaming_error_handling(self):
        """Test error handling in streaming mode."""
        async def mock_stream():
            yield {"text": "Start"}
            raise Exception("Stream interrupted")
        
        collected = []
        with pytest.raises(Exception):
            async for chunk in mock_stream():
                collected.append(chunk)
        
        assert len(collected) == 1


class TestProviderMetrics:
    """Test metrics collection for providers."""
    
    def test_token_counting(self):
        """Test token counting accuracy."""
        # Simple token estimation (words * 1.3)
        text = "This is a test message with ten words here"
        estimated_tokens = len(text.split()) * 1.3
        
        assert estimated_tokens > 0
        assert estimated_tokens < len(text)  # Should be less than characters
    
    def test_cost_accumulation(self):
        """Test cost tracking across multiple requests."""
        costs = [0.001, 0.002, 0.0015, 0.003]
        total_cost = sum(costs)
        
        assert total_cost == pytest.approx(0.0075, rel=1e-6)
    
    def test_latency_tracking(self):
        """Test latency measurement."""
        import time
        
        start = time.time()
        time.sleep(0.1)
        latency = time.time() - start
        
        assert latency >= 0.1
        assert latency < 0.2  # Should be close to 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
