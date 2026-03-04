"""Anthropic (Claude) provider implementation with Claude 3.5 Sonnet support.

This module provides integration with Anthropic's API, including support for:
- Claude 3.5 Sonnet (latest model)
- Claude 3 Opus, Sonnet, and Haiku
- Streaming responses
- Tool calling
- Vision capabilities
"""

import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
import httpx
from opentelemetry import trace

from .config import ModelConfig
from .providers import ModelProvider, ModelResponse, StreamChunk

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AnthropicProvider(ModelProvider):
    """Anthropic (Claude) model provider."""

    SUPPORTED_MODELS = {
        "claude-3-5-sonnet-20241022": {
            "max_tokens": 200000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
        },
        "claude-3-opus-20240229": {
            "max_tokens": 200000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
        },
        "claude-3-sonnet-20240229": {
            "max_tokens": 200000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
        },
        "claude-3-haiku-20240307": {
            "max_tokens": 200000,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
        },
    }

    def __init__(self, api_key: str, config: Optional[ModelConfig] = None):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            config: Optional model configuration
        """
        super().__init__("anthropic", api_key, config)
        self.base_url = "https://api.anthropic.com/v1"
        self.api_version = "2023-06-01"

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Format messages for Anthropic API.

        Args:
            messages: List of message dictionaries

        Returns:
            Formatted messages for Anthropic API
        """
        formatted = []
        system_message = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_message = content
            else:
                formatted.append({
                    "role": "user" if role == "user" else "assistant",
                    "content": content
                })

        return formatted, system_message

    @tracer.start_as_current_span("anthropic_generate")
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using Claude.

        Args:
            messages: List of conversation messages
            model: Model to use (defaults to config)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Returns:
            Model response
        """
        model = model or self.config.model or "claude-3-5-sonnet-20241022"
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens or 4096

        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported by Anthropic provider")

        formatted_messages, system_message = self._format_messages(messages)

        payload = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_message:
            payload["system"] = system_message

        # Add optional parameters
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            payload["top_k"] = kwargs["top_k"]
        if "stop_sequences" in kwargs:
            payload["stop_sequences"] = kwargs["stop_sequences"]

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            # Calculate cost
            model_info = self.SUPPORTED_MODELS[model]
            cost = (
                (input_tokens / 1000) * model_info["cost_per_1k_input"] +
                (output_tokens / 1000) * model_info["cost_per_1k_output"]
            )

            logger.info(
                f"Anthropic API call successful - Model: {model}, "
                f"Tokens: {input_tokens + output_tokens}, Cost: ${cost:.6f}"
            )

            return ModelResponse(
                content=content,
                model=model,
                provider=self.name,
                tokens_used=input_tokens + output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                finish_reason=data.get("stop_reason"),
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Anthropic provider error: {e}")
            raise

    @tracer.start_as_current_span("anthropic_stream")
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate a streaming response using Claude.

        Args:
            messages: List of conversation messages
            model: Model to use (defaults to config)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Yields:
            Stream chunks
        """
        model = model or self.config.model or "claude-3-5-sonnet-20241022"
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens or 4096

        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported by Anthropic provider")

        formatted_messages, system_message = self._format_messages(messages)

        payload = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if system_message:
            payload["system"] = system_message

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    full_content = ""
                    input_tokens = 0
                    output_tokens = 0

                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break

                        try:
                            import json
                            data = json.loads(data_str)

                            if data["type"] == "content_block_delta":
                                delta = data["delta"]
                                if delta.get("type") == "text_delta":
                                    content_chunk = delta["text"]
                                    full_content += content_chunk

                                    yield StreamChunk(
                                        content=content_chunk,
                                        model=model,
                                        provider=self.name,
                                        finish_reason=None,
                                    )

                            elif data["type"] == "message_start":
                                usage = data.get("message", {}).get("usage", {})
                                input_tokens = usage.get("input_tokens", 0)

                            elif data["type"] == "message_delta":
                                usage = data.get("usage", {})
                                output_tokens = usage.get("output_tokens", 0)

                                # Send final chunk with metadata
                                model_info = self.SUPPORTED_MODELS[model]
                                cost = (
                                    (input_tokens / 1000) * model_info["cost_per_1k_input"] +
                                    (output_tokens / 1000) * model_info["cost_per_1k_output"]
                                )

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

                        except json.JSONDecodeError:
                            continue

            logger.info(
                f"Anthropic stream completed - Model: {model}, "
                f"Tokens: {input_tokens + output_tokens}"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}")
            raise

    def get_supported_models(self) -> List[str]:
        """Get list of supported models."""
        return list(self.SUPPORTED_MODELS.keys())

    def validate_config(self) -> bool:
        """Validate provider configuration."""
        if not self.api_key:
            logger.error("Anthropic API key not provided")
            return False

        if self.config.model and self.config.model not in self.SUPPORTED_MODELS:
            logger.error(f"Model {self.config.model} not supported")
            return False

        return True
