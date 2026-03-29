"""
Cohere Command R+ Provider

Implements the multi-provider LLM interface for Cohere's Command R+ model,
supporting streaming responses, tool/function calling, and context-aware
retrieval-augmented generation (RAG) grounding.

Model: command-r-plus-08-2024
Context Window: 128K tokens
Key strengths: RAG, multi-step tool use, multilingual
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COHERE_API_BASE = "https://api.cohere.com/v2"
DEFAULT_MODEL_ID = "command-r-plus-08-2024"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.3
REQUEST_TIMEOUT = 120.0  # seconds


# ---------------------------------------------------------------------------
# Provider class
# ---------------------------------------------------------------------------


class CohereCommandRPlusProvider:
    """
    LLM provider for Cohere Command R+ (command-r-plus-08-2024).

    Supports:
    - Synchronous and streaming chat completions via Cohere's v2 API.
    - Tool/function calling with automatic JSON schema translation.
    - Citation and grounding metadata passthrough.

    Usage::

        provider = CohereCommandRPlusProvider(api_key="co-...")
        response = await provider.generate(
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print(response["content"])
    """

    # ------------------------------------------------------------------ #
    # Class-level metadata consumed by ModelManager / provider registry   #
    # ------------------------------------------------------------------ #

    model_id: str = DEFAULT_MODEL_ID
    provider_name: str = "cohere"
    display_name: str = "Cohere Command R+"
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    max_context_tokens: int = 128_000
    max_output_tokens: int = DEFAULT_MAX_TOKENS

    # Cost per 1 K tokens (USD) — approximate as of 2024-Q4
    cost_per_1k_input_tokens: float = 0.003
    cost_per_1k_output_tokens: float = 0.015

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL_ID,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        """
        Initialise the Command R+ provider.

        Args:
            api_key: Cohere API key (starts with ``co-``).
            model: Model identifier. Defaults to ``command-r-plus-08-2024``.
            max_tokens: Maximum tokens to generate per request.
            temperature: Sampling temperature (0.0 – 1.0).
            timeout: HTTP request timeout in seconds.
        """
        if not api_key:
            raise ValueError("Cohere API key must not be empty.")

        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        self._http_client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-initialised async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=COHERE_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Client-Name": "zakera",
                },
                timeout=self.timeout,
            )
        return self._http_client

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Construct the JSON payload for the Cohere v2 chat endpoint.

        Args:
            messages: Conversation history in OpenAI-compatible format.
            tools: Optional list of tool schemas (OpenAI function format).
            stream: Whether to request a streaming response.
            **kwargs: Additional overrides (e.g., ``temperature``, ``max_tokens``).

        Returns:
            A dictionary ready to be serialised and sent as the request body.
        """
        # Separate system prompt from chat turns
        system_content: Optional[str] = None
        chat_messages: List[Dict[str, str]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_content = content
            else:
                chat_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": stream,
        }

        if system_content:
            payload["system"] = system_content

        if tools:
            payload["tools"] = self._translate_tools(tools)

        return payload

    @staticmethod
    def _translate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Translate OpenAI-style function schemas to Cohere tool format.

        Args:
            tools: List of tool definitions using OpenAI's function schema.

        Returns:
            List of tool definitions in Cohere's v2 format.
        """
        cohere_tools: List[Dict[str, Any]] = []
        for tool in tools:
            fn = tool.get("function", tool)
            cohere_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": fn.get("name", ""),
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", {}),
                    },
                }
            )
        return cohere_tools

    @staticmethod
    def _extract_tool_calls(response_body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse tool call stubs from a Cohere response body.

        Args:
            response_body: Raw response JSON from the Cohere API.

        Returns:
            List of normalised tool-call dicts with ``name`` and ``arguments``.
        """
        tool_calls: List[Dict[str, Any]] = []
        message = response_body.get("message", {})
        for tc in message.get("tool_calls", []):
            fn = tc.get("function", {})
            tool_calls.append(
                {
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "arguments": fn.get("arguments", {}),
                }
            )
        return tool_calls

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a single (non-streaming) chat completion.

        Args:
            messages: Conversation history.  Each entry must have ``role``
                      and ``content`` keys.
            tools: Optional tool/function definitions.
            **kwargs: Overrides for ``model``, ``max_tokens``, ``temperature``.

        Returns:
            A dictionary with keys:
            - ``content`` (str): The assistant's reply.
            - ``model`` (str): Model identifier echoed from the response.
            - ``usage`` (dict): Token counts — ``prompt_tokens``,
              ``completion_tokens``, ``total_tokens``.
            - ``tool_calls`` (list): Parsed tool-call stubs (may be empty).
            - ``finish_reason`` (str): Stop reason from the API.
        """
        client = await self._get_client()
        payload = self._build_payload(messages, tools=tools, stream=False, **kwargs)

        logger.debug("CohereCommandRPlus.generate → %s tokens requested", payload["max_tokens"])

        try:
            response = await client.post("/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Cohere API error %s: %s", exc.response.status_code, exc.response.text
            )
            raise

        body = response.json()

        # Extract assistant text
        message = body.get("message", {})
        content_blocks = message.get("content", [])
        content = (
            content_blocks[0].get("text", "") if content_blocks else ""
        )

        usage = body.get("usage", {})
        billed = usage.get("billed_units", {})

        return {
            "content": content,
            "model": body.get("model", self.model),
            "usage": {
                "prompt_tokens": billed.get("input_tokens", 0),
                "completion_tokens": billed.get("output_tokens", 0),
                "total_tokens": billed.get("input_tokens", 0) + billed.get("output_tokens", 0),
            },
            "tool_calls": self._extract_tool_calls(body),
            "finish_reason": body.get("finish_reason", ""),
            "citations": body.get("citations", []),  # RAG grounding
        }

    async def stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a chat completion, yielding incremental chunks.

        Each yielded chunk is a dict with:
        - ``delta`` (str): Incremental text for this chunk (may be empty).
        - ``finish_reason`` (str | None): Set on the final chunk; ``None`` otherwise.
        - ``usage`` (dict | None): Token usage, present only on the final chunk.

        Args:
            messages: Conversation history.
            tools: Optional tool/function definitions.
            **kwargs: Overrides forwarded to ``_build_payload``.

        Yields:
            Streaming chunks as described above.

        Example::

            async for chunk in provider.stream(messages):
                print(chunk["delta"], end="", flush=True)
        """
        client = await self._get_client()
        payload = self._build_payload(messages, tools=tools, stream=True, **kwargs)

        logger.debug("CohereCommandRPlus.stream → initiating SSE stream")

        try:
            async with client.stream("POST", "/chat", json=payload) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    if not raw_line or not raw_line.startswith("data:"):
                        continue

                    data_str = raw_line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed SSE event: %s", data_str)
                        continue

                    event_type = event.get("type", "")

                    if event_type == "content-delta":
                        delta = (
                            event.get("delta", {})
                            .get("message", {})
                            .get("content", {})
                            .get("text", "")
                        )
                        yield {"delta": delta, "finish_reason": None, "usage": None}

                    elif event_type == "message-end":
                        usage_raw = event.get("delta", {}).get("usage", {})
                        billed = usage_raw.get("billed_units", {})
                        yield {
                            "delta": "",
                            "finish_reason": event.get("delta", {}).get("finish_reason", "COMPLETE"),
                            "usage": {
                                "prompt_tokens": billed.get("input_tokens", 0),
                                "completion_tokens": billed.get("output_tokens", 0),
                                "total_tokens": (
                                    billed.get("input_tokens", 0)
                                    + billed.get("output_tokens", 0)
                                ),
                            },
                        }

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Cohere streaming error %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise

    async def handle_tool_call(
        self,
        tool_call: Dict[str, Any],
        tool_result: Any,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Submit a tool result back to the model and obtain its final reply.

        This follows Cohere's multi-step tool-use pattern: after the model
        returns a ``tool_calls`` list, execute the tools locally and pass
        the results back using this method.

        Args:
            tool_call: The original tool-call stub (from ``generate()``).
            tool_result: The serialisable result produced by the local tool.
            messages: The full conversation history up to the tool-call turn.
            **kwargs: Additional generation overrides.

        Returns:
            A standard generate-style response dict with the model's final answer.
        """
        # Append the assistant turn that triggered the tool call
        tool_use_message: Dict[str, Any] = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tool_call.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": json.dumps(tool_call.get("arguments", {})),
                    },
                }
            ],
            "content": "",
        }

        # Append the tool result
        tool_result_message: Dict[str, Any] = {
            "role": "tool",
            "tool_call_id": tool_call.get("id", ""),
            "content": json.dumps(tool_result),
        }

        updated_messages = list(messages) + [tool_use_message, tool_result_message]
        return await self.generate(updated_messages, **kwargs)

    async def close(self) -> None:
        """Release the underlying HTTP client connection pool."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            logger.debug("CohereCommandRPlusProvider HTTP client closed.")

    async def __aenter__(self) -> "CohereCommandRPlusProvider":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def __repr__(self) -> str:
        return (
            f"CohereCommandRPlusProvider(model={self.model!r}, "
            f"max_tokens={self.max_tokens}, streaming={self.supports_streaming})"
        )
