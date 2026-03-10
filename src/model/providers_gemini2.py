"""Google Gemini 2.0 Flash provider implementation.

This module provides integration with Google's Gemini 2.0 Flash API, including:
- Gemini 2.0 Flash (latest model with enhanced multimodal capabilities)
- Streaming responses with proper chunk handling
- Native multimodal support (text, images, video, audio)
- Safety settings configuration
- Grounding with Google Search
- JSON mode and code execution
- Advanced error handling with retry logic
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, AsyncGenerator, Any
import httpx
from opentelemetry import trace

from .config import ModelConfig
from .providers import ModelProvider, ModelResponse, StreamChunk

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class Gemini2Provider(ModelProvider):
    """Google Gemini 2.0 Flash model provider."""

    SUPPORTED_MODELS = {
        "gemini-2.0-flash-exp": {
            "max_tokens": 1048576,  # 1M tokens context
            "cost_per_1k_input": 0.0,  # Currently free in preview
            "cost_per_1k_output": 0.0,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_audio": True,
            "supports_video": True,
            "max_output_tokens": 8192,
        },
        "gemini-2.0-flash-thinking-exp": {
            "max_tokens": 32768,
            "cost_per_1k_input": 0.0,
            "cost_per_1k_output": 0.0,
            "supports_streaming": True,
            "supports_tools": True,
            "supports_vision": True,
            "supports_audio": False,
            "supports_video": False,
            "max_output_tokens": 8192,
        },
    }

    SAFETY_SETTINGS = {
        "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
    }

    def __init__(self, api_key: str, config: Optional[ModelConfig] = None):
        """Initialize Gemini 2.0 provider.

        Args:
            api_key: Google API key for Gemini
            config: Optional model configuration
        """
        super().__init__("gemini2", api_key, config)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.max_retries = 3
        self.retry_delay = 1.0

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers."""
        return {
            "Content-Type": "application/json",
        }

    def _format_messages(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Format messages for Gemini API.

        Args:
            messages: List of message dictionaries

        Returns:
            Formatted request payload for Gemini API
        """
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        return {"system_instruction": system_instruction, "contents": contents}

    def _get_safety_settings(self) -> List[Dict[str, str]]:
        """Get safety settings for the API request."""
        return [
            {"category": category, "threshold": threshold}
            for category, threshold in self.SAFETY_SETTINGS.items()
        ]

    async def _retry_with_backoff(
        self, func, *args, **kwargs
    ) -> Any:
        """Retry a function with exponential backoff.

        Args:
            func: Async function to retry
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from the function
        """
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limited, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Request failed, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

    @tracer.start_as_current_span("gemini2_generate")
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using Gemini 2.0.

        Args:
            messages: List of conversation messages
            model: Model to use (defaults to config)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Returns:
            Model response
        """
        model = model or self.config.model or "gemini-2.0-flash-exp"
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens or 8192

        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported by Gemini 2.0 provider")

        formatted = self._format_messages(messages)

        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }

        # Add optional parameters
        if "top_p" in kwargs:
            generation_config["topP"] = kwargs["top_p"]
        if "top_k" in kwargs:
            generation_config["topK"] = kwargs["top_k"]
        if "response_mime_type" in kwargs:
            generation_config["responseMimeType"] = kwargs["response_mime_type"]

        payload = {
            "contents": formatted["contents"],
            "generationConfig": generation_config,
            "safetySettings": self._get_safety_settings(),
        }

        if formatted["system_instruction"]:
            payload["systemInstruction"] = formatted["system_instruction"]

        # Add grounding if requested
        if kwargs.get("use_search_grounding"):
            payload["tools"] = [{"googleSearchRetrieval": {}}]

        async def _make_request():
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{model}:generateContent",
                    headers=self._get_headers(),
                    params={"key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

        try:
            data = await self._retry_with_backoff(_make_request)

            # Extract response
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No response candidates returned")

            candidate = candidates[0]
            content_parts = candidate.get("content", {}).get("parts", [])
            
            if not content_parts:
                raise ValueError("No content in response")

            content = content_parts[0].get("text", "")

            # Get usage metadata
            usage = data.get("usageMetadata", {})
            input_tokens = usage.get("promptTokenCount", 0)
            output_tokens = usage.get("candidatesTokenCount", 0)
            total_tokens = usage.get("totalTokenCount", input_tokens + output_tokens)

            # Calculate cost
            model_info = self.SUPPORTED_MODELS[model]
            cost = (
                (input_tokens / 1000) * model_info["cost_per_1k_input"] +
                (output_tokens / 1000) * model_info["cost_per_1k_output"]
            )

            logger.info(
                f"Gemini 2.0 API call successful - Model: {model}, "
                f"Tokens: {total_tokens}, Cost: ${cost:.6f}"
            )

            return ModelResponse(
                content=content,
                model=model,
                provider=self.name,
                tokens_used=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                finish_reason=candidate.get("finishReason"),
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini 2.0 API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Gemini 2.0 provider error: {e}")
            raise

    @tracer.start_as_current_span("gemini2_stream")
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[StreamChunk, None]:
        """Generate a streaming response using Gemini 2.0.

        Args:
            messages: List of conversation messages
            model: Model to use (defaults to config)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Yields:
            Stream chunks
        """
        model = model or self.config.model or "gemini-2.0-flash-exp"
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens or 8192

        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported by Gemini 2.0 provider")

        formatted = self._format_messages(messages)

        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }

        if "top_p" in kwargs:
            generation_config["topP"] = kwargs["top_p"]
        if "top_k" in kwargs:
            generation_config["topK"] = kwargs["top_k"]

        payload = {
            "contents": formatted["contents"],
            "generationConfig": generation_config,
            "safetySettings": self._get_safety_settings(),
        }

        if formatted["system_instruction"]:
            payload["systemInstruction"] = formatted["system_instruction"]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/models/{model}:streamGenerateContent",
                    headers=self._get_headers(),
                    params={"key": self.api_key, "alt": "sse"},
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    input_tokens = 0
                    output_tokens = 0
                    full_content = ""

                    async for line in response.aiter_lines():
                        if not line.strip() or not line.startswith("data: "):
                            continue

                        data_str = line[6:].strip()
                        if not data_str:
                            continue

                        try:
                            data = json.loads(data_str)

                            # Extract content from chunks
                            candidates = data.get("candidates", [])
                            if candidates:
                                candidate = candidates[0]
                                content_parts = candidate.get("content", {}).get("parts", [])
                                
                                if content_parts and "text" in content_parts[0]:
                                    chunk_text = content_parts[0]["text"]
                                    full_content += chunk_text

                                    yield StreamChunk(
                                        content=chunk_text,
                                        model=model,
                                        provider=self.name,
                                        finish_reason=None,
                                    )

                            # Get usage metadata from final chunk
                            usage = data.get("usageMetadata", {})
                            if usage:
                                input_tokens = usage.get("promptTokenCount", input_tokens)
                                output_tokens = usage.get("candidatesTokenCount", output_tokens)

                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE data: {e}")
                            continue

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
                        finish_reason="STOP",
                        tokens_used=input_tokens + output_tokens,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost=cost,
                    )

            logger.info(
                f"Gemini 2.0 stream completed - Model: {model}, "
                f"Tokens: {input_tokens + output_tokens}"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini 2.0 API error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Gemini 2.0 stream error: {e}")
            raise

    def get_supported_models(self) -> List[str]:
        """Get list of supported models."""
        return list(self.SUPPORTED_MODELS.keys())

    def validate_config(self) -> bool:
        """Validate provider configuration."""
        if not self.api_key:
            logger.error("Google API key not provided")
            return False

        if self.config.model and self.config.model not in self.SUPPORTED_MODELS:
            logger.error(f"Model {self.config.model} not supported")
            return False

        return True
