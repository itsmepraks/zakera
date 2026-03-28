"""
Meta Llama 3 provider for Zakera AI Chat Agent.

Routes Llama 3 requests through the Groq inference API, which offers
low-latency access to llama3-8b-8192, llama3-70b-8192, and the reasoning
variant llama-3.1-405b-reasoning.  The implementation follows the same
pattern as providers_groq.py and providers_deepseek.py so it plugs
seamlessly into the existing ModelManager routing logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model catalogue
# ---------------------------------------------------------------------------

LLAMA3_MODELS: Dict[str, Dict[str, Any]] = {
    "llama3-8b-8192": {
        "display_name": "Llama 3 8B",
        "context_window": 8192,
        "supports_function_calling": True,
        "supports_streaming": True,
        "input_cost_per_1k_tokens": 0.00005,
        "output_cost_per_1k_tokens": 0.00010,
        "description": "Fast, efficient Llama 3 8B model via Groq",
    },
    "llama3-70b-8192": {
        "display_name": "Llama 3 70B",
        "context_window": 8192,
        "supports_function_calling": True,
        "supports_streaming": True,
        "input_cost_per_1k_tokens": 0.00059,
        "output_cost_per_1k_tokens": 0.00079,
        "description": "High-capability Llama 3 70B model via Groq",
    },
    "llama-3.1-405b-reasoning": {
        "display_name": "Llama 3.1 405B Reasoning",
        "context_window": 131072,
        "supports_function_calling": True,
        "supports_streaming": True,
        "input_cost_per_1k_tokens": 0.00300,
        "output_cost_per_1k_tokens": 0.00300,
        "description": "State-of-the-art Llama 3.1 405B reasoning model via Groq",
    },
}

DEFAULT_MODEL = "llama3-70b-8192"
GROQ_CHAT_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0  # seconds


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


@dataclass
class LlamaMessage:
    """A single chat message in Llama 3 format."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class LlamaResponse:
    """Normalised response from a Llama 3 completion."""

    content: str
    model: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    cost_usd: float = 0.0

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


