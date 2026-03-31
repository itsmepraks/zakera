"""
Groq Whisper Audio Transcription Provider
=========================================
Provides ultra-fast speech-to-text transcription using Groq's hosted
Whisper-large-v3 model. Integrates with the existing provider registry
and follows the same interface conventions as other zakera providers.

Supported audio formats: wav, mp3, m4a, webm, ogg, flac
Max file size per request: 25 MB (auto-chunked above this threshold)
"""

from __future__ import annotations

import io
import logging
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GROQ_WHISPER_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_WHISPER_MODEL = "whisper-large-v3"
GROQ_WHISPER_TURBO_MODEL = "whisper-large-v3-turbo"  # ~3× faster, slight quality trade-off
MAX_CHUNK_BYTES = 24 * 1024 * 1024  # 24 MB (leaving 1 MB headroom)
DEFAULT_TIMEOUT_SECONDS = 60
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 1.5  # exponential back-off multiplier

SUPPORTED_FORMATS = frozenset(
    ["audio/wav", "audio/mpeg", "audio/mp4", "audio/webm", "audio/ogg",
     "audio/flac", "audio/x-wav", "audio/x-m4a"]
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class TranscriptionSegment:
    """A time-aligned segment from word-level transcription."""
    id: int
    text: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    """Full result returned by GroqWhisperProvider.transcribe()."""
    text: str
    language: str
    duration_seconds: float
    segments: List[TranscriptionSegment] = field(default_factory=list)
    model_used: str = GROQ_WHISPER_MODEL
    processing_time_ms: float = 0.0
    # Token / cost accounting (mirrors other provider result shapes)
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def words_per_minute(self) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return (self.word_count / self.duration_seconds) * 60


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------
class GroqWhisperProvider:
    """
    Audio transcription provider backed by Groq's Whisper API.

    Usage::

        provider = GroqWhisperProvider(api_key="gsk_...")
        result = await provider.transcribe(audio_bytes, filename="recording.mp3")
        print(result.text)

    Configuration can also be driven entirely from environment variables:
    - GROQ_API_KEY   : Groq API key (required)
    - GROQ_WHISPER_MODEL : override default model (optional)
    - GROQ_WHISPER_LANGUAGE : ISO-639-1 hint e.g. "en" (optional)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = GROQ_WHISPER_MODEL,
        language: Optional[str] = None,
        temperature: float = 0.0,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        use_turbo: bool = False,
    ) -> None:
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Groq API key is required. Set GROQ_API_KEY env var or pass api_key."
            )

        self.model = GROQ_WHISPER_TURBO_MODEL if use_turbo else model
        self.language = language or os.environ.get("GROQ_WHISPER_LANGUAGE")
        self.temperature = temperature
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def transcribe(
        self,
        audio: bytes | BinaryIO,
        filename: str = "audio.wav",
        content_type: Optional[str] = None,
        response_format: str = "verbose_json",
        timestamp_granularities: Optional[List[str]] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio bytes or a file-like object.

        Args:
            audio: Raw audio bytes or a BinaryIO stream.
            filename: Original filename (used to infer MIME type).
            content_type: Explicit MIME type; inferred from filename if omitted.
            response_format: 'json', 'verbose_json', 'text', 'srt', 'vtt'.
            timestamp_granularities: ['word'] and/or ['segment'] for timestamps.

        Returns:
            TranscriptionResult with text, language, timing metadata.
        """
        if isinstance(audio, (bytes, bytearray)):
            audio_bytes = bytes(audio)
        else:
            audio_bytes = audio.read()

        if content_type is None:
            content_type = self._infer_content_type(filename)

        # Auto-chunk large files
        if len(audio_bytes) > MAX_CHUNK_BYTES:
            return await self._transcribe_chunked(audio_bytes, filename, content_type)

        return await self._transcribe_single(
            audio_bytes,
            filename,
            content_type,
            response_format,
            timestamp_granularities or ["segment"],
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "GroqWhisperProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _transcribe_single(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
        response_format: str,
        timestamp_granularities: List[str],
    ) -> TranscriptionResult:
        """Send a single-chunk transcription request with retry logic."""
        t_start = time.monotonic()
        last_error: Optional[Exception] = None

        for attempt in range(RETRY_ATTEMPTS):
            try:
                files = {
                    "file": (filename, io.BytesIO(audio_bytes), content_type),
                }
                data: Dict[str, Any] = {
                    "model": self.model,
                    "response_format": response_format,
                    "temperature": self.temperature,
                }
                if self.language:
                    data["language"] = self.language
                if timestamp_granularities:
                    data["timestamp_granularities[]"] = timestamp_granularities

                response = await self._client.post(
                    GROQ_WHISPER_API_URL, files=files, data=data
                )
                response.raise_for_status()
                processing_ms = (time.monotonic() - t_start) * 1000
                return self._parse_response(response.json(), processing_ms)

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429:  # rate limit
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Groq Whisper rate-limited (attempt %d/%d), waiting %.1fs",
                        attempt + 1, RETRY_ATTEMPTS, wait,
                    )
                    time.sleep(wait)
                    last_error = exc
                elif status >= 500:
                    last_error = exc
                    continue
                else:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "Network error on attempt %d: %s", attempt + 1, exc
                )

        raise RuntimeError(
            f"Groq Whisper transcription failed after {RETRY_ATTEMPTS} attempts."
        ) from last_error

    async def _transcribe_chunked(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> TranscriptionResult:
        """
        Split oversized audio into MAX_CHUNK_BYTES pieces and concatenate results.
        NOTE: This is a best-effort chunking by byte size. For production use,
        split on silence boundaries using a library such as pydub.
        """
        num_chunks = math.ceil(len(audio_bytes) / MAX_CHUNK_BYTES)
        logger.info(
            "Audio size %d bytes exceeds limit; splitting into %d chunks.",
            len(audio_bytes), num_chunks,
        )

        all_texts: List[str] = []
        total_duration = 0.0
        all_segments: List[TranscriptionSegment] = []
        seg_id_offset = 0
        time_offset = 0.0
        detected_language = "en"
        total_processing_ms = 0.0

        for i in range(num_chunks):
            chunk = audio_bytes[i * MAX_CHUNK_BYTES:(i + 1) * MAX_CHUNK_BYTES]
            suffix = Path(filename).suffix or ".wav"
            chunk_name = f"chunk_{i:03d}{suffix}"

            result = await self._transcribe_single(
                chunk, chunk_name, content_type, "verbose_json", ["segment"]
            )
            all_texts.append(result.text)
            total_duration += result.duration_seconds
            total_processing_ms += result.processing_time_ms
            detected_language = result.language

            for seg in result.segments:
                all_segments.append(
                    TranscriptionSegment(
                        id=seg.id + seg_id_offset,
                        text=seg.text,
                        start=seg.start + time_offset,
                        end=seg.end + time_offset,
                        confidence=seg.confidence,
                    )
                )
            if result.segments:
                time_offset += result.segments[-1].end
            seg_id_offset += len(result.segments)

        return TranscriptionResult(
            text=" ".join(all_texts),
            language=detected_language,
            duration_seconds=total_duration,
            segments=all_segments,
            model_used=self.model,
            processing_time_ms=total_processing_ms,
        )

    @staticmethod
    def _parse_response(data: Dict[str, Any], processing_ms: float) -> TranscriptionResult:
        """Convert the Groq API JSON response into a TranscriptionResult."""
        segments: List[TranscriptionSegment] = []
        for seg in data.get("segments", []):
            segments.append(
                TranscriptionSegment(
                    id=seg.get("id", 0),
                    text=seg.get("text", ""),
                    start=float(seg.get("start", 0)),
                    end=float(seg.get("end", 0)),
                    confidence=float(seg.get("avg_logprob", 0) + 1),  # logprob → 0-1 approx
                )
            )

        return TranscriptionResult(
            text=data.get("text", "").strip(),
            language=data.get("language", "unknown"),
            duration_seconds=float(data.get("duration", 0)),
            segments=segments,
            model_used=data.get("model", GROQ_WHISPER_MODEL),
            processing_time_ms=processing_ms,
        )

    @staticmethod
    def _infer_content_type(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        mapping = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/x-m4a",
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }
        return mapping.get(ext, "audio/wav")


# ---------------------------------------------------------------------------
# Provider registry helper (mirrors pattern used by other providers)
# ---------------------------------------------------------------------------
def create_groq_whisper_provider(
    config: Optional[Dict[str, Any]] = None,
) -> GroqWhisperProvider:
    """
    Factory function that creates a GroqWhisperProvider from a config dict
    or falls back to environment variables.

    Expected config keys:
        api_key, model, language, temperature, timeout, use_turbo
    """
    cfg = config or {}
    return GroqWhisperProvider(
        api_key=cfg.get("api_key"),
        model=cfg.get("model", GROQ_WHISPER_MODEL),
        language=cfg.get("language"),
        temperature=float(cfg.get("temperature", 0.0)),
        timeout=float(cfg.get("timeout", DEFAULT_TIMEOUT_SECONDS)),
        use_turbo=bool(cfg.get("use_turbo", False)),
    )
