"""
Cohere Command R+ provider for Zakera AI Chat Agent.

Supports streaming, tool calls, and the command-r-plus-08-2024 model.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import cohere

from .providers import BaseProvider, ProviderConfig, ProviderResponse


class CohereCommandRPlusProvider(BaseProvider):
    """Provider implementation for Cohere Command R+.

    Command R+ (08-2024) is optimised for RAG and multi-step tool use with a
    128 k token context window and strong multilingual capabilities.
    """

    MODEL_ID = "command-r-plus-08-2024"
    MAX_TOKENS: int = 4096
    SUPPORTS_STREAMING: bool = True
    SUPPORTS_TOOLS: bool = True

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client = cohere.AsyncClientV2(api_key=config.api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Generate a single (non-streaming) response."""
        chat_history, last_message = self._split_messages(messages)
        response = await self._client.chat(
            model=self.MODEL_ID,
            messages=self._format_messages(chat_history, system_prompt),
            message=last_message,
            temperature=temperature,
            max_tokens=max_tokens or self.MAX_TOKENS,
            tools=self._coerce_tools(tools),
        )
        content = response.message.content[0].text if response.message.content else ""
        tool_calls = self._extract_tool_calls(response)
        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            model=self.MODEL_ID,
            usage={
                "prompt_tokens": response.meta.tokens.input_tokens if response.meta else 0,
                "completion_tokens": response.meta.tokens.output_tokens if response.meta else 0,
            },
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens as they are generated."""
        chat_history, last_message = self._split_messages(messages)
        async with await self._client.chat_stream(
            model=self.MODEL_ID,
            messages=self._format_messages(chat_history, system_prompt),
            message=last_message,
            temperature=temperature,
            max_tokens=max_tokens or self.MAX_TOKENS,
        ) as stream:
            async for event in stream:
                if event.type == "content-delta":
                    yield event.delta.message.content.text

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[list[dict[str, str]], str]:
        """Return (history, last_user_message)."""
        if not messages:
            return [], ""
        return messages[:-1], messages[-1].get("content", "")

    @staticmethod
    def _format_messages(
        messages: list[dict[str, str]],
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        formatted: list[dict[str, str]] = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        for m in messages:
            formatted.append({"role": m["role"], "content": m["content"]})
        return formatted

    @staticmethod
    def _coerce_tools(tools: list[dict[str, Any]] | None) -> list[Any] | None:
        """Convert generic tool dicts to Cohere tool format."""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                },
            }
            for t in tools
        ]

    @staticmethod
    def _extract_tool_calls(response: Any) -> list[dict[str, Any]]:
        calls = []
        if hasattr(response.message, "tool_calls") and response.message.tool_calls:
            for tc in response.message.tool_calls:
                calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                )
        return calls
