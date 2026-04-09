"""
Fireworks AI Provider for Zakera AI Chat Agent.

OpenAI-compatible provider for Fireworks Inference API.

Supports:
  - Streaming responses via async generator
  - OpenAI-compatible tool/function calling
  - Token usage tracking
  - Automatic retry with exponential back-off
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

from .providers import Message, ModelProvider, ModelResponse, ToolDefinition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIREWORKS_API_BASE = "https://api.fireworks.ai/inference/v1"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0  # seconds
DEFAULT_TIMEOUT = 120.0  # seconds


# ---------------------------------------------------------------------------
# Enums / data classes
# ---------------------------------------------------------------------------


class FireworksModel(str, Enum):
    """Supported Fireworks model identifiers."""

    LLAMA_V3P1_70B_INSTRUCT = "accounts/fireworks/models/llama-v3p1-70b-instruct"
    LLAMA_V3P1_8B_INSTRUCT = "accounts/fireworks/models/llama-v3p1-8b-instruct"
    LLAMA_V3P1_405B_INSTRUCT = "accounts/fireworks/models/llama-v3p1-405b-instruct"
    MISTRAL_NEMO_INSTRUCT_2407 = "accounts/fireworks/models/mistral-nemo-instruct-2407"
    QWEN2P5_72B_INSTRUCT = "accounts/fireworks/models/qwen2p5-72b-instruct"
    DEEPSEEK_R1_DISTILL_LLAMA_70B = "accounts/fireworks/models/deepseek-r1-distill-llama-70b"

    @classmethod
    def values(cls) -> List[str]:
        return [m.value for m in cls]


@dataclass
class FireworksConfig:
    """Configuration for the Fireworks provider."""

    api_key: str
    model: str = FireworksModel.LLAMA_V3P1_70B_INSTRUCT.value
    api_base: str = FIREWORKS_API_BASE
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout: float = DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        if isinstance(self.model, FireworksModel):
            self.model = self.model.value
        if self.model not in FireworksModel.values():
            raise ValueError(
                f"Unsupported Fireworks model '{self.model}'. "
                f"Choose from: {FireworksModel.values()}"
            )
        if not self.api_key:
            raise ValueError("Fireworks api_key must not be empty.")


@dataclass
class TokenUsage:
    """Tracks token consumption for a single request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    request_id: Optional[str] = None

    @classmethod
    def from_response(
        cls,
        data: Dict[str, Any],
        model: str,
        request_id: Optional[str] = None,
    ) -> "TokenUsage":
        usage = data.get("usage", {})
        return cls(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=model,
            request_id=request_id,
        )


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


