"""
Enhanced Ollama local provider for Zakera AI chat agent.

Provides a production-grade async interface to a locally-running Ollama
instance, including model management, structured output with JSON-Schema
validation, streaming, health checks, and automatic retry logic.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class OllamaConnectionError(RuntimeError):
    """Raised when the Ollama server cannot be reached."""


class ModelPullError(RuntimeError):
    """Raised when a model pull from the Ollama registry fails."""


class StructuredOutputError(ValueError):
    """Raised when the model response fails JSON-Schema validation."""

    def __init__(self, message: str, raw_text: str) -> None:
        super().__init__(message)
        self.raw_text = raw_text


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"  # reachable but target model is not loaded
    DOWN = "down"


@dataclass
class OllamaModelInfo:
    name: str
    size_bytes: int = 0
    modified_at: str = ""
    family: str = ""
    parameter_size: str = ""
    quantization_level: str = ""

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "OllamaModelInfo":
        details = data.get("details", {})
        return cls(
            name=data.get("name", ""),
            size_bytes=data.get("size", 0),
            modified_at=data.get("modified_at", ""),
            family=details.get("family", ""),
            parameter_size=details.get("parameter_size", ""),
            quantization_level=details.get("quantization_level", ""),
        )


@dataclass
class ChatResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"

    @property
    def usage(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_BACKOFF_BASE = 0.5  # seconds


class OllamaLocalProvider:
    """
    Async provider that wraps a locally-running Ollama server.

    Usage::

        async with OllamaLocalProvider(model="llama3") as provider:
            response = await provider.generate([
                {"role": "user", "content": "Hello!"}
            ])
            print(response.content)
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
        pull_on_missing: bool = False,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.pull_on_missing = pull_on_missing
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                limits=limits,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OllamaLocalProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _with_retry(
        self,
        coro_factory,
        retryable_statuses: tuple[int, ...] = (429, 500, 502, 503, 504),
    ) -> httpx.Response:
        """
        Call *coro_factory()* up to *max_retries* times.
        Retries on connection errors or retryable HTTP status codes with
        exponential back-off.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = await coro_factory()
                if resp.status_code not in retryable_statuses:
                    return resp
                last_exc = RuntimeError(
                    f"Ollama returned HTTP {resp.status_code}: {resp.text}"
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_exc = OllamaConnectionError(
                    f"Cannot reach Ollama at {self.base_url}: {exc}"
                )
            if attempt < self.max_retries - 1:
                wait = _BACKOFF_BASE * (2 ** attempt)
                logger.debug("Ollama retry %d in %.1fs", attempt + 1, wait)
                await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        extra_options: Optional[Dict[str, Any]] = None,
        response_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        options: Dict[str, Any] = {}
        allowed_opts = {
            "temperature", "top_p", "top_k", "repeat_penalty",
            "seed", "num_predict", "num_ctx",
        }
        if extra_options:
            for k, v in extra_options.items():
                if k in allowed_opts:
                    options[k] = v

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options
        if response_format:
            payload["format"] = response_format
        return payload

    async def generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> ChatResponse:
        """
        Send a list of chat messages and return a complete ChatResponse.

        Kwargs forwarded to Ollama options:
            temperature, top_p, top_k, repeat_penalty, seed, num_predict, num_ctx
        """
        t0 = time.monotonic()
        payload = self._build_payload(messages, stream=False, extra_options=kwargs)
        client = self._get_client()

        if self.pull_on_missing:
            await self._ensure_model_exists()

        resp = await self._with_retry(
            lambda: client.post("/api/chat", json=payload)
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Ollama generate failed [{resp.status_code}]: {resp.text}"
            )

        data = resp.json()
        msg = data.get("message", {})
        content = msg.get("content", "")
        latency_ms = (time.monotonic() - t0) * 1000

        return ChatResponse(
            content=content,
            model=data.get("model", self.model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            latency_ms=latency_ms,
            finish_reason=data.get("done_reason", "stop"),
        )

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama, yielding content delta strings.

        The generator closes cleanly when Ollama sends done=true.
        """
        payload = self._build_payload(messages, stream=True, extra_options=kwargs)
        client = self._get_client()

        if self.pull_on_missing:
            await self._ensure_model_exists()

        try:
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise RuntimeError(
                        f"Ollama stream failed [{resp.status_code}]: {body.decode()}"
                    )
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if chunk.get("done"):
                        break
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise OllamaConnectionError(
                f"Streaming connection lost: {exc}"
            ) from exc

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Request a JSON-formatted response and validate it against *schema*.

        Raises StructuredOutputError if the model output does not match the
        provided JSON Schema.
        """
        payload = self._build_payload(
            messages,
            stream=False,
            extra_options=kwargs,
            response_format="json",
        )
        client = self._get_client()
        resp = await self._with_retry(
            lambda: client.post("/api/chat", json=payload)
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Ollama structured generate failed [{resp.status_code}]: {resp.text}"
            )

        data = resp.json()
        raw_text = data.get("message", {}).get("content", "")

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(
                f"Model output is not valid JSON: {exc}", raw_text
            ) from exc

        # Validate against schema using jsonschema if available
        try:
            import jsonschema  # optional dependency

            jsonschema.validate(instance=parsed, schema=schema)
        except ImportError:
            logger.debug("jsonschema not installed; skipping schema validation")
        except Exception as exc:
            raise StructuredOutputError(
                f"Response failed JSON-Schema validation: {exc}", raw_text
            ) from exc

        return parsed  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    async def list_models(self) -> List[OllamaModelInfo]:
        """Return all models currently installed in this Ollama instance."""
        client = self._get_client()
        try:
            resp = await client.get("/api/tags")
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise OllamaConnectionError(
                f"Cannot reach Ollama at {self.base_url}: {exc}"
            ) from exc
        if resp.status_code != 200:
            raise RuntimeError(f"list_models failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        return [OllamaModelInfo.from_api(m) for m in data.get("models", [])]

    async def pull_model(
        self,
        model_name: str,
        stream_progress: bool = False,
    ) -> None:
        """
        Pull *model_name* from the Ollama registry.

        If *stream_progress* is True, progress dicts are logged at DEBUG
        level (status, completed, total).
        """
        client = self._get_client()
        payload = {"name": model_name, "stream": True}
        try:
            async with client.stream("POST", "/api/pull", json=payload) as resp:
                if resp.status_code == 404:
                    raise ModelPullError(
                        f"Model '{model_name}' not found in Ollama registry"
                    )
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise ModelPullError(
                        f"pull_model failed [{resp.status_code}]: {body.decode()}"
                    )
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        progress = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if stream_progress:
                        logger.debug(
                            "pull %s: %s (%s/%s)",
                            model_name,
                            progress.get("status"),
                            progress.get("completed"),
                            progress.get("total"),
                        )
                    if progress.get("status") == "success":
                        break
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            raise OllamaConnectionError(
                f"Cannot reach Ollama during pull: {exc}"
            ) from exc

    async def delete_model(self, model_name: str) -> None:
        """Delete *model_name* from the local Ollama store."""
        client = self._get_client()
        resp = await client.request("DELETE", "/api/delete", json={"name": model_name})
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"delete_model failed [{resp.status_code}]: {resp.text}"
            )

    async def get_model_info(self, model_name: str) -> Optional[OllamaModelInfo]:
        """Return metadata for *model_name*, or None if not installed."""
        client = self._get_client()
        resp = await client.post("/api/show", json={"name": model_name})
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise RuntimeError(
                f"get_model_info failed [{resp.status_code}]: {resp.text}"
            )
        return OllamaModelInfo.from_api(resp.json())

    async def _ensure_model_exists(self) -> None:
        """Pull self.model if it is not already installed."""
        info = await self.get_model_info(self.model)
        if info is None:
            logger.info("Model '%s' not found locally; pulling…", self.model)
            await self.pull_model(self.model)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthStatus:
        """
        Return the health status of the Ollama instance.

        - HealthStatus.OK       — server reachable, model installed
        - HealthStatus.DEGRADED — server reachable, model not installed
        - HealthStatus.DOWN     — server unreachable
        """
        client = self._get_client()
        try:
            resp = await client.get("/")
        except (httpx.ConnectError, httpx.ReadTimeout):
            return HealthStatus.DOWN

        if resp.status_code not in (200, 404):
            return HealthStatus.DOWN

        # Check if the target model is available
        try:
            models = await self.list_models()
            model_names = [m.name for m in models]
            # Ollama model names may include tags: llama3, llama3:latest, etc.
            base = self.model.split(":")[0]
            if any(m.split(":")[0] == base for m in model_names):
                return HealthStatus.OK
            return HealthStatus.DEGRADED
        except Exception:
            return HealthStatus.DEGRADED
