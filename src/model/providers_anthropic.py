"""
Anthropic (Claude) provider implementation with Claude 3.7 Sonnet and extended thinking.

This module provides integration with Anthropic's API, including support for:
- Claude 3.7 Sonnet (latest model with extended thinking)
- Claude 3.5 Sonnet, Claude 3.5 Haiku
- Claude 3 Opus, Sonnet, and Haiku
- Streaming responses
- Tool calling
- Vision capabilities
- Extended thinking (step-by-step reasoning traces)
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import httpx
from opentelemetry import trace

from .config import ModelConfig
from .providers import ModelProvider, ModelResponse, StreamChunk, ToolDefinition

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

AnthropicMessage = Dict[str, Any]
ToolLike = Union[ToolDefinition, Dict[str, Any]]


@dataclass
class ExtendedThinkingConfig:
    """Configuration for Claude's extended thinking feature.

    Extended thinking lets Claude show its step-by-step reasoning before
    producing a final answer.  It is only available on models that list
    ``supports_extended_thinking: True`` in ``SUPPORTED_MODELS``.

    Attributes:
        enabled:       Whether to enable extended thinking for this request.
        budget_tokens: Maximum tokens Claude may use for the thinking block.
                       Must be >= 1024.  Defaults to 8192.
    """

    enabled: bool = False
    budget_tokens: int = 8192

    def __post_init__(self) -> None:
        if self.enabled and self.budget_tokens < 1024:
            raise ValueError(
                f"budget_tokens must be >= 1024 when extended thinking is "
                f"enabled, got {self.budget_tokens}"
            )


class AnthropicProvider(ModelProvider):
    """Anthropic (Claude) model provider.

    Supports the full Claude 3.x and 3.5/3.7 model families.  Extended
    thinking is available on claude-3-7-sonnet-20250219 and can be
    activated by passing ``extended_thinking=True`` (or an
    ``ExtendedThinkingConfig`` instance) to :meth:`generate` /
    :meth:`stream`.
    """

    #: Registry of every model this provider can serve.  Cost figures are
    #: per-1k tokens in USD and reflect Anthropic's March 2026 pricing.
    SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
        # ── Claude 3.7 ────────────────────────────────────────────────────
        "claude-3-7-sonnet-20250219": {
            "max_tokens": 200_000,
            "max_output_tokens": 64_000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_extended_thinking": True,
            "tier": "advanced",
        },
        # ── Claude 3.5 ────────────────────────────────────────────────────
        "claude-3-5-sonnet-20241022": {
            "max_tokens": 200_000,
            "max_output_tokens": 8_096,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_extended_thinking": False,
            "tier": "advanced",
        },
        "claude-3-5-haiku-20241022": {
            "max_tokens": 200_000,
            "max_output_tokens": 8_096,
            "cost_per_1k_input": 0.0008,
            "cost_per_1k_output": 0.004,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_extended_thinking": False,
            "tier": "fast",
        },
        # ── Claude 3 ──────────────────────────────────────────────────────
        "claude-3-opus-20240229": {
            "max_tokens": 200_000,
            "max_output_tokens": 4_096,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_extended_thinking": False,
            "tier": "powerful",
        },
        "claude-3-sonnet-20240229": {
            "max_tokens": 200_000,
            "max_output_tokens": 4_096,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_extended_thinking": False,
            "tier": "balanced",
        },
        "claude-3-haiku-20240307": {
            "max_tokens": 200_000,
            "max_output_tokens": 4_096,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_extended_thinking": False,
            "tier": "fast",
        },
    }

    #: Default model when none is specified in config or call args.
    DEFAULT_MODEL = "claude-3-7-sonnet-20250219"

    def __init__(
        self,
        api_key: str,
        config: Optional[ModelConfig] = None,
        extended_thinking: Optional[ExtendedThinkingConfig] = None,
    ) -> None:
        """Initialise the Anthropic provider.

        Args:
            api_key:           Anthropic API key.
            config:            Optional shared model configuration.
            extended_thinking: Default extended-thinking settings applied to
                               every request unless overridden per-call.
        """
        super().__init__("anthropic", api_key, config)
        self.base_url = "https://api.anthropic.com/v1"
        self.api_version = "2023-06-01"
        self.default_thinking = extended_thinking or ExtendedThinkingConfig()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def supports_tools(self) -> bool:
        """Return True because Anthropic models support tool calling."""
        return True

    def _get_headers(self) -> Dict[str, str]:
        """Return HTTP headers required by the Anthropic Messages API."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }
        # Required beta header for extended thinking (harmless on other models)
        headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"
        return headers

    def _normalize_content_blocks(self, content: Any) -> List[Dict[str, Any]]:
        """Normalise arbitrary content into Anthropic content blocks."""
        if content is None:
            return []

        if isinstance(content, list):
            blocks: List[Dict[str, Any]] = []
            for item in content:
                blocks.extend(self._normalize_content_blocks(item))
            return blocks

        if isinstance(content, dict):
            block_type = content.get("type")
            if block_type in {"text", "image", "tool_use", "tool_result", "thinking"}:
                return [content]
            if "image_url" in content:
                return [
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": content["image_url"],
                        },
                    }
                ]
            if "text" in content and len(content) == 1:
                return [{"type": "text", "text": str(content["text"])}]
            return [{"type": "text", "text": json.dumps(content, ensure_ascii=False)}]

        if isinstance(content, str):
            return [{"type": "text", "text": content}]

        return [{"type": "text", "text": str(content)}]

    def _content_to_text(self, content: Any) -> str:
        """Convert multi-part content to a single system prompt string."""
        blocks = self._normalize_content_blocks(content)
        parts: List[str] = []

        for block in blocks:
            block_type = block.get("type")
            if block_type == "text":
                parts.append(str(block.get("text", "")))
            elif block_type == "thinking":
                parts.append(str(block.get("thinking", "")))
            elif block_type == "image":
                parts.append("[image]")
            elif block_type == "tool_use":
                parts.append(f"[tool_use:{block.get('name', 'tool')}]")
            elif block_type == "tool_result":
                result_content = block.get("content")
                if isinstance(result_content, str):
                    parts.append(result_content)
                elif isinstance(result_content, list):
                    parts.append(self._content_to_text(result_content))

        return "\n".join(part for part in parts if part).strip()

    def _coerce_tool_input(self, value: Any) -> Any:
        """Coerce tool input JSON into a structured object when possible."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _normalize_tool_definition(self, tool: ToolLike) -> Dict[str, Any]:
        """Convert OpenAI-style or native tool definitions to Anthropic format."""
        if hasattr(tool, "to_openai_dict"):
            tool = tool.to_openai_dict()  # type: ignore[assignment]

        if not isinstance(tool, dict):
            raise TypeError(f"Unsupported tool definition type: {type(tool)!r}")

        if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
            function = tool["function"]
            return {
                "name": function["name"],
                "description": function.get("description", ""),
                "input_schema": function.get("parameters", {}),
            }

        if "input_schema" in tool:
            return {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool["input_schema"],
            }

        if "parameters" in tool:
            return {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool["parameters"],
            }

        return tool

    def _normalize_tool_use_blocks(self, message: AnthropicMessage) -> List[Dict[str, Any]]:
        """Normalise assistant tool-use messages into Anthropic tool_use blocks."""
        content = message.get("content")

        if isinstance(content, list):
            tool_use_blocks = [
                block
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            ]
            if tool_use_blocks:
                return tool_use_blocks

        if isinstance(content, dict) and content.get("type") == "tool_use":
            return [content]

        tool_calls = message.get("tool_calls") or []
        blocks: List[Dict[str, Any]] = []
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue

            function = tool_call.get("function", {})
            if not isinstance(function, dict):
                function = {}

            arguments = function.get("arguments", tool_call.get("input", {}))
            block: Dict[str, Any] = {
                "type": "tool_use",
                "id": tool_call.get("id") or tool_call.get("tool_call_id"),
                "name": function.get("name") or tool_call.get("name") or message.get("name") or "tool",
                "input": self._coerce_tool_input(arguments),
            }
            blocks.append({k: v for k, v in block.items() if v is not None})

        if blocks:
            return blocks

        if message.get("tool_call_id"):
            block = {
                "type": "tool_use",
                "id": message.get("tool_call_id"),
                "name": message.get("name") or "tool",
                "input": self._coerce_tool_input(content),
            }
            return [{k: v for k, v in block.items() if v is not None}]

        if isinstance(content, str):
            return [
                {
                    "type": "tool_use",
                    "name": message.get("name") or "tool",
                    "input": self._coerce_tool_input(content),
                }
            ]

        return self._normalize_content_blocks(content)

    def _normalize_tool_result_blocks(self, message: AnthropicMessage) -> List[Dict[str, Any]]:
        """Normalise tool result messages into Anthropic tool_result blocks."""
        content = message.get("content")

        if isinstance(content, list):
            tool_result_blocks = [
                block
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_result"
            ]
            if tool_result_blocks:
                return tool_result_blocks

            block: Dict[str, Any] = {
                "type": "tool_result",
                "content": self._normalize_content_blocks(content),
            }
            tool_use_id = (
                message.get("tool_use_id")
                or message.get("tool_call_id")
                or message.get("id")
            )
            if tool_use_id:
                block["tool_use_id"] = tool_use_id
            if "is_error" in message:
                block["is_error"] = message["is_error"]
            return [block]

        if isinstance(content, dict) and content.get("type") == "tool_result":
            return [content]

        block = {
            "type": "tool_result",
            "content": content if content is not None else "",
        }
        tool_use_id = (
            message.get("tool_use_id")
            or message.get("tool_call_id")
            or message.get("id")
        )
        if tool_use_id:
            block["tool_use_id"] = tool_use_id
        if "is_error" in message:
            block["is_error"] = message["is_error"]
        return [block]

    def _format_messages(
        self, messages: List[AnthropicMessage]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Split *messages* into Anthropic-formatted turns and a system prompt."""
        formatted: List[Dict[str, Any]] = []
        system_message: Optional[str] = None

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                system_text = self._content_to_text(content)
                if system_text:
                    system_message = (
                        f"{system_message}\n{system_text}" if system_message else system_text
                    )
                continue

            if role in {"tool_result", "tool"}:
                formatted.append(
                    {
                        "role": "user",
                        "content": self._normalize_tool_result_blocks(msg),
                    }
                )
                continue

            if role == "tool_use":
                formatted.append(
                    {
                        "role": "assistant",
                        "content": self._normalize_tool_use_blocks(msg),
                    }
                )
                continue

            if role == "assistant" and (msg.get("tool_calls") or isinstance(content, list)):
                content_blocks = self._normalize_content_blocks(content)
                if msg.get("tool_calls"):
                    content_blocks.extend(self._normalize_tool_use_blocks(msg))
                formatted.append({"role": "assistant", "content": content_blocks})
                continue

            anthropic_role = "assistant" if role == "assistant" else "user"
            formatted.append(
                {
                    "role": anthropic_role,
                    "content": self._normalize_content_blocks(content),
                }
            )

        return formatted, system_message

    def _build_thinking_block(self, thinking_cfg: ExtendedThinkingConfig) -> Dict[str, Any]:
        """Build the ``thinking`` request block for the API payload."""
        return {
            "type": "enabled",
            "budget_tokens": thinking_cfg.budget_tokens,
        }

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate request cost in USD."""
        info = self.SUPPORTED_MODELS[model]
        return (
            (input_tokens / 1_000) * info["cost_per_1k_input"]
            + (output_tokens / 1_000) * info["cost_per_1k_output"]
        )

    def validate_extended_thinking(self, model: str) -> None:
        """Raise *ValueError* if *model* does not support extended thinking."""
        info = self.SUPPORTED_MODELS.get(model, {})
        if not info.get("supports_extended_thinking", False):
            raise ValueError(
                f"Model '{model}' does not support extended thinking. "
                "Use 'claude-3-7-sonnet-20250219' or later."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @tracer.start_as_current_span("anthropic_generate")
    async def generate(
        self,
        messages: List[AnthropicMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extended_thinking: Optional[bool] = None,
        thinking_budget: int = 8_192,
        tools: Optional[List[ToolLike]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a single response using Claude.

        Args:
            messages:          Conversation history (system / user / assistant).
            model:             Model identifier; falls back to config then
                               :attr:`DEFAULT_MODEL`.
            temperature:       Sampling temperature in ``[0, 1]``.
            max_tokens:        Maximum *output* tokens to generate.
            extended_thinking: Override whether extended thinking is active.
                               ``None`` inherits ``self.default_thinking``.
            thinking_budget:   Budget tokens for the thinking block (>= 1024).
            tools:             Anthropic or OpenAI-style tool definitions.
            **kwargs:          Additional Anthropic API parameters
                               (``top_p``, ``top_k``, ``stop_sequences``).

        Returns:
            :class:`~.providers.ModelResponse` including parsed ``tool_calls``
            when the model returns ``tool_use`` blocks.

        Raises:
            ValueError:             If the model is unknown or extended
                                    thinking is requested on an unsupported model.
            httpx.HTTPStatusError:  On non-2xx API responses.
        """
        model = model or self.config.model or self.DEFAULT_MODEL
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens or 4_096

        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model '{model}' not supported by AnthropicProvider")

        # Resolve extended-thinking flag
        use_thinking = (
            extended_thinking
            if extended_thinking is not None
            else self.default_thinking.enabled
        )
        if use_thinking:
            self.validate_extended_thinking(model)

        formatted_messages, system_message = self._format_messages(messages)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_message:
            payload["system"] = system_message
        if use_thinking:
            payload["thinking"] = self._build_thinking_block(
                ExtendedThinkingConfig(enabled=True, budget_tokens=thinking_budget)
            )
        if tools:
            payload["tools"] = [self._normalize_tool_definition(tool) for tool in tools]
            payload["tool_choice"] = {"type": "auto"}
        for key in ("top_p", "top_k", "stop_sequences"):
            if key in kwargs:
                payload[key] = kwargs[key]

        logger.debug(
            "Anthropic request — model=%s tier=%s thinking=%s budget=%d tools=%s",
            model,
            self.SUPPORTED_MODELS[model]["tier"],
            use_thinking,
            thinking_budget if use_thinking else 0,
            bool(tools),
        )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            # Extract text + optional thinking from the content blocks list
            text_content = ""
            thinking_content = ""
            tool_calls: List[Dict[str, Any]] = []
            for block in data.get("content", []):
                block_type = block.get("type")
                if block_type == "text":
                    text_content += block.get("text", "")
                elif block_type == "thinking":
                    thinking_content += block.get("thinking", "")
                elif block_type == "tool_use":
                    tool_call: Dict[str, Any] = {
                        "id": block.get("id"),
                        "type": "tool_use",
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                    }
                    tool_calls.append(
                        {k: v for k, v in tool_call.items() if v is not None}
                    )

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            logger.info(
                "Anthropic response OK — model=%s tokens=%d cost=$%.6f",
                model,
                input_tokens + output_tokens,
                cost,
            )

            return ModelResponse(
                content=text_content,
                model=data.get("model", model),
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                finish_reason=data.get("stop_reason") or "stop",
                tool_calls=tool_calls or None,
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Anthropic HTTP error %d — %s",
                exc.response.status_code,
                exc.response.text[:400],
            )
            raise
        except Exception as exc:
            logger.error("AnthropicProvider.generate error: %s", exc)
            raise

    @tracer.start_as_current_span("anthropic_stream")
    async def stream(
        self,
        messages: List[AnthropicMessage],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extended_thinking: Optional[bool] = None,
        thinking_budget: int = 8_192,
        tools: Optional[List[ToolLike]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a Claude response token-by-token.

        When *extended_thinking* is active the generator first yields
        ``StreamChunk`` objects whose ``content`` is empty while the reasoning
        block is emitted.  Tool-use blocks are surfaced through the
        ``tool_call`` field so the caller can dispatch the tool and continue the
        conversation loop.

        Args:
            messages:          Conversation history.
            model:             Model identifier.
            temperature:       Sampling temperature.
            max_tokens:        Maximum output tokens.
            extended_thinking: Enable extended thinking for this stream.
            thinking_budget:   Token budget for the thinking block.
            tools:             Anthropic or OpenAI-style tool definitions.
            **kwargs:          Extra Anthropic parameters.

        Yields:
            :class:`~.providers.StreamChunk` — one per SSE event.
        """
        model = model or self.config.model or self.DEFAULT_MODEL
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens or 4_096

        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model '{model}' not supported by AnthropicProvider")

        use_thinking = (
            extended_thinking
            if extended_thinking is not None
            else self.default_thinking.enabled
        )
        if use_thinking:
            self.validate_extended_thinking(model)

        formatted_messages, system_message = self._format_messages(messages)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system_message:
            payload["system"] = system_message
        if use_thinking:
            payload["thinking"] = self._build_thinking_block(
                ExtendedThinkingConfig(enabled=True, budget_tokens=thinking_budget)
            )
        if tools:
            payload["tools"] = [self._normalize_tool_definition(tool) for tool in tools]
            payload["tool_choice"] = {"type": "auto"}
        for key in ("top_p", "top_k", "stop_sequences"):
            if key in kwargs:
                payload[key] = kwargs[key]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    input_tokens = 0
                    output_tokens = 0
                    current_tool_use: Optional[Dict[str, Any]] = None
                    tool_input_parts: List[str] = []
                    final_usage_emitted = False

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.debug("Skipping malformed SSE chunk: %s", data_str)
                            continue

                        event_type = data.get("type", "")

                        if event_type == "message_start":
                            usage = data.get("message", {}).get("usage", {})
                            input_tokens = usage.get("input_tokens", 0)

                        elif event_type == "content_block_start":
                            block = data.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_use = {
                                    "id": block.get("id"),
                                    "name": block.get("name"),
                                }
                                tool_input_parts = []
                                yield StreamChunk(
                                    content="",
                                    model=data.get("model", model),
                                    tool_call={
                                        k: v for k, v in {
                                            "id": block.get("id"),
                                            "type": "tool_use",
                                            "name": block.get("name"),
                                            "input": {},
                                        }.items() if v is not None
                                    },
                                )

                        elif event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            delta_type = delta.get("type", "")

                            if delta_type == "text_delta":
                                chunk_text = delta.get("text", "")
                                if chunk_text:
                                    yield StreamChunk(
                                        content=chunk_text,
                                        model=data.get("model", model),
                                    )

                            elif delta_type == "thinking_delta":
                                thinking_text = delta.get("thinking", "")
                                if thinking_text:
                                    yield StreamChunk(
                                        content=thinking_text,
                                        model=data.get("model", model),
                                    )

                            elif (
                                delta_type == "input_json_delta"
                                and current_tool_use is not None
                            ):
                                partial_json = delta.get("partial_json", "")
                                if partial_json:
                                    tool_input_parts.append(partial_json)
                                    yield StreamChunk(
                                        content="",
                                        model=data.get("model", model),
                                        tool_call={
                                            k: v for k, v in {
                                                "id": current_tool_use.get("id"),
                                                "type": "tool_use",
                                                "name": current_tool_use.get("name"),
                                                "partial_json": partial_json,
                                            }.items() if v is not None
                                        },
                                    )

                        elif event_type == "content_block_stop":
                            if current_tool_use is not None:
                                raw_input = "".join(tool_input_parts).strip()
                                parsed_input: Any = {}
                                if raw_input:
                                    try:
                                        parsed_input = json.loads(raw_input)
                                    except json.JSONDecodeError:
                                        parsed_input = raw_input

                                yield StreamChunk(
                                    content="",
                                    model=data.get("model", model),
                                    tool_call={
                                        k: v for k, v in {
                                            "id": current_tool_use.get("id"),
                                            "type": "tool_use",
                                            "name": current_tool_use.get("name"),
                                            "input": parsed_input,
                                        }.items() if v is not None
                                    },
                                )

                                current_tool_use = None
                                tool_input_parts = []

                        elif event_type == "message_delta":
                            usage = data.get("usage", {})
                            output_tokens = usage.get("output_tokens", output_tokens)
                            finish_reason = data.get("delta", {}).get("stop_reason")
                            total_tokens = input_tokens + output_tokens
                            cost = self._calculate_cost(model, input_tokens, output_tokens)
                            yield StreamChunk(
                                content="",
                                model=data.get("model", model),
                                usage={
                                    "prompt_tokens": input_tokens,
                                    "completion_tokens": output_tokens,
                                    "total_tokens": total_tokens,
                                },
                                finish_reason=finish_reason,
                            )
                            final_usage_emitted = True

                        elif event_type == "message_stop" and not final_usage_emitted:
                            usage = data.get("usage", {})
                            output_tokens = usage.get("output_tokens", output_tokens)
                            finish_reason = data.get("stop_reason")
                            total_tokens = input_tokens + output_tokens
                            _ = self._calculate_cost(model, input_tokens, output_tokens)
                            yield StreamChunk(
                                content="",
                                model=data.get("model", model),
                                usage={
                                    "prompt_tokens": input_tokens,
                                    "completion_tokens": output_tokens,
                                    "total_tokens": total_tokens,
                                },
                                finish_reason=finish_reason,
                            )
                            final_usage_emitted = True

                    logger.info(
                        "Anthropic stream done — model=%s tokens=%d",
                        model,
                        input_tokens + output_tokens,
                    )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Anthropic stream HTTP error %d",
                exc.response.status_code,
            )
            raise
        except Exception as exc:
            logger.error("AnthropicProvider.stream error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_supported_models(self) -> Dict[str, Dict[str, Any]]:
        """Return the full model registry with capability metadata."""
        return self.SUPPORTED_MODELS

    def get_model_ids(self) -> List[str]:
        """Return a flat list of model identifiers."""
        return list(self.SUPPORTED_MODELS.keys())

    def validate_config(self) -> bool:
        """Return ``True`` if the provider is correctly configured."""
        if not self.api_key:
            logger.error("Anthropic API key not set")
            return False
        if self.config.model and self.config.model not in self.SUPPORTED_MODELS:
            logger.error("Unsupported model in config: %s", self.config.model)
            return False
        return True
