"""
Comprehensive unit tests for src/model/providers_openai.py.

All HTTP calls are mocked — no real OpenAI API key is required to run these tests.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from src.model.providers_openai import (
    FunctionDefinition,
    ImageContent,
    OpenAIConfig,
    OpenAIModel,
    OpenAIProvider,
    TokenUsage,
    build_text_message,
    build_vision_message,
    create_openai_provider,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_API_KEY = "sk-test-xxxxxxxxxxxxxxxxxxxxxxxx"


@pytest.fixture
def basic_config() -> OpenAIConfig:
    return OpenAIConfig(api_key=VALID_API_KEY, model=OpenAIModel.GPT_4O)


@pytest.fixture
def provider(basic_config: OpenAIConfig) -> OpenAIProvider:
    return OpenAIProvider(basic_config)


def _make_chat_response(
    content: str = "Hello!",
    model: str = "gpt-4o",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    finish_reason: str = "stop",
    request_id: str = "req-abc123",
    tool_calls: Any = None,
) -> httpx.Response:
    """Build a fake OpenAI chat completion response."""
    body: Dict[str, Any] = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return httpx.Response(
        status_code=200,
        json=body,
        headers={"x-request-id": request_id},
    )


def _make_sse_bytes(chunks: List[str], usage: Dict[str, int] | None = None) -> bytes:
    """Encode a list of text chunks as SSE data lines plus a [DONE] sentinel."""
    lines: List[str] = []
    for i, chunk in enumerate(chunks):
        event: Dict[str, Any] = {
            "id": f"chunk-{i}",
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": chunk}, "index": 0, "finish_reason": None}],
        }
        lines.append(f"data: {json.dumps(event)}\n\n")

    if usage:
        usage_event: Dict[str, Any] = {
            "id": "chunk-usage",
            "object": "chat.completion.chunk",
            "choices": [],
            "usage": usage,
        }
        lines.append(f"data: {json.dumps(usage_event)}\n\n")

    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


# ---------------------------------------------------------------------------
# OpenAIConfig
# ---------------------------------------------------------------------------


class TestOpenAIConfig:
    def test_valid_config(self):
        cfg = OpenAIConfig(api_key=VALID_API_KEY, model=OpenAIModel.GPT_4O_MINI)
        assert cfg.model == OpenAIModel.GPT_4O_MINI
        assert cfg.max_tokens == 4096

    def test_default_model_is_gpt4o(self):
        cfg = OpenAIConfig(api_key=VALID_API_KEY)
        assert cfg.model == OpenAIModel.GPT_4O

    def test_raises_on_empty_api_key(self):
        with pytest.raises(ValueError, match="api_key"):
            OpenAIConfig(api_key="")

    def test_raises_on_unknown_model(self):
        with pytest.raises(ValueError, match="Unsupported"):
            OpenAIConfig(api_key=VALID_API_KEY, model="gpt-99-ultra")

    def test_custom_temperature(self):
        cfg = OpenAIConfig(api_key=VALID_API_KEY, temperature=0.2)
        assert cfg.temperature == 0.2

    def test_list_models(self):
        models = OpenAIModel.values()
        assert "gpt-4o" in models
        assert "gpt-3.5-turbo" in models


# ---------------------------------------------------------------------------
# TokenUsage
# ---------------------------------------------------------------------------


class TestTokenUsage:
    def test_from_response_standard(self):
        data = {
            "usage": {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50},
        }
        usage = TokenUsage.from_response(data, model="gpt-4o", request_id="rid-1")
        assert usage.prompt_tokens == 20
        assert usage.completion_tokens == 30
        assert usage.total_tokens == 50
        assert usage.model == "gpt-4o"
        assert usage.request_id == "rid-1"

    def test_from_response_missing_usage_key(self):
        usage = TokenUsage.from_response({}, model="gpt-4o")
        assert usage.total_tokens == 0

    def test_from_response_partial_usage(self):
        data = {"usage": {"prompt_tokens": 5}}
        usage = TokenUsage.from_response(data, model="gpt-4o")
        assert usage.prompt_tokens == 5
        assert usage.completion_tokens == 0


# ---------------------------------------------------------------------------
# FunctionDefinition
# ---------------------------------------------------------------------------


class TestFunctionDefinition:
    def test_to_dict_basic(self):
        fn = FunctionDefinition(
            name="get_weather",
            description="Get current weather.",
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        )
        result = fn.to_dict()
        assert result["type"] == "function"
        assert result["function"]["name"] == "get_weather"
        assert "strict" not in result["function"]

    def test_to_dict_strict_mode(self):
        fn = FunctionDefinition(
            name="strict_fn",
            description="A strict function.",
            parameters={"type": "object", "properties": {}},
            strict=True,
        )
        result = fn.to_dict()
        assert result["function"]["strict"] is True


# ---------------------------------------------------------------------------
# ImageContent
# ---------------------------------------------------------------------------


class TestImageContent:
    def test_url_content_part(self):
        img = ImageContent(url="https://example.com/photo.jpg", detail="high")
        part = img.to_content_part()
        assert part["type"] == "image_url"
        assert part["image_url"]["url"] == "https://example.com/photo.jpg"
        assert part["image_url"]["detail"] == "high"

    def test_base64_content_part(self):
        b64 = "aGVsbG8="  # base64 of 'hello'
        img = ImageContent(base64_data=b64, media_type="image/png")
        part = img.to_content_part()
        assert part["image_url"]["url"].startswith("data:image/png;base64,")
        assert b64 in part["image_url"]["url"]

    def test_raises_when_no_source(self):
        img = ImageContent()
        with pytest.raises(ValueError, match="url"):
            img.to_content_part()


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------


class TestMessageBuilders:
    def test_build_text_message(self):
        msg = build_text_message("user", "Hello!")
        assert msg == {"role": "user", "content": "Hello!"}

    def test_build_vision_message_single_image(self):
        img = ImageContent(url="https://example.com/img.jpg")
        msg = build_vision_message("user", "Describe this image.", [img])
        assert msg["role"] == "user"
        assert isinstance(msg["content"], list)
        assert msg["content"][0] == {"type": "text", "text": "Describe this image."}
        assert msg["content"][1]["type"] == "image_url"

    def test_build_vision_message_no_images(self):
        msg = build_vision_message("user", "Plain text.", [])
        assert len(msg["content"]) == 1  # only the text part


# ---------------------------------------------------------------------------
# OpenAIProvider — chat (non-streaming)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpenAIProviderChat:
    async def test_chat_returns_content(self, provider: OpenAIProvider):
        mock_resp = _make_chat_response(content="I am Zakera.", prompt_tokens=8, completion_tokens=4)

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await provider.chat([build_text_message("user", "Who are you?")])

        assert result["content"] == "I am Zakera."
        assert result["finish_reason"] == "stop"
        assert result["usage"].prompt_tokens == 8
        assert result["usage"].completion_tokens == 4

    async def test_chat_tracks_cumulative_usage(self, provider: OpenAIProvider):
        mock_resp = _make_chat_response(prompt_tokens=10, completion_tokens=5)

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            await provider.chat([build_text_message("user", "Hello")])
            await provider.chat([build_text_message("user", "Again")])

        total = provider.get_total_usage()
        assert total.prompt_tokens == 20
        assert total.completion_tokens == 10

    async def test_chat_reset_usage(self, provider: OpenAIProvider):
        mock_resp = _make_chat_response(prompt_tokens=10, completion_tokens=5)

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            await provider.chat([build_text_message("user", "Hello")])

        provider.reset_usage()
        assert provider.get_total_usage().total_tokens == 0

    async def test_chat_raises_on_api_error(self, provider: OpenAIProvider):
        mock_resp = httpx.Response(status_code=400, json={"error": {"message": "Bad request"}})

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(RuntimeError, match="400"):
                await provider.chat([build_text_message("user", "Bad input")])

    async def test_chat_includes_system_message(self, provider: OpenAIProvider):
        captured_payload: Dict[str, Any] = {}
        mock_resp = _make_chat_response()

        async def capture_and_return(endpoint, payload):
            captured_payload.update(payload)
            return mock_resp

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = capture_and_return
            messages = [
                build_text_message("system", "You are a helpful assistant."),
                build_text_message("user", "Hi"),
            ]
            await provider.chat(messages)

        assert captured_payload["messages"][0]["role"] == "system"
        assert captured_payload["stream"] is False


# ---------------------------------------------------------------------------
# OpenAIProvider — streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpenAIProviderStream:
    async def _collect_stream(self, provider: OpenAIProvider, messages) -> str:
        parts = []
        async for chunk in provider.stream_chat(messages):
            parts.append(chunk)
        return "".join(parts)

    async def test_stream_yields_chunks(self, provider: OpenAIProvider):
        sse_data = _make_sse_bytes(
            ["Hello", ", ", "world", "!"],
            usage={"prompt_tokens": 5, "completion_tokens": 4, "total_tokens": 9},
        )

        mock_stream_resp = MagicMock()
        mock_stream_resp.status_code = 200
        mock_stream_resp.aiter_lines = AsyncMock(return_value=iter(sse_data.decode().splitlines()))

        # Simulate async context manager
        async def fake_aiter_lines():
            for line in sse_data.decode().splitlines():
                yield line

        mock_stream_resp.aiter_lines = fake_aiter_lines

        class FakeStreamCtx:
            async def __aenter__(self):
                return mock_stream_resp

            async def __aexit__(self, *args):
                pass

        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.stream.return_value = FakeStreamCtx()
            mock_client.return_value = mock_http_client

            result = await self._collect_stream(
                provider, [build_text_message("user", "Say hello")]
            )

        assert "Hello" in result
        assert "world" in result

    async def test_stream_raises_on_error_status(self, provider: OpenAIProvider):
        mock_stream_resp = MagicMock()
        mock_stream_resp.status_code = 401
        mock_stream_resp.aread = AsyncMock(return_value=b'"Unauthorized"')

        class FakeStreamCtx:
            async def __aenter__(self):
                return mock_stream_resp

            async def __aexit__(self, *args):
                pass

        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.stream.return_value = FakeStreamCtx()
            mock_client.return_value = mock_http_client

            with pytest.raises(RuntimeError, match="401"):
                async for _ in provider.stream_chat([build_text_message("user", "Hi")]):
                    pass


# ---------------------------------------------------------------------------
# OpenAIProvider — vision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpenAIProviderVision:
    async def test_vision_chat_url(self, provider: OpenAIProvider):
        mock_resp = _make_chat_response(content="A cat sitting on a mat.")

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await provider.vision_chat(
                "Describe the image.",
                [ImageContent(url="https://example.com/cat.jpg")],
                system_prompt="You are a vision model.",
            )

        assert "cat" in result["content"].lower()

    async def test_vision_chat_base64(self, provider: OpenAIProvider):
        mock_resp = _make_chat_response(content="A pie chart.")
        b64 = "aGVsbG8="

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await provider.vision_chat(
                "What does this chart show?",
                [ImageContent(base64_data=b64, media_type="image/png")],
            )

        assert result["content"] == "A pie chart."


# ---------------------------------------------------------------------------
# OpenAIProvider — function / tool calling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpenAIProviderToolCalling:
    async def test_tool_calls_returned(self, provider: OpenAIProvider):
        fake_tool_calls = [
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"location":"DC"}'},
            }
        ]
        mock_resp = _make_chat_response(
            content="",
            tool_calls=fake_tool_calls,
            finish_reason="tool_calls",
        )

        fn = FunctionDefinition(
            name="get_weather",
            description="Get weather",
            parameters={"type": "object", "properties": {"location": {"type": "string"}}},
        )

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            result = await provider.chat_with_tools(
                [build_text_message("user", "What's the weather in DC?")],
                functions=[fn],
            )

        assert result["finish_reason"] == "tool_calls"
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"

    async def test_payload_includes_tools(self, provider: OpenAIProvider):
        captured: Dict[str, Any] = {}
        mock_resp = _make_chat_response()

        async def capture(endpoint, payload):
            captured.update(payload)
            return mock_resp

        fn = FunctionDefinition(
            name="search_web",
            description="Search the web",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        )

        with patch.object(provider, "_post_with_retry", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = capture
            await provider.chat_with_tools(
                [build_text_message("user", "Search for AI")],
                functions=[fn],
                tool_choice="auto",
            )

        assert "tools" in captured
        assert captured["tools"][0]["function"]["name"] == "search_web"


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryLogic:
    async def test_retries_on_429(self, provider: OpenAIProvider):
        success_resp = _make_chat_response(content="OK after retry")
        rate_limit_resp = httpx.Response(status_code=429, text="Rate limited")

        call_count = 0

        async def flaky_post(endpoint, json, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return rate_limit_resp
            return success_resp

        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post.side_effect = flaky_post
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                resp = await provider._post_with_retry("/chat/completions", {})

        assert resp.status_code == 200
        assert call_count == 2

    async def test_raises_after_max_retries(self, provider: OpenAIProvider):
        always_500 = httpx.Response(status_code=500, text="Server error")

        async def always_fail(endpoint, json, **kwargs):
            return always_500

        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.post.side_effect = always_fail
            mock_get_client.return_value = mock_http

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="retries"):
                    await provider._post_with_retry("/chat/completions", {})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_healthy_response(self, provider: OpenAIProvider):
        ok_resp = httpx.Response(status_code=200, json={"object": "list", "data": []})

        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get.return_value = ok_resp
            mock_get_client.return_value = mock_http
            result = await provider.health_check()

        assert result["status"] == "healthy"
        assert result["provider"] == "openai"

    async def test_unhealthy_on_exception(self, provider: OpenAIProvider):
        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_get_client.side_effect = Exception("Connection refused")
            result = await provider.health_check()

        assert result["status"] == "unhealthy"
        assert "Connection refused" in result["error"]

    async def test_degraded_on_non_200(self, provider: OpenAIProvider):
        degraded_resp = httpx.Response(status_code=503, text="Service unavailable")

        with patch.object(provider, "_get_client", new_callable=AsyncMock) as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get.return_value = degraded_resp
            mock_get_client.return_value = mock_http
            result = await provider.health_check()

        assert result["status"] == "degraded"
        assert result["http_status"] == 503


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestCreateOpenAIProvider:
    def test_creates_provider_from_settings(self):
        settings = {
            "openai_api_key": VALID_API_KEY,
            "openai_model": "gpt-4o-mini",
            "openai_max_tokens": "2048",
            "openai_temperature": "0.3",
        }
        p = create_openai_provider(settings)
        assert isinstance(p, OpenAIProvider)
        assert p.config.model == "gpt-4o-mini"
        assert p.config.max_tokens == 2048
        assert p.config.temperature == pytest.approx(0.3)

    def test_uses_defaults_when_optional_keys_missing(self):
        p = create_openai_provider({"openai_api_key": VALID_API_KEY})
        assert p.config.model == OpenAIModel.GPT_4O
        assert p.config.max_tokens == 4096

    def test_raises_on_missing_api_key(self):
        with pytest.raises(KeyError):
            create_openai_provider({})


# ---------------------------------------------------------------------------
# Provider metadata
# ---------------------------------------------------------------------------


class TestProviderMetadata:
    def test_list_models(self):
        models = OpenAIProvider.list_models()
        assert len(models) >= 4
        assert "gpt-4o" in models

    def test_repr(self, provider: OpenAIProvider):
        assert "gpt-4o" in repr(provider)
        assert "OpenAIProvider" in repr(provider)
