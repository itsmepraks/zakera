"""DeepInfra provider for Zakera AI Chat Agent.

DeepInfra exposes an OpenAI-compatible chat completions API, so this provider
wraps that interface and normalises the responses into Zakera's model layer.
The provider keeps a curated list of recommended model IDs while still allowing
custom DeepInfra model names to be passed through when needed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from .providers import Message, ModelProvider, ModelResponse

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepinfra.com/v1/openai"
DEFAULT_MODEL = "meta-llama/Llama-3-70b-chat-hf"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TOP_P = 1.0

DEEPINFRA_MODELS: Dict[str, Dict[str, Any]] = {
    "meta-llama/Llama-3-70b-chat-hf": {
        "display_name": "Llama 3 70B Chat",
        "context_window": 8192,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "High-capacity Llama 3 chat model on DeepInfra",
    },
    "meta-llama/Llama-3-8b-chat-hf": {
        "display_name": "Llama 3 8B Chat",
        "context_window": 8192,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "Fast Llama 3 chat model on DeepInfra",
    },
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {
        "display_name": "Llama 3.1 8B Instruct",
        "context_window": 128000,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "Compact instruction-tuned Llama 3.1 model",
    },
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {
        "display_name": "Llama 3.1 70B Instruct",
        "context_window": 128000,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "Large instruction-tuned Llama 3.1 model",
    },
    "mistralai/Mixtral-8x7B-Instruct-v0.1": {
        "display_name": "Mixtral 8x7B Instruct",
        "context_window": 32768,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "Mixture-of-experts instruction model",
    },
    "mistralai/Mistral-7B-Instruct-v0.3": {
        "display_name": "Mistral 7B Instruct",
        "context_window": 32768,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "Small, capable instruction model",
    },
    "Qwen/Qwen2.5-72B-Instruct": {
        "display_name": "Qwen2.5 72B Instruct",
        "context_window": 32768,
        "supports_streaming": True,
        "supports_tools": True,
        "description": "High-quality multilingual instruction model",
    },
}


@dataclass(frozen=True)
class DeepInfraConfig:
    """Configuration for DeepInfra model access."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    default_model: str = DEFAULT_MODEL
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    top_p: float = DEFAULT_TOP_P


