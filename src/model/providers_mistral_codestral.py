"""
Mistral Codestral Provider for Zakera AI Chat Agent.

Supports:
- Standard chat completions (streaming + non-streaming)
- Fill-in-the-Middle (FIM) completions for code generation
- Async-first design compatible with the existing provider interface

Models:
    CODESTRAL_LATEST   - latest stable Codestral checkpoint
    CODESTRAL_2501     - Codestral January 2025 snapshot

Usage::

    provider = MistralCodestralProvider(
        api_key=os.environ["MISTRAL_CODESTRAL_API_KEY"]
    )
    async for chunk in provider.stream_chat(messages):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

CODESTRAL_LATEST = "codestral-latest"
CODESTRAL_2501 = "codestral-2501"

_CODESTRAL_CHAT_URL = "https://codestral.mistral.ai/v1/chat/completions"
_CODESTRAL_FIM_URL = "https://codestral.mistral.ai/v1/fim/completions"

_DEFAULT_TIMEOUT = 120.0  # seconds
_DEFAULT_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # exponential back-off


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CodestralMessage:
    """A single chat message compatible with the Mistral chat API."""

    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class CodestralConfig:
    """Runtime configuration for a single Codestral request."""

    model: str = CODESTRAL_LATEST
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 1024
    stop: List[str] = field(default_factory=list)
    safe_prompt: bool = False
    stream: bool = True


@dataclass
class FIMRequest:
    """Parameters for a Fill-in-the-Middle completion request."""

    prompt: str
    suffix: str = ""
    model: str = CODESTRAL_LATEST
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 512
    stop: List[str] = field(default_factory=lambda: ["\n\n"])
    stream: bool = False


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class MistralCodestralProvider:
    """
    Async provider wrapping Mistral's Codestral endpoints.

    Supports:
    * ``stream_chat()``   – streaming chat completions (SSE)
    * ``chat()``          – non-streaming chat completion
    * ``complete_fim()``  – Fill-in-the-Middle code completion
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        if not api_key:
            raise ValueError(
                "MISTRAL_CODESTRAL_API_KEY must be set to use the Codestral provider."
            )
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def stream_chat(
        self,
        messages: List[CodestralMessage],
        config: Optional[CodestralConfig] = None,
    ) -> AsyncIterator[str]:
        """
        Yield text delta chunks from a streaming chat completion.

        Args:
            messages: Conversation history as ``CodestralMessage`` objects.
            config:   Optional ``CodestralConfig``; defaults are used if omitted.

        Yields:
            Incremental text strings as they arrive from the API.
        """
        cfg = config or CodestralConfig(stream=True)
        cfg.stream = True
        payload = self._build_chat_payload(messages, cfg)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                _CODESTRAL_CHAT_URL,
                headers=self._headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    chunk = self._parse_sse_line(line)
                    if chunk is not None:
                        yield chunk

    async def chat(
        self,
        messages: List[CodestralMessage],
        config: Optional[CodestralConfig] = None,
    ) -> str:
        """
        Return the full assistant reply as a single string (non-streaming).

        Args:
            messages: Conversation history.
            config:   Optional request configuration.

        Returns:
            The assistant's complete response text.
        """
        cfg = config or CodestralConfig(stream=False)
        cfg.stream = False
        payload = self._build_chat_payload(messages, cfg)

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        _CODESTRAL_CHAT_URL,
                        headers=self._headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                if attempt < self._max_retries - 1:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Codestral chat attempt %d/%d failed (%s). Retrying in %.1fs.",
                        attempt + 1,
                        self._max_retries,
                        exc,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        # Should never reach here
        raise RuntimeError("Max retries exhausted for Codestral chat request.")

    async def complete_fim(
        self,
        request: FIMRequest,
    ) -> str:
        """
        Perform a Fill-in-the-Middle completion.

        Useful for code completion scenarios where the model must fill a
        gap between a known *prefix* (``prompt``) and *suffix* (``suffix``).

        Args:
            request: A ``FIMRequest`` describing the code context.

        Returns:
            The generated in-fill text.
        """
        payload: Dict[str, Any] = {
            "model": request.model,
            "prompt": request.prompt,
            "suffix": request.suffix,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "stream": request.stream,
        }
        if request.stop:
            payload["stop"] = request.stop

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                _CODESTRAL_FIM_URL,
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_chat_payload(
        self,
        messages: List[CodestralMessage],
        config: CodestralConfig,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": config.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "stream": config.stream,
            "safe_prompt": config.safe_prompt,
        }
        if config.stop:
            payload["stop"] = config.stop
        return payload

    @staticmethod
    def _parse_sse_line(line: str) -> Optional[str]:
        """Extract text delta from a Server-Sent Events line.

        Returns ``None`` for non-data lines or the [DONE] sentinel.
        """
        if not line.startswith("data: "):
            return None
        raw = line[len("data: "):].strip()
        if raw == "[DONE]":
            return None
        try:
            import json
            payload = json.loads(raw)
            choices = payload.get("choices", [])
            if not choices:
                return None
            delta = choices[0].get("delta", {})
            return delta.get("content")  # may be None for role-only deltas
        except Exception:  # noqa: BLE001
            logger.debug("Failed to parse SSE line: %r", line)
            return None

    def __repr__(self) -> str:
        return (
            f"MistralCodestralProvider("
            f"timeout={self._timeout}, "
            f"max_retries={self._max_retries})"
        )
