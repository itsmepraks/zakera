"""
Tests for MistralCodestralProvider.

All network calls are mocked via pytest-httpx / unittest.mock so that
these tests run fully offline without real API keys.
"""

from __future__ import annotations

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import AsyncIterator

from src.model.providers_mistral_codestral import (
    MistralCodestralProvider,
    CodestralConfig,
    CodestralMessage,
    FIMRequest,
    CODESTRAL_LATEST,
    CODESTRAL_2501,
    _CODESTRAL_CHAT_URL,
    _CODESTRAL_FIM_URL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def provider() -> MistralCodestralProvider:
    """A provider instance with a fake API key."""
    return MistralCodestralProvider(api_key="test-codestral-key")


@pytest.fixture
def sample_messages() -> list[CodestralMessage]:
    return [
        CodestralMessage(role="system", content="You are a helpful coding assistant."),
        CodestralMessage(role="user", content="Write a Python hello-world function."),
    ]


def _make_sse_stream(chunks: list[str]) -> list[str]:
    """Build a list of SSE lines from text chunks."""
    lines = []
    for chunk in chunks:
        payload = json.dumps({"choices": [{"delta": {"content": chunk}}]})
        lines.append(f"data: {payload}")
    lines.append("data: [DONE]")
    return lines


def _make_chat_response(content: str) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 35},
    }


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="MISTRAL_CODESTRAL_API_KEY"):
            MistralCodestralProvider(api_key="")

    def test_repr_contains_timeout(self):
        p = MistralCodestralProvider(api_key="key", timeout=30.0)
        assert "30.0" in repr(p)

    def test_default_max_retries(self):
        p = MistralCodestralProvider(api_key="key")
        assert p._max_retries == 3

    def test_custom_timeout_and_retries(self):
        p = MistralCodestralProvider(api_key="key", timeout=60.0, max_retries=5)
        assert p._timeout == 60.0
        assert p._max_retries == 5


# ---------------------------------------------------------------------------
# SSE parsing
# ---------------------------------------------------------------------------

class TestSSEParsing:
    def test_data_line_with_content(self):
        line = 'data: {"choices": [{"delta": {"content": "Hello"}}]}'
        assert MistralCodestralProvider._parse_sse_line(line) == "Hello"

    def test_done_sentinel_returns_none(self):
        assert MistralCodestralProvider._parse_sse_line("data: [DONE]") is None

    def test_non_data_line_returns_none(self):
        assert MistralCodestralProvider._parse_sse_line(": keep-alive") is None
        assert MistralCodestralProvider._parse_sse_line("") is None

    def test_malformed_json_returns_none(self):
        assert MistralCodestralProvider._parse_sse_line("data: {not valid json}") is None

    def test_role_only_delta_returns_none(self):
        """Deltas that carry only a role (no content) should return None."""
        line = 'data: {"choices": [{"delta": {"role": "assistant"}}]}'
        assert MistralCodestralProvider._parse_sse_line(line) is None


# ---------------------------------------------------------------------------
# Streaming chat
# ---------------------------------------------------------------------------

class TestStreamChat:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, provider, sample_messages):
        """stream_chat() should yield each text delta in order."""
        sse_lines = _make_sse_stream(["def ", "hello", "():\n", "    print", '("Hello!")'])

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = AsyncMock(
            return_value=aiter(sse_lines)
        )

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_context)

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=False)

        with patch("src.model.providers_mistral_codestral.httpx.AsyncClient",
                   return_value=mock_client_context):
            chunks = []
            async for chunk in provider.stream_chat(sample_messages):
                if chunk is not None:
                    chunks.append(chunk)

        assert len(chunks) == 5
        assert "".join(chunks) == 'def hello():\n    print("Hello!")'

    @pytest.mark.asyncio
    async def test_stream_uses_correct_url(self, provider, sample_messages):
        """stream_chat() must POST to the codestral chat endpoint."""
        sse_lines = _make_sse_stream(["ok"])

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = AsyncMock(return_value=aiter(sse_lines))

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_context)

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=False)

        with patch("src.model.providers_mistral_codestral.httpx.AsyncClient",
                   return_value=mock_client_context):
            async for _ in provider.stream_chat(sample_messages):
                pass

        mock_client.stream.assert_called_once()
        call_args = mock_client.stream.call_args
        assert call_args[0][1] == _CODESTRAL_CHAT_URL


