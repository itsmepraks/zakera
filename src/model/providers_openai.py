"""
OpenAI Provider for Zakera AI Chat Agent.

Supports GPT-4o, GPT-4o-mini, GPT-4-turbo, and GPT-3.5-turbo with:
  - Streaming responses via async generator
  - Structured function / tool calling
  - Vision (multimodal) inputs (base64 or URL)
  - Automatic retry with exponential back-off
  - Token usage tracking
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0  # seconds
DEFAULT_TIMEOUT = 120.0  # seconds


# ---------------------------------------------------------------------------
# Enums / data classes
# ---------------------------------------------------------------------------


class OpenAIModel(str, Enum):
    """Supported OpenAI model identifiers."""

    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"

    @classmethod
    def values(cls) -> List[str]:
        return [m.value for m in cls]


@dataclass
class OpenAIConfig:
    """Configuration for the OpenAI provider."""

    api_key: str
    model: str = OpenAIModel.GPT_4O
    api_base: str = OPENAI_API_BASE
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout: float = DEFAULT_TIMEOUT
    organization: Optional[str] = None

    def __post_init__(self) -> None:
        if self.model not in OpenAIModel.values():
            raise ValueError(
                f"Unsupported OpenAI model '{self.model}'. "
                f"Choose from: {OpenAIModel.values()}"
            )
        if not self.api_key:
            raise ValueError("OpenAI api_key must not be empty.")


@dataclass
class TokenUsage:
    """Tracks token consumption for a single request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    request_id: Optional[str] = None

    @classmethod
    def from_response(cls, data: Dict[str, Any], model: str, request_id: Optional[str] = None) -> "TokenUsage":
        usage = data.get("usage", {})
        return cls(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            model=model,
            request_id=request_id,
        )


