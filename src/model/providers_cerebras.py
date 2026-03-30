"""Cerebras AI Provider - Ultra-fast Llama inference.

Cerebras provides industry-leading inference speeds using their
CS-3 wafer-scale chips, delivering thousands of tokens per second
for Llama-based models.

Supported Models:
- llama3.1-8b:  8B parameter Llama 3.1, fastest option
- llama3.1-70b: 70B parameter Llama 3.1, high quality
- llama3.3-70b: 70B parameter Llama 3.3, latest and best quality

Documentation: https://inference-docs.cerebras.ai/
API Base:       https://api.cerebras.ai/v1
"""

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from .providers import BaseProvider, ModelResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class CerebrasConfig(BaseModel):
    """Cerebras provider configuration."""

    api_key: str = Field(..., description="Cerebras Cloud API key")
    base_url: str = Field(
        default="https://api.cerebras.ai/v1",
        description="Cerebras API base URL (OpenAI-compatible)",
    )
    default_model: str = Field(
        default="llama3.3-70b",
        description="Default model to use",
    )
    timeout: int = Field(
        default=60,
        ge=1,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts on transient errors",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.5,
        description="Sampling temperature (0.0–1.5 for Cerebras)",
    )
    max_tokens: int = Field(
        default=8192,
        gt=0,
        description="Maximum tokens to generate",
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability mass",
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility",
    )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class CerebrasProvider(BaseProvider):
    """Cerebras AI provider for ultra-fast Llama inference.

    Cerebras exposes an OpenAI-compatible chat-completions endpoint, so
    this provider uses ``httpx`` directly (same as GroqProvider) rather
    than the vendor SDK — making the dependency optional and keeping
    cold-start times minimal.

    If ``cerebras-cloud-sdk`` is installed it is used for token counting;
    otherwise a character-based heuristic is used as a fallback.

    Usage::

        config = CerebrasConfig(api_key=os.environ["CEREBRAS_API_KEY"])
        provider = CerebrasProvider(config)
        response = await provider.generate(messages)
        print(response.text)
    """

    SUPPORTED_MODELS: List[str] = [
        "llama3.1-8b",
        "llama3.1-70b",
        "llama3.3-70b",
    ]

    # Cerebras model metadata — context windows from official docs
    MODEL_SPECS: Dict[str, Dict[str, Any]] = {
        "llama3.1-8b": {
            "name": "Llama 3.1 8B",
            "description": "Compact 8B model — lowest latency, ideal for real-time chat",
            "context_window": 128_000,
            "max_completion_tokens": 16_384,
            "speed_tokens_per_sec": 2_100,  # approximate
            "quality": "good",
            "best_for": "real-time chat, quick Q&A, high-throughput pipelines",
        },
        "llama3.1-70b": {
            "name": "Llama 3.1 70B",
            "description": "70B model — excellent balance of speed and quality",
            "context_window": 128_000,
            "max_completion_tokens": 16_384,
            "speed_tokens_per_sec": 450,
            "quality": "high",
            "best_for": "complex reasoning, code generation, long-form content",
        },
        "llama3.3-70b": {
            "name": "Llama 3.3 70B",
            "description": "Latest 70B model — best quality on Cerebras hardware",
            "context_window": 128_000,
            "max_completion_tokens": 16_384,
            "speed_tokens_per_sec": 450,
            "quality": "highest",
            "best_for": "production workloads requiring top quality and fast speed",
        },
    }

    def __init__(self, config: CerebrasConfig) -> None:
        """Initialise the Cerebras provider.

        Args:
            config: A validated :class:`CerebrasConfig` instance.

        Raises:
            ValueError: If the requested model is not in :attr:`SUPPORTED_MODELS`.
        """
        self.config = config

        if config.default_model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Model '{config.default_model}' is not supported by CerebrasProvider. "
                f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
            )

        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "zakera-ai-agent/0.5.0",
            },
            timeout=config.timeout,
        )

        # Try to import the optional Cerebras Cloud SDK for exact token counts.
        self._sdk_client: Any = None
        try:
            from cerebras.cloud.sdk import Cerebras as CerebrasSDK  # type: ignore
            self._sdk_client = CerebrasSDK(api_key=config.api_key)
            logger.info("cerebras-cloud-sdk detected — using SDK for token counting")
        except ImportError:
            logger.debug(
                "cerebras-cloud-sdk not installed; "
                "falling back to heuristic token counting"
            )

        logger.info(
            "Initialised CerebrasProvider | model=%s | base_url=%s",
            config.default_model,
            config.base_url,
        )

    # ------------------------------------------------------------------
    # Public API — generate (non-streaming)
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a chat completion.

        Args:
            messages:    List of ``{"role": ..., "content": ...}`` dicts.
            model:       Override the default model.
            stream:      If ``True``, delegates to :meth:`_generate_stream`.
            **kwargs:    Optional overrides: ``temperature``, ``max_tokens``,
                         ``top_p``, ``seed``, ``stop``, ``frequency_penalty``,
                         ``presence_penalty``.

        Returns:
            :class:`~src.model.providers.ModelResponse`

        Raises:
            ValueError:         If the requested model is unsupported.
            httpx.HTTPError:    On unrecoverable HTTP failures.
            Exception:          After all retries are exhausted.
        """
        model = model or self.config.default_model
        self._validate_model(model)

        if stream:
            # Streaming path — caller must iterate the returned async generator
            return await self._generate_stream(messages, model, **kwargs)  # type: ignore[return-value]

        payload = self._build_payload(model, messages, stream=False, **kwargs)

        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return self._parse_response(data, model)

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code

                if status == 401:
                    logger.error("Cerebras auth failed — check CEREBRAS_API_KEY")
                    raise
                if status == 400:
                    body = exc.response.text
                    logger.error("Cerebras bad request: %s", body)
                    raise
                if status == 422:
                    body = exc.response.text
                    logger.error("Cerebras unprocessable entity: %s", body)
                    raise

                wait = self._backoff(attempt, status)
                logger.warning(
                    "Cerebras HTTP %s on attempt %d/%d — retrying in %.1fs",
                    status, attempt + 1, self.config.max_retries, wait,
                )
                await asyncio.sleep(wait)

            except httpx.RequestError as exc:
                last_error = exc
                wait = self._backoff(attempt)
                logger.warning(
                    "Cerebras network error on attempt %d/%d — retrying in %.1fs: %s",
                    attempt + 1, self.config.max_retries, wait, exc,
                )
                await asyncio.sleep(wait)

            except Exception as exc:
                last_error = exc
                wait = self._backoff(attempt)
                logger.warning(
                    "Cerebras unexpected error on attempt %d/%d — retrying in %.1fs: %s",
                    attempt + 1, self.config.max_retries, wait, exc,
                )
                await asyncio.sleep(wait)

        msg = f"CerebrasProvider.generate failed after {self.config.max_retries} attempts"
        logger.error("%s: %s", msg, last_error)
        raise Exception(f"{msg}: {last_error}")

    # ------------------------------------------------------------------
    # Public API — stream_generate
    # ------------------------------------------------------------------

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion, yielding text chunks as they arrive.

        Args:
            messages: List of ``{"role": ..., "content": ...}`` dicts.
            model:    Override the default model.
            **kwargs: Same optional overrides as :meth:`generate`.

        Yields:
            Incremental text chunks (``str``).

        Raises:
            ValueError:      If the requested model is unsupported.
            httpx.HTTPError: On HTTP failures.
        """
        model = model or self.config.default_model
        self._validate_model(model)

        payload = self._build_payload(model, messages, stream=True, **kwargs)

        try:
            async with self.client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.debug("Cerebras SSE: skipping unparseable line: %r", data_str)
                        continue

                    choices = chunk.get("choices") or []
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    text = delta.get("content")
                    if text:
                        yield text

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Cerebras streaming HTTP %s: %s",
                exc.response.status_code, exc.response.text,
            )
            raise
        except Exception as exc:
            logger.error("Cerebras streaming error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Private helpers — also called by _generate_stream alias above
    # ------------------------------------------------------------------

    async def _generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Internal alias so :meth:`generate(stream=True)` works correctly."""
        async for chunk in self.stream_generate(messages, model=model, **kwargs):
            yield chunk

    def _build_payload(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Construct the JSON payload for /chat/completions."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": stream,
        }

        # Optional parameters — only include if explicitly provided
        if self.config.seed is not None:
            payload["seed"] = kwargs.get("seed", self.config.seed)
        elif "seed" in kwargs:
            payload["seed"] = kwargs["seed"]

        for opt in ("stop", "frequency_penalty", "presence_penalty"):
            if opt in kwargs:
                payload[opt] = kwargs[opt]

        return payload

    def _parse_response(self, data: Dict[str, Any], model: str) -> ModelResponse:
        """Parse a raw API response dict into a :class:`ModelResponse`."""
        choice = data["choices"][0]
        usage  = data.get("usage") or {}

        return ModelResponse(
            text=choice["message"]["content"],
            provider="cerebras",
            model=model,
            finish_reason=choice.get("finish_reason"),
            usage={
                "prompt_tokens":     usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens":      usage.get("total_tokens", 0),
            },
            metadata={
                "cerebras_id":  data.get("id"),
                "created":      data.get("created"),
                "model_specs":  self.MODEL_SPECS.get(model, {}),
            },
        )

    def _validate_model(self, model: str) -> None:
        """Raise ValueError if *model* is not in SUPPORTED_MODELS."""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"CerebrasProvider does not support model '{model}'. "
                f"Supported: {', '.join(self.SUPPORTED_MODELS)}"
            )

    @staticmethod
    def _backoff(attempt: int, status_code: Optional[int] = None) -> float:
        """Return exponential-backoff delay in seconds.

        Rate-limit responses (429) get a longer base delay.
        """
        base = 5.0 if status_code == 429 else 1.0
        return min(base * (2 ** attempt), 60.0)  # cap at 60 s

    # ------------------------------------------------------------------
    # Token counting
    # ------------------------------------------------------------------

    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Estimate the number of tokens in *text*.

        Uses the Cerebras Cloud SDK if available for an accurate count;
        falls back to a character-based heuristic (~4 chars / token).

        Args:
            text:  The text to count.
            model: Model to use for tokenisation (defaults to
                   ``config.default_model``).

        Returns:
            Estimated token count.
        """
        if self._sdk_client is not None:
            try:
                # SDK tokenise endpoint (if present in installed version)
                result = self._sdk_client.tokenize(text=text)
                return result.count
            except Exception as exc:
                logger.debug("SDK token count failed, falling back: %s", exc)

        # Heuristic fallback: ~4 characters per token
        return max(1, len(text) // 4)

    # ------------------------------------------------------------------
    # Model info & health
    # ------------------------------------------------------------------

    def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Return metadata for *model* (defaults to the configured default)."""
        model = model or self.config.default_model
        return self.MODEL_SPECS.get(
            model,
            {
                "name": model,
                "description": "Unknown Cerebras model",
                "context_window": 128_000,
                "max_completion_tokens": 8_192,
            },
        )

    async def health_check(self) -> Dict[str, Any]:
        """Probe the Cerebras API and return a health-status dict."""
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            models_data = response.json()
            available = [m["id"] for m in models_data.get("data", [])]
            return {
                "status":          "healthy",
                "provider":        "cerebras",
                "available_models": available,
                "default_model":   self.config.default_model,
                "base_url":        self.config.base_url,
            }
        except Exception as exc:
            logger.error("Cerebras health check failed: %s", exc)
            return {
                "status":   "unhealthy",
                "provider": "cerebras",
                "error":    str(exc),
            }

    async def get_available_models(self) -> List[str]:
        """Fetch the live model list from the Cerebras API.

        Falls back to :attr:`SUPPORTED_MODELS` on error.
        """
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as exc:
            logger.error("Failed to fetch Cerebras model list: %s", exc)
            return list(self.SUPPORTED_MODELS)

    def recommend_model(self, priority: str = "balanced") -> str:
        """Suggest a model based on *priority*.

        Args:
            priority: One of ``'speed'``, ``'quality'``, or ``'balanced'``.

        Returns:
            A model identifier string.
        """
        recommendations: Dict[str, str] = {
            "speed":    "llama3.1-8b",
            "quality":  "llama3.3-70b",
            "balanced": "llama3.1-70b",
        }
        return recommendations.get(priority, self.config.default_model)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
        logger.info("CerebrasProvider HTTP client closed")

    async def __aenter__(self) -> "CerebrasProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def create_cerebras_provider(
    api_key: Optional[str] = None,
    model: str = "llama3.3-70b",
    **kwargs: Any,
) -> CerebrasProvider:
    """Create a :class:`CerebrasProvider` from individual arguments.

    Args:
        api_key: Cerebras API key. Falls back to the ``CEREBRAS_API_KEY``
                 environment variable when not provided.
        model:   Default model name (default: ``"llama3.3-70b"``).
        **kwargs: Any extra fields accepted by :class:`CerebrasConfig`.

    Returns:
        A ready-to-use :class:`CerebrasProvider` instance.

    Raises:
        ValueError: If no API key is found.
    """
    resolved_key = api_key or os.environ.get("CEREBRAS_API_KEY", "")
    if not resolved_key:
        raise ValueError(
            "Cerebras API key not provided. "
            "Pass api_key= or set the CEREBRAS_API_KEY environment variable."
        )
    config = CerebrasConfig(api_key=resolved_key, default_model=model, **kwargs)
    return CerebrasProvider(config)
