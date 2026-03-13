"""
Tests for src/model/providers_together.py

All external HTTP calls are mocked with pytest-mock / unittest.mock so no real
API key or network access is needed.
"""

from __future__ import annotations

import json
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.model.providers import Message
from src.model.providers_together import (
    TOGETHER_MODELS,
    DEFAULT_MODEL,
    TogetherAIProvider,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_KEY = "together-test-key-abc123"


def _make_chat_response(
    content: str = "Hello from Together!",
    model: str = DEFAULT_MODEL,
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> dict:
    return {
        "id": "chatcmpl-xyz",
        "model": model,
        "choices": [
            {
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


def _sse_lines(*chunks: str, done: bool = True) -> list[str]:
    """Build a list of raw SSE text lines for mocking aiter_lines."""
    lines: list[str] = []
    for chunk in chunks:
        payload = {
            "choices": [{"delta": {"content": chunk}, "finish_reason": None}]
        }
        lines.append(f"data: {json.dumps(payload)}")
    if done:
        lines.append("data: [DONE]")
    return lines


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider() -> TogetherAIProvider:
    return TogetherAIProvider(api_key=FAKE_KEY, model_name=DEFAULT_MODEL)


@pytest.fixture
def messages() -> list[Message]:
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Say hi!"),
    ]


# ---------------------------------------------------------------------------
# generate() — success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_returns_model_response(provider, messages):
    raw = _make_chat_response(content="Hi there!")
    mock_response = MagicMock()
    mock_response.json.return_value = raw
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        result = await provider.generate(messages)

    assert result.content == "Hi there!"
    assert result.model == DEFAULT_MODEL
    assert result.finish_reason == "stop"
    assert result.usage["total_tokens"] == 15


@pytest.mark.asyncio
async def test_generate_passes_temperature_and_max_tokens(provider, messages):
    raw = _make_chat_response()
    mock_response = MagicMock()
    mock_response.json.return_value = raw
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        await provider.generate(messages, temperature=0.2, max_tokens=512)

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 512
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_generate_includes_stop_sequences(provider, messages):
    raw = _make_chat_response()
    mock_response = MagicMock()
    mock_response.json.return_value = raw
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        await provider.generate(messages, stop=["\n", "END"])

    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["stop"] == ["\n", "END"]


# ---------------------------------------------------------------------------
# generate() — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_raises_value_error_on_401(provider, messages):
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="authentication failed"):
            await provider.generate(messages)


@pytest.mark.asyncio
async def test_generate_raises_runtime_error_on_429(provider, messages):
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Too Many Requests"
    http_error = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_response)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=http_error)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="rate limit"):
            await provider.generate(messages)


@pytest.mark.asyncio
async def test_generate_raises_runtime_error_on_connect_error(provider, messages):
    import httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Could not connect"):
            await provider.generate(messages)


@pytest.mark.asyncio
async def test_generate_raises_when_no_api_key(messages):
    provider_no_key = TogetherAIProvider(api_key=None, model_name=DEFAULT_MODEL)
    # Ensure env-var is not accidentally set
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("TOGETHER_API_KEY", None)
        with pytest.raises(ValueError, match="API key"):
            await provider_no_key.generate(messages)


# ---------------------------------------------------------------------------
# stream_generate() — success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_generate_yields_chunks(provider, messages):
    sse_lines = _sse_lines("Hello ", "world", "!")

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_stream_response = AsyncMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.aiter_lines = mock_aiter_lines
    mock_stream_response.__aenter__ = AsyncMock(return_value=mock_stream_response)
    mock_stream_response.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_stream_response)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        chunks = []
        async for chunk in provider.stream_generate(messages):
            chunks.append(chunk)

    assert chunks == ["Hello ", "world", "!"]


@pytest.mark.asyncio
async def test_stream_generate_stops_at_done_sentinel(provider, messages):
    sse_lines = ["data: [DONE]", "data: {\"choices\":[{\"delta\":{\"content\":\"AFTER\"}}]}"]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_stream_response = AsyncMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.aiter_lines = mock_aiter_lines
    mock_stream_response.__aenter__ = AsyncMock(return_value=mock_stream_response)
    mock_stream_response.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_stream_response)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        chunks = []
        async for chunk in provider.stream_generate(messages):
            chunks.append(chunk)

    # "AFTER" should NOT be yielded because [DONE] breaks the loop
    assert "AFTER" not in chunks
    assert chunks == []


@pytest.mark.asyncio
async def test_stream_generate_skips_malformed_json_lines(provider, messages):
    sse_lines = [
        "data: NOT_VALID_JSON",
        "data: {\"choices\":[{\"delta\":{\"content\":\"ok\"}}]}",
        "data: [DONE]",
    ]

    async def mock_aiter_lines():
        for line in sse_lines:
            yield line

    mock_stream_response = AsyncMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.aiter_lines = mock_aiter_lines
    mock_stream_response.__aenter__ = AsyncMock(return_value=mock_stream_response)
    mock_stream_response.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_stream_response)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        chunks = []
        async for chunk in provider.stream_generate(messages):
            chunks.append(chunk)

    assert chunks == ["ok"]


# ---------------------------------------------------------------------------
# stream_generate() — error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_generate_raises_value_error_on_401(provider, messages):
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(side_effect=http_error)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_stream)

    with patch("src.model.providers_together.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="authentication failed"):
            async for _ in provider.stream_generate(messages):
                pass


# ---------------------------------------------------------------------------
# Class-level helpers
# ---------------------------------------------------------------------------


def test_list_models_returns_all_catalogue_entries():
    models = TogetherAIProvider.list_models()
    assert len(models) == len(TOGETHER_MODELS)
    ids = [m["id"] for m in models]
    assert DEFAULT_MODEL in ids


def test_get_model_info_known_model():
    info = TogetherAIProvider.get_model_info(DEFAULT_MODEL)
    assert info is not None
    assert info["id"] == DEFAULT_MODEL
    assert "context_length" in info
    assert "capabilities" in info


def test_get_model_info_unknown_model():
    info = TogetherAIProvider.get_model_info("unknown/model-xyz")
    assert info is None


def test_supports_capability_known_model(provider):
    assert provider.supports_capability("chat") is True


def test_supports_capability_unknown_capability(provider):
    assert provider.supports_capability("image_generation") is False


def test_supports_capability_unknown_model():
    p = TogetherAIProvider(api_key=FAKE_KEY, model_name="unknown/model")
    # Unknown models fall back to assuming 'chat' support
    assert p.supports_capability("chat") is True
    assert p.supports_capability("code") is False


# ---------------------------------------------------------------------------
# health_check()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_healthy(provider):
    from src.model.providers import ModelResponse

    with patch.object(
        provider,
        "generate",
        new_callable=AsyncMock,
        return_value=ModelResponse(
            content="p",
            model=DEFAULT_MODEL,
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            finish_reason="stop",
        ),
    ):
        result = await provider.health_check()

    assert result["status"] == "healthy"
    assert result["provider"] == "together_ai"
    assert result["model"] == DEFAULT_MODEL


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_exception(provider):
    with patch.object(
        provider,
        "generate",
        new_callable=AsyncMock,
        side_effect=RuntimeError("API down"),
    ):
        result = await provider.health_check()

    assert result["status"] == "unhealthy"
    assert "error" in result
    assert "API down" in result["error"]