# ---------------------------------------------------------------------------
# Non-streaming chat
# ---------------------------------------------------------------------------

class TestChat:
    @pytest.mark.asyncio
    async def test_chat_returns_content(self, provider, sample_messages):
        response_data = _make_chat_response("def hello():\n    print('Hello, World!')")

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=response_data)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=False)

        with patch("src.model.providers_mistral_codestral.httpx.AsyncClient",
                   return_value=mock_client_context):
            result = await provider.chat(sample_messages)

        assert "hello" in result
        assert "print" in result

    @pytest.mark.asyncio
    async def test_chat_retries_on_http_error(self, provider, sample_messages):
        """chat() should retry up to max_retries on transient HTTP errors."""
        import httpx

        success_data = _make_chat_response("result after retry")
        success_resp = AsyncMock()
        success_resp.raise_for_status = MagicMock()
        success_resp.json = MagicMock(return_value=success_data)

        fail_resp = MagicMock()
        fail_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "503", request=MagicMock(), response=MagicMock(status_code=503)
            )
        )

        mock_client = AsyncMock()
        # First call fails, second succeeds
        mock_client.post = AsyncMock(side_effect=[fail_resp, success_resp])

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=False)

        p = MistralCodestralProvider(api_key="key", max_retries=3)

        with patch("src.model.providers_mistral_codestral.httpx.AsyncClient",
                   return_value=mock_client_context), \
             patch("src.model.providers_mistral_codestral.asyncio.sleep",
                   new_callable=AsyncMock):
            result = await p.chat(sample_messages)

        assert result == "result after retry"


# ---------------------------------------------------------------------------
# Fill-in-the-Middle
# ---------------------------------------------------------------------------

class TestFIM:
    @pytest.mark.asyncio
    async def test_complete_fim_returns_infill(self, provider):
        fim_req = FIMRequest(
            prompt="def greet(name: str) -> str:\n    ",
            suffix="\n    return greeting",
        )

        fim_response = {
            "choices": [{"message": {"content": 'greeting = f"Hello, {name}!"'}}]
        }

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=fim_response)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=False)

        with patch("src.model.providers_mistral_codestral.httpx.AsyncClient",
                   return_value=mock_client_context):
            result = await provider.complete_fim(fim_req)

        assert "greeting" in result
        # Verify the FIM endpoint was targeted
        call_args = mock_client.post.call_args
        assert call_args[0][0] == _CODESTRAL_FIM_URL

    @pytest.mark.asyncio
    async def test_fim_payload_includes_suffix(self, provider):
        """The suffix field must be present in the request body."""
        fim_req = FIMRequest(prompt="x = ", suffix=" + 1")
        fim_response = {"choices": [{"message": {"content": "0"}}]}

        mock_resp = AsyncMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value=fim_response)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=False)

        with patch("src.model.providers_mistral_codestral.httpx.AsyncClient",
                   return_value=mock_client_context):
            await provider.complete_fim(fim_req)

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["suffix"] == " + 1"
        assert payload["prompt"] == "x = "


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

class TestModelConstants:
    def test_codestral_latest_value(self):
        assert CODESTRAL_LATEST == "codestral-latest"

    def test_codestral_2501_value(self):
        assert CODESTRAL_2501 == "codestral-2501"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def aiter(items):
    """Convert a list to an async iterator (for mocking aiter_lines)."""
    for item in items:
        yield item
