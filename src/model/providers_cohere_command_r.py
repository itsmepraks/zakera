"""
Cohere Command R / Command R+ Provider for Zakera AI Chat Agent.

Supports:
  - Command R and Command R+ with streaming and non-streaming modes
  - Native tool-use (function calling) via Cohere's tool schema
  - RAG / grounded generation with document injection
  - Citation extraction from grounded responses
  - Automatic retry with exponential back-off
  - Token usage tracking consistent with other Zakera providers
"""

from __future__ import annotations

import asyncio
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

COHERE_API_BASE = "https://api.cohere.com/v2"
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0  # seconds
DEFAULT_TIMEOUT = 120.0  # seconds


# ---------------------------------------------------------------------------
# Enums / data classes
# ---------------------------------------------------------------------------


class CohereModel(str, Enum):
    """Supported Cohere model identifiers."""

    COMMAND_R_PLUS = "command-r-plus"
    COMMAND_R_PLUS_08_2024 = "command-r-plus-08-2024"
    COMMAND_R = "command-r"
    COMMAND_R_08_2024 = "command-r-08-2024"
    COMMAND_R_03_2024 = "command-r-03-2024"

    @classmethod
    def values(cls) -> List[str]:
        return [m.value for m in cls]


@dataclass
class CohereConfig:
    """Configuration for the Cohere Command R provider."""

    api_key: str
    model: str = CohereModel.COMMAND_R_PLUS
    api_base: str = COHERE_API_BASE
    max_tokens: int = 4096
    temperature: float = 0.3
    top_p: float = 0.75
    top_k: int = 0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    max_retries: int = DEFAULT_MAX_RETRIES
    timeout: float = DEFAULT_TIMEOUT
    # RAG preamble override
    preamble: Optional[str] = None

    def __post_init__(self) -> None:
        if self.model not in CohereModel.values():
            raise ValueError(
                f"Unsupported Cohere model '{self.model}'. "
                f"Choose from: {CohereModel.values()}"
            )
        if not self.api_key:
            raise ValueError("Cohere api_key must not be empty.")


