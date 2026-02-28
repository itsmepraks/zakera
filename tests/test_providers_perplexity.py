"""Tests for Perplexity AI provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.model.providers import ProviderConfig
from src.model.providers_perplexity import PerplexityProvider


@pytest.fixture
def perplexity_config():
    """Create test configuration for Perplexity."""
    return ProviderConfig(
        provider="perplexity",
        api_key="test-api-key",
        timeout=30.0
    )


@pytest.fixture
def perplexity_provider(perplexity_config):
    """Create Perplexity provider instance."""
    return PerplexityProvider(perplexity_config)


@pytest.mark.asyncio
async def test_perplexity_provider_initialization(perplexity_provider):
    """Test Perplexity provider initialization."""
    assert perplexity_provider.api_key == "test-api-key"
    assert perplexity_provider.base_url == "https://api.perplexity.ai"
    assert "sonar" in perplexity_provider.pricing


@pytest.mark.asyncio
async def test_generate_sync_response(perplexity_provider):
    """Test synchronous response generation."""
    mock_response = {
        "choices": [{
            "message": {
                "content": "Quantum computing uses quantum mechanics principles.",
                "citations": ["https://example.com/quantum"]
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        },
        "model": "sonar"
    }
    
    with patch.object(perplexity_provider.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        
        response = await perplexity_provider.generate(
            prompt="Explain quantum computing",
            model="sonar",
            temperature=0.7
        )
        
        assert response.content == "Quantum computing uses quantum mechanics principles."
        assert response.provider == "perplexity"
        assert response.model == "sonar"
        assert response.input_tokens == 10
        assert response.output_tokens == 20
        assert len(response.metadata["citations"]) == 1


@pytest.mark.asyncio
async def test_generate_with_search_params(perplexity_provider):
    """Test generation with search-specific parameters."""
    mock_response = {
        "choices": [{
            "message": {
                "content": "Latest news content",
                "citations": ["https://news.example.com"]
            },
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}
    }
    
    with patch.object(perplexity_provider.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        
        response = await perplexity_provider.generate(
            prompt="What's the latest AI news?",
            model="sonar",
            search_recency_filter="day",
            return_citations=True,
            search_domain_filter=["arxiv.org", "github.com"]
        )
        
        # Verify search parameters were included in request
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        
        assert payload["search_recency_filter"] == "day"
        assert payload["return_citations"] is True
        assert "arxiv.org" in payload["search_domain_filter"]
        assert response.metadata["citations"][0] == "https://news.example.com"


@pytest.mark.asyncio
async def test_cost_calculation(perplexity_provider):
    """Test cost calculation for different models."""
    cost_sonar = perplexity_provider._calculate_cost("sonar", 1000, 1000)
    cost_large = perplexity_provider._calculate_cost("sonar-large", 1000, 1000)
    
    assert cost_sonar == 0.002  # (1000/1000 * 0.001) * 2
    assert cost_large == 0.004  # (1000/1000 * 0.002) * 2
    assert cost_large > cost_sonar


@pytest.mark.asyncio
async def test_list_models(perplexity_provider):
    """Test listing available models."""
    models = await perplexity_provider.list_models()
    
    assert len(models) == 3
    assert any(m["id"] == "sonar" for m in models)
    assert any(m["id"] == "sonar-medium" for m in models)
    assert any(m["id"] == "sonar-large" for m in models)
    
    # All models should support search
    for model in models:
        assert model["supports_search"] is True
        assert model["supports_streaming"] is True


@pytest.mark.asyncio
async def test_error_handling(perplexity_provider):
    """Test error handling for API failures."""
    with patch.object(perplexity_provider.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("API connection failed")
        
        with pytest.raises(Exception) as exc_info:
            await perplexity_provider.generate(
                prompt="Test prompt",
                model="sonar"
            )
        
        assert "API connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_config_success(perplexity_provider):
    """Test successful configuration validation."""
    mock_response = {
        "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
    }
    
    with patch.object(perplexity_provider.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp
        
        result = await perplexity_provider.validate_config()
        assert result is True


@pytest.mark.asyncio
async def test_validate_config_failure(perplexity_config):
    """Test configuration validation failure."""
    perplexity_config.api_key = None
    provider = PerplexityProvider(perplexity_config)
    
    result = await provider.validate_config()
    assert result is False


@pytest.mark.asyncio 
async def test_streaming_response(perplexity_provider):
    """Test streaming response generation."""
    response = await perplexity_provider.generate(
        prompt="Test streaming",
        model="sonar",
        stream=True
    )
    
    assert response.metadata["streaming"] is True
    assert response.stream is not None
    assert response.provider == "perplexity"
