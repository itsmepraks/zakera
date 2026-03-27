"""
Test suite for the Cohere Command R / Command R+ provider.

Covers:
  - Config validation
  - Non-streaming chat
  - Streaming chat
  - RAG / grounded generation with documents
  - Tool-use (function calling)
  - Retry behaviour on transient errors
  - Token usage tracking
  - Health check
  - Factory helper
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from src.model.providers_cohere_command_r import (
    CohereCommandRProvider,
    CohereConfig,
    CohereDocument,
    CohereModel,
    CohereTool,
    CohereTokenUsage,
    CohereCitation,
    build_cohere_message,
    create_cohere_provider,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> CohereConfig:
    return CohereConfig(
        api_key="test-cohere-key-abc123",
        model=CohereModel.COMMAND_R_PLUS,
        max_tokens=1024,
        temperature=0.3,
    )


@pytest.fixture
def provider(config: CohereConfig) -> CohereCommandRProvider:
    return CohereCommandRProvider(config)


@pytest.fixture
def sample_messages() -> list:
    return [
        {"role": "user", "content": "What are the capitals of France and Germany?"},
    ]


@pytest.fixture
def sample_documents() -> list:
    return [
        CohereDocument(
            id="doc1",
            data={"title": "Geography Facts", "text": "Paris is the capital of France."},
        ),
        CohereDocument(
            id="doc2",
            data={"title": "European Capitals", "text": "Berlin is the capital of Germany."},
        ),
    ]


@pytest.fixture
def sample_tools() -> list:
    return [
        CohereTool(
            name="get_weather",
            description="Get the current weather for a city.",
            parameters_definitions={
                "city": {
                    "description": "The city name",
                    "type": "str",
                    "required": True,
                }
            },
        )
    ]


def _make_chat_response(text: str = "Paris and Berlin.", finish_reason: str = "COMPLETE") -> dict:
    """Build a minimal Cohere v2 chat response dict."""
    return {
        "id": "resp-abc123",
        "finish_reason": finish_reason,
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
        },
        "usage": {
            "billed_units": {
                "input_tokens": 20,
                "output_tokens": 10,
            }
        },
        "model": "command-r-plus",
        "citations": [],
    }


def _make_grounded_response(text: str = "Paris is the capital of France.") -> dict:
    """Build a Cohere response with citations."""
    resp = _make_chat_response(text)
    resp["citations"] = [
        {
            "start": 0,
            "end": 30,
            "text": "Paris is the capital of France",
            "sources": [{"id": "doc1", "document": {"title": "Geography Facts"}}],
        }
    ]
    return resp


def _make_tool_call_response() -> dict:
    resp = _make_chat_response(text="")
    resp["message"]["tool_calls"] = [
        {
            "id": "tool-call-1",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"city": "Paris"}),
            },
        }
    ]
    resp["finish_reason"] = "TOOL_CALL"
    return resp


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestCohereConfig:
    def test_valid_config(self):
        config = CohereConfig(api_key="key", model=CohereModel.COMMAND_R)
        assert config.model == "command-r"
        assert config.temperature == 0.3

    def test_invalid_model_raises(self):
        with pytest.raises(ValueError, match="Unsupported Cohere model"):
            CohereConfig(api_key="key", model="gpt-invalid")

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="api_key must not be empty"):
            CohereConfig(api_key="")

    def test_all_models_valid(self):
        for model in CohereModel.values():
            config = CohereConfig(api_key="key", model=model)
            assert config.model == model

    def test_defaults(self):
        config = CohereConfig(api_key="key")
        assert config.model == CohereModel.COMMAND_R_PLUS
        assert config.max_tokens == 4096
        assert config.temperature == 0.3
        assert config.preamble is None


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


class TestMessageHelpers:
    def test_build_user_message(self):
        msg = build_cohere_message("user", "Hello")
        assert msg["role"] == "USER"
        assert msg["message"] == "Hello"

    def test_build_assistant_message(self):
        msg = build_cohere_message("assistant", "Hi there")
        assert msg["role"] == "CHATBOT"
        assert msg["message"] == "Hi there"

    def test_build_system_treated_as_chatbot(self):
        # Non-user roles map to CHATBOT
        msg = build_cohere_message("system", "You are helpful")
        assert msg["role"] == "CHATBOT"


# ---------------------------------------------------------------------------
# Document helper
# ---------------------------------------------------------------------------


class TestCohereDocument:
    def test_to_dict(self):
        doc = CohereDocument(id="d1", data={"title": "Test", "text": "Content"})
        d = doc.to_dict()
        assert d["id"] == "d1"
        assert d["data"]["title"] == "Test"


# ---------------------------------------------------------------------------
# Tool helper
# ---------------------------------------------------------------------------


class TestCohereTool:
    def test_to_dict(self, sample_tools):
        tool = sample_tools[0]
        d = tool.to_dict()
        assert d["name"] == "get_weather"
        assert "city" in d["parameter_definitions"]
        assert d["parameter_definitions"]["city"]["required"] is True


# ---------------------------------------------------------------------------
# Citation helper
# ---------------------------------------------------------------------------


class TestCohereCitation:
    def test_from_dict(self):
        raw = {"start": 5, "end": 20, "text": "Paris", "sources": [{"id": "doc1"}]}
        citation = CohereCitation.from_dict(raw)
        assert citation.start == 5
        assert citation.end == 20
        assert citation.text == "Paris"
        assert len(citation.sources) == 1

    def test_defaults(self):
        citation = CohereCitation.from_dict({})
        assert citation.start == 0
        assert citation.end == 0
        assert citation.sources == []


# ---------------------------------------------------------------------------
# Provider: non-streaming chat
# ---------------------------------------------------------------------------


class TestCohereCommandRProviderChat:
    @pytest.mark.asyncio
    async def test_basic_chat_returns_content(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_chat_response("Paris and Berlin.")
        mock_resp.headers = {"x-request-id": "req-001"}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            result = await provider.chat(sample_messages)

        assert result["content"] == "Paris and Berlin."
        assert result["finish_reason"] == "COMPLETE"
        assert result["model"] == "command-r-plus"
        assert result["request_id"] == "req-001"

    @pytest.mark.asyncio
    async def test_chat_token_usage_tracked(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_chat_response()
        mock_resp.headers = {}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            await provider.chat(sample_messages)

        usage = provider.get_total_usage()
        assert usage.input_tokens == 20
        assert usage.output_tokens == 10
        assert usage.total_tokens == 30

    @pytest.mark.asyncio
    async def test_chat_api_error_raises(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 400
        mock_resp.text = "Bad request: invalid model"

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            with pytest.raises(RuntimeError, match="Cohere API error 400"):
                await provider.chat(sample_messages)

    @pytest.mark.asyncio
    async def test_chat_with_system_prompt(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_chat_response("Paris.")
        mock_resp.headers = {}

        captured_payload = {}

        async def capture_post(endpoint, payload):
            captured_payload.update(payload)
            return mock_resp

        with patch.object(provider, "_post_with_retry", new=capture_post):
            await provider.chat(sample_messages, system_prompt="You are a geography expert.")

        # System message should appear first
        assert captured_payload["messages"][0]["role"] == "system"
        assert "geography" in captured_payload["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_chat_empty_citations_when_no_rag(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_chat_response()
        mock_resp.headers = {}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            result = await provider.chat(sample_messages)

        assert result["citations"] == []


# ---------------------------------------------------------------------------
# Provider: RAG / grounded generation
# ---------------------------------------------------------------------------


class TestCohereCommandRProviderRAG:
    @pytest.mark.asyncio
    async def test_chat_with_documents_returns_citations(
        self, provider, sample_messages, sample_documents
    ):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_grounded_response()
        mock_resp.headers = {}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            result = await provider.chat_with_documents(sample_messages, sample_documents)

        assert len(result["citations"]) == 1
        citation = result["citations"][0]
        assert isinstance(citation, CohereCitation)
        assert citation.text == "Paris is the capital of France"
        assert citation.sources[0]["id"] == "doc1"

    @pytest.mark.asyncio
    async def test_documents_included_in_payload(self, provider, sample_messages, sample_documents):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_grounded_response()
        mock_resp.headers = {}

        captured = {}

        async def capture(endpoint, payload):
            captured.update(payload)
            return mock_resp

        with patch.object(provider, "_post_with_retry", new=capture):
            await provider.chat_with_documents(sample_messages, sample_documents)

        assert "documents" in captured
        assert len(captured["documents"]) == 2
        assert captured["documents"][0]["id"] == "doc1"


# ---------------------------------------------------------------------------
# Provider: tool-use
# ---------------------------------------------------------------------------


class TestCohereCommandRProviderTools:
    @pytest.mark.asyncio
    async def test_chat_with_tools_returns_tool_calls(
        self, provider, sample_messages, sample_tools
    ):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_tool_call_response()
        mock_resp.headers = {}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            result = await provider.chat_with_tools(sample_messages, sample_tools)

        assert result["finish_reason"] == "TOOL_CALL"
        assert result["tool_calls"] is not None
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"

    @pytest.mark.asyncio
    async def test_tools_included_in_payload(self, provider, sample_messages, sample_tools):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_tool_call_response()
        mock_resp.headers = {}

        captured = {}

        async def capture(endpoint, payload):
            captured.update(payload)
            return mock_resp

        with patch.object(provider, "_post_with_retry", new=capture):
            await provider.chat_with_tools(sample_messages, sample_tools)

        assert "tools" in captured
        assert captured["tools"][0]["name"] == "get_weather"


# ---------------------------------------------------------------------------
# Provider: streaming chat
# ---------------------------------------------------------------------------


class TestCohereCommandRProviderStreaming:
    @pytest.mark.asyncio
    async def test_stream_chat_yields_text_chunks(self, provider, sample_messages):
        sse_lines = [
            'data: {"type": "content-delta", "delta": {"message": {"content": {"text": "Par"}}}}',
            'data: {"type": "content-delta", "delta": {"message": {"content": {"text": "is"}}}}',
            'data: {"type": "content-delta", "delta": {"message": {"content": {"text": "!"}}}}',
            'data: {"type": "message-end", "delta": {"finish_reason": "COMPLETE", "usage": {"billed_units": {"input_tokens": 10, "output_tokens": 5}}}}',
        ]

        mock_response = AsyncMock()
        mock_response.status_code = 200

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            chunks = []
            async for chunk in provider.stream_chat(sample_messages):
                chunks.append(chunk)

        assert chunks == ["Par", "is", "!"]

    @pytest.mark.asyncio
    async def test_stream_chat_tracks_usage(self, provider, sample_messages):
        sse_lines = [
            'data: {"type": "content-delta", "delta": {"message": {"content": {"text": "Hi"}}}}',
            'data: {"type": "message-end", "delta": {"finish_reason": "COMPLETE", "usage": {"billed_units": {"input_tokens": 8, "output_tokens": 3}}}}',
        ]

        mock_response = AsyncMock()
        mock_response.status_code = 200

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            async for _ in provider.stream_chat(sample_messages):
                pass

        usage = provider.get_total_usage()
        assert usage.input_tokens == 8
        assert usage.output_tokens == 3

    @pytest.mark.asyncio
    async def test_stream_chat_raises_on_error_status(self, provider, sample_messages):
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.aread = AsyncMock(return_value=b"Unauthorized")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream.return_value = mock_response

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            with pytest.raises(RuntimeError, match="Cohere stream error 401"):
                async for _ in provider.stream_chat(sample_messages):
                    pass


# ---------------------------------------------------------------------------
# Provider: retry logic
# ---------------------------------------------------------------------------


class TestCohereRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_429(self, provider, sample_messages):
        rate_limit_resp = MagicMock(spec=httpx.Response)
        rate_limit_resp.status_code = 429
        rate_limit_resp.text = "Too Many Requests"

        success_resp = MagicMock(spec=httpx.Response)
        success_resp.status_code = 200
        success_resp.json.return_value = _make_chat_response()
        success_resp.headers = {}

        call_count = 0

        async def mock_post(endpoint, json):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return rate_limit_resp
            return success_resp

        mock_client = AsyncMock()
        mock_client.post = mock_post

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            with patch("asyncio.sleep", new=AsyncMock()):
                await provider.chat(sample_messages)

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_exceeded(self, config):
        config.max_retries = 2
        provider = CohereCommandRProvider(config)

        always_fail = MagicMock(spec=httpx.Response)
        always_fail.status_code = 503
        always_fail.text = "Service Unavailable"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=always_fail)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            with patch("asyncio.sleep", new=AsyncMock()):
                with pytest.raises(RuntimeError, match="failed after 2 retries"):
                    await provider.chat([{"role": "user", "content": "test"}])


# ---------------------------------------------------------------------------
# Provider: health check
# ---------------------------------------------------------------------------


class TestCohereHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, provider):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await provider.health_check()

        assert result["status"] == "healthy"
        assert result["provider"] == "cohere"
        assert result["model"] == "command-r-plus"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, provider):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 503

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch.object(provider, "_get_client", new=AsyncMock(return_value=mock_client)):
            result = await provider.health_check()

        assert result["status"] == "degraded"
        assert result["http_status"] == 503

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(self, provider):
        with patch.object(
            provider,
            "_get_client",
            new=AsyncMock(side_effect=httpx.ConnectError("connection refused")),
        ):
            result = await provider.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result


# ---------------------------------------------------------------------------
# Provider: usage tracking
# ---------------------------------------------------------------------------


class TestCohereTokenUsageTracking:
    @pytest.mark.asyncio
    async def test_cumulative_usage_across_multiple_calls(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_chat_response()
        mock_resp.headers = {}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            await provider.chat(sample_messages)
            await provider.chat(sample_messages)

        usage = provider.get_total_usage()
        assert usage.input_tokens == 40  # 20 * 2
        assert usage.output_tokens == 20  # 10 * 2
        assert usage.total_tokens == 60  # 30 * 2

    @pytest.mark.asyncio
    async def test_reset_usage(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_chat_response()
        mock_resp.headers = {}

        with patch.object(provider, "_post_with_retry", new=AsyncMock(return_value=mock_resp)):
            await provider.chat(sample_messages)

        provider.reset_usage()
        usage = provider.get_total_usage()
        assert usage.input_tokens == 0
        assert usage.total_tokens == 0

    def test_token_usage_from_response(self):
        data = {"usage": {"billed_units": {"input_tokens": 50, "output_tokens": 25}}}
        usage = CohereTokenUsage.from_response(data, model="command-r-plus")
        assert usage.input_tokens == 50
        assert usage.output_tokens == 25
        assert usage.total_tokens == 75


# ---------------------------------------------------------------------------
# Provider: metadata & lifecycle
# ---------------------------------------------------------------------------


class TestCohereProviderMetadata:
    def test_list_models(self):
        models = CohereCommandRProvider.list_models()
        assert "command-r-plus" in models
        assert "command-r" in models
        assert len(models) >= 4

    def test_repr(self, provider):
        assert "command-r-plus" in repr(provider)
        assert "CohereCommandRProvider" in repr(provider)

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        async with CohereCommandRProvider(config) as p:
            assert p is not None
            assert isinstance(p, CohereCommandRProvider)


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


class TestCreateCohereProvider:
    def test_factory_creates_provider(self):
        settings = {
            "cohere_api_key": "test-key",
            "cohere_model": "command-r",
            "cohere_max_tokens": "2048",
            "cohere_temperature": "0.5",
            "cohere_preamble": "You are a helpful assistant.",
        }
        p = create_cohere_provider(settings)
        assert isinstance(p, CohereCommandRProvider)
        assert p.config.model == "command-r"
        assert p.config.max_tokens == 2048
        assert p.config.temperature == 0.5
        assert p.config.preamble == "You are a helpful assistant."

    def test_factory_uses_defaults(self):
        settings = {"cohere_api_key": "test-key"}
        p = create_cohere_provider(settings)
        assert p.config.model == "command-r-plus"
        assert p.config.max_tokens == 4096
        assert p.config.preamble is None

    def test_factory_raises_without_api_key(self):
        with pytest.raises(KeyError):
            create_cohere_provider({})
