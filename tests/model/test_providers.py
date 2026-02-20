"""Tests for model providers."""
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestModelProviders:
    """Test suite for model providers."""
    
    @pytest.mark.asyncio
    async def test_openai_provider_generation(self, mock_openai_provider):
        """Test OpenAI provider generates response."""
        response = await mock_openai_provider.generate("Hello, world!")
        
        assert response is not None
        assert "Mock response" in response
        assert mock_openai_provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_anthropic_provider_generation(self, mock_anthropic_provider):
        """Test Anthropic provider generates response."""
        response = await mock_anthropic_provider.generate("Test prompt")
        
        assert response is not None
        assert "Anthropic" in response
        assert mock_anthropic_provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_ollama_provider_generation(self, mock_ollama_provider):
        """Test Ollama provider generates response."""
        response = await mock_ollama_provider.generate("Test prompt")
        
        assert response is not None
        assert "Ollama" in response
    
    @pytest.mark.asyncio
    async def test_provider_streaming(self, mock_openai_provider):
        """Test provider streaming response."""
        chunks = []
        async for chunk in mock_openai_provider.generate_stream("Test"):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert mock_openai_provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_provider_failure(self, failing_provider):
        """Test provider handles failures."""
        with pytest.raises(Exception) as exc_info:
            await failing_provider.generate("Test")
        
        assert "Mock failure" in str(exc_info.value)
    
    def test_provider_availability(self, mock_openai_provider, failing_provider):
        """Test provider availability checking."""
        assert mock_openai_provider.is_available() is True
        assert failing_provider.is_available() is False
    
    @pytest.mark.asyncio
    async def test_provider_fallback(self, mock_openai_provider, mock_anthropic_provider, failing_provider):
        """Test fallback between providers."""
        # Simulate trying failing provider first, then successful one
        providers = [failing_provider, mock_anthropic_provider]
        
        response = None
        for provider in providers:
            try:
                response = await provider.generate("Test")
                break
            except Exception:
                continue
        
        assert response is not None
        assert "Anthropic" in response
        assert mock_anthropic_provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_multiple_provider_calls(self, mock_openai_provider):
        """Test provider handles multiple calls."""
        for i in range(3):
            await mock_openai_provider.generate(f"Test {i}")
        
        assert mock_openai_provider.call_count == 3
