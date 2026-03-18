"""
Comprehensive unit tests for GeminiFlashProvider.

All external HTTP calls are patched via pytest-mock / unittest.mock so that
no real network requests are made.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from src.model.providers.gemini_flash import (
    DEFAULT_MODEL,
    GeminiFlashProvider,
    _convert_messages_to_gemini,
    _convert_tools_to_gemini,
)
from src.model.config import ProviderConfig, load_provider_config
from src.model.exceptions import ModelProviderError, RateLimitError, TokenLimitError
from src.model.providers import PROVIDER_REGISTRY


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def config() -> ProviderConfig:
    return ProviderConfig(api_key="test-google-key", model="gemini-2.0-flash-exp")


@pytest.fixture()
def provider(config: ProviderConfig) -> GeminiFlashProvider:
    return GeminiFlashProvider(config)


@pytest.fixture()
def sample_messages():
    return [
        {"role": "user", "content": "Hello, Zakera!"},
    ]


@pytest.fixture()
def gemini_success_response():
    """A minimal successful Gemini generateContent JSON response."""
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": "Hi there!"}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "totalTokenCount": 15,
        },
        "modelVersion": "gemini-2.0-flash-exp",
    }


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestProviderInit:
    def test_valid_model_accepted(self, config):
        p = GeminiFlashProvider(config)
        assert p.provider_id == "gemini_flash"

    def test_thinking_variant_accepted(self):
        cfg = ProviderConfig(api_key="key", model="gemini-2.0-flash-thinking-exp")
        p = GeminiFlashProvider(cfg)
        assert p._model == "gemini-2.0-flash-thinking-exp"

    def test_invalid_model_raises(self):
        cfg = ProviderConfig(api_key="key", model="gpt-not-gemini")
        with pytest.raises(ModelProviderError, match="Unsupported model"):
            GeminiFlashProvider(cfg)

    def test_default_model_used_when_none(self):
        cfg = ProviderConfig(api_key="key")
        p = GeminiFlashProvider(cfg)
        assert p._model == DEFAULT_MODEL

    def test_metadata_context_window(self, provider):
        assert provider.model_metadata.context_window == 1_048_576


# ---------------------------------------------------------------------------
# Message conversion
# ---------------------------------------------------------------------------

class TestConvertMessages:
    def test_plain_user_message(self):
        _, contents = _convert_messages_to_gemini([{"role": "user", "content": "Hi"}])
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"] == [{"text": "Hi"}]

    def test_assistant_maps_to_model(self):
        _, contents = _convert_messages_to_gemini(
            [{"role": "assistant", "content": "Hello back"}]
        )
        assert contents[0]["role"] == "model"

    def test_system_message_extracted(self):
        sys_instr, contents = _convert_messages_to_gemini(
            [
                {"role": "system",    "content": "Be helpful."},
                {"role": "user",      "content": "Yo"},
            ]
        )
        assert sys_instr is not None
        assert "Be helpful" in sys_instr["parts"][0]["text"]
        assert len(contents) == 1  # system message removed from contents

    def test_explicit_system_prompt_param(self):
        sys_instr, _ = _convert_messages_to_gemini(
            [{"role": "user", "content": "Q"}],
            system_prompt="You are Zakera.",
        )
        assert "Zakera" in sys_instr["parts"][0]["text"]

    def test_multimodal_base64_image(self):
        b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12NgAAIABQ"
        _, contents = _convert_messages_to_gemini(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ]
        )
        parts = contents[0]["parts"]
        assert parts[0] == {"text": "What's in this image?"}
        assert "inline_data" in parts[1]
        assert parts[1]["inline_data"]["mime_type"] == "image/png"

    def test_multimodal_file_uri(self):
        _, contents = _convert_messages_to_gemini(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "gs://my-bucket/img.jpg"}},
                    ],
                }
            ]
        )
        assert "file_data" in contents[0]["parts"][0]


# ---------------------------------------------------------------------------
# Tool conversion
# ---------------------------------------------------------------------------

class TestConvertTools:
    def test_single_function(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather.",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }
        ]
        result = _convert_tools_to_gemini(tools)
        assert len(result) == 1
        decls = result[0]["function_declarations"]
        assert decls[0]["name"] == "get_weather"

    def test_multiple_functions_in_one_declaration_block(self):
        tools = [
            {"type": "function", "function": {"name": "fn_a", "description": "", "parameters": {}}},
            {"type": "function", "function": {"name": "fn_b", "description": "", "parameters": {}}},
        ]
        result = _convert_tools_to_gemini(tools)
        assert len(result[0]["function_declarations"]) == 2


# ---------------------------------------------------------------------------
# generate() — happy path and errors
# ---------------------------------------------------------------------------

class TestGenerate:
    @pytest.mark.asyncio
    async def test_success_returns_standard_response(
        self, provider, sample_messages, gemini_success_response
    ):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = gemini_success_response
        mock_resp.raise_for_status = MagicMock()  # no-op

        provider._http.post = AsyncMock(return_value=mock_resp)

        result = await provider.generate(sample_messages)

        assert result["role"] == "assistant"
        assert result["content"] == "Hi there!"
        assert result["usage"]["total_tokens"] == 15
        assert result["finish_reason"] == "STOP"
        assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_rate_limit_raises_rate_limit_error(self, provider, sample_messages):
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 429
        error_resp.json.return_value = {"error": {"message": "Quota exceeded"}}
        exc = httpx.HTTPStatusError("429", request=MagicMock(), response=error_resp)
        error_resp.raise_for_status.side_effect = exc

        provider._http.post = AsyncMock(return_value=error_resp)

        with pytest.raises(RateLimitError, match="rate limit"):
            await provider.generate(sample_messages)

    @pytest.mark.asyncio
    async def test_generic_http_error_raises_model_provider_error(
        self, provider, sample_messages
    ):
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 500
        error_resp.json.return_value = {"error": {"message": "Internal error"}}
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=error_resp)
        error_resp.raise_for_status.side_effect = exc

        provider._http.post = AsyncMock(return_value=error_resp)

        with pytest.raises(ModelProviderError, match="500"):
            await provider.generate(sample_messages)

    @pytest.mark.asyncio
    async def test_empty_candidates_raises(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"candidates": [], "usageMetadata": {}}
        provider._http.post = AsyncMock(return_value=mock_resp)

        with pytest.raises(ModelProviderError, match="no candidates"):
            await provider.generate(sample_messages)

    @pytest.mark.asyncio
    async def test_tool_call_parsed_correctly(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_weather",
                                    "args": {"location": "DC"},
                                }
                            }
                        ],
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 8, "totalTokenCount": 28},
        }
        provider._http.post = AsyncMock(return_value=mock_resp)

        result = await provider.generate(sample_messages)
        assert result["tool_calls"] is not None
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"
        args = json.loads(result["tool_calls"][0]["function"]["arguments"])
        assert args["location"] == "DC"


# ---------------------------------------------------------------------------
# generate_stream()
# ---------------------------------------------------------------------------

class TestGenerateStream:
    @pytest.mark.asyncio
    async def test_stream_yields_deltas_and_done(self, provider, sample_messages):
        sse_lines = [
            'data: {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}',
            'data: {"candidates": [{"content": {"parts": [{"text": " world"}]}}], '
            '"usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2}}',
            "data: [DONE]",
        ]

        async def mock_aiter_lines():
            for line in sse_lines:
                yield line

        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        provider._http.stream = MagicMock(return_value=mock_response)

        events = []
        async for event in provider.generate_stream(sample_messages):
            events.append(event)

        delta_events = [e for e in events if e["type"] == "delta"]
        done_events  = [e for e in events if e["type"] == "done"]

        assert len(delta_events) == 2
        assert delta_events[0]["content"] == "Hello"
        assert delta_events[1]["content"] == " world"

        assert len(done_events) == 1
        assert done_events[0]["usage"]["prompt_tokens"] == 5
        assert done_events[0]["usage"]["completion_tokens"] == 2


# ---------------------------------------------------------------------------
# count_tokens()
# ---------------------------------------------------------------------------

class TestCountTokens:
    @pytest.mark.asyncio
    async def test_returns_token_count(self, provider, sample_messages):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"totalTokens": 42}
        provider._http.post = AsyncMock(return_value=mock_resp)

        count = await provider.count_tokens(sample_messages)
        assert count == 42

    @pytest.mark.asyncio
    async def test_graceful_fallback_on_error(self, provider, sample_messages):
        error_resp = MagicMock(spec=httpx.Response)
        error_resp.status_code = 400
        exc = httpx.HTTPStatusError("400", request=MagicMock(), response=error_resp)
        error_resp.raise_for_status.side_effect = exc
        provider._http.post = AsyncMock(return_value=error_resp)

        # Should NOT raise — just returns 0
        count = await provider.count_tokens(sample_messages)
        assert count == 0


# ---------------------------------------------------------------------------
# _build_payload() — generation config options
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def test_json_mode_sets_mime_type(self, provider, sample_messages):
        payload = provider._build_payload(
            sample_messages,
            system_prompt=None,
            temperature=0.5,
            max_tokens=512,
            tools=None,
            response_format={"type": "json_object"},
        )
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["maxOutputTokens"] == 512

    def test_tool_choice_required_sets_any_mode(self, provider, sample_messages):
        tools = [{"type": "function", "function": {"name": "fn", "description": "", "parameters": {}}}]
        payload = provider._build_payload(
            sample_messages,
            system_prompt=None,
            temperature=0.7,
            max_tokens=None,
            tools=tools,
            tool_choice="required",
        )
        assert payload["toolConfig"]["functionCallingConfig"]["mode"] == "ANY"

    def test_tool_choice_none_sets_none_mode(self, provider, sample_messages):
        tools = [{"type": "function", "function": {"name": "fn", "description": "", "parameters": {}}}]
        payload = provider._build_payload(
            sample_messages,
            system_prompt=None,
            temperature=0.7,
            max_tokens=None,
            tools=tools,
            tool_choice="none",
        )
        assert payload["toolConfig"]["functionCallingConfig"]["mode"] == "NONE"


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

class TestProviderRegistry:
    def test_gemini_flash_registered(self):
        assert "gemini_flash" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["gemini_flash"] is GeminiFlashProvider


# ---------------------------------------------------------------------------
# load_provider_config()
# ---------------------------------------------------------------------------

class TestLoadProviderConfig:
    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "env-key-123")
        cfg = load_provider_config("gemini_flash")
        assert cfg.api_key == "env-key-123"
        assert cfg.model == "gemini-2.0-flash-exp"

    def test_missing_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
            load_provider_config("gemini_flash")

    def test_override_model(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        cfg = load_provider_config(
            "gemini_flash",
            override={"model": "gemini-2.0-flash-thinking-exp"}
        )
        assert cfg.model == "gemini-2.0-flash-thinking-exp"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            load_provider_config("not-a-real-provider")
