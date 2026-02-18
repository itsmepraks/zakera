"""Mistral AI model provider implementation.

Provides integration with Mistral AI's API for text generation,
including support for streaming responses and multiple model variants.
"""

import os
import time
from typing import Dict, List, Optional, AsyncIterator, Any
import httpx
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MistralConfig:
    """Configuration for Mistral AI provider."""
    api_key: str
    base_url: str = "https://api.mistral.ai/v1"
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0


class MistralProvider:
    """Mistral AI model provider.
    
    Supports all Mistral models including:
    - mistral-tiny-latest: Fast, efficient model
    - mistral-small-latest: Balanced performance
    - mistral-medium-latest: Higher quality
    - mistral-large-latest: Best performance
    """
    
    AVAILABLE_MODELS = [
        "mistral-tiny-latest",
        "mistral-small-latest",
        "mistral-medium-latest",
        "mistral-large-latest",
        "open-mistral-7b",
        "open-mixtral-8x7b",
        "open-mixtral-8x22b",
    ]
    
    # Pricing per 1M tokens (input/output)
    MODEL_PRICING = {
        "mistral-tiny-latest": (0.14, 0.42),
        "mistral-small-latest": (0.6, 1.8),
        "mistral-medium-latest": (2.5, 7.5),
        "mistral-large-latest": (4.0, 12.0),
        "open-mistral-7b": (0.25, 0.25),
        "open-mixtral-8x7b": (0.7, 0.7),
        "open-mixtral-8x22b": (2.0, 6.0),
    }
    
    def __init__(self, config: Optional[MistralConfig] = None):
        """Initialize Mistral provider.
        
        Args:
            config: Configuration object. If None, reads from environment.
        """
        if config is None:
            api_key = os.getenv("MISTRAL_API_KEY")
            if not api_key:
                raise ValueError("MISTRAL_API_KEY environment variable not set")
            config = MistralConfig(api_key=api_key)
        
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
        )
        logger.info("Mistral AI provider initialized")
    
    async def generate(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a response using Mistral AI.
        
        Args:
            model: Model name to use
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            Dict containing response text, usage stats, and metadata
        """
        if model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model {model} not in known models, attempting anyway")
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        start_time = time.time()
        
        try:
            if stream:
                return await self._stream_generate(payload, start_time)
            else:
                return await self._non_stream_generate(payload, start_time)
        except Exception as e:
            logger.error(f"Mistral generation error: {e}")
            raise
    
    async def _non_stream_generate(
        self, payload: Dict, start_time: float
    ) -> Dict[str, Any]:
        """Generate non-streaming response."""
        retries = 0
        last_error = None
        
        while retries < self.config.max_retries:
            try:
                response = await self.client.post("/chat/completions", json=payload)
                response.raise_for_status()
                
                data = response.json()
                elapsed_time = time.time() - start_time
                
                # Extract response
                choice = data["choices"][0]
                message = choice["message"]["content"]
                
                # Extract usage information
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
                
                # Calculate cost
                model = payload["model"]
                cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
                
                return {
                    "text": message,
                    "model": model,
                    "provider": "mistral",
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    },
                    "cost": cost,
                    "latency": elapsed_time,
                    "finish_reason": choice.get("finish_reason", "stop"),
                }
            
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    retries += 1
                    if retries < self.config.max_retries:
                        delay = self.config.retry_delay * (2 ** (retries - 1))
                        logger.warning(
                            f"Mistral API error {e.response.status_code}, "
                            f"retrying in {delay}s (attempt {retries}/{self.config.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                raise
            
            except Exception as e:
                logger.error(f"Mistral generation error: {e}")
                raise
        
        raise last_error or Exception("Max retries exceeded")
    
    async def _stream_generate(
        self, payload: Dict, start_time: float
    ) -> AsyncIterator[Dict[str, Any]]:
        """Generate streaming response."""
        try:
            async with self.client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                
                full_text = ""
                async for line in response.aiter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data: "):
                        line = line[6:]
                    
                    try:
                        chunk_data = json.loads(line)
                        delta = chunk_data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        
                        if content:
                            full_text += content
                            yield {
                                "text": content,
                                "full_text": full_text,
                                "finish_reason": chunk_data["choices"][0].get("finish_reason"),
                            }
                    except json.JSONDecodeError:
                        continue
                
                # Send final message with metadata
                elapsed_time = time.time() - start_time
                yield {
                    "text": "",
                    "full_text": full_text,
                    "done": True,
                    "latency": elapsed_time,
                    "model": payload["model"],
                    "provider": "mistral",
                }
        
        except Exception as e:
            logger.error(f"Mistral streaming error: {e}")
            raise
    
    def _calculate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Calculate cost for the API call.
        
        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Cost in USD
        """
        if model not in self.MODEL_PRICING:
            logger.warning(f"Unknown model {model} for pricing")
            return 0.0
        
        input_price, output_price = self.MODEL_PRICING[model]
        
        # Prices are per 1M tokens, convert to per token
        input_cost = (prompt_tokens / 1_000_000) * input_price
        output_cost = (completion_tokens / 1_000_000) * output_price
        
        return input_cost + output_cost
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Mistral API is accessible.
        
        Returns:
            Dict with health status information
        """
        try:
            # Try a minimal request to check API accessibility
            response = await self.client.get("/models")
            response.raise_for_status()
            
            return {
                "status": "healthy",
                "provider": "mistral",
                "available_models": self.AVAILABLE_MODELS,
                "api_accessible": True,
            }
        except Exception as e:
            logger.error(f"Mistral health check failed: {e}")
            return {
                "status": "unhealthy",
                "provider": "mistral",
                "error": str(e),
                "api_accessible": False,
            }
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def __repr__(self) -> str:
        return f"<MistralProvider models={len(self.AVAILABLE_MODELS)}>"


import asyncio
import json
