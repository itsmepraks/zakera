"""Anthropic (Claude) provider implementation.

This provider mirrors the shared ``ModelProvider`` abstraction in
``src/model/providers.py`` while adding Anthropic-specific capabilities:

- Claude 3 / 3.5 / 3.7 model support
- tool calling via ``tool_use`` / ``tool_result`` blocks
- vision / multimodal message formatting
- optional extended thinking
- text-only ``stream_generate`` plus richer ``stream`` chunks

The implementation is intentionally tolerant of both the base dataclass
messages used elsewhere in the repo and raw dict payloads so it can be used
from the older route handlers as well as the newer provider manager.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, AsyncIterator, Dict, List, Optional, Tuple, Union

import httpx
from opentelemetry import trace

from .config import ModelConfig
from .providers import Message as BaseMessage, ModelProvider, ModelResponse, StreamChunk, ToolDefinition

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

AnthropicMessage = Union[BaseMessage, Dict[str, Any]]
ToolLike = Union[ToolDefinition, Dict[str, Any]]


@dataclass
class ExtendedThinkingConfig:
    """Configuration for Claude extended thinking."""

    enabled: bool = False
    budget_tokens: int = 8192

    def __post_init__(self) -> None:
        if self.enabled and self.budget_tokens < 1024:
            raise ValueError(
                "budget_tokens must be >= 1024 when extended thinking is enabled"
            )


class AnthropicProvider(ModelProvider):
    """Anthropic Claude provider with tool calling and vision support."""

    SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
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

    DEFAULT_MODEL = "claude-3-7-sonnet-20250219"
    API_BASE = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str,
        config: Optional[ModelConfig] = None,
        model_name: Optional[str] = None,
        extended_thinking: Optional[ExtendedThinkingConfig] = None,
    ) -> None:
        self.config = config or ModelConfig()
        resolved_model = model_name or getattr(self.config, "anthropic_model", None) or self.DEFAULT_MODEL
        super().__init__(api_key, resolved_model)
        self.base_url = self.API_BASE
        self.api_version = self.API_VERSION
        self.default_thinking = extended_thinking or ExtendedThinkingConfig()

    # ------------------------------------------------------------------
    # Capability helpers
    # ------------------------------------------------------------------

    def supports_tools(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _message_to_dict(message: AnthropicMessage) -> Dict[str, Any]:
        if isinstance(message, dict):
            return dict(message)

        data: Dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if getattr(message, "name", None):
            data["name"] = message.name
        if getattr(message, "tool_calls", None):
            data["tool_calls"] = message.tool_calls
        if getattr(message, "tool_call_id", None):
            data["tool_call_id"] = message.tool_call_id
        return data

    def _normalize_content_blocks(self, content: Any) -> List[Dict[str, Any]]:
        if content is None:
            return []

        if isinstance(content, list):
            blocks: List[Dict[str, Any]] = []
            for item in content:
                blocks.extend(self._normalize_content_blocks(item))
            return blocks

        if isinstance(content, dict):
            block_type = content.get("type")

            if block_type == "image_url":
                image_url = content.get("image_url", {})
                if isinstance(image_url, str):
                    image_url = {"url": image_url}
                url = image_url.get("url")
                if not url:
                    return []
                return [self._image_url_to_block(url)]

            if block_type in {"text", "image", "tool_use", "tool_result", "thinking"}:
                return [content]

            if "image_url" in content:
                image_url = content["image_url"]
                if isinstance(image_url, str):
                    image_url = {"url": image_url}
                url = image_url.get("url") if isinstance(image_url, dict) else None
                if url:
                    return [self._image_url_to_block(url)]

            if "text" in content and len(content) == 1:
                return [{"type": "text", "text": str(content["text"])}]

            return [{"type": "text", "text": json.dumps(content, ensure_ascii=False)}]

        if isinstance(content, str):
            return [{"type": "text", "text": content}]

        return [{"type": "text", "text": str(content)}]

    def _image_url_to_block(self, url: str) -> Dict[str, Any]:
        """Convert an OpenAI-style image URL into an Anthropic image block."""
        if url.startswith("data:"):
            try:
                header, encoded = url.split(",", 1)
                media_type = header.split(";")[0][5:] or "image/jpeg"
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": encoded,
                    },
                }
            except ValueError:
                pass

        return {
            "type": "image",
            "source": {
                "type": "url",
                "url": url,
            },
        }

    def _content_to_text(self, content: Any) -> str:
        parts: List[str] = []
        for block in self._normalize_content_blocks(content):
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

    @staticmethod
    def _coerce_tool_input(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _normalize_tool_definition(self, tool: ToolLike) -> Dict[str, Any]:
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

    def _normalize_tool_use_blocks(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
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

            function = tool_call.get("function") or {}
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

    def _normalize_tool_result_blocks(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
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
        formatted: List[Dict[str, Any]] = []
        system_message: Optional[str] = None

        for raw_msg in messages:
            msg = self._message_to_dict(raw_msg)
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
                formatted.append({"role": "user", "content": self._normalize_tool_result_blocks(msg)})
                continue

            if role == "tool_use":
                formatted.append({"role": "assistant", "content": self._normalize_tool_use_blocks(msg)})
                continue

            if role == "assistant" and (msg.get("tool_calls") or isinstance(content, list)):
                content_blocks = self._normalize_content_blocks(content)
                if msg.get("tool_calls") and not any(
                    isinstance(block, dict) and block.get("type") == "tool_use"
                    for block in content_blocks
                ):
                    content_blocks.extend(self._normalize_tool_use_blocks(msg))
                formatted.append({"role": "assistant", "content": content_blocks})
                continue

            anthropic_role = "assistant" if role == "assistant" else "user"
            formatted.append({
                "role": anthropic_role,
                "content": self._normalize_content_blocks(content),
            })

        return formatted, system_message

    def _build_thinking_block(self, thinking_cfg: ExtendedThinkingConfig) -> Dict[str, Any]:
        return {
            "type": "enabled",
            "budget_tokens": thinking_cfg.budget_tokens,
        }

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        info = self.SUPPORTED_MODELS[model]
        return (
            (input_tokens / 1_000) * info["cost_per_1k_input"]
            + (output_tokens / 1_000) * info["cost_per_1k_output"]
        )

    def validate_extended_thinking(self, model: str) -> None:
        info = self.SUPPORTED_MODELS.get(model, {})
        if not info.get("supports_extended_thinking", False):
            raise ValueError(
                f"Model '{model}' does not support extended thinking. "
                "Use 'claude-3-7-sonnet-20250219' or later."
            )

    def _resolve_model(self, model: Optional[str]) -> str:
        resolved = model or self.model_name or getattr(self.config, "anthropic_model", None) or self.DEFAULT_MODEL
        if resolved not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model '{resolved}' not supported by AnthropicProvider")
        return resolved

    def _build_payload(
        self,
        messages: List[AnthropicMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extended_thinking: Optional[bool] = None,
        thinking_budget: int = 8_192,
        tools: Optional[List[ToolLike]] = None,
        **kwargs: Any,
    ) -> Tuple[str, Dict[str, Any]]:
        resolved_model = self._resolve_model(model)

        temperature = self.config.temperature if temperature is None else temperature
        max_tokens = self.config.max_tokens if max_tokens is None else max_tokens

        use_thinking = (
            extended_thinking
            if extended_thinking is not None
            else self.default_thinking.enabled
        )
        if use_thinking:
            self.validate_extended_thinking(resolved_model)

        formatted_messages, system_message = self._format_messages(messages)
        payload: Dict[str, Any] = {
            "model": resolved_model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature
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
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

        return resolved_model, payload

    def _tool_call_from_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        raw_input = block.get("input", {})
        if isinstance(raw_input, str):
            arguments = raw_input
        else:
            arguments = json.dumps(raw_input, ensure_ascii=False)

        tool_call: Dict[str, Any] = {
            "id": block.get("id"),
            "type": "function",
            "function": {
                "name": block.get("name") or "tool",
                "arguments": arguments,
            },
        }
        return {k: v for k, v in tool_call.items() if v is not None}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @tracer.start_as_current_span("anthropic_generate")
    async def generate(
        self,
        messages: List[AnthropicMessage],
        tools: Optional[List[ToolLike]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        model = kwargs.pop("model", None)
        temperature = kwargs.pop("temperature", None)
        max_tokens = kwargs.pop("max_tokens", None)
        extended_thinking = kwargs.pop("extended_thinking", None)
        thinking_budget = kwargs.pop("thinking_budget", 8_192)

        resolved_model, payload = self._build_payload(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            extended_thinking=extended_thinking,
            thinking_budget=thinking_budget,
            tools=tools,
            **kwargs,
        )

        logger.debug(
            "Anthropic request — model=%s tier=%s thinking=%s tools=%s",
            resolved_model,
            self.SUPPORTED_MODELS[resolved_model]["tier"],
            bool(payload.get("thinking")),
            bool(tools),
        )

        try:
            async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            text_content = ""
            tool_calls: List[Dict[str, Any]] = []
            for block in data.get("content", []):
                block_type = block.get("type")
                if block_type == "text":
                    text_content += block.get("text", "")
                elif block_type == "tool_use":
                    tool_calls.append(self._tool_call_from_block(block))

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            logger.info(
                "Anthropic response OK — model=%s tokens=%d cost=$%.6f",
                data.get("model", resolved_model),
                input_tokens + output_tokens,
                self._calculate_cost(resolved_model, input_tokens, output_tokens),
            )

            return ModelResponse(
                content=text_content,
                model=data.get("model", resolved_model),
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                finish_reason=data.get("stop_reason") or "stop",
                tool_calls=tool_calls or None,
            )

        except httpx.HTTPStatusError:
            logger.exception("Anthropic HTTP error during generate")
            raise
        except Exception:
            logger.exception("AnthropicProvider.generate error")
            raise

    @tracer.start_as_current_span("anthropic_stream")
    async def stream(
        self,
        messages: List[AnthropicMessage],
        tools: Optional[List[ToolLike]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        model = kwargs.pop("model", None)
        temperature = kwargs.pop("temperature", None)
        max_tokens = kwargs.pop("max_tokens", None)
        extended_thinking = kwargs.pop("extended_thinking", None)
        thinking_budget = kwargs.pop("thinking_budget", 8_192)

        resolved_model, payload = self._build_payload(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            extended_thinking=extended_thinking,
            thinking_budget=thinking_budget,
            tools=tools,
            **kwargs,
        )
        payload["stream"] = True

        try:
            async with httpx.AsyncClient(timeout=self.config.request_timeout) as client:
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
                        if not line.strip() or not line.startswith("data: "):
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
                                    model=data.get("model", resolved_model),
                                    tool_call={
                                        "id": block.get("id"),
                                        "type": "function",
                                        "function": {
                                            "name": block.get("name") or "tool",
                                            "arguments": "",
                                        },
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
                                        model=data.get("model", resolved_model),
                                    )

                            elif delta_type == "thinking_delta":
                                thinking_text = delta.get("thinking", "")
                                if thinking_text:
                                    yield StreamChunk(
                                        content=thinking_text,
                                        model=data.get("model", resolved_model),
                                    )

                            elif delta_type == "input_json_delta" and current_tool_use is not None:
                                partial_json = delta.get("partial_json", "")
                                if partial_json:
                                    tool_input_parts.append(partial_json)
                                    yield StreamChunk(
                                        content="",
                                        model=data.get("model", resolved_model),
                                        tool_call={
                                            "id": current_tool_use.get("id"),
                                            "type": "function",
                                            "function": {
                                                "name": current_tool_use.get("name") or "tool",
                                                "arguments": partial_json,
                                            },
                                            "partial_json": partial_json,
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

                                final_tool_call = {
                                    "id": current_tool_use.get("id"),
                                    "type": "function",
                                    "function": {
                                        "name": current_tool_use.get("name") or "tool",
                                        "arguments": json.dumps(parsed_input, ensure_ascii=False),
                                    },
                                }
                                yield StreamChunk(
                                    content="",
                                    model=data.get("model", resolved_model),
                                    tool_call=final_tool_call,
                                )

                                current_tool_use = None
                                tool_input_parts = []

                        elif event_type == "message_delta":
                            usage = data.get("usage", {})
                            output_tokens = usage.get("output_tokens", output_tokens)
                            finish_reason = data.get("delta", {}).get("stop_reason")
                            yield StreamChunk(
                                content="",
                                model=data.get("model", resolved_model),
                                usage={
                                    "prompt_tokens": input_tokens,
                                    "completion_tokens": output_tokens,
                                    "total_tokens": input_tokens + output_tokens,
                                },
                                finish_reason=finish_reason,
                            )
                            final_usage_emitted = True

                        elif event_type == "message_stop" and not final_usage_emitted:
                            usage = data.get("usage", {})
                            output_tokens = usage.get("output_tokens", output_tokens)
                            finish_reason = data.get("stop_reason")
                            yield StreamChunk(
                                content="",
                                model=data.get("model", resolved_model),
                                usage={
                                    "prompt_tokens": input_tokens,
                                    "completion_tokens": output_tokens,
                                    "total_tokens": input_tokens + output_tokens,
                                },
                                finish_reason=finish_reason,
                            )
                            final_usage_emitted = True

                    logger.info(
                        "Anthropic stream done — model=%s tokens=%d",
                        resolved_model,
                        input_tokens + output_tokens,
                    )

        except httpx.HTTPStatusError:
            logger.exception("Anthropic HTTP error during stream")
            raise
        except Exception:
            logger.exception("AnthropicProvider.stream error")
            raise

    async def stream_generate(
        self,
        messages: List[AnthropicMessage],
        tools: Optional[List[ToolLike]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        async for chunk in self.stream(messages, tools=tools, **kwargs):
            if chunk.content:
                yield chunk.content

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
            "anthropic-beta": "interleaved-thinking-2025-05-14",
        }
        return headers

    def get_supported_models(self) -> Dict[str, Dict[str, Any]]:
        return self.SUPPORTED_MODELS

    def get_model_ids(self) -> List[str]:
        return list(self.SUPPORTED_MODELS.keys())

    def validate_config(self) -> bool:
        if not self.api_key:
            logger.error("Anthropic API key not set")
            return False
        if self.model_name not in self.SUPPORTED_MODELS:
            logger.error("Unsupported model in config: %s", self.model_name)
            return False
        return True


# Backwards-compatible alias expected by src/model/__init__.py.
AnthropicStreamingProvider = AnthropicProvider
