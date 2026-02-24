"""Azure OpenAI Provider for Zakera AI Chat Agent.

This module provides integration with Azure OpenAI Service, enabling
enterprise customers to use their Azure deployments with full compliance
and data residency requirements.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, AsyncGenerator, Any
import aiohttp
import time
from datetime import datetime

from .config import ModelConfig, ModelProvider


logger = logging.getLogger(__name__)


class AzureOpenAIProvider:
    """Azure OpenAI provider implementation.
    
    Supports:
    - GPT-4, GPT-3.5-Turbo, GPT-4-Vision models
    - Custom deployment names
    - Multi-region deployments
    - API key and Azure AD authentication
    - Automatic retry with exponential backoff
    - Streaming responses
    - Cost tracking and token usage metrics
    """

    PROVIDER_NAME = ModelProvider.AZURE_OPENAI
    
    # Azure OpenAI API versions
    DEFAULT_API_VERSION = "2024-02-15-preview"
    SUPPORTED_API_VERSIONS = [
        "2024-02-15-preview",
        "2023-12-01-preview",
        "2023-09-01-preview",
        "2023-05-15",
    ]
    
    # Model configurations
    MODEL_CONFIGS = {
        "gpt-4": {
            "max_tokens": 8192,
            "context_window": 8192,
            "cost_per_1k_input": 0.03,
            "cost_per_1k_output": 0.06,
        },
        "gpt-4-32k": {
            "max_tokens": 32768,
            "context_window": 32768,
            "cost_per_1k_input": 0.06,
            "cost_per_1k_output": 0.12,
        },
        "gpt-4-turbo": {
            "max_tokens": 128000,
            "context_window": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
        },
        "gpt-35-turbo": {
            "max_tokens": 4096,
            "context_window": 4096,
            "cost_per_1k_input": 0.0015,
            "cost_per_1k_output": 0.002,
        },
        "gpt-35-turbo-16k": {
            "max_tokens": 16384,
            "context_window": 16384,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.004,
        },
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize Azure OpenAI provider.
        
        Args:
            config: Configuration dictionary containing:
                - azure_endpoint: Azure OpenAI endpoint URL
                - api_key: Azure OpenAI API key
                - deployment_name: Name of the deployment
                - api_version: API version (optional)
                - resource_group: Azure resource group (optional)
                - region: Azure region (optional)
        """
        self.azure_endpoint = config.get("azure_endpoint") or os.getenv(
            "AZURE_OPENAI_ENDPOINT"
        )
        self.api_key = config.get("api_key") or os.getenv(
            "AZURE_OPENAI_API_KEY"
        )
        self.deployment_name = config.get("deployment_name") or os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        )
        self.api_version = config.get(
            "api_version", self.DEFAULT_API_VERSION
        )
        self.resource_group = config.get("resource_group")
        self.region = config.get("region")
        
        # Retry configuration
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1.0)
        self.timeout = config.get("timeout", 60)
        
        # Validate configuration
        if not self.azure_endpoint:
            raise ValueError(
                "Azure endpoint is required. Set AZURE_OPENAI_ENDPOINT or "
                "provide azure_endpoint in config."
            )
        if not self.api_key:
            raise ValueError(
                "API key is required. Set AZURE_OPENAI_API_KEY or "
                "provide api_key in config."
            )
        if not self.deployment_name:
            raise ValueError(
                "Deployment name is required. Set AZURE_OPENAI_DEPLOYMENT_NAME "
                "or provide deployment_name in config."
            )
        
        # Ensure endpoint doesn't end with slash
        self.azure_endpoint = self.azure_endpoint.rstrip("/")
        
        logger.info(
            f"Initialized Azure OpenAI provider with deployment: "
            f"{self.deployment_name}, region: {self.region}"
        )

    def _get_endpoint_url(self, deployment: Optional[str] = None) -> str:
        """Construct the full endpoint URL.
        
        Args:
            deployment: Optional deployment name override
            
        Returns:
            Full API endpoint URL
        """
        deployment = deployment or self.deployment_name
        return (
            f"{self.azure_endpoint}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers.
        
        Returns:
            Dictionary of headers
        """
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make a request to Azure OpenAI API.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            API response dictionary
            
        Raises:
            Exception: If request fails after retries
        """
        url = self._get_endpoint_url()
        headers = self._get_headers()
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        # Add additional parameters
        for key in ["top_p", "frequency_penalty", "presence_penalty", "stop"]:
            if key in kwargs:
                payload[key] = kwargs[key]
        
        # Retry logic
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    timeout = aiohttp.ClientTimeout(total=self.timeout)
                    async with session.post(
                        url, json=payload, headers=headers, timeout=timeout
                    ) as response:
                        if response.status == 200:
                            if stream:
                                return response
                            return await response.json()
                        
                        error_text = await response.text()
                        logger.error(
                            f"Azure OpenAI API error (attempt {attempt + 1}): "
                            f"Status {response.status}, Body: {error_text}"
                        )
                        
                        # Don't retry on client errors (4xx)
                        if 400 <= response.status < 500:
                            raise Exception(
                                f"Azure OpenAI API client error: {error_text}"
                            )
                        
                        last_error = Exception(
                            f"Azure OpenAI API error: {error_text}"
                        )
            
            except asyncio.TimeoutError as e:
                logger.warning(
                    f"Request timeout (attempt {attempt + 1}/{self.max_retries})"
                )
                last_error = e
            
            except Exception as e:
                logger.error(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                last_error = e
            
            # Wait before retrying (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        raise last_error or Exception("Request failed after all retries")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a response.
        
        Args:
            messages: List of message dictionaries
            model: Model name (uses deployment name if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary with content, tokens, and cost
        """
        start_time = time.time()
        
        try:
            response = await self._make_request(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **kwargs,
            )
            
            # Extract response data
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage", {})
            
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # Calculate cost
            model_config = self.MODEL_CONFIGS.get(
                model or "gpt-35-turbo", self.MODEL_CONFIGS["gpt-35-turbo"]
            )
            cost = (
                (input_tokens / 1000) * model_config["cost_per_1k_input"]
                + (output_tokens / 1000) * model_config["cost_per_1k_output"]
            )
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                f"Azure OpenAI response generated in {elapsed_time:.2f}s, "
                f"tokens: {total_tokens}, cost: ${cost:.6f}"
            )
            
            return {
                "content": content,
                "model": model or self.deployment_name,
                "provider": self.PROVIDER_NAME,
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                "cost": cost,
                "latency": elapsed_time,
                "finish_reason": response["choices"][0].get("finish_reason"),
                "metadata": {
                    "deployment": self.deployment_name,
                    "region": self.region,
                    "api_version": self.api_version,
                },
            }
        
        except Exception as e:
            logger.error(f"Azure OpenAI generation failed: {e}")
            raise

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream a response.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Yields:
            Response chunks as they arrive
        """
        try:
            response = await self._make_request(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )
            
            # Process streaming response
            async for line in response.content:
                line = line.decode("utf-8").strip()
                
                if not line or line == "data: [DONE]":
                    continue
                
                if line.startswith("data: "):
                    try:
                        import json
                        data = json.loads(line[6:])
                        
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content")
                            
                            if content:
                                yield content
                    
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse streaming response: {line}")
                        continue
        
        except Exception as e:
            logger.error(f"Azure OpenAI streaming failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the provider is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Make a minimal request to check health
            messages = [{"role": "user", "content": "test"}]
            await self._make_request(
                messages=messages,
                temperature=0,
                max_tokens=1,
            )
            return True
        except Exception as e:
            logger.error(f"Azure OpenAI health check failed: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available models.
        
        Returns:
            List of model names
        """
        return list(self.MODEL_CONFIGS.keys())

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model.
        
        Args:
            model: Model name
            
        Returns:
            Model configuration dictionary
        """
        return self.MODEL_CONFIGS.get(model, {})
