"""Perplexity AI Provider Implementation.

This module provides integration with Perplexity AI's models, including
their search-enhanced Sonar models that provide real-time web search capabilities.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .providers import ModelProvider as BaseProvider, ModelResponse

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class PerplexityProvider(BaseProvider):
    """Perplexity AI provider implementation with search capabilities."""

    def __init__(self, config: Any):
        """Initialize Perplexity provider.
        
        Args:
            config: Provider configuration containing API key and settings
        """
        super().__init__(config)
        self.api_key = config.api_key
        self.base_url = "https://api.perplexity.ai"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=config.timeout or 60.0
        )
        
        # Perplexity model pricing (per 1K tokens)
        self.pricing = {
            "sonar": {"input": 0.001, "output": 0.001},
            "sonar-medium": {"input": 0.0015, "output": 0.0015},
            "sonar-large": {"input": 0.002, "output": 0.002},
        }

    async def generate(
        self,
        prompt: str,
        model: str = "sonar",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using Perplexity AI.
        
        Args:
            prompt: The input prompt
            model: Model name (sonar, sonar-medium, sonar-large)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters (search_domain_filter, etc.)
            
        Returns:
            ModelResponse with generated text and metadata
        """
        with tracer.start_as_current_span(
            "perplexity_generate",
            attributes={
                "model": model,
                "stream": stream,
                "temperature": temperature,
            }
        ) as span:
            try:
                if stream:
                    return await self._generate_stream(prompt, model, temperature, max_tokens, **kwargs)
                else:
                    return await self._generate_sync(prompt, model, temperature, max_tokens, **kwargs)
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Perplexity generation failed: {e}")
                raise

    async def _generate_sync(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> ModelResponse:
        """Generate a synchronous response."""
        payload = self._build_request_payload(
            prompt, model, temperature, max_tokens, stream=False, **kwargs
        )
        
        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract response data
            message = data["choices"][0]["message"]
            content = message["content"]
            usage = data.get("usage", {})
            
            # Extract citations if available (Sonar models provide these)
            citations = message.get("citations", [])
            
            # Calculate cost
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            
            return ModelResponse(
                content=content,
                model=model,
                provider="perplexity",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=usage.get("total_tokens", input_tokens + output_tokens),
                cost=cost,
                metadata={
                    "citations": citations,
                    "finish_reason": data["choices"][0].get("finish_reason"),
                    "model_used": data.get("model", model),
                }
            )
        except httpx.HTTPStatusError as e:
            error_msg = f"Perplexity API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Perplexity request failed: {e}")
            raise

    async def _generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> ModelResponse:
        """Generate a streaming response."""
        payload = self._build_request_payload(
            prompt, model, temperature, max_tokens, stream=True, **kwargs
        )
        
        async def stream_generator() -> AsyncGenerator[str, None]:
            """Stream response chunks."""
            try:
                async with self.client.stream("POST", "/chat/completions", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                import json
                                data = json.loads(data_str)
                                delta = data["choices"][0]["delta"]
                                if "content" in delta:
                                    yield delta["content"]
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                raise
        
        # For streaming, return response with generator
        return ModelResponse(
            content="",  # Content will be streamed
            model=model,
            provider="perplexity",
            input_tokens=0,  # Will be updated after streaming completes
            output_tokens=0,
            total_tokens=0,
            cost=0.0,
            stream=stream_generator(),
            metadata={"streaming": True}
        )

    def _build_request_payload(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        stream: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """Build request payload for Perplexity API."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Perplexity-specific parameters
        if "search_domain_filter" in kwargs:
            payload["search_domain_filter"] = kwargs["search_domain_filter"]
        
        if "return_citations" in kwargs:
            payload["return_citations"] = kwargs["return_citations"]
        
        if "return_related_questions" in kwargs:
            payload["return_related_questions"] = kwargs["return_related_questions"]
        
        if "search_recency_filter" in kwargs:
            payload["search_recency_filter"] = kwargs["search_recency_filter"]
        
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        
        if "top_k" in kwargs:
            payload["top_k"] = kwargs["top_k"]
        
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        
        return payload

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage."""
        # Get pricing for model (default to sonar if not found)
        pricing = self.pricing.get(model, self.pricing["sonar"])
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Perplexity models.
        
        Returns:
            List of available models with metadata
        """
        return [
            {
                "id": "sonar",
                "name": "Sonar",
                "description": "Fast search-enhanced model with real-time web access",
                "context_length": 12000,
                "supports_streaming": True,
                "supports_search": True,
            },
            {
                "id": "sonar-medium",
                "name": "Sonar Medium",
                "description": "Balanced search-enhanced model with extended context",
                "context_length": 16000,
                "supports_streaming": True,
                "supports_search": True,
            },
            {
                "id": "sonar-large",
                "name": "Sonar Large",
                "description": "Most capable search-enhanced model",
                "context_length": 32000,
                "supports_streaming": True,
                "supports_search": True,
            },
        ]

    async def validate_config(self) -> bool:
        """Validate provider configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.api_key:
            logger.error("Perplexity API key not provided")
            return False
        
        try:
            # Test with a simple request
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5,
                }
            )
            response.raise_for_status()
            logger.info("Perplexity configuration validated successfully")
            return True
        except Exception as e:
            logger.error(f"Perplexity validation failed: {e}")
            return False

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()

    def __del__(self):
        """Ensure cleanup on deletion."""
        try:
            asyncio.create_task(self.close())
        except RuntimeError:
            pass  # Event loop might be closed
