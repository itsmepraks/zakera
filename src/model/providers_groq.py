"""Groq AI Provider - Ultra-fast LLM inference.

Groq provides lightning-fast inference using LPU (Language Processing Unit)
technology, offering speeds up to 750 tokens/second.

Supported Models:
- llama-3.1-70b-versatile: Best quality, 128K context
- llama-3.1-8b-instant: Ultra-fast, great for most tasks
- mixtral-8x7b-32768: High quality, 32K context
- gemma2-9b-it: Google's Gemma, efficient
- gemma-7b-it: Lightweight Gemma model

Documentation: https://console.groq.com/docs
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from .providers import BaseProvider, ModelResponse

logger = logging.getLogger(__name__)


class GroqConfig(BaseModel):
    """Groq provider configuration."""
    
    api_key: str = Field(..., description="Groq API key")
    base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq API base URL"
    )
    default_model: str = Field(
        default="llama-3.1-70b-versatile",
        description="Default model to use"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=8000, gt=0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


class GroqProvider(BaseProvider):
    """Groq AI provider implementation.
    
    Features:
    - Ultra-fast inference (up to 750 tokens/sec)
    - Support for Llama 3.1, Mixtral, Gemma models
    - Streaming responses
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    """
    
    def __init__(self, config: GroqConfig):
        """Initialize Groq provider.
        
        Args:
            config: Groq configuration
        """
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=config.timeout
        )
        
        # Model specifications for optimal routing
        self.model_specs = {
            "llama-3.1-70b-versatile": {
                "context_length": 131072,
                "speed": "fast",
                "quality": "high",
                "best_for": "general purpose, complex reasoning"
            },
            "llama-3.1-8b-instant": {
                "context_length": 131072,
                "speed": "ultra-fast",
                "quality": "good",
                "best_for": "real-time chat, quick responses"
            },
            "mixtral-8x7b-32768": {
                "context_length": 32768,
                "speed": "fast",
                "quality": "high",
                "best_for": "code generation, analysis"
            },
            "gemma2-9b-it": {
                "context_length": 8192,
                "speed": "very-fast",
                "quality": "good",
                "best_for": "efficient inference, good balance"
            },
            "gemma-7b-it": {
                "context_length": 8192,
                "speed": "very-fast",
                "quality": "moderate",
                "best_for": "lightweight tasks, high throughput"
            }
        }
        
        logger.info(
            f"Initialized Groq provider with model: {config.default_model}"
        )
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> ModelResponse:
        """Generate completion using Groq.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to config.default_model)
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the API
        
        Returns:
            ModelResponse containing the generated text and metadata
        
        Raises:
            Exception: If generation fails after all retries
        """
        model = model or self.config.default_model
        
        if stream:
            return await self._generate_stream(messages, model, **kwargs)
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": False
        }
        
        # Add optional parameters
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        
        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Extract response data
                choice = data["choices"][0]
                usage = data.get("usage", {})
                
                model_response = ModelResponse(
                    text=choice["message"]["content"],
                    provider="groq",
                    model=model,
                    finish_reason=choice.get("finish_reason"),
                    usage={
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0)
                    },
                    metadata={
                        "system_fingerprint": data.get("system_fingerprint"),
                        "model_specs": self.model_specs.get(model, {}),
                        "groq_id": data.get("id"),
                        "created": data.get("created")
                    }
                )
                
                logger.info(
                    f"Groq generation successful: {usage.get('total_tokens', 0)} tokens"
                )
                
                return model_response
            
            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code
                
                # Handle specific error codes
                if status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Groq rate limit hit, waiting {wait_time}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait_time)
                elif status_code == 401:  # Authentication error
                    logger.error("Groq authentication failed - check API key")
                    raise
                elif status_code == 400:  # Bad request
                    logger.error(f"Groq bad request: {e.response.text}")
                    raise
                else:
                    logger.warning(
                        f"Groq request failed with status {status_code} (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Groq generation attempt {attempt + 1} failed: {str(e)}"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries exhausted
        error_msg = f"Groq generation failed after {self.config.max_retries} attempts"
        logger.error(f"{error_msg}: {last_error}")
        raise Exception(f"{error_msg}: {last_error}")
    
    async def _generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream generation from Groq.
        
        Args:
            messages: List of message dictionaries
            model: Model to use
            **kwargs: Additional parameters
        
        Yields:
            Text chunks as they are generated
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "stream": True
        }
        
        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=payload
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
                            continue
        
        except Exception as e:
            logger.error(f"Groq streaming failed: {str(e)}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Groq API health.
        
        Returns:
            Dictionary with health status and available models
        """
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            
            models_data = response.json()
            available_models = [m["id"] for m in models_data.get("data", [])]
            
            return {
                "status": "healthy",
                "provider": "groq",
                "available_models": available_models,
                "default_model": self.config.default_model,
                "base_url": self.config.base_url
            }
        
        except Exception as e:
            logger.error(f"Groq health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "provider": "groq",
                "error": str(e)
            }
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Groq models.
        
        Returns:
            List of model identifiers
        """
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            
            models_data = response.json()
            return [m["id"] for m in models_data.get("data", [])]
        
        except Exception as e:
            logger.error(f"Failed to fetch Groq models: {str(e)}")
            return list(self.model_specs.keys())
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Groq provider client closed")
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get detailed information about a specific model.
        
        Args:
            model: Model identifier
        
        Returns:
            Dictionary with model specifications
        """
        return self.model_specs.get(model, {
            "context_length": "unknown",
            "speed": "unknown",
            "quality": "unknown",
            "best_for": "general purpose"
        })
    
    def recommend_model(
        self,
        priority: str = "balanced"
    ) -> str:
        """Recommend a model based on priority.
        
        Args:
            priority: One of 'speed', 'quality', or 'balanced'
        
        Returns:
            Recommended model identifier
        """
        recommendations = {
            "speed": "llama-3.1-8b-instant",
            "quality": "llama-3.1-70b-versatile",
            "balanced": "gemma2-9b-it",
            "code": "mixtral-8x7b-32768"
        }
        
        return recommendations.get(priority, self.config.default_model)
