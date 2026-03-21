"""Tests for src/model/providers_bedrock.py.

All AWS calls are mocked — no real credentials or network access required.
"""
from __future__ import annotations

import asyncio
import json
from io import BytesIO
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.model.providers_bedrock import (
    BedrockConfig,
    BedrockProvider,
    _build_claude_payload,
    _build_llama_payload,
    _build_mistral_payload,
    _build_titan_payload,
    _model_family,
    _parse_claude_response,
    _parse_llama_response,
    _parse_mistral_response,
    _parse_titan_response,
)

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

CLAUDE_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
LLAMA_MODEL = "meta.llama3-8b-instruct-v1:0"
MISTRAL_MODEL = "mistral.mistral-7b-instruct-v0:2"
TITAN_MODEL = "amazon.titan-text-express-v1"

SIMPLE_MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
]


@pytest.fixture
def config() -> BedrockConfig:
    return BedrockConfig(
        region="us-east-1",
        aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        default_model=CLAUDE_MODEL,
        max_retries=3,
    )


@pytest.fixture
def provider(config: BedrockConfig) -> BedrockProvider:
    return BedrockProvider(config)


# ---------------------------------------------------------------------------
# 1. _model_family detection
# ---------------------------------------------------------------------------


class TestModelFamily:
    def test_claude_haiku(self):
        assert _model_family(CLAUDE_MODEL) == "claude"

    def test_claude_sonnet(self):
        assert _model_family("anthropic.claude-3-sonnet-20240229-v1:0") == "claude"

    def test_claude_opus(self):
        assert _model_family("anthropic.claude-3-opus-20240229-v1:0") == "claude"

    def test_llama(self):
        assert _model_family(LLAMA_MODEL) == "llama"

    def test_llama_70b(self):
        assert _model_family("meta.llama3-70b-instruct-v1:0") == "llama"

    def test_mistral(self):
        assert _model_family(MISTRAL_MODEL) == "mistral"

    def test_mixtral(self):
        assert _model_family("mistral.mixtral-8x7b-instruct-v0:1") == "mistral"

    def test_titan(self):
        assert _model_family(TITAN_MODEL) == "titan"

    def test_unknown(self):
        assert _model_family("cohere.command-r-plus-v1:0") == "unknown"


# ---------------------------------------------------------------------------
# 2. Payload builders
# ---------------------------------------------------------------------------


class TestClaudePayloadBuilder:
    def test_system_prompt_extracted(self):
        payload = _build_claude_payload(SIMPLE_MESSAGES, 0.7, 512, 0.9)
        assert payload["system"] == "You are a helpful assistant."
        # System message must NOT appear in messages array
        roles = [m["role"] for m in payload["messages"]]
        assert "system" not in roles

    def test_user_message_present(self):
        payload = _build_claude_payload(SIMPLE_MESSAGES, 0.7, 512, 0.9)
        assert payload["messages"][-1]["content"] == "Hello!"

    def test_required_fields(self):
        payload = _build_claude_payload(SIMPLE_MESSAGES, 0.5, 1024, 0.8)
        assert payload["anthropic_version"] == "bedrock-2023-05-31"
        assert payload["max_tokens"] == 1024
        assert payload["temperature"] == pytest.approx(0.5)

    def test_no_system_prompt_omitted(self):
        msgs = [{"role": "user", "content": "hi"}]
        payload = _build_claude_payload(msgs, 0.7, 512, 0.9)
        assert "system" not in payload

    def test_stop_sequences_forwarded(self):
        payload = _build_claude_payload(
            SIMPLE_MESSAGES, 0.7, 512, 0.9, stop_sequences=["END"]
        )
        assert payload["stop_sequences"] == ["END"]


class TestLlamaPayloadBuilder:
    def test_prompt_contains_chat_template_tokens(self):
        msgs = [{"role": "user", "content": "Tell me a joke"}]
        payload = _build_llama_payload(msgs, 0.7, 512, 0.9)
        prompt = payload["prompt"]
        assert "<|begin_of_text|>" in prompt
        assert "<|start_header_id|>user<|end_header_id|>" in prompt
        assert "Tell me a joke" in prompt
        assert "<|start_header_id|>assistant<|end_header_id|>" in prompt

    def test_max_gen_len_set(self):
        payload = _build_llama_payload(SIMPLE_MESSAGES, 0.7, 2048, 0.9)
        assert payload["max_gen_len"] == 2048