def _build_text_message(role: str, content: str) -> Dict[str, Any]:
    return {"role": role, "content": content}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class FireworksProvider(ModelProvider):
    """
    Async Fireworks provider that implements the Zakera provider interface.

    Usage::

        provider = FireworksProvider(model_name="accounts/fireworks/models/llama-v3p1-70b-instruct")

        response = await provider.generate(messages)
        async for chunk in provider.stream_generate(messages):
            print(chunk, end="")
    """

    PROVIDER_NAME = "fireworks"

    def __init__(self, api_key: Optional[str] = None, model_name: str = FireworksModel.LLAMA_V3P1_70B_INSTRUCT.value):
        super().__init__(api_key or os.getenv("FIREWORKS_API_KEY"), model_name)
        self.config = FireworksConfig(api_key=self.api_key or "", model=model_name)
        self._client: Optional[httpx.AsyncClient] = None
        self._total_usage: TokenUsage = TokenUsage(model=self.model_name or self.config.model)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "FireworksProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            resp = await client.get("/models")
            if resp.status_code == 200:
                return {
                    "status": "healthy",
                    "provider": self.PROVIDER_NAME,
                    "model": self.model_name,
                }
            return {
                "status": "degraded",
                "http_status": resp.status_code,
                "provider": self.PROVIDER_NAME,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "unhealthy", "error": str(exc), "provider": self.PROVIDER_NAME}

    # ------------------------------------------------------------------
    # Request building
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Message],
        *,
        stream: bool = False,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [_build_text_message(m.role, m.content or "") for m in messages],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": stream,
        }
        if tools:
            payload["tools"] = [t.to_openai_dict() for t in tools]
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format
        if seed is not None:
            payload["seed"] = seed
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    # ------------------------------------------------------------------
    # Retry logic
    # ------------------------------------------------------------------

    @staticmethod
    def _is_retryable(status_code: int) -> bool:
        return status_code in (429, 500, 502, 503, 504)

    async def _post_with_retry(self, endpoint: str, payload: Dict[str, Any]) -> httpx.Response:
        client = await self._get_client()
        last_exc: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 200 or not self._is_retryable(resp.status_code):
                    return resp
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning(
                    "Fireworks request failed (status=%s), retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    self.config.max_retries,
                )
                await asyncio.sleep(wait)
                last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.RequestError as exc:
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning("Fireworks network error: %s, retrying in %.1fs", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"Fireworks request failed after {self.config.max_retries} retries") from last_exc

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        payload = self._build_payload(
            messages,
            stream=False,
            tools=tools,
            tool_choice=kwargs.get("tool_choice"),
            response_format=kwargs.get("response_format"),
            seed=kwargs.get("seed"),
        )
        if "temperature" in kwargs and kwargs["temperature"] is not None:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs and kwargs["top_p"] is not None:
            payload["top_p"] = kwargs["top_p"]
        if "presence_penalty" in kwargs and kwargs["presence_penalty"] is not None:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        if "frequency_penalty" in kwargs and kwargs["frequency_penalty"] is not None:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]

        resp = await self._post_with_retry("/chat/completions", payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Fireworks API error {resp.status_code}: {resp.text}")

        data = resp.json()
        choice = data["choices"][0]
        message = choice.get("message", {})
        request_id = resp.headers.get("x-request-id")
        usage = TokenUsage.from_response(data, model=data.get("model", self.model_name), request_id=request_id)
        self._accumulate_usage(usage)

        raw_tool_calls = message.get("tool_calls")
        return ModelResponse(
            content=message.get("content") or "",
            model=data.get("model", self.model_name),
            usage={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
            finish_reason=choice.get("finish_reason") or "stop",
            tool_calls=raw_tool_calls,
        )

    # ------------------------------------------------------------------
    # Streaming chat
    # ------------------------------------------------------------------

    async def stream_generate(self, messages: List[Message], **kwargs: Any) -> AsyncGenerator[str, None]:
        payload = self._build_payload(
            messages,
            stream=True,
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
            response_format=kwargs.get("response_format"),
            seed=kwargs.get("seed"),
        )
        if "temperature" in kwargs and kwargs["temperature"] is not None:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs and kwargs["top_p"] is not None:
            payload["top_p"] = kwargs["top_p"]

        client = await self._get_client()
        async with client.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"Fireworks stream error {resp.status_code}: {body.decode()[:200]}")

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                raw = line[len("data: "):].strip()
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse Fireworks SSE line: %s", raw)
                    continue

                if event.get("usage"):
                    usage = TokenUsage.from_response(event, model=self.model_name)
                    self._accumulate_usage(usage)
                    continue

                choices = event.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                text = delta.get("content")
                if text:
                    yield text

    # ------------------------------------------------------------------
    # Tool / usage helpers
    # ------------------------------------------------------------------

    def supports_tools(self) -> bool:
        return True

    async def chat_with_tools(
        self,
        messages: List[Message],
        tools: List[ToolDefinition],
        *,
        tool_choice: str = "auto",
    ) -> ModelResponse:
        return await self.generate(messages, tools=tools, tool_choice=tool_choice)

    def _accumulate_usage(self, usage: TokenUsage) -> None:
        self._total_usage.prompt_tokens += usage.prompt_tokens
        self._total_usage.completion_tokens += usage.completion_tokens
        self._total_usage.total_tokens += usage.total_tokens

    def get_total_usage(self) -> TokenUsage:
        return self._total_usage

    def reset_usage(self) -> None:
        self._total_usage = TokenUsage(model=self.model_name or self.config.model)

    # ------------------------------------------------------------------
    # Provider metadata
    # ------------------------------------------------------------------

    @staticmethod
    def list_models() -> List[str]:
        return FireworksModel.values()

    def __repr__(self) -> str:
        return f"FireworksProvider(model={self.model_name!r})"


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def create_fireworks_provider(settings: Dict[str, Any]) -> FireworksProvider:
    """
    Convenience factory that builds a FireworksProvider from a settings dict.

    Expected keys:
      - fireworks_api_key (required)
      - fireworks_model (optional)
      - fireworks_max_tokens (optional)
      - fireworks_temperature (optional)
    """
    return FireworksProvider(
        api_key=settings["fireworks_api_key"],
        model_name=settings.get("fireworks_model", FireworksModel.LLAMA_V3P1_70B_INSTRUCT.value),
    )
