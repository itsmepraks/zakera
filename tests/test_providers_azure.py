"""Tests for Azure OpenAI provider."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.model.providers_azure import AzureOpenAIProvider


@pytest.fixture
def azure_config():
    """Test configuration."""
    return {
        "azure_endpoint": "https://test.openai.azure.com",
        "api_key": "test-api-key",
        "deployment_name": "gpt-4-test",
        "api_version": "2024-02-15-preview",
        "region": "eastus",
    }


@pytest.fixture
def provider(azure_config):
    """Create provider instance."""
    return AzureOpenAIProvider(azure_config)


class TestAzureOpenAIProvider:
    """Test Azure OpenAI provider functionality."""

    def test_initialization(self, provider, azure_config):
        """Test provider initialization."""
        assert provider.azure_endpoint == azure_config["azure_endpoint"]
        assert provider.api_key == azure_config["api_key"]
        assert provider.deployment_name == azure_config["deployment_name"]
        assert provider.api_version == azure_config["api_version"]
        assert provider.region == azure_config["region"]

    def test_missing_endpoint(self):
        """Test error when endpoint is missing."""
        with pytest.raises(ValueError, match="Azure endpoint is required"):
            AzureOpenAIProvider({
                "api_key": "test-key",
                "deployment_name": "test",
            })

    def test_missing_api_key(self):
        """Test error when API key is missing."""
        with pytest.raises(ValueError, match="API key is required"):
            AzureOpenAIProvider({
                "azure_endpoint": "https://test.openai.azure.com",
                "deployment_name": "test",
            })

    def test_missing_deployment_name(self):
        """Test error when deployment name is missing."""
        with pytest.raises(ValueError, match="Deployment name is required"):
            AzureOpenAIProvider({
                "azure_endpoint": "https://test.openai.azure.com",
                "api_key": "test-key",
            })

    def test_endpoint_url_construction(self, provider):
        """Test endpoint URL construction."""
        url = provider._get_endpoint_url()
        expected = (
            "https://test.openai.azure.com/openai/deployments/gpt-4-test"
            "/chat/completions?api-version=2024-02-15-preview"
        )
        assert url == expected

    def test_headers(self, provider):
        """Test request headers."""
        headers = provider._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["api-key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_generate_success(self, provider):
        """Test successful generation."""
        mock_response = {
            "choices": [{
                "message": {"content": "Test response"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
        
        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_response
            
            messages = [{"role": "user", "content": "Test"}]
            result = await provider.generate(messages)
            
            assert result["content"] == "Test response"
            assert result["tokens"]["total"] == 30
            assert result["provider"] == "azure_openai"
            assert "cost" in result
            assert "latency" in result

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test successful health check."""
        with patch.object(provider, "_make_request", new_callable=AsyncMock):
            result = await provider.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider):
        """Test failed health check."""
        with patch.object(
            provider, "_make_request", side_effect=Exception("Connection error")
        ):
            result = await provider.health_check()
            assert result is False

    def test_get_available_models(self, provider):
        """Test getting available models."""
        models = provider.get_available_models()
        assert "gpt-4" in models
        assert "gpt-35-turbo" in models
        assert len(models) > 0

    def test_get_model_info(self, provider):
        """Test getting model information."""
        info = provider.get_model_info("gpt-4")
        assert "max_tokens" in info
        assert "context_window" in info
        assert "cost_per_1k_input" in info
        assert "cost_per_1k_output" in info
