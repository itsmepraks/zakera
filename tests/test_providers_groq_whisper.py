"""
Unit tests for src/model/providers_groq_whisper.py
====================================================
All external HTTP calls are mocked via unittest.mock.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from src.model.providers_groq_whisper import (
        GroqWhisperProvider,
        TranscriptionResult,
        TranscriptionSegment,
        MAX_CHUNK_BYTES,
        create_groq_whisper_provider,
        GROQ_WHISPER_MODEL,
        GROQ_WHISPER_TURBO_MODEL,
    )  # type: ignore
except ImportError:
    GroqWhisperProvider = None  # type: ignore
    TranscriptionResult = None  # type: ignore
    TranscriptionSegment = None  # type: ignore
    MAX_CHUNK_BYTES = 24 * 1024 * 1024
    create_groq_whisper_provider = None  # type: ignore
    GROQ_WHISPER_MODEL = "whisper-large-v3"
    GROQ_WHISPER_TURBO_MODEL = "whisper-large-v3-turbo"

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_verbose_json(
    text: str = "Hello world.",
    language: str = "en",
    duration: float = 3.5,
) -> dict:
    return {
        "text": text,
        "language": language,
        "duration": duration,
        "model": GROQ_WHISPER_MODEL,
        "segments": [
            {"id": 0, "text": text, "start": 0.0, "end": duration, "avg_logprob": -0.1}
        ],
    }


def _make_provider(**kwargs) -> "GroqWhisperProvider":
    if GroqWhisperProvider is None:
        pytest.skip("GroqWhisperProvider not importable")
    return GroqWhisperProvider(api_key="test-groq-key", **kwargs)


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestGroqWhisperProviderInit:
    def test_explicit_api_key(self):
        p = _make_provider()
        assert p.api_key == "test-groq-key"

    def test_env_var_fallback(self, monkeypatch):
        if GroqWhisperProvider is None:
            pytest.skip()
        monkeypatch.setenv("GROQ_API_KEY", "env-groq-key")
        p = GroqWhisperProvider()
        assert p.api_key == "env-groq-key"

    def test_missing_key_raises(self, monkeypatch):
        if GroqWhisperProvider is None:
            pytest.skip()
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key"):
            GroqWhisperProvider(api_key="")

    def test_default_model_is_standard(self):
        p = _make_provider()
        assert p.model == GROQ_WHISPER_MODEL

    def test_use_turbo_flag_switches_model(self):
        p = _make_provider(use_turbo=True)
        assert p.model == GROQ_WHISPER_TURBO_MODEL

    def test_language_env_var(self, monkeypatch):
        if GroqWhisperProvider is None:
            pytest.skip()
        monkeypatch.setenv("GROQ_WHISPER_LANGUAGE", "fr")
        p = GroqWhisperProvider(api_key="k")
        assert p.language == "fr"

    def test_factory_function_creates_provider(self, monkeypatch):
        if create_groq_whisper_provider is None:
            pytest.skip()
        monkeypatch.setenv("GROQ_API_KEY", "factory-key")
        p = create_groq_whisper_provider()
        assert isinstance(p, GroqWhisperProvider)


# ---------------------------------------------------------------------------
# transcribe() happy path
# ---------------------------------------------------------------------------


class TestTranscribeHappyPath:
    async def test_returns_transcription_result(self):
        p = _make_provider()
        fake_json = _fake_verbose_json("The quick brown fox.")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = fake_json

        with patch.object(p._client, "post", new=AsyncMock(return_value=mock_resp)):
            result = await p.transcribe(b"fake-audio-bytes", filename="test.wav")

        assert isinstance(result, TranscriptionResult)
        assert result.text == "The quick brown fox."
        assert result.language == "en"
        assert result.duration_seconds == pytest.approx(3.5)

    async def test_language_hint_forwarded(self):
        p = _make_provider(language="es")
        captured_data = {}

        async def fake_post(url, **kwargs):
            captured_data.update(kwargs.get("data", {}))
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = _fake_verbose_json(language="es")
            return resp

        with patch.object(p._client, "post", new=fake_post):
            await p.transcribe(b"audio", filename="speech.mp3")

        assert captured_data.get("language") == "es"

    async def test_file_object_accepted(self):
        p = _make_provider()
        audio_io = io.BytesIO(b"fake-audio")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _fake_verbose_json()

        with patch.object(p._client, "post", new=AsyncMock(return_value=mock_resp)):
            result = await p.transcribe(audio_io, filename="recording.ogg")

        assert result.text  # non-empty string

    async def test_segments_parsed(self):
        p = _make_provider()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _fake_verbose_json()

        with patch.object(p._client, "post", new=AsyncMock(return_value=mock_resp)):
            result = await p.transcribe(b"audio", filename="r.wav")

        assert len(result.segments) == 1
        assert isinstance(result.segments[0], TranscriptionSegment)
        assert result.segments[0].start == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# TranscriptionResult properties
# ---------------------------------------------------------------------------


class TestTranscriptionResultProperties:
    def _make_result(self, text: str, duration: float) -> "TranscriptionResult":
        if TranscriptionResult is None:
            pytest.skip()
        return TranscriptionResult(
            text=text,
            language="en",
            duration_seconds=duration,
        )

    def test_word_count(self):
        r = self._make_result("one two three four five", 10.0)
        assert r.word_count == 5

    def test_words_per_minute(self):
        # 60 words in 60 seconds = 60 wpm
        text = " ".join(["word"] * 60)
        r = self._make_result(text, 60.0)
        assert r.words_per_minute == pytest.approx(60.0)

    def test_zero_duration_wpm_is_zero(self):
        r = self._make_result("hello world", 0.0)
        assert r.words_per_minute == 0.0


# ---------------------------------------------------------------------------
# MIME type inference
# ---------------------------------------------------------------------------


class TestMimeTypeInference:
    def _infer(self, filename: str) -> str:
        if GroqWhisperProvider is None:
            pytest.skip()
        return GroqWhisperProvider._infer_content_type(filename)

    def test_wav(self):
        assert self._infer("audio.wav") == "audio/wav"

    def test_mp3(self):
        assert self._infer("song.mp3") == "audio/mpeg"

    def test_m4a(self):
        assert self._infer("voice.m4a") == "audio/x-m4a"

    def test_webm(self):
        assert self._infer("clip.webm") == "audio/webm"

    def test_ogg(self):
        assert self._infer("podcast.ogg") == "audio/ogg"

    def test_flac(self):
        assert self._infer("lossless.flac") == "audio/flac"

    def test_unknown_defaults_to_wav(self):
        assert self._infer("mystery.xyz") == "audio/wav"

    def test_uppercase_extension(self):
        assert self._infer("FILE.MP3") == "audio/mpeg"


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------


class TestRetryBehaviour:
    async def test_retries_on_429(self):
        import httpx

        p = _make_provider()
        call_count = 0

        async def flaky_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                bad = MagicMock(spec=httpx.Response)
                bad.status_code = 429
                bad.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "429", request=MagicMock(), response=bad
                )
                return bad
            good = MagicMock()
            good.raise_for_status = MagicMock()
            good.json.return_value = _fake_verbose_json("retry success")
            return good

        with patch.object(p._client, "post", new=flaky_post), patch("time.sleep"):
            result = await p.transcribe(b"audio", filename="r.wav")

        assert call_count == 3
        assert "retry success" in result.text

    async def test_no_retry_on_400(self):
        """Client errors (4xx except 429) should raise immediately."""
        import httpx

        p = _make_provider()

        async def bad_request(url, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 400
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "400", request=MagicMock(), response=resp
            )
            return resp

        with patch.object(p._client, "post", new=bad_request):
            with pytest.raises(Exception):
                await p.transcribe(b"audio", filename="r.wav")


# ---------------------------------------------------------------------------
# Large-file chunking
# ---------------------------------------------------------------------------


class TestChunking:
    async def test_large_file_triggers_chunked_path(self, monkeypatch):
        """Files exceeding MAX_CHUNK_BYTES should call _transcribe_chunked."""
        p = _make_provider()
        oversized = b"x" * (MAX_CHUNK_BYTES + 1)
        chunked_called = []

        async def mock_chunked(audio_bytes, filename, content_type):
            chunked_called.append(True)
            return TranscriptionResult(
                text="chunked result",
                language="en",
                duration_seconds=60.0,
            )

        monkeypatch.setattr(p, "_transcribe_chunked", mock_chunked)

        result = await p.transcribe(oversized, filename="big.wav")

        assert chunked_called, "_transcribe_chunked was not called for oversized file"
        assert result.text == "chunked result"

    async def test_small_file_does_not_chunk(self, monkeypatch):
        p = _make_provider()
        chunked_called = []

        async def mock_chunked(*args, **kwargs):
            chunked_called.append(True)
            return TranscriptionResult(text="chunked", language="en", duration_seconds=1.0)

        monkeypatch.setattr(p, "_transcribe_chunked", mock_chunked)

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = _fake_verbose_json()

        with patch.object(p._client, "post", new=AsyncMock(return_value=mock_resp)):
            await p.transcribe(b"small-audio", filename="small.wav")

        assert not chunked_called, "_transcribe_chunked should NOT be called for small files"


# ---------------------------------------------------------------------------
# Async context manager
# ---------------------------------------------------------------------------


class TestAsyncContextManager:
    async def test_close_called_on_exit(self):
        p = _make_provider()
        close_called = []

        async def mock_close():
            close_called.append(True)

        p.close = mock_close

        async with p:
            pass

        assert close_called, "close() should be called on __aexit__"