@dataclass
class CohereTokenUsage:
    """Tracks token consumption for a single Cohere request."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    request_id: Optional[str] = None

    @classmethod
    def from_response(cls, data: Dict[str, Any], model: str, request_id: Optional[str] = None) -> "CohereTokenUsage":
        usage = data.get("usage", {}).get("billed_units", {})
        input_tok = usage.get("input_tokens", 0)
        output_tok = usage.get("output_tokens", 0)
        return cls(
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=input_tok + output_tok,
            model=model,
            request_id=request_id,
        )


@dataclass
class CohereTool:
    """Describes a callable tool for the Cohere model."""

    name: str
    description: str
    parameters_definitions: Dict[str, Any]  # name -> {description, type, required}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameter_definitions": self.parameters_definitions,
        }


@dataclass
class CohereDocument:
    """A document chunk for Cohere RAG grounding."""

    id: str
    data: Dict[str, str]  # e.g. {"title": "...", "text": "..."}

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "data": self.data}


@dataclass
class CohereCitation:
    """A citation returned by a grounded Cohere response."""

    start: int
    end: int
    text: str
    sources: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CohereCitation":
        return cls(
            start=data.get("start", 0),
            end=data.get("end", 0),
            text=data.get("text", ""),
            sources=data.get("sources", []),
        )


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


def build_cohere_message(role: str, content: str) -> Dict[str, Any]:
    """Build a Cohere chat message dict. Role must be 'user' or 'assistant'."""
    cohere_role = "USER" if role.lower() == "user" else "CHATBOT"
    return {"role": cohere_role, "message": content}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class CohereCommandRProvider:
    """
    Async Cohere Command R / Command R+ provider.

    Implements the Zakera provider interface for grounded, tool-aware chat.

    Usage::

        config = CohereConfig(api_key="...", model="command-r-plus")
        provider = CohereCommandRProvider(config)

        # Non-streaming
        response = await provider.chat(messages)

        # Streaming
        async for chunk in provider.stream_chat(messages):
            print(chunk, end="", flush=True)

        # RAG / grounded generation
        docs = [CohereDocument(id="doc1", data={"title": "...", "text": "..."})]
        response = await provider.chat_with_documents(messages, documents=docs)
    """

    PROVIDER_NAME = "cohere"

    def __init__(self, config: CohereConfig) -> None:
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._total_usage = CohereTokenUsage(model=config.model)

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
                    "Accept": "application/json",
                    "X-Client-Name": "zakera-ai-agent",
                },
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Cleanly close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "CohereCommandRProvider":
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
            # Cohere v2 /models endpoint lists available models
            resp = await client.get("/models")
            if resp.status_code == 200:
                return {"status": "healthy", "provider": self.PROVIDER_NAME, "model": self.config.model}
            return {"status": "degraded", "http_status": resp.status_code, "provider": self.PROVIDER_NAME}
        except Exception as exc:  # noqa: BLE001
            return {"status": "unhealthy", "error": str(exc), "provider": self.PROVIDER_NAME}

    # ------------------------------------------------------------------
    # Request building
    # ------------------------------------------------------------------

    def _build_chat_payload(
        self,
        messages: List[Dict[str, Any]],
        *,
        stream: bool = False,
        tools: Optional[List[CohereTool]] = None,
        documents: Optional[List[CohereDocument]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build the request payload for the Cohere v2 /chat endpoint.

        Cohere v2 uses an OpenAI-compatible message schema with role strings
        'system', 'user', 'assistant', and 'tool'.
        """
        cohere_messages: List[Dict[str, Any]] = []

        # Inject system prompt as first message if provided
        if system_prompt or self.config.preamble:
            cohere_messages.append({
                "role": "system",
                "content": system_prompt or self.config.preamble,
            })

        # Convert incoming messages — accept both Zakera-style and raw Cohere-style
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", msg.get("message", ""))
            if role == "system":
                cohere_messages.append({"role": "system", "content": content})
            elif role in ("user", "human"):
                cohere_messages.append({"role": "user", "content": content})
            else:
                cohere_messages.append({"role": "assistant", "content": content})

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": cohere_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "p": self.config.top_p,
            "k": self.config.top_k,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            "stream": stream,
        }

        if tools:
            payload["tools"] = [t.to_dict() for t in tools]

        if documents:
            payload["documents"] = [d.to_dict() for d in documents]

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
                    "Cohere request failed (status=%s), retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    wait,
                    attempt + 1,
                    self.config.max_retries,
                )
                await asyncio.sleep(wait)
                last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.RequestError as exc:
                wait = DEFAULT_BACKOFF_BASE ** attempt
                logger.warning("Cohere network error: %s, retrying in %.1fs", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc
        raise RuntimeError(f"Cohere request failed after {self.config.max_retries} retries") from last_exc

    # ------------------------------------------------------------------
    # Non-streaming chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[CohereTool]] = None,
        documents: Optional[List[CohereDocument]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a chat request and return the full response.

        Returns a dict with keys:
          - ``content``     (str) — assistant reply text
          - ``usage``       (CohereTokenUsage) — token counts
          - ``citations``   (list[CohereCitation]) — grounding citations if RAG used
          - ``tool_calls``  (list | None) — tool-use results if tools were provided
          - ``finish_reason`` (str)
          - ``model``       (str)
          - ``request_id``  (str | None)
        """
        payload = self._build_chat_payload(
            messages,
            stream=False,
            tools=tools,
            documents=documents,
            system_prompt=system_prompt,
        )
        resp = await self._post_with_retry("/chat", payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Cohere API error {resp.status_code}: {resp.text}")

        data = resp.json()
        request_id = resp.headers.get("x-request-id")
        usage = CohereTokenUsage.from_response(data, model=self.config.model, request_id=request_id)
        self._accumulate_usage(usage)

        # v2 response: message.content is a list of content blocks
        message = data.get("message", {})
        content_blocks = message.get("content", [])
        text_content = ""
        if isinstance(content_blocks, list):
            text_content = "".join(
                block.get("text", "") for block in content_blocks if block.get("type") == "text"
            )
        elif isinstance(content_blocks, str):
            text_content = content_blocks

        # Extract citations
        citations = [
            CohereCitation.from_dict(c)
            for c in data.get("citations", [])
        ]

        # Extract tool calls
        tool_calls = message.get("tool_calls")

        finish_reason = data.get("finish_reason", "")

        return {
            "content": text_content,
            "usage": usage,
            "citations": citations,
            "tool_calls": tool_calls,
            "finish_reason": finish_reason,
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
        tools: Optional[List[CohereTool]] = None,
        documents: Optional[List[CohereDocument]] = None,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Yield text chunks as they arrive from the Cohere streaming API.

        Usage::

            async for token in provider.stream_chat(messages):
                print(token, end="", flush=True)
        """
        payload = self._build_chat_payload(
            messages,
            stream=True,
            tools=tools,
            documents=documents,
            system_prompt=system_prompt,
        )
        client = await self._get_client()
        async with client.stream("POST", "/chat", json=payload) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"Cohere stream error {resp.status_code}: {body.decode()[:200]}")

            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[len("data:"):].strip()
                if not raw or raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    logger.debug("Failed to parse Cohere SSE line: %s", raw)
                    continue

                event_type = event.get("type", "")

                if event_type == "content-delta":
                    delta = event.get("delta", {})
                    message_delta = delta.get("message", {})
                    content_parts = message_delta.get("content", {})
                    text = content_parts.get("text", "")
                    if text:
                        yield text

                elif event_type == "message-end":
                    # Final usage info
                    delta = event.get("delta", {})
                    usage_data = delta.get("usage", {})
                    if usage_data:
                        billed = usage_data.get("billed_units", {})
                        usage = CohereTokenUsage(
                            input_tokens=billed.get("input_tokens", 0),
                            output_tokens=billed.get("output_tokens", 0),
                            total_tokens=billed.get("input_tokens", 0) + billed.get("output_tokens", 0),
                            model=self.config.model,
                        )
                        self._accumulate_usage(usage)

    # ------------------------------------------------------------------
    # RAG / grounded generation convenience method
    # ------------------------------------------------------------------

    async def chat_with_documents(
        self,
        messages: List[Dict[str, Any]],
        documents: List[CohereDocument],
        *,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a grounded chat request with document context.

        The model will use the supplied documents to answer the query
        and return citations linking the response to source passages.

        Args:
            messages: Conversation history.
            documents: Document chunks to ground the response.
            system_prompt: Optional system context.

        Returns:
            Response dict with ``content``, ``citations``, and ``usage``.
        """
        return await self.chat(messages, documents=documents, system_prompt=system_prompt)

    # ------------------------------------------------------------------
    # Tool-use convenience method
    # ------------------------------------------------------------------

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[CohereTool],
        *,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run a chat completion that may invoke one or more tools.

        Returns the response dict with ``tool_calls`` populated when
        the model decides to invoke a function.
        """
        return await self.chat(messages, tools=tools, system_prompt=system_prompt)

    # ------------------------------------------------------------------
    # Token / usage tracking
    # ------------------------------------------------------------------

    def _accumulate_usage(self, usage: CohereTokenUsage) -> None:
        self._total_usage.input_tokens += usage.input_tokens
        self._total_usage.output_tokens += usage.output_tokens
        self._total_usage.total_tokens += usage.total_tokens

    def get_total_usage(self) -> CohereTokenUsage:
        """Return cumulative token usage across all requests this session."""
        return self._total_usage

    def reset_usage(self) -> None:
        """Reset session-level token counters."""
        self._total_usage = CohereTokenUsage(model=self.config.model)

    # ------------------------------------------------------------------
    # Provider metadata
    # ------------------------------------------------------------------

    @staticmethod
    def list_models() -> List[str]:
        """Return the list of supported model identifiers."""
        return CohereModel.values()

    def __repr__(self) -> str:
        return f"CohereCommandRProvider(model={self.config.model!r})"


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def create_cohere_provider(settings: Dict[str, Any]) -> CohereCommandRProvider:
    """
    Convenience factory that builds a ``CohereCommandRProvider`` from a settings dict.

    Expected keys:
      - ``cohere_api_key``   (required)
      - ``cohere_model``     (optional, default command-r-plus)
      - ``cohere_max_tokens`` (optional)
      - ``cohere_temperature`` (optional)
      - ``cohere_preamble``  (optional system preamble)
    """
    config = CohereConfig(
        api_key=settings["cohere_api_key"],
        model=settings.get("cohere_model", CohereModel.COMMAND_R_PLUS),
        max_tokens=int(settings.get("cohere_max_tokens", 4096)),
        temperature=float(settings.get("cohere_temperature", 0.3)),
        preamble=settings.get("cohere_preamble"),
    )
    return CohereCommandRProvider(config)
