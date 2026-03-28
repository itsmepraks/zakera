"""
Comprehensive tests for src/model/providers_llama3.py.

Follows the same pattern as test_providers_groq.py and
test_deepseek_provider.py so reviewers can navigate the suite
conventionally.

All network I/O is mocked; no real Groq API key is needed.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.model.providers_llama3 import (
    DEFAULT_MODEL,
    LLAMA3_MODELS,
    LlamaProvider,
    LlamaResponse,
    create_llama_provider,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def provider() -> LlamaProvider:
    """Return a LlamaProvider instance with a fake API key."""
    return LlamaProvider(api_key="gsk_test_fake_key_1234", max_retries=3)


def _make_completion_payload(
    content: str = "Hello from Llama!",
    model: str = DEFAULT_MODEL,
    prompt_tokens: int = 20,
    completion_tokens: int = 10,
    finish_reason: str = "stop",
    tool_calls: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Build a minimal Groq chat-completion response payload."""
    message: Dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _make_mock_response(
    payload: Dict[str, Any],
    status_code: int = 200,
) -> MagicMock:
    """Return a mock httpx.Response-like object."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = payload
    if status_code >= 400:
        mock.raise_for_status.side_effect = Exception(
            f"HTTP {status_code} error"
        )
    else:
        mock.raise_for_status.return_value = None
    return mock


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


class TestLlamaProviderInit:
    def test_valid_init(self) -> None:
        p = LlamaProvider(api_key="gsk_valid")
        assert p.default_model == DEFAULT_MODEL
        assert p.max_retries == 3  # default

    def test_custom_model(self) -> None:
        p = LlamaProvider(
            api_key="gsk_valid", default_model="llama3-8b-8192"
        )
        assert p.default_model == "llama3-8b-8192"

    def test_empty_api_key_raises(self) -> None:
        with pytest.raises(ValueError, match="API key"):
            LlamaProvider(api_key="")

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown Llama model"):
            LlamaProvider(api_key="gsk_valid", default_model="gpt-4")

    def test_create_factory_function(self) -> None:
        p = create_llama_provider(api_key="gsk_valid", model="llama3-8b-8192")
        assert isinstance(p, LlamaProvider)
        assert p.default_model == "llama3-8b-8192"


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestModelCatalogue:
    def test_list_models_returns_all(self, provider: LlamaProvider) -> None:
        models = provider.list_models()
        assert len(models) == len(LLAMA3_MODELS)
        ids = {m["id"] for m in models}
        assert "llama3-8b-8192" in ids
        assert "llama3-70b-8192" in ids
        assert "llama-3.1-405b-reasoning" in ids

    def test_list_models_has_required_fields(self, provider: LlamaProvider) -> None:
        for m in provider.list_models():
            assert "context_window" in m
            assert "supports_streaming" in m
            assert "supports_function_calling" in m
            assert m["context_window"] > 0

    def test_get_model_info_valid(self, provider: LlamaProvider) -> None:
        info = provider.get_model_info("llama3-70b-8192")
        assert info["id"] == "llama3-70b-8192"
        assert info["context_window"] == 8192

    def test_get_model_info_invalid(self, provider: LlamaProvider) -> None:
        with pytest.raises(ValueError, match="Unknown model"):
            provider.get_model_info("claude-3")

    def test_405b_has_large_context(self, provider: LlamaProvider) -> None:
        info = provider.get_model_info("llama-3.1-405b-reasoning")
        assert info["context_window"] >= 131072


# ---------------------------------------------------------------------------
# Successful chat completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestChatCompletion:
    async def test_basic_chat_returns_response(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload(content="Hi there!")
        mock_resp = _make_mock_response(payload)

        with patch.object(
            provider, "_post_with_retry", new=AsyncMock(return_value=payload)
        ):
            response = await provider.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )

        assert isinstance(response, LlamaResponse)
        assert response.content == "Hi there!"
        assert response.finish_reason == "stop"

    async def test_uses_specified_model(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload(model="llama3-8b-8192")
        captured: Dict[str, Any] = {}

        async def fake_post(p: Dict[str, Any]) -> Dict[str, Any]:
            captured.update(p)
            return payload

        with patch.object(provider, "_post_with_retry", new=fake_post):
            await provider.chat(
                messages=[{"role": "user", "content": "Hey"}],
                model="llama3-8b-8192",
            )

        assert captured["model"] == "llama3-8b-8192"

    async def test_temperature_forwarded(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload()
        captured: Dict[str, Any] = {}

        async def fake_post(p: Dict[str, Any]) -> Dict[str, Any]:
            captured.update(p)
            return payload

        with patch.object(provider, "_post_with_retry", new=fake_post):
            await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.2,
            )

        assert captured["temperature"] == pytest.approx(0.2)

    async def test_max_tokens_forwarded(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload()
        captured: Dict[str, Any] = {}

        async def fake_post(p: Dict[str, Any]) -> Dict[str, Any]:
            captured.update(p)
            return payload

        with patch.object(provider, "_post_with_retry", new=fake_post):
            await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=512,
            )

        assert captured["max_tokens"] == 512

    async def test_system_prompt_prepended(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload()
        captured: Dict[str, Any] = {}

        async def fake_post(p: Dict[str, Any]) -> Dict[str, Any]:
            captured.update(p)
            return payload

        with patch.object(provider, "_post_with_retry", new=fake_post):
            await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                system_prompt="You are a helpful assistant.",
            )

        msgs = captured["messages"]
        assert msgs[0]["role"] == "system"
        assert "helpful assistant" in msgs[0]["content"]

    async def test_stop_sequences_forwarded(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload()
        captured: Dict[str, Any] = {}

        async def fake_post(p: Dict[str, Any]) -> Dict[str, Any]:
            captured.update(p)
            return payload

        with patch.object(provider, "_post_with_retry", new=fake_post):
            await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                stop_sequences=["\n\n", "END"],
            )

        assert captured["stop"] == ["\n\n", "END"]

    async def test_unknown_model_in_chat_raises(self, provider: LlamaProvider) -> None:
        with pytest.raises(ValueError, match="Unsupported Llama model"):
            await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                model="nonexistent-model",
            )


# ---------------------------------------------------------------------------
# Token usage & cost estimation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTokenUsageAndCost:
    async def test_token_usage_extracted(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload(
            prompt_tokens=100, completion_tokens=50
        )
        with patch.object(
            provider, "_post_with_retry", new=AsyncMock(return_value=payload)
        ):
            resp = await provider.chat(
                messages=[{"role": "user", "content": "Hi"}]
            )

        assert resp.prompt_tokens == 100
        assert resp.completion_tokens == 50
        assert resp.total_tokens == 150
        assert resp.usage == {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

    async def test_cost_estimated_for_70b(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload(
            model="llama3-70b-8192",
            prompt_tokens=1000,
            completion_tokens=1000,
        )
        with patch.object(
            provider, "_post_with_retry", new=AsyncMock(return_value=payload)
        ):
            resp = await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                model="llama3-70b-8192",
            )

        # 1k prompt @ 0.00059 + 1k completion @ 0.00079 = 0.00138
        expected_cost = 0.00059 + 0.00079
        assert resp.cost_usd == pytest.approx(expected_cost, rel=1e-5)

    async def test_latency_ms_populated(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload()
        with patch.object(
            provider, "_post_with_retry", new=AsyncMock(return_value=payload)
        ):
            resp = await provider.chat(
                messages=[{"role": "user", "content": "Hi"}]
            )
        assert resp.latency_ms >= 0


# ---------------------------------------------------------------------------
# Tool / function call support
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFunctionCalling:
    async def test_tool_calls_parsed(self, provider: LlamaProvider) -> None:
        tool_calls = [
            {
                "id": "call_abc",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"city": "Washington DC"}',
                },
            }
        ]
        payload = _make_completion_payload(
            content="",
            finish_reason="tool_calls",
            tool_calls=tool_calls,
        )
        with patch.object(
            provider, "_post_with_retry", new=AsyncMock(return_value=payload)
        ):
            resp = await provider.chat(
                messages=[{"role": "user", "content": "Weather?"}],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "parameters": {"type": "object"},
                        },
                    }
                ],
            )

        assert resp.finish_reason == "tool_calls"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["function"]["name"] == "get_weather"

    async def test_tools_payload_sent(self, provider: LlamaProvider) -> None:
        payload = _make_completion_payload()
        captured: Dict[str, Any] = {}

        async def fake_post(p: Dict[str, Any]) -> Dict[str, Any]:
            captured.update(p)
            return payload

        tools = [{"type": "function", "function": {"name": "fn"}}]
        with patch.object(provider, "_post_with_retry", new=fake_post):
            await provider.chat(
                messages=[{"role": "user", "content": "Hi"}],
                tools=tools,
            )

        assert captured.get("tools") == tools
        assert captured.get("tool_choice") == "auto"


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStreaming:
    async def test_stream_yields_deltas(self, provider: LlamaProvider) -> None:
        """Verify that stream() correctly yields each SSE content delta."""
        chunks = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            "data: [DONE]",
        ]

        async def fake_aiter_lines():
            for line in chunks:
                yield line

        mock_response = AsyncMock()
        mock_response.aiter_lines = fake_aiter_lines
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = ""
            async for delta in provider.stream(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                result += delta

        assert result == "Hello world"

    async def test_stream_stops_at_done(self, provider: LlamaProvider) -> None:
        chunks = [
            'data: {"choices": [{"delta": {"content": "A"}}]}',
            "data: [DONE]",
            'data: {"choices": [{"delta": {"content": "B"}}]}',  # after DONE
        ]

        async def fake_aiter_lines():
            for line in chunks:
                yield line

        mock_response = AsyncMock()
        mock_response.aiter_lines = fake_aiter_lines
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response

        collected: List[str] = []
        with patch.object(
            provider, "_get_client", new=AsyncMock(return_value=mock_client)
        ):
            async for delta in provider.stream(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                collected.append(delta)

        assert collected == ["A"]  # B must not appear

    async def test_stream_skips_malformed_chunks(self, provider: LlamaProvider) -> None:
        chunks = [
            "data: NOT_JSON",
            'data: {"choices": [{"delta": {"content": "ok"}}]}',
            "data: [DONE]",
        ]

        async def fake_aiter_lines():
            for line in chunks:
                yield line

        mock_response = AsyncMock()
        mock_response.aiter_lines = fake_aiter_lines
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response

        collected: List[str] = []
        with patch.object(
            provider, "_get_client", new=AsyncMock(return_value=mock_client)
        ):
            async for delta in provider.stream(
                messages=[{"role": "user", "content": "Hi"}]
            ):
                collected.append(delta)

        assert collected == ["ok"]


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryLogic:
    async def test_retries_on_429_then_succeeds(
        self, provider: LlamaProvider
    ) -> None:
        """Provider should retry after a 429 and eventually return a response."""
        import httpx

        payload = _make_completion_payload()
        call_count = 0

        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.raise_for_status.side_effect = None

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.raise_for_status.return_value = None
        mock_200.json.return_value = payload

        responses = [mock_429, mock_429, mock_200]

        async def fake_post(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            r = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return r

        mock_client = AsyncMock()
        mock_client.post = fake_post

        with patch.object(
            provider, "_get_client", new=AsyncMock(return_value=mock_client)
        ), patch("asyncio.sleep", new=AsyncMock()):
            result = await provider._post_with_retry({"model": DEFAULT_MODEL})

        assert result == payload
        assert call_count == 3

    async def test_raises_after_max_retries(
        self, provider: LlamaProvider
    ) -> None:
        """Provider should raise RuntimeError when all retries are exhausted."""
        provider.max_retries = 2

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.raise_for_status.return_value = None

        async def always_429(url: str, **kwargs: Any) -> MagicMock:
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = always_429

        with patch.object(
            provider, "_get_client", new=AsyncMock(return_value=mock_client)
        ), patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError, match="retry attempts failed"):
                await provider._post_with_retry({"model": DEFAULT_MODEL})

    async def test_raises_immediately_on_4xx_client_error(
        self, provider: LlamaProvider
    ) -> None:
        """4xx errors (except 429) must not be retried."""
        import httpx

        http_exc = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=MagicMock(status_code=401),
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = http_exc

        async def fake_post(url: str, **kwargs: Any) -> MagicMock:
            return mock_resp

        mock_client = AsyncMock()
        mock_client.post = fake_post

        call_count = 0
        original_post = mock_client.post

        async def counting_post(url: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            return await original_post(url, **kwargs)

        mock_client.post = counting_post

        with patch.object(
            provider, "_get_client", new=AsyncMock(return_value=mock_client)
        ), patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(httpx.HTTPStatusError):
                await provider._post_with_retry({"model": DEFAULT_MODEL})

        assert call_count == 1  # no retries for 401


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLifecycle:
    async def test_close_cleans_up_client(self, provider: LlamaProvider) -> None:
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client  # type: ignore[attr-defined]

        await provider.close()

        mock_client.aclose.assert_awaited_once()

    async def test_close_no_op_when_no_client(self, provider: LlamaProvider) -> None:
        provider._client = None  # type: ignore[attr-defined]
        # Should not raise
        await provider.close()
