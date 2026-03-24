"""
xAI Grok-2 and Grok-2-Vision provider implementation.

Supports:
- grok-2-latest          : flagship text model
- grok-2-vision-latest   : multimodal (text + image) model

Ref: https://docs.x.ai/api
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAI_API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-2-latest"
DEFAULT_VISION_MODEL = "grok-2-vision-latest"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------

class XAIModel(str, Enum):
    GROK_2 = "grok-2-latest"
    GROK_2_MINI = "grok-2-mini-latest"
    GROK_2_VISION = "grok-2-vision-latest"


@dataclass
class XAIConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = 1.0
    timeout: float = 60.0
    max_retries: int = MAX_RETRIES
    base_url: str = XAI_API_BASE
    extra_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class XAIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class XAIResponse:
    content: str
    model: str
    usage: XAIUsage
    finish_reason: str = "stop"
    raw: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class XAIProviderError(Exception):
    """Base exception for xAI provider errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class XAIAuthError(XAIProviderError):
    """Raised when the API key is invalid or missing."""


class XAIRateLimitError(XAIProviderError):
    """Raised when the rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class XAIContextLengthError(XAIProviderError):
    """Raised when the prompt exceeds the model's context window."""


class XAIServiceError(XAIProviderError):
    """Raised on 5xx responses from the xAI API."""


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def build_text_message(role: str, content: str) -> Dict[str, Any]:
    """Build a plain-text chat message dict."""
    return {"role": role, "content": content}


def build_vision_message(
    role: str,
    text: str,
    images: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a multimodal message for Grok-2-Vision.

    Parameters
    ----------
    role:   "user" or "assistant"
    text:   text portion of the message
    images: list of image URLs *or* raw bytes encoded as data-URIs
            ("data:image/jpeg;base64,...")
    """
    content: List[Dict[str, Any]] = [{"type": "text", "text": text}]
    for img in images or []:
        if img.startswith("data:"):
            content.append({"type": "image_url", "image_url": {"url": img}})
        else:
            content.append({"type": "image_url", "image_url": {"url": img}})
    return {"role": role, "content": content}


def encode_image_to_data_uri(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Convert raw image bytes to a base64 data URI."""
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:{mime_type};base64,{b64}"


# ---------------------------------------------------------------------------
# Core provider class
# ---------------------------------------------------------------------------

class XAIGrok2Provider:
    """
    Async provider for xAI Grok-2 / Grok-2-Vision.

    Usage
    -----
    .. code-block:: python

        config = XAIConfig(api_key=os.environ["XAI_API_KEY"])
        provider = XAIGrok2Provider(config)

        response = await provider.complete(
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(response.content)

        # Streaming
        async for chunk in provider.stream(
            messages=[{"role": "user", "content": "Write a poem."}]
        ):
            print(chunk, end="", flush=True)
    """

    def __init__(self, config: XAIConfig) -> None:
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> XAIResponse:
        """
        Send a non-streaming chat completion request.

        Returns
        -------
        XAIResponse
            Parsed response including content, usage statistics, and finish reason.
        """
        payload = self._build_payload(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            stream=False,
            **kwargs,
        )
        raw = await self._request_with_retry(payload)
        return self._parse_response(raw)

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Send a streaming chat completion request.

        Yields
        ------
        str
            Text delta chunks as they arrive from the server.
        """
        payload = self._build_payload(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            stream=True,
            **kwargs,
        )
        async for chunk in self._stream_request(payload):
            yield chunk

    async def health_check(self) -> bool:
        """
        Perform a lightweight health-check against the xAI API.

        Returns True if the API is reachable and the key is valid.
        """
        try:
            await self.complete(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except XAIAuthError:
            logger.error("xAI health check failed: invalid API key")
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("xAI health check failed: %s", exc)
            return False

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "XAIGrok2Provider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                    **self.config.extra_headers,
                },
            )
        return self._client

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        system_prompt: Optional[str],
        stream: bool,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        effective_model = model or self.config.model
        effective_max_tokens = max_tokens or self.config.max_tokens
        effective_temperature = temperature if temperature is not None else self.config.temperature

        all_messages: List[Dict[str, Any]] = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": effective_model,
            "messages": all_messages,
            "max_tokens": effective_max_tokens,
            "temperature": effective_temperature,
            "top_p": self.config.top_p,
            "stream": stream,
        }
        payload.update(kwargs)
        return payload

    async def _request_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        last_exc: Exception = RuntimeError("Unreachable")
        for attempt in range(self.config.max_retries):
            try:
                client = self._get_client()
                response = await client.post("/chat/completions", json=payload)
                return self._handle_response(response)
            except XAIRateLimitError as exc:
                last_exc = exc
                delay = exc.retry_after or (RETRY_BASE_DELAY * 2**attempt)
                logger.warning(
                    "xAI rate limit hit (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    self.config.max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
            except XAIServiceError as exc:
                last_exc = exc
                delay = RETRY_BASE_DELAY * 2**attempt
                logger.warning(
                    "xAI service error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    self.config.max_retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
            except (XAIAuthError, XAIContextLengthError):
                # Non-retryable errors
                raise
        raise last_exc

    async def _stream_request(
        self, payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            self._raise_for_status(response)
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]  # strip "data: "
                if data == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    text = delta.get("content") or ""
                    if text:
                        yield text
                except (KeyError, ValueError) as exc:
                    logger.debug("Skipping unparseable SSE chunk: %s — %s", data, exc)

    @staticmethod
    def _handle_response(response: httpx.Response) -> Dict[str, Any]:
        XAIGrok2Provider._raise_for_status(response)
        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 200:
            return
        try:
            body = response.json()
            message = body.get("error", {}).get("message", response.text)
        except Exception:  # noqa: BLE001
            message = response.text

        if response.status_code == 401:
            raise XAIAuthError(f"Authentication failed: {message}", 401)
        if response.status_code == 429:
            retry_after = None
            try:
                retry_after = float(response.headers.get("retry-after", 0))
            except (TypeError, ValueError):
                pass
            raise XAIRateLimitError(f"Rate limit exceeded: {message}", retry_after)
        if response.status_code == 400 and "context" in message.lower():
            raise XAIContextLengthError(f"Context length exceeded: {message}", 400)
        if response.status_code >= 500:
            raise XAIServiceError(f"xAI service error ({response.status_code}): {message}", response.status_code)
        raise XAIProviderError(f"xAI API error ({response.status_code}): {message}", response.status_code)

    @staticmethod
    def _parse_response(raw: Dict[str, Any]) -> XAIResponse:
        choice = raw["choices"][0]
        content = choice["message"].get("content") or ""
        finish_reason = choice.get("finish_reason", "stop")
        usage_data = raw.get("usage", {})
        usage = XAIUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )
        return XAIResponse(
            content=content,
            model=raw.get("model", DEFAULT_MODEL),
            usage=usage,
            finish_reason=finish_reason,
            raw=raw,
        )
