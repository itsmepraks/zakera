"""
Unit tests for the xAI Grok-2 provider.

All HTTP calls are intercepted with pytest-mock / unittest.mock so no real
API key is required.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.model.providers_xai_grok2 import (
    XAIAuthError,
    XAIConfig,
    XAIContextLengthError,
    XAIGrok2Provider,
    XAIModel,
    XAIRateLimitError,
    XAIResponse,
    XAIServiceError,
    XAIUsage,
    build_text_message,
    build_vision_message,
    encode_image_to_data_uri,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> XAIConfig:
    return XAIConfig(api_key="test-key-xai-12345")


@pytest.fixture
def provider(config: XAIConfig) -> XAIGrok2Provider:
    return XAIGrok2Provider(config)


def _make_completion_response(
    content: str = "Hello!",
    model: str = "grok-2-latest",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> dict:
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _make_mock_httpx_response(status_code: int = 200, json_body: dict | None = None, text: str = ""):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = text
    mock_resp.json.return_value = json_body or {}
    mock_resp.headers = {}
    return mock_resp


# ---------------------------------------------------------------------------
# Helper / utility tests
# ---------------------------------------------------------------------------

class TestMessageBuilders:
    def test_build_text_message(self):
        msg = build_text_message("user", "Hello!")
        assert msg == {"role": "user", "content": "Hello!"}

    def test_build_vision_message_text_only(self):
        msg = build_vision_message("user", "Describe this")
        assert msg["role"] == "user"
        assert msg["content"] == [{"type": "text", "text": "Describe this"}]

    def test_build_vision_message_with_url(self):
        msg = build_vision_message("user", "What is this?", images=["https://example.com/img.jpg"])
        content = msg["content"]
        assert len(content) == 2
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "https://example.com/img.jpg"

    def test_build_vision_message_with_data_uri(self):
        data_uri = "data:image/png;base64,abc123"
        msg = build_vision_message("user", "Describe", images=[data_uri])
        assert msg["content"][1]["image_url"]["url"] == data_uri

    def test_encode_image_to_data_uri(self):
        data_uri = encode_image_to_data_uri(b"\x00\x01\x02", mime_type="image/png")
        assert data_uri.startswith("data:image/png;base64,")
        import base64
        decoded = base64.b64decode(data_uri.split(",", 1)[1])
        assert decoded == b"\x00\x01\x02"


# ---------------------------------------------------------------------------
# XAIConfig tests
# ---------------------------------------------------------------------------

class TestXAIConfig:
    def test_defaults(self, config):
        assert config.model == "grok-2-latest"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.max_retries == 3

    def test_custom_model(self):
        cfg = XAIConfig(api_key="k", model=XAIModel.GROK_2_VISION)
        assert cfg.model == "grok-2-vision-latest"


# ---------------------------------------------------------------------------
# Completion tests
# ---------------------------------------------------------------------------

class TestXAIGrok2ProviderComplete:
    @pytest.mark.asyncio
    async def test_complete_success(self, provider):
        raw = _make_completion_response(content="Hi there!", prompt_tokens=8, completion_tokens=3)
        mock_resp = _make_mock_httpx_response(200, raw)

        with patch.object(provider._get_client(), "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            provider._client = mock_post.__self__

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
                # Re-instantiate to get a fresh client
                p = XAIGrok2Provider(provider.config)
                # Patch the internal client post method
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_resp)
                p._client = mock_client

                result = await p.complete([{"role": "user", "content": "Hello"}])

        assert isinstance(result, XAIResponse)
        assert result.content == "Hi there!"
        assert result.usage.prompt_tokens == 8
        assert result.usage.completion_tokens == 3
        assert result.usage.total_tokens == 11
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_complete_with_system_prompt(self, provider):
        raw = _make_completion_response(content="Sure!")
        mock_resp = _make_mock_httpx_response(200, raw)

        p = XAIGrok2Provider(provider.config)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        await p.complete(
            [{"role": "user", "content": "Help me"}],
            system_prompt="You are a helpful assistant.",
        )
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_complete_custom_model_and_temperature(self, provider):
        raw = _make_completion_response(model="grok-2-mini-latest")
        mock_resp = _make_mock_httpx_response(200, raw)

        p = XAIGrok2Provider(provider.config)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        result = await p.complete(
            [{"role": "user", "content": "Hi"}],
            model=XAIModel.GROK_2_MINI,
            temperature=0.1,
        )
        call_payload = mock_client.post.call_args[1]["json"]
        assert call_payload["model"] == "grok-2-mini-latest"
        assert call_payload["temperature"] == 0.1


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------

class TestXAIGrok2ProviderErrors:
    @pytest.mark.asyncio
    async def test_auth_error_on_401(self, provider):
        mock_resp = _make_mock_httpx_response(
            401, {"error": {"message": "Invalid API key"}}
        )
        p = XAIGrok2Provider(provider.config)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client
        p.config.max_retries = 1  # Speed up the test

        with pytest.raises(XAIAuthError) as exc_info:
            await p.complete([{"role": "user", "content": "Hi"}])
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rate_limit_error_on_429(self, provider):
        mock_resp = _make_mock_httpx_response(
            429, {"error": {"message": "Rate limit exceeded"}}
        )
        mock_resp.headers = {"retry-after": "0.01"}  # Very short for test speed
        p = XAIGrok2Provider(provider.config)
        p.config.max_retries = 1
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        with pytest.raises(XAIRateLimitError):
            await p.complete([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_context_length_error_on_400(self, provider):
        mock_resp = _make_mock_httpx_response(
            400, {"error": {"message": "context window exceeded"}}
        )
        p = XAIGrok2Provider(provider.config)
        p.config.max_retries = 1
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        with pytest.raises(XAIContextLengthError):
            await p.complete([{"role": "user", "content": "Very long prompt..."}])

    @pytest.mark.asyncio
    async def test_service_error_on_503_retries(self, provider):
        mock_resp = _make_mock_httpx_response(
            503, {"error": {"message": "Service unavailable"}}
        )
        p = XAIGrok2Provider(provider.config)
        p.config.max_retries = 2
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        with pytest.raises(XAIServiceError):
            await p.complete([{"role": "user", "content": "Hi"}])
        assert mock_client.post.call_count == 2


# ---------------------------------------------------------------------------
# Health-check test
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        raw = _make_completion_response(content="p", completion_tokens=1)
        mock_resp = _make_mock_httpx_response(200, raw)
        p = XAIGrok2Provider(provider.config)
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        ok = await p.health_check()
        assert ok is True

    @pytest.mark.asyncio
    async def test_health_check_auth_failure(self, provider):
        mock_resp = _make_mock_httpx_response(401, {"error": {"message": "Unauthorized"}})
        p = XAIGrok2Provider(provider.config)
        p.config.max_retries = 1
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        p._client = mock_client

        ok = await p.health_check()
        assert ok is False


# ---------------------------------------------------------------------------
# Context-manager test
# ---------------------------------------------------------------------------

class TestContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager_closes_client(self, config):
        async with XAIGrok2Provider(config) as p:
            assert isinstance(p, XAIGrok2Provider)
        # After exit, _client should be None (closed)
        assert p._client is None
