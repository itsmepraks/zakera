"""
Tests for src.model.providers_google_vertex_gemini2

All network calls are intercepted with pytest-httpx (or unittest.mock)
so these tests run completely offline.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.model.config import ModelConfig
from src.model.providers_google_vertex_gemini2 import (
    GoogleVertexGemini2Provider,
    _CachedToken,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def basic_provider() -> GoogleVertexGemini2Provider:
    """Provider using a static bearer token — no ADC needed."""
    return GoogleVertexGemini2Provider(
        project_id="test-project",
        location="us-central1",
        access_token="fake-token-abc123",
    )


@pytest.fixture()
def configured_provider() -> GoogleVertexGemini2Provider:
    """Provider with a custom ModelConfig."""
    cfg = ModelConfig(
        model="gemini-2.0-flash-001",
        temperature=0.5,
        max_tokens=2048,
    )
    return GoogleVertexGemini2Provider(
        project_id="test-project",
        location="europe-west4",
        access_token="fake-token-xyz",
        config=cfg,
    )


@pytest.fixture()
def sample_messages() -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2 + 2?"},
    ]


@pytest.fixture()
def vertex_generate_response() -> Dict[str, Any]:
    """Minimal valid Vertex AI generateContent response body."""
    return {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": "2 + 2 = 4"}]},
                "finishReason": "STOP",
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 12,
            "candidatesTokenCount": 8,
            "totalTokenCount": 20,
        },
    }


# ---------------------------------------------------------------------------
# Unit tests — no I/O
# ---------------------------------------------------------------------------


class TestInit:
    def test_init_with_static_token(self, basic_provider):
        assert basic_provider.project_id == "test-project"
        assert basic_provider.location == "us-central1"
        assert basic_provider._static_token == "fake-token-abc123"
        assert basic_provider.name == "google_vertex_gemini2"

    def test_init_without_token(self):
        provider = GoogleVertexGemini2Provider(
            project_id="my-project", location="us-east1"
        )
        assert provider._static_token is None
        assert provider._cached_token is None

    def test_base_url_includes_project_and_location(self, basic_provider):
        assert "test-project" in basic_provider._base_url
        assert "us-central1" in basic_provider._base_url


class TestValidateConfig:
    def test_validate_config_ok(self, basic_provider):
        assert basic_provider.validate_config() is True

    def test_validate_config_missing_project(self):
        provider = GoogleVertexGemini2Provider(
            project_id="",
            location="us-central1",
            access_token="token",
        )
        assert provider.validate_config() is False

    def test_validate_config_empty_token(self):
        provider = GoogleVertexGemini2Provider(
            project_id="proj",
            location="us-central1",
            access_token="",
        )
        assert provider.validate_config() is False

    def test_validate_config_bad_model(self):
        cfg = ModelConfig(model="gemini-99-super")
        provider = GoogleVertexGemini2Provider(
            project_id="proj",
            location="us-central1",
            access_token="token",
            config=cfg,
        )
        assert provider.validate_config() is False


class TestSupportedModels:
    def test_get_supported_models_has_flash(self, basic_provider):
        models = basic_provider.get_supported_models()
        assert "gemini-2.0-flash-001" in models

    def test_get_supported_models_has_lite(self, basic_provider):
        models = basic_provider.get_supported_models()
        assert "gemini-2.0-flash-lite-001" in models

    def test_get_model_ids_returns_list(self, basic_provider):
        ids = basic_provider.get_model_ids()
        assert isinstance(ids, list)
        assert len(ids) == 2  # flash + flash-lite

    def test_default_model_is_flash_001(self):
        assert GoogleVertexGemini2Provider.DEFAULT_MODEL == "gemini-2.0-flash-001"


class TestFormatContents:
    def test_basic_user_turn(self, basic_provider):
        msgs = [{"role": "user", "content": "Hello"}]
        contents, system = basic_provider._format_contents(msgs)
        assert system is None
        assert contents == [{"role": "user", "parts": [{"text": "Hello"}]}]

    def test_system_message_extracted(self, basic_provider):
        msgs = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Hi"},
        ]
        contents, system = basic_provider._format_contents(msgs)
        assert system == "Be concise."
        assert contents[0]["role"] == "user"

    def test_assistant_role_mapped_to_model(self, basic_provider):
        msgs = [
            {"role": "user", "content": "Ping"},
            {"role": "assistant", "content": "Pong"},
        ]
        contents, _ = basic_provider._format_contents(msgs)
        assert contents[1]["role"] == "model"

    def test_consecutive_same_role_merged(self, basic_provider):
        """Two consecutive user turns should be merged into one."""
        msgs = [
            {"role": "user", "content": "First"},
            {"role": "user", "content": "Second"},
        ]
        contents, _ = basic_provider._format_contents(msgs)
        assert len(contents) == 1
        assert len(contents[0]["parts"]) == 2
        assert contents[0]["parts"][0]["text"] == "First"
        assert contents[0]["parts"][1]["text"] == "Second"


class TestCalculateCost:
    def test_flash_cost(self, basic_provider):
        cost = basic_provider._calculate_cost("gemini-2.0-flash-001", 1000, 1000)
        info = basic_provider.SUPPORTED_MODELS["gemini-2.0-flash-001"]
        expected = (
            (1000 / 1000) * info["cost_per_1k_input"]
            + (1000 / 1000) * info["cost_per_1k_output"]
        )
        assert abs(cost - expected) < 1e-9

    def test_lite_model_cost_is_lower(self, basic_provider):
        cost_flash = basic_provider._calculate_cost("gemini-2.0-flash-001", 1000, 1000)
        cost_lite = basic_provider._calculate_cost(
            "gemini-2.0-flash-lite-001", 1000, 1000
        )
        assert cost_lite < cost_flash


class TestBuildPayload:
    def test_minimal_payload(self, basic_provider, sample_messages):
        payload = basic_provider._build_payload(
            sample_messages, max_output_tokens=512, temperature=0.7
        )
        assert "contents" in payload
        assert "generationConfig" in payload
        assert payload["generationConfig"]["maxOutputTokens"] == 512
        assert payload["generationConfig"]["temperature"] == 0.7
        # system message extracted
        assert "systemInstruction" in payload

    def test_optional_params_forwarded(self, basic_provider, sample_messages):
        payload = basic_provider._build_payload(
            sample_messages,
            max_output_tokens=256,
            temperature=0.3,
            top_p=0.9,
            stop_sequences=["</answer>"],
        )
        gc = payload["generationConfig"]
        assert gc["topP"] == 0.9
        assert gc["stopSequences"] == ["</answer>"]


class TestExtractTextFromCandidates:
    def test_basic_extraction(self, basic_provider):
        candidates = [
            {
                "content": {"parts": [{"text": "Hello "}, {"text": "World"}]},
                "finishReason": "STOP",
            }
        ]
        text, reason = basic_provider._extract_text_from_candidates(candidates)
        assert text == "Hello World"
        assert reason == "STOP"

    def test_empty_candidates(self, basic_provider):
        text, reason = basic_provider._extract_text_from_candidates([])
        assert text == ""
        assert reason is None


class TestCachedToken:
    def test_valid_token_not_expired(self):
        token = _CachedToken(
            token="abc",
            expires_at=time.monotonic() + 3_600,
        )
        assert token.is_valid() is True

    def test_expired_token_invalid(self):
        token = _CachedToken(
            token="abc",
            # Already expired
            expires_at=time.monotonic() - 1,
        )
        assert token.is_valid() is False

    def test_near_expiry_token_invalid(self):
        """Token within the refresh margin should be treated as invalid."""
        from src.model.providers_google_vertex_gemini2 import (
            CREDENTIAL_REFRESH_MARGIN_SECONDS,
        )

        token = _CachedToken(
            token="abc",
            expires_at=time.monotonic() + CREDENTIAL_REFRESH_MARGIN_SECONDS - 5,
        )
        assert token.is_valid() is False


# ---------------------------------------------------------------------------
# Integration tests — httpx mocked
# ---------------------------------------------------------------------------


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(
        self, basic_provider, sample_messages, vertex_generate_response
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = vertex_generate_response
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await basic_provider.generate(sample_messages)

        assert result.content == "2 + 2 = 4"
        assert result.provider == "google_vertex_gemini2"
        assert result.input_tokens == 12
        assert result.output_tokens == 8
        assert result.tokens_used == 20
        assert result.finish_reason == "STOP"
        assert result.cost > 0

    @pytest.mark.asyncio
    async def test_generate_unknown_model(self, basic_provider, sample_messages):
        with pytest.raises(ValueError, match="not supported"):
            await basic_provider.generate(
                sample_messages, model="gemini-99-nonexistent"
            )

    @pytest.mark.asyncio
    async def test_generate_http_error(self, basic_provider, sample_messages):
        import httpx

        error_response = MagicMock()
        error_response.status_code = 429
        error_response.text = "Rate limit exceeded"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "429 Rate Limit",
                request=MagicMock(),
                response=error_response,
            )
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await basic_provider.generate(sample_messages)

    @pytest.mark.asyncio
    async def test_generate_uses_config_model(self, configured_provider, sample_messages):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "ok"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 3,
            },
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await configured_provider.generate(sample_messages)

        # Should use the model from config
        assert result.model == "gemini-2.0-flash-001"


class TestStream:
    @pytest.mark.asyncio
    async def test_stream_success(self, basic_provider, sample_messages):
        """Verify that text chunks from multiple SSE payloads are yielded."""
        sse_events = [
            json.dumps({
                "candidates": [{
                    "content": {"parts": [{"text": "Hello "}]},
                    "finishReason": None,
                }],
                "usageMetadata": {},
            }),
            json.dumps({
                "candidates": [{
                    "content": {"parts": [{"text": "World"}]},
                    "finishReason": "STOP",
                }],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                },
            }),
        ]
        raw_lines = [f"data: {evt}" for evt in sse_events]

        async def _mock_aiter_lines():
            for line in raw_lines:
                yield line

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = _mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.stream = MagicMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in basic_provider.stream(sample_messages):
                chunks.append(chunk)

        text_chunks = [c for c in chunks if c.content]
        assert any("Hello" in c.content for c in text_chunks)
        assert any("World" in c.content for c in text_chunks)

    @pytest.mark.asyncio
    async def test_stream_terminal_chunk_has_cost(
        self, basic_provider, sample_messages
    ):
        """The final StreamChunk (finishReason set) must carry cost and token counts."""
        final_payload = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "done"}]},
                "finishReason": "STOP",
            }],
            "usageMetadata": {
                "promptTokenCount": 20,
                "candidatesTokenCount": 10,
            },
        })

        async def _mock_aiter_lines():
            yield f"data: {final_payload}"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = _mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.stream = MagicMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in basic_provider.stream(sample_messages):
                chunks.append(chunk)

        terminal = next(c for c in chunks if c.finish_reason == "STOP")
        assert terminal.tokens_used == 30
        assert terminal.cost is not None and terminal.cost > 0

    @pytest.mark.asyncio
    async def test_stream_unknown_model(self, basic_provider, sample_messages):
        with pytest.raises(ValueError, match="not supported"):
            async for _ in basic_provider.stream(
                sample_messages, model="gemini-fake-model"
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_malformed_sse_line_skipped(
        self, basic_provider, sample_messages
    ):
        """Garbled JSON in a data: line must not raise — it is silently skipped."""
        async def _mock_aiter_lines():
            yield "data: {INVALID JSON{{{"
            yield "data: " + json.dumps({
                "candidates": [{
                    "content": {"parts": [{"text": "ok"}]},
                    "finishReason": "STOP",
                }],
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
            })

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = _mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.stream = MagicMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            chunks = []
            async for chunk in basic_provider.stream(sample_messages):
                chunks.append(chunk)

        # The valid payload should still produce chunks
        assert len(chunks) > 0


class TestMultimodalInput:
    @pytest.mark.asyncio
    async def test_multimodal_image_parts_pass_through(
        self, basic_provider
    ):
        """Inline image parts (already in Vertex format) must be included in contents."""
        messages = [
            {
                "role": "user",
                # Pre-built list of Vertex-compatible parts
                "content": [
                    {"text": "What does this image show?"},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": "base64encodeddata==",
                        }
                    },
                ],
            }
        ]

        contents, system = basic_provider._format_contents(messages)
        assert len(contents) == 1
        parts = contents[0]["parts"]
        # Both the text and the inline_data parts must be present
        assert any("text" in p for p in parts)
        assert any("inline_data" in p for p in parts)


class TestGetAccessToken:
    @pytest.mark.asyncio
    async def test_static_token_returned_directly(self, basic_provider):
        token = await basic_provider._get_access_token()
        assert token == "fake-token-abc123"

    @pytest.mark.asyncio
    async def test_cached_valid_token_reused(self):
        provider = GoogleVertexGemini2Provider(
            project_id="proj", location="us-central1"
        )
        # Pre-populate with a valid cached token
        provider._cached_token = _CachedToken(
            token="cached-token",
            expires_at=time.monotonic() + 3_600,
        )
        token = await provider._get_access_token()
        assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_missing_google_auth_raises_runtime_error(self):
        """ImportError from google.auth must be re-raised as RuntimeError."""
        provider = GoogleVertexGemini2Provider(
            project_id="proj", location="us-central1"
        )
        with patch.dict("sys.modules", {"google.auth": None}):
            with pytest.raises(RuntimeError, match="google-auth is required"):
                await provider._get_access_token()
