"""Jina AI embedding provider for Zakera.

Provides async access to Jina AI's embedding endpoints with:
  - dataclass-based configuration
  - async HTTP client lifecycle management
  - retry/backoff for transient failures
  - token and request usage tracking
  - optional local embedding normalisation
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import httpx

logger = logging.getLogger(__name__)

JINA_API_BASE = "https://api.jina.ai/v1"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0
DEFAULT_TIMEOUT = 60.0


class JinaEmbeddingModel(str, Enum):
    """Supported Jina AI embedding model identifiers."""

    JINA_EMBEDDINGS_V3 = "jina-embeddings-v3"
    JINA_EMBEDDINGS_V2_BASE_EN = "jina-embeddings-v2-base-en"
    JINA_EMBEDDINGS_V2_SMALL_EN = "jina-embeddings-v2-small-en"
    JINA_EMBEDDINGS_V2_BASE_ZH = "jina-embeddings-v2-base-zh"

    @classmethod
    def values(cls) -> List[str]:
        return [model.value for model in cls]


@dataclass
class JinaAIConfig:
    """Configuration for the Jina AI embeddings provider."""

    api_key: str
    model: str = JinaEmbeddingModel.JINA_EMBEDDINGS_V3.value
    api_base: str = JINA_API_BASE
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    batch_size: int = 16
    normalize_embeddings: bool = True
    task: Optional[str] = None
    dimensions: Optional[int] = None
    truncate: Optional[bool] = None
    encoding_format: str = "float"

    def __post_init__(self) -> None:
        if isinstance(self.model, JinaEmbeddingModel):
            self.model = self.model.value
        if self.model not in JinaEmbeddingModel.values():
            logger.warning(
                "JinaAIConfig model '%s' is not in the built-in catalogue. "
                "Proceeding anyway.",
                self.model,
            )
        if not self.api_key:
            raise ValueError("Jina AI api_key must not be empty.")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than 0.")
        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0.")
        if self.batch_size < 1:
            raise ValueError("batch_size must be greater than 0.")


@dataclass
class EmbeddingUsage:
    """Tracks token and request usage for embedding calls."""

    prompt_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    input_items: int = 0
    model: str = ""
    request_id: Optional[str] = None

    @classmethod
    def from_response(
        cls,
        data: Dict[str, Any],
        model: str,
        request_id: Optional[str] = None,
        input_items: int = 0,
    ) -> "EmbeddingUsage":
        usage = data.get("usage", {}) or {}
        prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        total_tokens = usage.get("total_tokens", prompt_tokens)
        return cls(
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            requests=1,
            input_items=input_items,
            model=model,
            request_id=request_id,
        )


class JinaAIProvider:
    """
    Async Jina AI embeddings provider.

    Usage::

        config = JinaAIConfig(api_key="jina_...", model="jina-embeddings-v3")
        provider = JinaAIProvider(config)

        embedding = await provider.embed_text("Hello world")
        embeddings = await provider.embed_batch(["first", "second"])
    """

    PROVIDER_NAME = "jina"

    SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
        JinaEmbeddingModel.JINA_EMBEDDINGS_V3.value: {
            "description": "Latest multilingual embedding model for semantic search and retrieval.",
            "use_cases": ["retrieval", "semantic_search", "classification", "clustering"],
        },
        JinaEmbeddingModel.JINA_EMBEDDINGS_V2_BASE_EN.value: {
            "description": "English embedding model with broad general-purpose coverage.",
            "use_cases": ["retrieval", "semantic_search"],
        },
        JinaEmbeddingModel.JINA_EMBEDDINGS_V2_SMALL_EN.value: {
            "description": "Compact English embedding model for cost-conscious workloads.",
            "use_cases": ["retrieval", "semantic_search"],
        },
        JinaEmbeddingModel.JINA_EMBEDDINGS_V2_BASE_ZH.value: {
            "description": "Chinese embedding model for multilingual semantic search.",
            "use_cases": ["retrieval", "semantic_search"],
        },
    }

    def __init__(
        self,
        config: Optional[JinaAIConfig] = None,
        api_key: Optional[str] = None,
        model_name: str = JinaEmbeddingModel.JINA_EMBEDDINGS_V3.value,
    ) -> None:
        if config is None:
            resolved_key = api_key or os.getenv("JINA_API_KEY")
            if not resolved_key:
                raise ValueError(
                    "Jina AI API key is required. Set JINA_API_KEY or pass api_key=."
                )
            config = JinaAIConfig(api_key=resolved_key, model=model_name)
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._total_usage: EmbeddingUsage = EmbeddingUsage(model=self.config.model)

        logger.info("Initialized Jina AI provider with model: %s", self.config.model)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base,
                headers=self._headers(),
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "JinaAIProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _batched(items: Sequence[str], batch_size: int) -> Sequence[List[str]]:
        for start in range(0, len(items), batch_size):
            yield list(items[start : start + batch_size])

    @staticmethod
    def _normalize_vector(vector: Sequence[float]) -> List[float]:
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0:
            return [float(value) for value in vector]
        return [float(value) / norm for value in vector]

    @staticmethod
    def _estimate_tokens(texts: Sequence[str]) -> int:
        combined = " ".join(texts)
        return max(1, len(combined) // 4)

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        return status_code in (429, 500, 502, 503, 504)

    @staticmethod
    def _format_api_error(status_code: int, body: str) -> Exception:
        message = body.strip() or "<empty response body>"
        message = message[:400]
        if status_code in (401, 403):
            return ValueError(f"Jina AI authentication failed ({status_code}): {message}")
        if status_code == 429:
            return RuntimeError(f"Jina AI rate limit exceeded: {message}")
        if status_code == 413:
            return ValueError(
                "Jina AI rejected the request as too large (413). "
                "Reduce the batch size or input text length. "
                f"Body: {message}"
            )
        if 400 <= status_code < 500:
            return ValueError(f"Jina AI request rejected ({status_code}): {message}")
        return RuntimeError(f"Jina AI API error {status_code}: {message}")

    def _build_payload(self, texts: Sequence[str], **kwargs: Any) -> Dict[str, Any]:
        task = kwargs.pop("task", self.config.task)
        dimensions = kwargs.pop("dimensions", self.config.dimensions)
        truncate = kwargs.pop("truncate", self.config.truncate)
        encoding_format = kwargs.pop("encoding_format", self.config.encoding_format)

        payload: Dict[str, Any] = {
            "model": kwargs.pop("model", self.config.model),
            "input": list(texts),
        }

        if task is not None:
            payload["task"] = task
        if dimensions is not None:
            payload["dimensions"] = dimensions
        if truncate is not None:
            payload["truncate"] = truncate
        if encoding_format is not None:
            payload["encoding_format"] = encoding_format

        # Pass through any explicitly provided Jina/OpenAI-compatible extras.
        for key in ("user", "extra_body"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

        return payload

    async def _post_with_retry(self, endpoint: str, payload: Dict[str, Any]) -> httpx.Response:
        client = await self._get_client()
        last_exc: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.post(endpoint, json=payload)
                if response.status_code == 200 or not self._is_retryable(response.status_code):
                    return response

                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning(
                    "Jina AI request failed (status=%s), retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    wait,
                    attempt + 1,
                    self.config.max_retries,
                )
                await asyncio.sleep(wait)
                last_exc = self._format_api_error(response.status_code, response.text)
            except httpx.RequestError as exc:
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning("Jina AI network error: %s, retrying in %.1fs", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc

        raise RuntimeError(
            f"Jina AI request failed after {self.config.max_retries} retries"
        ) from last_exc

    def _extract_embeddings(self, data: Dict[str, Any], expected_count: int) -> List[List[float]]:
        items = data.get("data", [])
        if not isinstance(items, list):
            raise RuntimeError("Jina AI response did not contain a valid 'data' list.")

        try:
            ordered = sorted(items, key=lambda item: item.get("index", 0))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Jina AI response contained malformed embedding items.") from exc

        embeddings: List[List[float]] = []
        for item in ordered:
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise RuntimeError("Jina AI response item is missing an embedding vector.")
            embeddings.append([float(value) for value in embedding])

        if expected_count and len(embeddings) != expected_count:
            raise RuntimeError(
                f"Jina AI returned {len(embeddings)} embeddings for {expected_count} inputs."
            )

        return embeddings

    def _accumulate_usage(self, usage: EmbeddingUsage) -> None:
        self._total_usage.prompt_tokens += usage.prompt_tokens
        self._total_usage.total_tokens += usage.total_tokens
        self._total_usage.requests += usage.requests
        self._total_usage.input_items += usage.input_items

    async def _embed_once(
        self,
        texts: Sequence[str],
        **kwargs: Any,
    ) -> Tuple[List[List[float]], EmbeddingUsage]:
        payload = self._build_payload(texts, **kwargs)
        response = await self._post_with_retry("/embeddings", payload)

        if response.status_code != 200:
            raise self._format_api_error(response.status_code, response.text)

        data = response.json()
        embeddings = self._extract_embeddings(data, expected_count=len(texts))

        if kwargs.get("normalize_embeddings", self.config.normalize_embeddings):
            embeddings = [self._normalize_vector(vector) for vector in embeddings]

        request_id = response.headers.get("x-request-id")
        usage = EmbeddingUsage.from_response(
            data,
            model=data.get("model", self.config.model),
            request_id=request_id,
            input_items=len(texts),
        )

        if usage.prompt_tokens == 0 and usage.total_tokens == 0:
            estimated = self._estimate_tokens(texts)
            usage.prompt_tokens = estimated
            usage.total_tokens = estimated

        return embeddings, usage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed(
        self,
        texts: Union[str, Sequence[str]],
        **kwargs: Any,
    ) -> Union[List[float], List[List[float]]]:
        """
        Embed a single string or a sequence of strings.

        Returns:
            A single embedding vector for a string input, or a list of vectors
            for sequence input.
        """
        if isinstance(texts, str):
            return await self.embed_text(texts, **kwargs)
        return await self.embed_batch(list(texts), **kwargs)

    async def embed_text(self, text: str, **kwargs: Any) -> List[float]:
        """Embed a single text string and return one vector."""
        embeddings = await self.embed_batch([text], **kwargs)
        return embeddings[0]

    async def embed_batch(
        self,
        texts: Sequence[str],
        **kwargs: Any,
    ) -> List[List[float]]:
        """Embed a batch of texts and return vectors in input order."""
        if isinstance(texts, str):
            raise TypeError(
                "embed_batch expects a sequence of strings; use embed_text() for a single string."
            )

        items = list(texts)
        if not items:
            raise ValueError("texts must not be empty.")

        batch_size = int(kwargs.pop("batch_size", self.config.batch_size))
        if batch_size < 1:
            raise ValueError("batch_size must be greater than 0.")

        all_embeddings: List[List[float]] = []
        for batch in self._batched(items, batch_size):
            embeddings, usage = await self._embed_once(batch, **kwargs)
            all_embeddings.extend(embeddings)
            self._accumulate_usage(usage)

        return all_embeddings

    async def health_check(self) -> Dict[str, Any]:
        """Perform a lightweight API reachability check."""
        try:
            client = await self._get_client()
            response = await client.get("/models")
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "provider": self.PROVIDER_NAME,
                    "model": self.config.model,
                    "supported_models": self.list_models(),
                }
            return {
                "status": "degraded",
                "http_status": response.status_code,
                "provider": self.PROVIDER_NAME,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "unhealthy",
                "error": str(exc),
                "provider": self.PROVIDER_NAME,
            }

    def get_total_usage(self) -> EmbeddingUsage:
        """Return cumulative embedding usage for this provider instance."""
        return self._total_usage

    def reset_usage(self) -> None:
        """Reset cumulative usage counters."""
        self._total_usage = EmbeddingUsage(model=self.config.model)

    @classmethod
    def list_models(cls) -> List[str]:
        """Return the built-in embedding model identifiers."""
        return list(cls.SUPPORTED_MODELS.keys())

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """Return metadata for a specific embedding model."""
        info = cls.SUPPORTED_MODELS.get(model_name)
        if info is None:
            return None
        return {"id": model_name, **info}

    def __repr__(self) -> str:
        return f"JinaAIProvider(model={self.config.model!r})"


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def create_jina_provider(settings: Dict[str, Any]) -> JinaAIProvider:
    """
    Convenience factory that builds a JinaAIProvider from a settings dict.

    Expected keys:
      - jina_api_key (required)
      - jina_model (optional, default jina-embeddings-v3)
      - jina_timeout (optional)
      - jina_max_retries (optional)
      - jina_batch_size (optional)
      - jina_normalize_embeddings (optional)
    """
    config = JinaAIConfig(
        api_key=settings["jina_api_key"],
        model=settings.get("jina_model", JinaEmbeddingModel.JINA_EMBEDDINGS_V3.value),
        timeout=float(settings.get("jina_timeout", DEFAULT_TIMEOUT)),
        max_retries=int(settings.get("jina_max_retries", DEFAULT_MAX_RETRIES)),
        batch_size=int(settings.get("jina_batch_size", 16)),
        normalize_embeddings=bool(settings.get("jina_normalize_embeddings", True)),
        task=settings.get("jina_task"),
        dimensions=settings.get("jina_dimensions"),
        truncate=settings.get("jina_truncate"),
        encoding_format=settings.get("jina_encoding_format", "float"),
    )
    return JinaAIProvider(config)
