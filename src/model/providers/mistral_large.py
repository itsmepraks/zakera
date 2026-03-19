"""
Mistral Large provider for Zakera AI Chat Agent.

Supports mistral-large-latest and mistral-medium-latest via
Mistral AI's REST API with native tool-calling and SSE streaming.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MISTRAL_API_BASE = "https://api.mistral.ai/v1"

SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
    "mistral-large-latest": {
        "context_window": 128_000,
        "prompt_price_per_1m": 3.00,
        "completion_price_per_1m": 9.00,
        "supports_vision": False,
        "supports_function_calling": True,
        "supports_json_mode": True,
    },
    "mistral-medium-latest": {
        "context_window": 32_000,
        "prompt_price_per_1m": 0.40,
        "completion_price_per_1m": 2.00,
        "supports_vision": False,
        "supports_function_calling": True,
        "supports_json_mode": True,
    },
    "open-mistral-nemo": {
        "context_window": 128_000,
        "prompt_price_per_1m": 0.15,
        "completion_price_per_1m": 0.15,
        "supports_vision": False,
        "supports_function_calling": True,
        "supports_json_mode": True,
    },
}

DEFAULT_MODEL = "mistral-large-latest"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MistralProviderError(Exception):
    """Base error for MistralLargeProvider."""


class RateLimitError(MistralProviderError):
    """Raised when the Mistral API returns HTTP 429."""


class AuthenticationError(MistralProviderError):
    """Raised when the Mistral API returns HTTP 401."""


# ---------------------------------------------------------------------------
# Provider implementation
# ---------------------------------------------------------------------------

class MistralLargeProvider:
    """
    Zakera provider for Mistral AI models.

    Usage::

        provider = MistralLargeProvider(model_name="mistral-large-latest")
        response = await provider.generate(messages=[{"role": "user", "content": "Hello"}])
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ) -> None:
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported Mistral model '{model_name}'. "
                f"Choose from: {list(SUPPORTED_MODELS)}"
            )

        self.model_name = model_name
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY environment variable is not set. "
                "Get your key at https://console.mistral.ai/"
            )

        self.timeout = timeout
        self._model_meta = SUPPORTED_MODELS[model_name]
        self._client = httpx.AsyncClient(
            base_url=MISTRAL_API_BASE,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        *,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Send a blocking (non-streaming) chat completion request.

        Returns a standardised response dict::

            {
                "content": str,
                "tool_calls": list,
                "finish_reason": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
                "model": str,
                "provider": "mistral_large",
            }
        """
        payload = self._build_payload(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            stream=False,
            **extra_kwargs,
        )

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self._client.post("/chat/completions", json=payload)
                self._raise_for_status(resp)
                data = resp.json()
                return self._parse_response(data)

            except RateLimitError:
                if attempt == MAX_RETRIES:
                    raise
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Mistral rate limit hit, retrying in %.1fs (attempt %d/%d)",
                    delay, attempt, MAX_RETRIES,
                )
                time.sleep(delay)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Mistral server error %d, retrying in %.1fs",
                        exc.response.status_code, delay,
                    )
                    time.sleep(delay)
                else:
                    raise MistralProviderError(
                        f"Mistral API error {exc.response.status_code}: {exc.response.text}"
                    ) from exc

        # Should be unreachable
        raise MistralProviderError("Max retries exceeded")

    async def generate_stream(
        self,
        messages: List[Dict[str, Any]],
        *,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
        **extra_kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a chat completion via SSE.

        Yields standardised StreamChunk dicts::

            {
                "type": "delta" | "tool_call" | "done",
                "delta": str,           # for type="delta"
                "tool_calls": list,     # for type="tool_call"
                "finish_reason": str,   # for type="done"
                "usage": {...},         # for type="done" (may be None)
            }
        """
        payload = self._build_payload(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            stream=True,
            **extra_kwargs,
        )

        async with self._client.stream("POST", "/chat/completions", json=payload) as resp:
            self._raise_for_status(resp)

            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue

                raw = line[len("data:"):].strip()
                if raw == "[DONE]":
                    break

                try:
                    chunk_data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("Skipping non-JSON SSE chunk: %s", raw)
                    continue

                choice = (chunk_data.get("choices") or [{}])[0]
                delta = choice.get("delta", {})
                finish_reason = choice.get("finish_reason")
                usage = chunk_data.get("usage")

                # Text delta
                text = delta.get("content")
                if text:
                    yield {"type": "delta", "delta": text}

                # Tool-call chunks
                tool_calls = delta.get("tool_calls")
                if tool_calls:
                    yield {"type": "tool_call", "tool_calls": tool_calls}

                # Final chunk
                if finish_reason:
                    yield {
                        "type": "done",
                        "finish_reason": finish_reason,
                        "usage": usage,
                    }

    async def count_tokens(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> int:
        """
        Return an accurate server-side token count for *messages*.

        Falls back to a tiktoken cl100k_base estimate if the /tokenize
        endpoint is unavailable (e.g., during unit tests with mocked HTTP).
        """
        try:
            msgs = self._prepend_system(messages, system_prompt)
            resp = await self._client.post(
                "/tokenize",
                json={"model": self.model_name, "messages": msgs},
            )
            self._raise_for_status(resp)
            return resp.json().get("count", 0)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Token count fallback triggered: %s", exc)
            # Rough estimate: 4 chars ≈ 1 token
            total_chars = sum(
                len(str(m.get("content", ""))) for m in messages
            )
            if system_prompt:
                total_chars += len(system_prompt)
            return total_chars // 4

    def get_provider_info(self) -> Dict[str, Any]:
        """Return metadata used by the model-selector UI."""
        meta = self._model_meta
        return {
            "provider": "mistral_large",
            "model": self.model_name,
            "context_window": meta["context_window"],
            "pricing": {
                "prompt_per_1m_tokens": meta["prompt_price_per_1m"],
                "completion_per_1m_tokens": meta["completion_price_per_1m"],
                "currency": "USD",
            },
            "capabilities": {
                "streaming": True,
                "function_calling": meta["supports_function_calling"],
                "vision": meta["supports_vision"],
                "json_mode": meta["supports_json_mode"],
            },
            "supported_models": list(SUPPORTED_MODELS),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        *,
        system_prompt: Optional[str],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        stream: bool,
        **extra_kwargs: Any,
    ) -> Dict[str, Any]:
        msgs = self._prepend_system(messages, system_prompt)
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        if tools:
            payload["tools"] = self._convert_tools_to_mistral(tools)
            payload["tool_choice"] = tool_choice

        payload.update(extra_kwargs)
        return payload

    @staticmethod
    def _prepend_system(
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Inject a system message at position 0 when provided."""
        if not system_prompt:
            return messages
        system_msg = {"role": "system", "content": system_prompt}
        # Avoid duplicating if the caller already included a system message
        if messages and messages[0].get("role") == "system":
            return messages
        return [system_msg] + messages

    @staticmethod
    def _convert_tools_to_mistral(
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert internal ToolDefinition dicts to Mistral's tools[] schema.

        Internal format::

            {
                "name": "get_weather",
                "description": "...",
                "parameters": {"type": "object", "properties": {...}},
            }

        Mistral format::

            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "...",
                    "parameters": {...},
                },
            }
        """
        mistral_tools = []
        for tool in tools:
            mistral_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return mistral_tools

    @staticmethod
    def _parse_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise a non-streaming Mistral API response."""
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {})

        return {
            "content": message.get("content") or "",
            "tool_calls": message.get("tool_calls") or [],
            "finish_reason": choice.get("finish_reason", "stop"),
            "usage": data.get("usage", {}),
            "model": data.get("model", ""),
            "provider": "mistral_large",
        }

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise typed exceptions for known HTTP error codes."""
        if response.status_code == 200:
            return
        if response.status_code == 401:
            raise AuthenticationError(
                "Invalid or missing MISTRAL_API_KEY. "
                "Verify your key at https://console.mistral.ai/"
            )
        if response.status_code == 429:
            raise RateLimitError("Mistral AI rate limit exceeded. Retrying…")
        response.raise_for_status()

    async def __aenter__(self) -> "MistralLargeProvider":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()