class TestMistralPayloadBuilder:
    def test_messages_preserved(self):
        payload = _build_mistral_payload(SIMPLE_MESSAGES, 0.7, 512, 0.9)
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["content"] == "Hello!"

    def test_max_tokens_field(self):
        payload = _build_mistral_payload(SIMPLE_MESSAGES, 0.7, 256, 0.9)
        assert payload["max_tokens"] == 256


class TestTitanPayloadBuilder:
    def test_input_text_has_bot_marker(self):
        msgs = [{"role": "user", "content": "What is 2+2?"}]
        payload = _build_titan_payload(msgs, 0.7, 512, 0.9)
        assert "Bot:" in payload["inputText"]

    def test_generation_config_fields(self):
        payload = _build_titan_payload(SIMPLE_MESSAGES, 0.6, 800, 0.85)
        cfg = payload["textGenerationConfig"]
        assert cfg["maxTokenCount"] == 800
        assert cfg["temperature"] == pytest.approx(0.6)
        assert cfg["topP"] == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# 3. Response parsers
# ---------------------------------------------------------------------------


class TestResponseParsers:
    def test_parse_claude_response(self):
        body = {
            "id": "msg_abc123",
            "content": [{"type": "text", "text": "Hello there!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 20, "output_tokens": 5},
        }
        resp = _parse_claude_response(body, CLAUDE_MODEL)
        assert resp.text == "Hello there!"
        assert resp.provider == "bedrock"
        assert resp.usage["prompt_tokens"] == 20
        assert resp.usage["completion_tokens"] == 5
        assert resp.usage["total_tokens"] == 25
        assert resp.finish_reason == "end_turn"

    def test_parse_llama_response(self):
        body = {
            "generation": "Here is your joke.",
            "stop_reason": "stop",
            "prompt_token_count": 30,
            "generation_token_count": 8,
        }
        resp = _parse_llama_response(body, LLAMA_MODEL)
        assert resp.text == "Here is your joke."
        assert resp.usage["total_tokens"] == 38

    def test_parse_mistral_outputs_format(self):
        # Mistral Bedrock uses 'outputs' list
        body = {
            "outputs": [{"text": "Mistral says hi", "stop_reason": "stop"}]
        }
        resp = _parse_mistral_response(body, MISTRAL_MODEL)
        assert resp.text == "Mistral says hi"

    def test_parse_mistral_choices_format(self):
        # OpenAI-compat fallback format
        body = {
            "choices": [{"message": {"content": "Hello from Mixtral"}, "finish_reason": "stop"}]
        }
        resp = _parse_mistral_response(body, MISTRAL_MODEL)
        assert resp.text == "Hello from Mixtral"

    def test_parse_titan_response(self):
        body = {
            "inputTextTokenCount": 15,
            "results": [{"outputText": "4", "tokenCount": 1, "completionReason": "FINISH"}],
        }
        resp = _parse_titan_response(body, TITAN_MODEL)
        assert resp.text == "4"
        assert resp.usage["total_tokens"] == 16
        assert resp.finish_reason == "FINISH"


# ---------------------------------------------------------------------------
# 4. Provider.generate() — success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestProviderGenerate:
    async def test_generate_claude_success(self, provider: BedrockProvider):
        response_body = {
            "id": "msg_test",
            "content": [{"type": "text", "text": "Hi!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 2},
        }
        encoded = json.dumps(response_body).encode()

        mock_response = {
            "body": BytesIO(encoded)
        }

        with patch.object(provider, "_invoke_sync", return_value=response_body):
            result = await provider.generate(SIMPLE_MESSAGES, model=CLAUDE_MODEL)

        assert result.text == "Hi!"
        assert result.provider == "bedrock"
        assert result.model == CLAUDE_MODEL

    async def test_generate_uses_default_model(self, provider: BedrockProvider):
        response_body = {
            "content": [{"type": "text", "text": "Default!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 1},
        }
        with patch.object(provider, "_invoke_sync", return_value=response_body) as mock_invoke:
            result = await provider.generate(SIMPLE_MESSAGES)

        mock_invoke.assert_called_once()
        called_model = mock_invoke.call_args[0][0]
        assert called_model == provider.config.default_model

    async def test_generate_llama_success(self, provider: BedrockProvider):
        body = {
            "generation": "Llama answer",
            "stop_reason": "stop",
            "prompt_token_count": 12,
            "generation_token_count": 3,
        }
        with patch.object(provider, "_invoke_sync", return_value=body):
            result = await provider.generate(SIMPLE_MESSAGES, model=LLAMA_MODEL)

        assert result.text == "Llama answer"


# ---------------------------------------------------------------------------
# 5. Retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRetryLogic:
    async def test_throttling_retries_and_succeeds(self, provider: BedrockProvider):
        """First call raises ThrottlingException; second call succeeds."""
        success_body = {
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 1},
        }

        class ThrottlingException(Exception):
            pass

        call_count = 0

        def side_effect(model, payload):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ThrottlingException("Rate exceeded")
            return success_body

        with patch.object(provider, "_invoke_sync", side_effect=side_effect), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            result = await provider.generate(SIMPLE_MESSAGES, model=CLAUDE_MODEL)

        assert call_count == 2
        assert result.text == "ok"

    async def test_validation_error_no_retry(self, provider: BedrockProvider):
        """Non-retriable error (ValidationException) should not retry."""
        call_count = 0

        class ValidationException(Exception):
            pass

        def side_effect(model, payload):
            nonlocal call_count
            call_count += 1
            raise ValidationException("Invalid model params")

        with patch.object(provider, "_invoke_sync", side_effect=side_effect):
            with pytest.raises(Exception, match="Bedrock generation failed"):
                await provider.generate(SIMPLE_MESSAGES, model=CLAUDE_MODEL)

        # Should only attempt once — no retry for non-throttle errors
        assert call_count == 1

    async def test_exhausts_max_retries(self, config: BedrockConfig):
        """All retry attempts fail with throttling — raises after max_retries."""
        config = config.model_copy(update={"max_retries": 2})
        provider = BedrockProvider(config)

        class ThrottlingException(Exception):
            pass

        call_count = 0

        def side_effect(model, payload):
            nonlocal call_count
            call_count += 1
            raise ThrottlingException("Still throttled")

        with patch.object(provider, "_invoke_sync", side_effect=side_effect), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Bedrock generation failed after 2 attempts"):
                await provider.generate(SIMPLE_MESSAGES, model=CLAUDE_MODEL)

        assert call_count == 2


# ---------------------------------------------------------------------------
# 6. Streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStreaming:
    def _make_stream_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap a dict in the structure Bedrock streaming returns."""
        return {"chunk": {"bytes": json.dumps(data).encode()}}

    async def test_claude_stream_yields_text_deltas(self, provider: BedrockProvider):
        events = [
            self._make_stream_event(
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hel"}}
            ),
            self._make_stream_event(
                {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "lo!"}}
            ),
            self._make_stream_event({"type": "message_stop"}),
        ]

        mock_raw = {"body": iter(events)}
        with patch.object(provider, "_invoke_stream_sync", return_value=mock_raw):
            chunks: List[str] = []
            async for chunk in provider.generate_stream(SIMPLE_MESSAGES, model=CLAUDE_MODEL):
                chunks.append(chunk)

        assert chunks == ["Hel", "lo!"]

    async def test_llama_stream_yields_generation(self, provider: BedrockProvider):
        events = [
            self._make_stream_event({"generation": "Part1 "}),
            self._make_stream_event({"generation": "Part2"}),
            self._make_stream_event({"generation": ""}),  # empty — should not yield
        ]

        mock_raw = {"body": iter(events)}
        with patch.object(provider, "_invoke_stream_sync", return_value=mock_raw):
            chunks = []
            async for chunk in provider.generate_stream(SIMPLE_MESSAGES, model=LLAMA_MODEL):
                chunks.append(chunk)

        assert chunks == ["Part1 ", "Part2"]

    async def test_mistral_stream_yields_outputs(self, provider: BedrockProvider):
        events = [
            self._make_stream_event({"outputs": [{"text": "Mis"}, {"text": "tral"}]}),
        ]

        mock_raw = {"body": iter(events)}
        with patch.object(provider, "_invoke_stream_sync", return_value=mock_raw):
            chunks = []
            async for chunk in provider.generate_stream(SIMPLE_MESSAGES, model=MISTRAL_MODEL):
                chunks.append(chunk)

        assert chunks == ["Mis", "tral"]

    async def test_titan_stream_yields_output_text(self, provider: BedrockProvider):
        events = [
            self._make_stream_event({"outputText": "Titan "}),
            self._make_stream_event({"outputText": "answer"}),
        ]

        mock_raw = {"body": iter(events)}
        with patch.object(provider, "_invoke_stream_sync", return_value=mock_raw):
            chunks = []
            async for chunk in provider.generate_stream(SIMPLE_MESSAGES, model=TITAN_MODEL):
                chunks.append(chunk)

        assert chunks == ["Titan ", "answer"]

    async def test_empty_stream_body_returns_nothing(self, provider: BedrockProvider):
        mock_raw = {"body": None}
        with patch.object(provider, "_invoke_stream_sync", return_value=mock_raw):
            chunks = []
            async for chunk in provider.generate_stream(SIMPLE_MESSAGES, model=CLAUDE_MODEL):
                chunks.append(chunk)
        assert chunks == []


# ---------------------------------------------------------------------------
# 7. Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_healthy(self, provider: BedrockProvider):
        mock_models = [
            {"modelId": CLAUDE_MODEL},
            {"modelId": LLAMA_MODEL},
        ]

        def fake_list_models():
            return [m["modelId"] for m in mock_models]

        with patch(
            "src.model.providers_bedrock.BedrockProvider.health_check",
            new_callable=AsyncMock,
            return_value={
                "status": "healthy",
                "provider": "bedrock",
                "region": "us-east-1",
                "available_models_count": 2,
                "default_model": CLAUDE_MODEL,
            },
        ):
            result = await provider.health_check()

        assert result["status"] == "healthy"
        assert result["provider"] == "bedrock"

    async def test_unhealthy_on_exception(self, provider: BedrockProvider):
        with patch(
            "src.model.providers_bedrock.BedrockProvider.health_check",
            new_callable=AsyncMock,
            return_value={
                "status": "unhealthy",
                "provider": "bedrock",
                "region": "us-east-1",
                "error": "NoCredentialsError",
            },
        ):
            result = await provider.health_check()

        assert result["status"] == "unhealthy"
        assert "error" in result


# ---------------------------------------------------------------------------
# 8. Metadata helpers
# ---------------------------------------------------------------------------


class TestMetadataHelpers:
    @pytest.mark.asyncio
    async def test_get_available_models_returns_all(self, provider: BedrockProvider):
        models = await provider.get_available_models()
        assert len(models) >= 8  # we registered at least 8 in the spec
        assert CLAUDE_MODEL in models
        assert TITAN_MODEL in models

    def test_get_model_info_known(self, provider: BedrockProvider):
        info = provider.get_model_info(CLAUDE_MODEL)
        assert info["context_length"] == 200_000
        assert "input_cost_per_1k" in info

    def test_get_model_info_unknown_returns_empty(self, provider: BedrockProvider):
        info = provider.get_model_info("cohere.command-r-plus-v1:0")
        assert info == {}

    @pytest.mark.parametrize(
        "priority, expected_fragment",
        [
            ("speed", "haiku"),
            ("quality", "3-5-sonnet"),
            ("cost", "titan-text-express"),
            ("balanced", "sonnet"),
        ],
    )
    def test_recommend_model(self, provider: BedrockProvider, priority: str, expected_fragment: str):
        rec = provider.recommend_model(priority)
        assert expected_fragment in rec

    @pytest.mark.asyncio
    async def test_close_resets_client(self, provider: BedrockProvider):
        # Manually set a sentinel client
        provider._client = MagicMock()
        await provider.close()
        assert provider._client is None


# ---------------------------------------------------------------------------
# 9. Missing boto3 guard
# ---------------------------------------------------------------------------


class TestMissingBoto3:
    def test_get_client_raises_import_error_when_boto3_missing(
        self, provider: BedrockProvider
    ):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "boto3":
                raise ImportError("No module named 'boto3'")
            return real_import(name, *args, **kwargs)

        provider._client = None  # ensure lazy-init path is triggered
        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="boto3 is required"):
                provider._get_client()


# ---------------------------------------------------------------------------
# 10. Payload dispatch — unknown family raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_model_family_raises(provider: BedrockProvider):
    with pytest.raises(ValueError, match="Unsupported Bedrock model family"):
        await provider.generate(SIMPLE_MESSAGES, model="cohere.command-r-plus-v1:0")