class DeepInfraProvider(ModelProvider):
    """OpenAI-compatible DeepInfra provider.

    The provider exposes the ``ModelProvider`` ABC methods expected by Zakera
    while also offering ``chat`` and ``stream_chat`` aliases for compatibility
    with existing provider call sites.
    """

    provider_name = "deepinfra"

    def __init__(
        self,
        config: Optional[DeepInfraConfig] = None,
        *,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        default_model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        top_p: float = DEFAULT_TOP_P,
    ) -> None:
        if config is None:
            resolved_api_key = (api_key or os.getenv("DEEPINFRA_API_KEY") or "").strip()
            if not resolved_api_key:
                raise ValueError(
                    "DeepInfra API key is required. Set DEEPINFRA_API_KEY or pass api_key."
                )
            config = DeepInfraConfig(
                api_key=resolved_api_key,
                base_url=base_url,
                default_model=default_model,
                timeout=timeout,
                max_retries=max_retries,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

        self.config = config
        self.api_key = config.api_key.strip()
        if not self.api_key:
            raise ValueError(
                "DeepInfra API key is required. Set DEEPINFRA_API_KEY or pass api_key."
            )

        self.base_url = config.base_url.rstrip("/")
        self.default_model = config.default_model
        self.timeout = float(config.timeout)
        self.max_retries = int(config.max_retries)
        self.default_temperature = float(config.temperature)
        self.default_max_tokens = int(config.max_tokens)
        self.default_top_p = float(config.top_p)
        self._client: Optional[httpx.AsyncClient] = None

        if self.default_model not in DEEPINFRA_MODELS:
            logger.info(
                "DeepInfra default model '%s' is not in the curated allowlist; "
                "custom model IDs will still be passed through.",
                self.default_model,
            )

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Zakera/DeepInfraProvider",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Any],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a single completion response."""
        resolved_model = model or self.default_model
        payload = self._build_payload(
            messages=messages,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=False,
            tools=tools,
            tool_choice=tool_choice,
            stop=stop,
            extra_params=kwargs,
        )

        start = time.monotonic()
        raw = await self._post_with_retry(payload)
        latency = time.monotonic() - start
        return self._parse_response(raw, resolved_model, latency)

    async def stream_generate(
        self,
        messages: List[Any],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion response as text deltas."""
        resolved_model = model or self.default_model
        payload = self._build_payload(
            messages=messages,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=True,
            tools=tools,
            tool_choice=tool_choice,
            stop=stop,
            extra_params=kwargs,
        )

        client = await self._get_client()
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data = line[6:].strip()
                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed DeepInfra SSE chunk: %s", data)
                    continue

                choice = (chunk.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content

    async def chat(self, *args: Any, **kwargs: Any) -> ModelResponse:
        """Compatibility alias for code that expects ``chat``."""
        return await self.generate(*args, **kwargs)

    async def stream_chat(self, *args: Any, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Compatibility alias for code that expects ``stream_chat``."""
        async for chunk in self.stream_generate(*args, **kwargs):
            yield chunk

    def get_available_models(self) -> List[str]:
        """Return the curated DeepInfra model allowlist."""
        return list(DEEPINFRA_MODELS.keys())

    def list_models(self) -> List[Dict[str, Any]]:
        """Return model metadata for UI or diagnostics."""
        return [{"id": model_id, **meta} for model_id, meta in DEEPINFRA_MODELS.items()]

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Return metadata for a single model if it is in the allowlist."""
        return DEEPINFRA_MODELS.get(model, {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalise_message(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, dict):
            payload = {
                key: value
                for key, value in message.items()
                if value is not None
            }
        elif hasattr(message, "to_dict"):
            payload = {
                key: value
                for key, value in message.to_dict().items()  # type: ignore[attr-defined]
                if value is not None
            }
        else:
            payload = {
                "role": getattr(message, "role", None),
                "content": getattr(message, "content", None),
            }
            name = getattr(message, "name", None)
            if name is not None:
                payload["name"] = name
            tool_call_id = getattr(message, "tool_call_id", None)
            if tool_call_id is not None:
                payload["tool_call_id"] = tool_call_id
            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls is not None:
                payload["tool_calls"] = tool_calls

        if not payload.get("role"):
            raise ValueError("Each message must include a role.")
        if "content" not in payload:
            payload["content"] = ""
        return payload

    def _build_payload(
        self,
        *,
        messages: List[Any],
        model: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        top_p: Optional[float],
        stream: bool,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        stop: Optional[List[str]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._normalise_message(message) for message in messages],
            "temperature": self.default_temperature if temperature is None else temperature,
            "top_p": self.default_top_p if top_p is None else top_p,
            "stream": stream,
        }

        resolved_max_tokens = self.default_max_tokens if max_tokens is None else max_tokens
        if resolved_max_tokens is not None:
            payload["max_tokens"] = resolved_max_tokens

        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if stop:
            payload["stop"] = stop

        for key, value in (extra_params or {}).items():
            if value is not None:
                payload[key] = value

        return payload

    async def _post_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await client.post("/chat/completions", json=payload)
                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(
                        "DeepInfra rate limit hit; retrying in %.1fs (attempt %d/%d)",
                        wait,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500:
                    raise
                wait = 2 ** attempt
                logger.warning(
                    "DeepInfra server error %d; retrying in %.1fs",
                    exc.response.status_code,
                    wait,
                )
                await asyncio.sleep(wait)
            except httpx.RequestError as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    "DeepInfra request error on attempt %d: %s",
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"DeepInfra request failed after {self.max_retries} attempts."
        ) from last_error

    def _parse_response(
        self,
        raw: Dict[str, Any],
        requested_model: str,
        latency_seconds: float,
    ) -> ModelResponse:
        choices = raw.get("choices") or []
        if not choices:
            raise RuntimeError("DeepInfra response did not contain any choices.")

        choice = choices[0]
        message = choice.get("message") or {}
        usage = raw.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(
            usage.get("total_tokens", prompt_tokens + completion_tokens) or 0
        )

        response_model = raw.get("model") or requested_model
        normalised_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

        logger.info(
            "DeepInfra response generated in %.2fs using %s (%d total tokens)",
            latency_seconds,
            response_model,
            total_tokens,
        )

        return ModelResponse(
            content=message.get("content") or "",
            model=response_model,
            usage=normalised_usage,
            finish_reason=choice.get("finish_reason") or "stop",
            cost=0.0,
        )


def create_deepinfra_provider(
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    **kwargs: Any,
) -> DeepInfraProvider:
    """Factory helper used by the model manager."""
    resolved_api_key = api_key or os.getenv("DEEPINFRA_API_KEY") or ""
    return DeepInfraProvider(api_key=resolved_api_key, default_model=model, **kwargs)


__all__ = [
    "DEEPINFRA_MODELS",
    "DeepInfraConfig",
    "DeepInfraProvider",
    "create_deepinfra_provider",
]