class LlamaProvider:
    """
    Async provider for Meta Llama 3 models running on Groq infrastructure.

    Usage::

        provider = LlamaProvider(api_key="gsk_...")
        response = await provider.chat(
            messages=[{"role": "user", "content": "Hello!"}],
            model="llama3-70b-8192",
        )
        print(response.content)
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        if not api_key:
            raise ValueError("A valid Groq API key is required for LlamaProvider.")
        if default_model not in LLAMA3_MODELS:
            raise ValueError(
                f"Unknown Llama model '{default_model}'. "
                f"Available: {list(LLAMA3_MODELS.keys())}"
            )

        self._api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        system_prompt: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> LlamaResponse:
        """
        Send a chat completion request and return a normalised response.

        Args:
            messages: List of message dicts with at least ``role`` and
                ``content`` keys.
            model: Llama model identifier (defaults to ``self.default_model``).
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens to generate.
            top_p: Nucleus sampling parameter.
            tools: OpenAI-compatible tool/function definitions.
            tool_choice: How the model selects tools ("auto", "none", or a
                specific tool name).
            system_prompt: If provided, prepended as a system message.
            stop_sequences: List of stop sequences.

        Returns:
            A :class:`LlamaResponse` with the generated content and usage.
        """
        resolved_model = model or self.default_model
        self._validate_model(resolved_model)

        payload = self._build_payload(
            messages=messages,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            tools=tools,
            tool_choice=tool_choice,
            system_prompt=system_prompt,
            stop_sequences=stop_sequences,
            stream=False,
        )

        start = time.monotonic()
        raw = await self._post_with_retry(payload)
        latency_ms = (time.monotonic() - start) * 1000

        return self._parse_response(raw, resolved_model, latency_ms)

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion, yielding text delta chunks as they arrive.

        Each yielded value is a decoded UTF-8 string fragment.
        The iterator raises :class:`StopAsyncIteration` after the final chunk.
        """
        resolved_model = model or self.default_model
        self._validate_model(resolved_model)

        payload = self._build_payload(
            messages=messages,
            model=resolved_model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            tools=tools,
            tool_choice="auto" if tools else None,
            system_prompt=system_prompt,
            stream=True,
        )

        client = await self._get_client()
        async with client.stream("POST", GROQ_CHAT_ENDPOINT, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[len("data: "):].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content") or ""
                    )
                    if delta:
                        yield delta
                except (json.JSONDecodeError, IndexError, KeyError):
                    logger.debug("Skipping malformed SSE chunk: %s", data)
                    continue

    def list_models(self) -> List[Dict[str, Any]]:
        """Return metadata for all supported Llama 3 models."""
        return [
            {"id": model_id, **meta}
            for model_id, meta in LLAMA3_MODELS.items()
        ]

    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Return metadata for a specific model."""
        if model_id not in LLAMA3_MODELS:
            raise ValueError(f"Unknown model '{model_id}'.")
        return {"id": model_id, **LLAMA3_MODELS[model_id]}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_model(self, model: str) -> None:
        if model not in LLAMA3_MODELS:
            raise ValueError(
                f"Unsupported Llama model '{model}'. "
                f"Choose from: {list(LLAMA3_MODELS.keys())}"
            )

    def _build_payload(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float,
        stream: bool,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        system_prompt: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Assemble the JSON payload for the Groq chat completions endpoint."""
        all_messages: List[Dict[str, Any]] = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice
        if stop_sequences:
            payload["stop"] = stop_sequences
        return payload

    async def _post_with_retry(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """POST with exponential back-off on 429/5xx responses."""
        client = await self._get_client()
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = await client.post(GROQ_CHAT_ENDPOINT, json=payload)
                if resp.status_code == 429:
                    wait = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        "Groq rate limit hit; retrying in %.1fs (attempt %d/%d)",
                        wait,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code < 500:
                    raise
                wait = BASE_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    "Groq server error %d; retrying in %.1fs",
                    exc.response.status_code,
                    wait,
                )
                await asyncio.sleep(wait)
            except httpx.RequestError as exc:
                last_error = exc
                wait = BASE_RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    "Request error on attempt %d: %s", attempt + 1, exc
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"LlamaProvider: all {self.max_retries} retry attempts failed."
        ) from last_error

    def _parse_response(
        self,
        raw: Dict[str, Any],
        model: str,
        latency_ms: float,
    ) -> LlamaResponse:
        """Convert a raw Groq API response into a :class:`LlamaResponse`."""
        choice = raw["choices"][0]
        message = choice["message"]
        usage = raw.get("usage", {})

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # Estimate cost
        model_meta = LLAMA3_MODELS.get(model, {})
        input_rate = model_meta.get("input_cost_per_1k_tokens", 0.0)
        output_rate = model_meta.get("output_cost_per_1k_tokens", 0.0)
        cost = (
            prompt_tokens / 1000 * input_rate
            + completion_tokens / 1000 * output_rate
        )

        tool_calls = [
            {
                "id": tc["id"],
                "type": tc["type"],
                "function": tc["function"],
            }
            for tc in message.get("tool_calls") or []
        ]

        return LlamaResponse(
            content=message.get("content") or "",
            model=raw.get("model", model),
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            tool_calls=tool_calls,
            latency_ms=latency_ms,
            cost_usd=cost,
        )


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_llama_provider(
    api_key: str,
    model: str = DEFAULT_MODEL,
    **kwargs: Any,
) -> LlamaProvider:
    """
    Factory function wired into the ModelManager provider registry.

    Args:
        api_key: Groq API key with Llama access.
        model: Default model identifier.
        **kwargs: Additional arguments forwarded to :class:`LlamaProvider`.
    """
    return LlamaProvider(api_key=api_key, default_model=model, **kwargs)
