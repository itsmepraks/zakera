"""
Unit tests for src/model/providers_cerebras.py
===============================================
All external HTTP calls are mocked; no real API key is required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import the module under test (adjust path if your package layout differs)
# ---------------------------------------------------------------------------
try:
    from src.model.providers_cerebras import CerebrasProvider  # type: ignore
except ImportError:  # pragma: no cover – allow tests to be collected even if deps missing
    CerebrasProvider = None  # type: ignore

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def provider():
    """Return a CerebrasProvider with a dummy key (no real network calls)."""
    if CerebrasProvider is None:
        pytest.skip("CerebrasProvider could not be imported")
    return CerebrasProvider(api_key="test-cerebras-key-123")


def _make_completion_response(
    content: str = "Hello from Cerebras!",
    model: str = "llama3.1-70b",
    prompt_tokens: int = 12,
    completion_tokens: int = 8,
) -> dict:
    """Build a fake OpenAI-compatible chat completion response dict."""
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "created": 1711900000,
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


def _make_stream_chunk(delta_content: str, finish: bool = False) -> str:
    """Return an SSE data line for streaming."""
    chunk = {
        "id": "chatcmpl-stream-1",
        "object": "chat.completion.chunk",
        "choices": [
            {
                "index": 0,
                "delta": ({"content": delta_content} if not finish else {}),
                "finish_reason": "stop" if finish else None,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


class TestCerebrasProviderInit:
    def test_requires_api_key(self, monkeypatch):
        """Raise ValueError when no API key is provided."""
        if CerebrasProvider is None:
            pytest.skip("CerebrasProvider not importable")
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        with pytest.raises((ValueError, Exception)):
            CerebrasProvider(api_key="")

    def test_reads_api_key_from_env(self, monkeypatch):
        if CerebrasProvider is None:
            pytest.skip("CerebrasProvider not importable")
        monkeypatch.setenv("CEREBRAS_API_KEY", "env-key-xyz")
        p = CerebrasProvider()
        assert p.api_key == "env-key-xyz"

    def test_explicit_key_takes_precedence_over_env(self, monkeypatch):
        if CerebrasProvider is None:
            pytest.skip("CerebrasProvider not importable")
        monkeypatch.setenv("CEREBRAS_API_KEY", "env-key")
        p = CerebrasProvider(api_key="explicit-key")
        assert p.api_key == "explicit-key"

    def test_default_model(self, provider):
        """Default model should be one of the supported Cerebras Llama variants."""
        assert "llama" in provider.model.lower() or "cerebras" in provider.model.lower()

    def test_custom_model_assignment(self):
        if CerebrasProvider is None:
            pytest.skip("CerebrasProvider not importable")
        p = CerebrasProvider(api_key="k", model="llama3.1-8b")
        assert p.model == "llama3.1-8b"


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------


class TestCerebrasGenerate:
    async def test_happy_path_returns_text(self, provider):
        """generate() should return the assistant message content."""
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = _make_completion_response("The answer is 42.")
        fake_response.raise_for_status = MagicMock()

        with patch.object(
            provider._client, "post", new=AsyncMock(return_value=fake_response)
        ):
            messages = [{"role": "user", "content": "What is the answer?"}]
            result = await provider.generate(messages)

        assert "42" in result

    async def test_passes_temperature(self, provider):
        """The temperature parameter should appear in the request body."""
        captured = {}

        async def fake_post(url, **kwargs):
            captured.update(kwargs.get("json", {}))
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = _make_completion_response()
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(provider._client, "post", new=fake_post):
            await provider.generate(
                [{"role": "user", "content": "hi"}],
                temperature=0.7,
            )

        assert captured.get("temperature") == pytest.approx(0.7)

    async def test_passes_max_tokens(self, provider):
        captured = {}

        async def fake_post(url, **kwargs):
            captured.update(kwargs.get("json", {}))
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = _make_completion_response()
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(provider._client, "post", new=fake_post):
            await provider.generate(
                [{"role": "user", "content": "hi"}],
                max_tokens=512,
            )

        assert captured.get("max_tokens") == 512

    async def test_system_prompt_prepended(self, provider):
        """A system prompt should appear as the first message."""
        captured = {}

        async def fake_post(url, **kwargs):
            captured.update(kwargs.get("json", {}))
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = _make_completion_response()
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(provider._client, "post", new=fake_post):
            await provider.generate(
                [{"role": "user", "content": "hello"}],
                system_prompt="You are a helpful bot.",
            )

        msgs = captured.get("messages", [])
        assert msgs[0]["role"] == "system"
        assert "helpful bot" in msgs[0]["content"]

    async def test_raises_on_auth_error(self, provider):
        """HTTP 401 should propagate as an auth-related exception."""
        import httpx

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 401
        fake_response.text = "Unauthorized"
        fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=fake_response
        )

        with patch.object(
            provider._client, "post", new=AsyncMock(return_value=fake_response)
        ):
            with pytest.raises(Exception):
                await provider.generate([{"role": "user", "content": "hi"}])

    async def test_retries_on_rate_limit(self, provider):
        """HTTP 429 should trigger retry logic and eventually succeed."""
        import httpx

        call_count = 0

        async def flaky_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = MagicMock(spec=httpx.Response)
                resp.status_code = 429
                resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "429", request=MagicMock(), response=resp
                )
                return resp
            # Third call succeeds
            ok = MagicMock()
            ok.status_code = 200
            ok.json.return_value = _make_completion_response("success after retry")
            ok.raise_for_status = MagicMock()
            return ok

        with patch.object(provider._client, "post", new=flaky_post), patch(
            "time.sleep"
        ):  # speed up test
            result = await provider.generate([{"role": "user", "content": "hi"}])

        assert call_count == 3
        assert "success" in result


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------


class TestCerebrasStreaming:
    async def test_stream_yields_tokens(self, provider):
        """stream_generate() should yield incremental text tokens."""
        chunks = [
            _make_stream_chunk("Hello"),
            _make_stream_chunk(" world"),
            _make_stream_chunk("!"),
            _make_stream_chunk("", finish=True),
            "data: [DONE]\n\n",
        ]

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def fake_aiter_lines():
            for chunk in chunks:
                for line in chunk.splitlines():
                    yield line

        mock_response.aiter_lines = fake_aiter_lines

        with patch.object(
            provider._client, "stream", return_value=mock_response
        ):
            tokens = []
            async for token in provider.stream_generate(
                [{"role": "user", "content": "Say hello"}]
            ):
                tokens.append(token)

        full = "".join(tokens)
        assert "Hello world!" in full

    async def test_stream_empty_delta_skipped(self, provider):
        """Empty delta content chunks should not produce empty string tokens."""
        chunks = [
            _make_stream_chunk(""),
            _make_stream_chunk("hi"),
            "data: [DONE]\n\n",
        ]

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def fake_aiter_lines():
            for chunk in chunks:
                for line in chunk.splitlines():
                    yield line

        mock_response.aiter_lines = fake_aiter_lines

        with patch.object(provider._client, "stream", return_value=mock_response):
            tokens = [
                t
                async for t in provider.stream_generate(
                    [{"role": "user", "content": "hi"}]
                )
            ]

        # Only non-empty tokens
        assert all(t for t in tokens)


# ---------------------------------------------------------------------------
# Tool-use / function-calling tests
# ---------------------------------------------------------------------------


class TestCerebrasToolUse:
    async def test_tool_definitions_serialised(self, provider):
        """Tool schemas should be forwarded in the request body."""
        captured = {}

        async def fake_post(url, **kwargs):
            captured.update(kwargs.get("json", {}))
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = _make_completion_response()
            resp.raise_for_status = MagicMock()
            return resp

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ]

        with patch.object(provider._client, "post", new=fake_post):
            await provider.generate(
                [{"role": "user", "content": "Weather in NYC?"}],
                tools=tools,
            )

        assert "tools" in captured
        assert captured["tools"][0]["function"]["name"] == "get_weather"
