"""Anthropic (Claude) provider implementation with Claude 3.7 Sonnet and extended thinking.

This module provides integration with Anthropic's API, including support for:
- Claude 3.7 Sonnet (latest model with extended thinking)
- Claude 3.5 Sonnet, Claude 3.5 Haiku
- Claude 3 Opus, Sonnet, and Haiku
- Streaming responses
- Tool calling
- Vision capabilities
- Extended thinking (step-by-step reasoning traces)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from opentelemetry import trace

from .config import ModelConfig
from .providers import ModelProvider, ModelResponse, StreamChunk

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


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

    def _format_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Split *messages* into Anthropic-formatted turns and a system prompt.

        The Anthropic Messages API requires ``system`` to be a top-level
        string rather than part of the messages list.

        Args:
            messages: Standard OpenAI-style message dicts.

        Returns:
            A ``(formatted_messages, system_message)`` tuple.
        """
        formatted: List[Dict[str, Any]] = []
        system_message: Optional[str] = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_message = content
            else:
                formatted.append(
                    {
                        "role": "user" if role == "user" else "assistant",
                        "content": content,
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
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extended_thinking: Optional[bool] = None,
        thinking_budget: int = 8_192,
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
            **kwargs:          Additional Anthropic API parameters
                               (``top_p``, ``top_k``, ``stop_sequences``).

        Returns:
            :class:`~.providers.ModelResponse` including optional
            ``thinking_content`` for extended-thinking responses.

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
        for key in ("top_p", "top_k", "stop_sequences"):
            if key in kwargs:
                payload[key] = kwargs[key]

        logger.debug(
            "Anthropic request — model=%s tier=%s thinking=%s budget=%d",
            model,
            self.SUPPORTED_MODELS[model]["tier"],
            use_thinking,
            thinking_budget if use_thinking else 0,
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
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")
                elif block.get("type") == "thinking":
                    thinking_content += block.get("thinking", "")

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
                model=model,
                provider=self.name,
                tokens_used=input_tokens + output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                finish_reason=data.get("stop_reason"),
                raw_response=data,
                # Extended fields — callers can introspect if needed
                thinking_content=thinking_content or None,
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
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        extended_thinking: Optional[bool] = None,
        thinking_budget: int = 8_192,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a Claude response token-by-token.

        When *extended_thinking* is active the generator first yields
        ``StreamChunk`` objects whose ``thinking`` attribute contains the
        incremental reasoning text (``content`` is empty for those chunks).
        After the thinking block is complete it yields normal content chunks.

        Args:
            messages:          Conversation history.
            model:             Model identifier.
            temperature:       Sampling temperature.
            max_tokens:        Maximum output tokens.
            extended_thinking: Enable extended thinking for this stream.
            thinking_budget:   Token budget for the thinking block.
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
                    # Track which content block we're currently inside
                    current_block_type: Optional[str] = None

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # strip "data: "
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("type", "")

                        if event_type == "content_block_start":
                            block = data.get("content_block", {})
                            current_block_type = block.get("type")

                        elif event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            delta_type = delta.get("type", "")

                            if delta_type == "text_delta":
                                chunk_text = delta.get("text", "")
                                yield StreamChunk(
                                    content=chunk_text,
                                    model=model,
                                    provider=self.name,
                                    finish_reason=None,
                                )

                            elif delta_type == "thinking_delta":
                                # Thinking text — surface as a special chunk
                                thinking_text = delta.get("thinking", "")
                                yield StreamChunk(
                                    content="",
                                    thinking=thinking_text,
                                    model=model,
                                    provider=self.name,
                                    finish_reason=None,
                                )

                        elif event_type == "content_block_stop":
                            current_block_type = None

                        elif event_type == "message_start":
                            usage = data.get("message", {}).get("usage", {})
                            input_tokens = usage.get("input_tokens", 0)

                        elif event_type == "message_delta":
                            usage = data.get("usage", {})
                            output_tokens = usage.get("output_tokens", 0)
                            cost = self._calculate_cost(model, input_tokens, output_tokens)
                            yield StreamChunk(
                                content="",
                                model=model,
                                provider=self.name,
                                finish_reason=data.get("delta", {}).get("stop_reason"),
                                tokens_used=input_tokens + output_tokens,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                cost=cost,
                            )

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
