"""DeepSeek AI model provider implementation.

Provides integration with DeepSeek's language models including:
- DeepSeek-V3: High-performance general-purpose model
- DeepSeek-R1: Advanced reasoning model
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DeepSeekConfig(BaseModel):
    """Configuration for DeepSeek provider."""

    api_key: str = Field(..., description="DeepSeek API key")
    api_base: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API base URL"
    )
    model: str = Field(
        default="deepseek-chat",
        description="Model name (deepseek-chat, deepseek-coder, deepseek-reasoner)"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=32768,
        description="Maximum tokens to generate"
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    timeout: int = Field(
        default=60,
        ge=1,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries"
    )


class DeepSeekProvider:
    """DeepSeek AI model provider.
    
    Supports DeepSeek's family of models:
    - deepseek-chat: General purpose conversational model
    - deepseek-coder: Specialized coding model
    - deepseek-reasoner: Advanced reasoning capabilities
    """

    SUPPORTED_MODELS = [
        "deepseek-chat",
        "deepseek-coder",
        "deepseek-reasoner",
    ]

    def __init__(self, config: DeepSeekConfig):
        """Initialize DeepSeek provider.
        
        Args:
            config: DeepSeek configuration
        
        Raises:
            ValueError: If model is not supported
        """
        self.config = config
        
        if config.model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Model {config.model} not supported. "
                f"Supported models: {', '.join(self.SUPPORTED_MODELS)}"
            )
        
        self.client = httpx.AsyncClient(
            base_url=config.api_base,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )
        
        logger.info(
            f"Initialized DeepSeek provider with model: {config.model}"
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate chat completion.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Response dictionary with 'content', 'model', 'usage' fields
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": False,
        }
        
        # Add optional parameters if provided
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        
        retries = 0
        last_error = None
        
        while retries <= self.config.max_retries:
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data["model"],
                    "usage": {
                        "prompt_tokens": data["usage"]["prompt_tokens"],
                        "completion_tokens": data["usage"]["completion_tokens"],
                        "total_tokens": data["usage"]["total_tokens"],
                    },
                    "finish_reason": data["choices"][0]["finish_reason"],
                }
            
            except httpx.HTTPError as e:
                last_error = e
                retries += 1
                
                if retries <= self.config.max_retries:
                    logger.warning(
                        f"DeepSeek API request failed (attempt {retries}/"
                        f"{self.config.max_retries}): {e}"
                    )
                    await self._exponential_backoff(retries)
                else:
                    logger.error(
                        f"DeepSeek API request failed after "
                        f"{self.config.max_retries} retries: {e}"
                    )
                    raise
        
        if last_error:
            raise last_error

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming chat completion.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Yields:
            Content chunks as they are generated
        
        Raises:
            httpx.HTTPError: If API request fails
        """
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": True,
        }
        
        # Add optional parameters if provided
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        
        async with self.client.stream(
            "POST",
            "/chat/completions",
            json=payload,
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        import json
                        data = json.loads(data_str)
                        
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            
                            if "content" in delta:
                                yield delta["content"]
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse SSE data: {data_str}")
                        continue

    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Estimate token count for text.
        
        Args:
            text: Input text
            model: Model name (uses configured model if not specified)
        
        Returns:
            Estimated token count
        
        Note:
            This is a rough estimation. For exact counts, use the DeepSeek API.
        """
        # Simple estimation: ~4 characters per token for English
        # This is a rough approximation and should be replaced with
        # proper tokenization if available
        return len(text) // 4

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Model information dictionary
        """
        model_info = {
            "deepseek-chat": {
                "name": "DeepSeek Chat",
                "description": "General-purpose conversational model",
                "max_tokens": 32768,
                "context_window": 64000,
            },
            "deepseek-coder": {
                "name": "DeepSeek Coder",
                "description": "Specialized coding assistant model",
                "max_tokens": 32768,
                "context_window": 64000,
            },
            "deepseek-reasoner": {
                "name": "DeepSeek Reasoner",
                "description": "Advanced reasoning and problem-solving model",
                "max_tokens": 32768,
                "context_window": 64000,
            },
        }
        
        return model_info.get(
            self.config.model,
            {
                "name": self.config.model,
                "description": "Unknown model",
                "max_tokens": 4096,
                "context_window": 8192,
            },
        )

    async def _exponential_backoff(self, retry_count: int) -> None:
        """Implement exponential backoff for retries.
        
        Args:
            retry_count: Current retry attempt number
        """
        import asyncio
        delay = min(2 ** retry_count, 32)  # Max 32 seconds
        await asyncio.sleep(delay)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("DeepSeek provider client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
