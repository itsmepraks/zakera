"""Tests for DeepSeek AI provider.

Tests cover:
- Provider initialization
- Chat completion
- Streaming responses
- Error handling and retries
- Configuration validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.model.model_manager import get_provider, reset as reset_provider_cache
from src.model.providers_deepseek import (
    DeepSeekConfig,
    DeepSeekProvider,
)


@pytest.fixture
def deepseek_config():
    """Create test DeepSeek configuration."""
    return DeepSeekConfig(
        api_key="test-api-key",
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=2048,
    )


@pytest.fixture
def mock_response():
    """Create mock API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?",
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


class TestDeepSeekConfig:
    """Test DeepSeek configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DeepSeekConfig(api_key="test-key")

        assert config.api_key == "test-key"
        assert config.model == "deepseek-chat"
        assert config.api_base == "https://api.deepseek.com/v1"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_custom_config(self):
        """Test custom configuration."""
        config = DeepSeekConfig(
            api_key="custom-key",
            model="deepseek-coder",
            temperature=0.5,
            max_tokens=8192,
            timeout=120,
        )

        assert config.api_key == "custom-key"
        assert config.model == "deepseek-coder"
        assert config.temperature == 0.5
        assert config.max_tokens == 8192
        assert config.timeout == 120


class TestDeepSeekProvider:
    """Test DeepSeek provider."""

    def test_initialization(self, deepseek_config):
        """Test provider initialization."""
        provider = DeepSeekProvider(deepseek_config)

        assert provider.config == deepseek_config
        assert provider.client is not None

    def test_unsupported_model(self):
        """Test initialization with unsupported model."""
        config = DeepSeekConfig(
            api_key="test-key",
            model="unsupported-model",
        )

        with pytest.raises(ValueError, match="not supported"):
            DeepSeekProvider(config)

    @pytest.mark.asyncio
    async def test_chat_completion(self, deepseek_config, mock_response):
        """Test chat completion."""
        provider = DeepSeekProvider(deepseek_config)

        # Mock the HTTP client
        with patch.object(
            provider.client,
            "post",
            return_value=AsyncMock(json=lambda: mock_response, raise_for_status=lambda: None)
        ) as mock_post:
            messages = [
                {"role": "user", "content": "Hello!"}
            ]

            response = await provider.chat(messages)

            assert response["content"] == "Hello! How can I help you today?"
            assert response["model"] == "deepseek-chat"
            assert response["usage"]["total_tokens"] == 30
            assert response["finish_reason"] == "stop"

            # Verify API call
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_with_custom_params(self, deepseek_config, mock_response):
        """Test chat with custom parameters."""
        provider = DeepSeekProvider(deepseek_config)

        with patch.object(
            provider.client,
            "post",
            return_value=AsyncMock(json=lambda: mock_response, raise_for_status=lambda: None)
        ) as mock_post:
            messages = [{"role": "user", "content": "Test"}]

            await provider.chat(
                messages,
                temperature=0.9,
                max_tokens=1024,
                top_p=0.95,
            )

            # Check that custom params were passed
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            assert payload["temperature"] == 0.9
            assert payload["max_tokens"] == 1024
            assert payload["top_p"] == 0.95

    @pytest.mark.asyncio
    async def test_chat_retry_on_error(self, deepseek_config):
        """Test retry mechanism on API errors."""
        deepseek_config.max_retries = 2
        provider = DeepSeekProvider(deepseek_config)

        # Mock to fail twice then succeed
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise httpx.HTTPError("API Error")

            mock_resp = AsyncMock()
            mock_resp.raise_for_status = lambda: None
            mock_resp.json = lambda: {
                "choices": [{"message": {"content": "Success"}, "finish_reason": "stop"}],
                "model": "deepseek-chat",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            }
            return mock_resp

        with patch.object(provider.client, "post", side_effect=mock_post):
            messages = [{"role": "user", "content": "Test"}]
            response = await provider.chat(messages)

            assert response["content"] == "Success"
            assert call_count == 2  # Failed once, succeeded second time

    @pytest.mark.asyncio
    async def test_get_model_info(self, deepseek_config):
        """Test getting model information."""
        provider = DeepSeekProvider(deepseek_config)

        info = await provider.get_model_info()

        assert "name" in info
        assert "description" in info
        assert "max_tokens" in info
        assert info["max_tokens"] > 0

    @pytest.mark.asyncio
    async def test_count_tokens(self, deepseek_config):
        """Test token counting."""
        provider = DeepSeekProvider(deepseek_config)

        text = "This is a test message"
        token_count = await provider.count_tokens(text)

        assert token_count > 0
        assert isinstance(token_count, int)

    @pytest.mark.asyncio
    async def test_close(self, deepseek_config):
        """Test closing provider."""
        provider = DeepSeekProvider(deepseek_config)

        await provider.close()

        # Client should be closed
        assert provider.client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager(self, deepseek_config):
        """Test using provider as async context manager."""
        async with DeepSeekProvider(deepseek_config) as provider:
            assert provider is not None
            assert provider.client is not None

        # Client should be closed after context
        assert provider.client.is_closed


class TestDeepSeekV3ProviderRegistry:
    """Test DeepSeek V3 provider registration and aliasing."""

    def test_model_manager_maps_deepseek_v3_to_deepseek_chat(self, monkeypatch):
        """Verify the model manager routes deepseek-v3 to deepseek-chat."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-api-key")
        reset_provider_cache()

        try:
            with patch("src.model.providers_deepseek.DeepSeekProvider") as mock_provider_cls:
                mock_instance = MagicMock()
                mock_provider_cls.return_value = mock_instance

                provider = get_provider("deepseek-v3")

            assert provider is mock_instance
            mock_provider_cls.assert_called_once()

            config = mock_provider_cls.call_args.args[0]
            assert config.api_key == "test-api-key"
            assert config.model == "deepseek-chat"
        finally:
            reset_provider_cache()