@dataclass
class FunctionDefinition:
    """Describes a callable tool/function for the model."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema object
    strict: bool = False

    def to_dict(self) -> Dict[str, Any]:
        tool: Dict[str, Any] = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
        if self.strict:
            tool["function"]["strict"] = True
        return tool


@dataclass
class ImageContent:
    """Represents an image for vision requests."""

    url: Optional[str] = None
    base64_data: Optional[str] = None
    media_type: str = "image/jpeg"
    detail: str = "auto"  # 'low' | 'high' | 'auto'

    def to_content_part(self) -> Dict[str, Any]:
        if self.url:
            image_url = {"url": self.url, "detail": self.detail}
        elif self.base64_data:
            data_uri = f"data:{self.media_type};base64,{self.base64_data}"
            image_url = {"url": data_uri, "detail": self.detail}
        else:
            raise ValueError("ImageContent requires either 'url' or 'base64_data'.")
        return {"type": "image_url", "image_url": image_url}


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


def build_text_message(role: str, content: str) -> Dict[str, Any]:
    """Build a plain text message dict."""
    return {"role": role, "content": content}


def build_vision_message(
    role: str,
    text: str,
    images: List[ImageContent],
) -> Dict[str, Any]:
    """Build a multimodal message with text and image parts."""
    content: List[Dict[str, Any]] = [{"type": "text", "text": text}]
    for img in images:
        content.append(img.to_content_part())
    return {"role": role, "content": content}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class OpenAIProvider:
    """
    Async OpenAI provider that implements the Zakera provider interface.

    Usage::

        config = OpenAIConfig(api_key="sk-...", model="gpt-4o")
        provider = OpenAIProvider(config)

        # Non-streaming
        response = await provider.chat(messages)

        # Streaming
        async for chunk in provider.stream_chat(messages):
            print(chunk, end="", flush=True)
    """

    PROVIDER_NAME = "openai"

    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._total_usage: TokenUsage = TokenUsage(model=config.model)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers: Dict[str, str] = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            if self.config.organization:
                headers["OpenAI-Organization"] = self.config.organization
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base,
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Cleanly close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OpenAIProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """Verify the provider is reachable and the API key is valid."""
        try:
            client = await self._get_client()
            resp = await client.get("/models")
            if resp.status_code == 200:
                return {"status": "healthy", "provider": self.PROVIDER_NAME, "model": self.config.model}
            return {"status": "degraded", "http_status": resp.status_code, "provider": self.PROVIDER_NAME}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unhealthy", "error": str(exc), "provider": self.PROVIDER_NAME}

    # ------------------------------------------------------------------
    # Request building
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        *,
        stream: bool = False,
        functions: Optional[List[FunctionDefinition]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        response_format: Optional[Dict[str, str]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": stream,
        }
        if functions:
            payload["tools"] = [f.to_dict() for f in functions]
            if function_call is not None:
                payload["tool_choice"] = function_call
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

    async def _post_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> httpx.Response:
        client = await self._get_client()
        last_exc: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 200 or not self._is_retryable(resp.status_code):
                    return resp
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning(
                    "OpenAI request failed (status=%s), retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    self.config.max_retries,
                )
                await asyncio.sleep(wait)
                last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.RequestError as exc:
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning("OpenAI network error: %s, retrying in %.1fs", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"OpenAI request failed after {self.config.max_retries} retries") from last_exc

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        functions: Optional[List[FunctionDefinition]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        response_format: Optional[Dict[str, str]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request and return the full response.

        Returns a dict with keys:
          - ``content``   (str) — assistant reply text
          - ``usage``     (TokenUsage) — token counts
          - ``tool_calls`` (list | None) — structured tool call objects if any
          - ``finish_reason`` (str)
          - ``model``     (str)
          - ``request_id`` (str | None)
        """
        payload = self._build_payload(
            messages,
            stream=False,
            functions=functions,
            function_call=function_call,
            response_format=response_format,
            seed=seed,
        )
        resp = await self._post_with_retry("/chat/completions", payload)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")

        data = resp.json()
        choice = data["choices"][0]
        message = choice["message"]
        request_id = resp.headers.get("x-request-id")
        usage = TokenUsage.from_response(data, model=self.config.model, request_id=request_id)
        self._accumulate_usage(usage)

        return {
            "content": message.get("content") or "",
            "usage": usage,
            "tool_calls": message.get("tool_calls"),
            "finish_reason": choice.get("finish_reason"),
            "model": data.get("model", self.config.model),
            "request_id": request_id,
        }

    # ------------------------------------------------------------------
    # Streaming chat
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        functions: Optional[List[FunctionDefinition]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        seed: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Yield text chunks as they arrive from the streaming API.

        Usage::

            async for token in provider.stream_chat(messages):
                print(token, end="", flush=True)
        """
        payload = self._build_payload(
            messages,
            stream=True,
            functions=functions,
            function_call=function_call,
            seed=seed,
        )
        client = await self._get_client()
        async with client.stream("POST", "/chat/completions", json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"OpenAI stream error {resp.status_code}: {body.decode()[:200]}")

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                raw = line[len("data: "):].strip()
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse SSE line: %s", raw)
                    continue

                # Handle usage chunk emitted at end of stream
                if event.get("usage"):
                    usage = TokenUsage.from_response(event, model=self.config.model)
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
    # Vision (multimodal) helpers
    # ------------------------------------------------------------------

    async def vision_chat(
        self,
        prompt: str,
        images: List[ImageContent],
        *,
        system_prompt: Optional[str] = None,
        stream: bool = False,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        Send a multimodal (text + image) request.

        Args:
            prompt: The user text prompt.
            images: List of ImageContent objects (URL or base64).
            system_prompt: Optional system context.
            stream: Whether to stream the response.

        Returns:
            Full response dict (stream=False) or async generator (stream=True).
        """
        messages: List[Dict[str, Any]] = []
        if system_prompt:
            messages.append(build_text_message("system", system_prompt))
        messages.append(build_vision_message("user", prompt, images))

        if stream:
            return self.stream_chat(messages)
        return await self.chat(messages)

    # ------------------------------------------------------------------
    # Function calling helpers
    # ------------------------------------------------------------------

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        functions: List[FunctionDefinition],
        *,
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        """
        Run a chat completion that may invoke one or more tools.

        Returns the raw response dict from ``chat()`` with ``tool_calls``
        populated when the model decides to call a function.
        """
        return await self.chat(messages, functions=functions, function_call=tool_choice)

    # ------------------------------------------------------------------
    # Token / usage tracking
    # ------------------------------------------------------------------

    def _accumulate_usage(self, usage: TokenUsage) -> None:
        self._total_usage.prompt_tokens += usage.prompt_tokens
        self._total_usage.completion_tokens += usage.completion_tokens
        self._total_usage.total_tokens += usage.total_tokens

    def get_total_usage(self) -> TokenUsage:
        """Return cumulative token usage across all requests this session."""
        return self._total_usage

    def reset_usage(self) -> None:
        """Reset session-level token counters."""
        self._total_usage = TokenUsage(model=self.config.model)

    # ------------------------------------------------------------------
    # Provider metadata
    # ------------------------------------------------------------------

    @staticmethod
    def list_models() -> List[str]:
        """Return the list of supported model identifiers."""
        return OpenAIModel.values()

    def __repr__(self) -> str:
        return f"OpenAIProvider(model={self.config.model!r})"


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def create_openai_provider(settings: Dict[str, Any]) -> OpenAIProvider:
    """
    Convenience factory that builds an ``OpenAIProvider`` from a settings dict.

    Expected keys:
      - ``openai_api_key`` (required)
      - ``openai_model``   (optional, default gpt-4o)
      - ``openai_org``     (optional)
      - ``openai_max_tokens`` (optional)
      - ``openai_temperature`` (optional)
    """
    config = OpenAIConfig(
        api_key=settings["openai_api_key"],
        model=settings.get("openai_model", OpenAIModel.GPT_4O),
        organization=settings.get("openai_org"),
        max_tokens=int(settings.get("openai_max_tokens", 4096)),
        temperature=float(settings.get("openai_temperature", 0.7)),
    )
    return OpenAIProvider(config)
