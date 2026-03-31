"""
POST /transcribe  –  Audio-to-text endpoint
============================================
Accepts a multipart/form-data upload of an audio file and returns a
structured JSON transcription using the GroqWhisperProvider.

Request (multipart/form-data):
  file          : audio file (wav | mp3 | m4a | webm | ogg | flac)
  language      : ISO-639-1 hint, e.g. "en" (optional)
  use_turbo     : bool – use faster whisper-large-v3-turbo model (optional)
  timestamp_granularities : "segment" | "word" (optional, default "segment")

Response 200:
  {
    "text": "...",
    "language": "en",
    "duration_seconds": 12.34,
    "processing_time_ms": 789.0,
    "word_count": 42,
    "words_per_minute": 204.0,
    "segments": [{"id": 0, "text": "...", "start": 0.0, "end": 2.4, "confidence": 0.97}]
  }
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.api.auth import get_current_user
from src.model.providers_groq_whisper import (
    GroqWhisperProvider,
    TranscriptionResult,
    create_groq_whisper_provider,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcribe", tags=["transcription"])

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class SegmentOut(BaseModel):
    id: int
    text: str
    start: float
    end: float
    confidence: float


class TranscriptionResponse(BaseModel):
    text: str
    language: str
    duration_seconds: float
    processing_time_ms: float
    word_count: int
    words_per_minute: float
    model_used: str
    segments: List[SegmentOut] = []


# ---------------------------------------------------------------------------
# Allowed MIME types / extensions
# ---------------------------------------------------------------------------
ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "application/octet-stream",  # some browsers send this for .webm
}

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB hard cap at API layer


# ---------------------------------------------------------------------------
# Dependency: provider instance
# ---------------------------------------------------------------------------
def get_whisper_provider() -> GroqWhisperProvider:
    """Dependency-inject a configured GroqWhisperProvider."""
    try:
        return create_groq_whisper_provider()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=TranscriptionResponse,
    summary="Transcribe audio to text",
    description=(
        "Upload an audio file (wav/mp3/m4a/webm/ogg/flac, max 100 MB) and receive "
        "a full transcription with language detection and optional timestamps."
    ),
    status_code=status.HTTP_200_OK,
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(
        None,
        description="ISO-639-1 language hint (e.g. 'en'). Auto-detected if omitted.",
    ),
    use_turbo: bool = Form(
        False,
        description="Use whisper-large-v3-turbo for ~3× faster processing.",
    ),
    timestamp_granularities: str = Form(
        "segment",
        description="Timestamp granularity: 'segment' or 'word'.",
    ),
    provider: GroqWhisperProvider = Depends(get_whisper_provider),
    current_user=Depends(get_current_user),
) -> TranscriptionResponse:
    # ---- Validate content type ----
    ct = (file.content_type or "").lower()
    if ct and ct not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type '{ct}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}.",
        )

    # ---- Read file ----
    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(audio_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({len(audio_bytes) // 1_048_576} MB). "
                   f"Maximum allowed is {MAX_UPLOAD_BYTES // 1_048_576} MB.",
        )

    # ---- Override provider settings from form params ----
    if language:
        provider.language = language
    provider.model = (
        "whisper-large-v3-turbo" if use_turbo else "whisper-large-v3"
    )

    granularities = (
        [timestamp_granularities]
        if timestamp_granularities in ("segment", "word")
        else ["segment"]
    )

    # ---- Call provider ----
    try:
        logger.info(
            "Transcribing audio: filename=%s size=%d bytes user=%s",
            file.filename,
            len(audio_bytes),
            getattr(current_user, "id", "unknown"),
        )
        result: TranscriptionResult = await provider.transcribe(
            audio=audio_bytes,
            filename=file.filename or "upload.wav",
            content_type=ct or None,
            timestamp_granularities=granularities,
        )
    except RuntimeError as exc:
        logger.exception("Transcription failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Transcription service error: {exc}",
        ) from exc
    finally:
        await provider.close()

    return TranscriptionResponse(
        text=result.text,
        language=result.language,
        duration_seconds=result.duration_seconds,
        processing_time_ms=result.processing_time_ms,
        word_count=result.word_count,
        words_per_minute=result.words_per_minute,
        model_used=result.model_used,
        segments=[
            SegmentOut(
                id=s.id,
                text=s.text,
                start=s.start,
                end=s.end,
                confidence=s.confidence,
            )
            for s in result.segments
        ],
    )
