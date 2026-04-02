"""Google Vertex AI – Gemini 2.0 Flash provider.

This module integrates Google's Vertex AI Gemini 2.0 Flash models into
Zakera's provider ecosystem.  It follows exactly the same interface
contract as every other provider in this package:

* :meth:`generate`  – single-turn, returns :class:`~.providers.ModelResponse`
* :meth:`stream`    – streaming, yields :class:`~.providers.StreamChunk`

Authentication
--------------
The provider accepts an explicit ``access_token`` **or** falls back to
Application Default Credentials (ADC) via ``google-auth``.  In both
cases the token is cached for ``CREDENTIAL_REFRESH_MARGIN_SECONDS``
before expiry to avoid per-request round-trips.

Usage example::

    from src.model.providers_google_vertex_gemini2 import (
        GoogleVertexGemini2Provider,
    )
    from src.model.config import ModelConfig

    provider = GoogleVertexGemini2Provider(
        project_id="my-gcp-project",
        location="us-central1",
        config=ModelConfig(model="gemini-2.0-flash-001", temperature=0.7),
    )
    response = await provider.generate([
        {"role": "user", "content": "Explain quantum entanglement briefly."}
    ])
    print(response.content)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx
from opentelemetry import trace

from .config import ModelConfig
from .providers import ModelProvider, ModelResponse, StreamChunk

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# How many seconds before token expiry we proactively refresh.
CREDENTIAL_REFRESH_MARGIN_SECONDS = 60


@dataclass
class _CachedToken:
    """Simple container for an OAuth2 bearer token with expiry tracking."""

    token: str
    expires_at: float  # Unix timestamp

    def is_valid(self) -> bool:
        """Return True when the token has more than the refresh margin left."""
        return time.monotonic() < self.expires_at - CREDENTIAL_REFRESH_MARGIN_SECONDS


class GoogleVertexGemini2Provider(ModelProvider):
    """Vertex AI Gemini 2.0 Flash model provider.

    Supported models
    ----------------
    .. list-table::
       :header-rows: 1

       * - Model ID
         - Max input tokens
         - Max output tokens
         - Tier
       * - ``gemini-2.0-flash-001``
         - 1 048 576
         - 8 192
         - fast
       * - ``gemini-2.0-flash-lite-001``
         - 1 048 576
         - 8 192
         - fast

    Parameters
    ----------
    project_id:
        GCP project that hosts the Vertex AI endpoint.
    location:
        GCP region, e.g. ``"us-central1"``.
    access_token:
        Optional static bearer token.  When omitted the provider uses
        Application Default Credentials (requires ``google-auth``).
    config:
        Shared :class:`~.config.ModelConfig` instance.
    """

    SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
        "gemini-2.0-flash-001": {
            "max_tokens": 1_048_576,
            "max_output_tokens": 8_192,
            "cost_per_1k_input": 0.000_075,   # $0.075 per 1M input tokens
            "cost_per_1k_output": 0.000_300,  # $0.30  per 1M output tokens
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_audio": True,
            "tier": "fast",
        },
        "gemini-2.0-flash-lite-001": {
            "max_tokens": 1_048_576,
            "max_output_tokens": 8_192,
            "cost_per_1k_input": 0.000_037_5,
            "cost_per_1k_output": 0.000_150,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_audio": False,
            "tier": "fast",
        },
    }

    DEFAULT_MODEL = "gemini-2.0-flash-001"

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        access_token: Optional[str] = None,
        config: Optional[ModelConfig] = None,
    ) -> None:
        # ModelProvider expects (name, api_key, config); we pass the token as
        # api_key for compatibility with the base-class validation path.
        super().__init__("google_vertex_gemini2", access_token or "", config)
        self.project_id = project_id
        self.location = location
        self._static_token = access_token
        self._cached_token: Optional[_CachedToken] = None

        self._base_url = (
            f"https://{location}-aiplatform.googleapis.com/v1"
            f"/projects/{project_id}/locations/{location}"
            f"/publishers/google/models"
        )

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Return a valid OAuth2 bearer token, refreshing when necessary."""
        if self._static_token:
            return self._static_token

        if self._cached_token and self._cached_token.is_valid():
            return self._cached_token.token

        try:
            import google.auth  # type: ignore
            import google.auth.transport.requests  # type: ignore

            credentials, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)

            token = credentials.token
            # google-auth tokens are valid for ~1 hour
            expiry_ts = time.monotonic() + 3_600.0
            self._cached_token = _CachedToken(token=token, expires_at=expiry_ts)
            logger.debug("Vertex AI: refreshed ADC access token")
            return token

        except ImportError as exc:
            raise RuntimeError(
                "google-auth is required for ADC authentication. "
                "Install it with: pip install google-auth"
            ) from exc
        except Exception as exc:
            logger.error("Failed to obtain Vertex AI credentials: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _headers(self) -> Dict[str, str]:
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _format_contents(
        self, messages: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Convert OpenAI-style messages to Vertex AI ``contents`` format.

        Returns a ``(contents, system_instruction)`` tuple.  The system
        instruction is returned separately because Vertex AI places it
        outside the ``contents`` array.
        """
        contents: List[Dict[str, Any]] = []
        system_instruction: Optional[str] = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content
                continue

            vertex_role = "user" if role == "user" else "model"

            # Support both plain strings and pre-built multimodal part lists.
            if isinstance(content, str):
                parts = [{"text": content}]
            elif isinstance(content, list):
                # Caller already built Vertex-compatible part dicts.
                parts = content
            else:
                parts = [{"text": str(content)}]

            # Merge consecutive turns from the same role to satisfy the
            # "alternating user/model" requirement of the Gemini API.
            if contents and contents[-1]["role"] == vertex_role:
                contents[-1]["parts"].extend(parts)
            else:
                contents.append({"role": vertex_role, "parts": parts})

        return contents, system_instruction

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        max_output_tokens: int,
        temperature: float,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Assemble the Vertex AI generateContent request body."""
        contents, system_instruction = self._format_contents(messages)

        generation_config: Dict[str, Any] = {
            "maxOutputTokens": max_output_tokens,
            "temperature": temperature,
        }
        if "top_p" in kwargs:
            generation_config["topP"] = kwargs["top_p"]
        if "top_k" in kwargs:
            generation_config["topK"] = kwargs["top_k"]
        if "stop_sequences" in kwargs:
            generation_config["stopSequences"] = kwargs["stop_sequences"]
        if "candidate_count" in kwargs:
            generation_config["candidateCount"] = kwargs["candidate_count"]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        if "safety_settings" in kwargs:
            payload["safetySettings"] = kwargs["safety_settings"]
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]

        return payload

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        info = self.SUPPORTED_MODELS[model]
        return (
            (input_tokens / 1_000) * info["cost_per_1k_input"]
            + (output_tokens / 1_000) * info["cost_per_1k_output"]
        )

    def _extract_text_from_candidates(
        self, candidates: List[Dict[str, Any]]
    ) -> Tuple[str, Optional[str]]:
        """Pull the generated text and finish reason from a candidates list."""
        text = ""
        finish_reason: Optional[str] = None
        for candidate in candidates:
            for part in candidate.get("content", {}).get("parts", []):
                text += part.get("text", "")
            finish_reason = candidate.get("finishReason") or finish_reason
        return text, finish_reason

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @tracer.start_as_current_span("vertex_gemini2_generate")
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a single response from Gemini 2.0 Flash via Vertex AI.

        Parameters
        ----------
        messages:
            Conversation history in OpenAI format
            (``{"role": "user"|"assistant"|"system", "content": ...}``).
        model:
            Model ID; defaults to ``gemini-2.0-flash-001``.
        temperature:
            Sampling temperature ``[0.0, 2.0]``.
        max_tokens:
            Maximum output tokens.
        **kwargs:
            Extra Vertex AI parameters: ``top_p``, ``top_k``,
            ``stop_sequences``, ``safety_settings``, ``tools``.

        Returns
        -------
        ModelResponse
            Provider-agnostic response object with ``content``,
            ``tokens_used``, ``cost``, and ``raw_response``.
        """
        model = model or self.config.model or self.DEFAULT_MODEL
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model '{model}' not supported by GoogleVertexGemini2Provider")

        temperature = temperature if temperature is not None else self.config.temperature
        model_info = self.SUPPORTED_MODELS[model]
        max_output_tokens = min(
            max_tokens or self.config.max_tokens or 4_096,
            model_info["max_output_tokens"],
        )

        payload = self._build_payload(
            messages, max_output_tokens, temperature, stream=False, **kwargs
        )
        url = f"{self._base_url}/{model}:generateContent"
        headers = await self._headers()

        logger.debug(
            "Vertex Gemini2 generate — model=%s max_tokens=%d",
            model,
            max_output_tokens,
        )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            candidates = data.get("candidates", [])
            text, finish_reason = self._extract_text_from_candidates(candidates)

            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            logger.info(
                "Vertex Gemini2 OK — model=%s tokens=%d cost=$%.6f",
                model,
                input_tokens + output_tokens,
                cost,
            )

            return ModelResponse(
                content=text,
                model=model,
                provider=self.name,
                tokens_used=input_tokens + output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                finish_reason=finish_reason,
                raw_response=data,
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Vertex Gemini2 HTTP error %d — %s",
                exc.response.status_code,
                exc.response.text[:400],
            )
            raise
        except Exception as exc:
            logger.error("GoogleVertexGemini2Provider.generate error: %s", exc)
            raise

    @tracer.start_as_current_span("vertex_gemini2_stream")
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a Gemini 2.0 Flash response via Vertex AI server-sent events.

        Each SSE payload from ``streamGenerateContent`` carries a partial
        ``GenerateContentResponse``.  This generator unpacks those payloads
        and yields one :class:`~.providers.StreamChunk` per candidate
        content part, with a final cost-bearing chunk when the
        ``finishReason`` is set.

        Yields
        ------
        StreamChunk
            Incremental text content with optional ``tokens_used`` and
            ``cost`` on the terminal chunk.
        """
        model = model or self.config.model or self.DEFAULT_MODEL
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model '{model}' not supported by GoogleVertexGemini2Provider")

        temperature = temperature if temperature is not None else self.config.temperature
        model_info = self.SUPPORTED_MODELS[model]
        max_output_tokens = min(
            max_tokens or self.config.max_tokens or 4_096,
            model_info["max_output_tokens"],
        )

        payload = self._build_payload(
            messages, max_output_tokens, temperature, stream=True, **kwargs
        )
        url = f"{self._base_url}/{model}:streamGenerateContent?alt=sse"
        headers = await self._headers()

        logger.debug(
            "Vertex Gemini2 stream — model=%s max_tokens=%d",
            model,
            max_output_tokens,
        )

        input_tokens = 0
        output_tokens = 0

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", url, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:].strip()
                        if not data_str or data_str == "[DONE]":
                            continue

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(
                                "Vertex Gemini2: could not parse SSE payload: %s",
                                data_str[:200],
                            )
                            continue

                        candidates = data.get("candidates", [])
                        for candidate in candidates:
                            parts = (
                                candidate.get("content", {}).get("parts", [])
                            )
                            finish_reason = candidate.get("finishReason")

                            for part in parts:
                                chunk_text = part.get("text", "")
                                if chunk_text:
                                    yield StreamChunk(
                                        content=chunk_text,
                                        model=model,
                                        provider=self.name,
                                        finish_reason=None,
                                    )

                            if finish_reason:
                                # Final usage is in the last payload
                                usage = data.get("usageMetadata", {})
                                input_tokens = usage.get("promptTokenCount", 0)
                                output_tokens = usage.get("candidatesTokenCount", 0)
                                cost = self._calculate_cost(
                                    model, input_tokens, output_tokens
                                )
                                yield StreamChunk(
                                    content="",
                                    model=model,
                                    provider=self.name,
                                    finish_reason=finish_reason,
                                    tokens_used=input_tokens + output_tokens,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    cost=cost,
                                )

            logger.info(
                "Vertex Gemini2 stream done — model=%s tokens=%d",
                model,
                input_tokens + output_tokens,
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Vertex Gemini2 stream HTTP error %d",
                exc.response.status_code,
            )
            raise
        except Exception as exc:
            logger.error("GoogleVertexGemini2Provider.stream error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_supported_models(self) -> Dict[str, Dict[str, Any]]:
        """Return the full model registry with capability metadata."""
        return self.SUPPORTED_MODELS

    def get_model_ids(self) -> List[str]:
        """Return a flat list of supported model identifiers."""
        return list(self.SUPPORTED_MODELS.keys())

    def validate_config(self) -> bool:
        """Return True if the provider is correctly configured.

        Checks that ``project_id`` and ``location`` are non-empty and,
        when a static access token is used, that it is non-empty too.
        """
        if not self.project_id:
            logger.error("Vertex AI: project_id is not set")
            return False
        if not self.location:
            logger.error("Vertex AI: location is not set")
            return False
        if self._static_token is not None and not self._static_token:
            logger.error("Vertex AI: access_token is empty")
            return False
        if self.config.model and self.config.model not in self.SUPPORTED_MODELS:
            logger.error(
                "Vertex AI: unsupported model in config: %s", self.config.model
            )
            return False
        return True
