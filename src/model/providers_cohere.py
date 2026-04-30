"""
Cohere AI Provider Implementation

Provides integration with Cohere's Command models for the AI chat agent.
Supports streaming, error handling, and comprehensive configuration.
"""

import logging
import os
from typing import AsyncIterator, Dict, List, Optional, Any
import cohere
from cohere.types import StreamedChatResponse, NonStreamedChatResponse

from .providers import ModelProvider as BaseProvider, ModelResponse
from .config import ModelConfig


logger = logging.getLogger(__name__)


class CohereProvider(BaseProvider):
    """
    Cohere AI provider implementation supporting Command R+ and Command Light models.
    
    Features:
    - Streaming and non-streaming responses
    - Token usage tracking
    - Cost calculation
    - Comprehensive error handling
    - Model health checks
    """
    
    SUPPORTED_MODELS = {
        "command-r-plus": {
            "name": "Command R+",
            "max_tokens": 128000,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "description": "Most capable model for complex tasks"
        },
        "command-r": {
            "name": "Command R",
            "max_tokens": 128000,
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.0015,
            "description": "Balanced performance and cost"
        },
        "command": {
            "name": "Command",
            "max_tokens": 4096,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.002,
            "description": "Fast, efficient for simple tasks"
        },
        "command-light": {
            "name": "Command Light",
            "max_tokens": 4096,
            "cost_per_1k_input": 0.0003,
            "cost_per_1k_output": 0.0006,
            "description": "Ultra-fast, low-cost option"
        }
    }
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Cohere provider.
        
        Args:
            api_key: Cohere API key (defaults to COHERE_API_KEY env var)
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        
        if not self.api_key:
            raise ValueError("Cohere API key not provided")
        
        self.client = cohere.Client(api_key=self.api_key)
        self.async_client = cohere.AsyncClient(api_key=self.api_key)
        
        logger.info("Cohere provider initialized successfully")
    
    @property
    def provider_name(self) -> str:
        return "cohere"
    
    def is_available(self) -> bool:
        """Check if Cohere API is accessible."""
        try:
            # Simple check by listing models
            self.client.check_api_key()
            return True
        except Exception as e:
            logger.error(f"Cohere availability check failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Return list of supported Cohere models."""
        return list(self.SUPPORTED_MODELS.keys())
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> tuple[str, Optional[str], List[Dict[str, str]]]:
        """
        Format messages for Cohere API.
        
        Cohere expects:
        - message: The current user message
        - preamble: Optional system message
        - chat_history: Previous conversation turns
        
        Returns:
            tuple: (current_message, preamble, chat_history)
        """
        preamble = None
        chat_history = []
        current_message = ""
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                preamble = content
            elif role == "user":
                current_message = content
            elif role == "assistant":
                # Add to history if we have a current message
                if current_message:
                    chat_history.append({
                        "role": "USER",
                        "message": current_message
                    })
                    chat_history.append({
                        "role": "CHATBOT",
                        "message": content
                    })
                    current_message = ""
        
        return current_message, preamble, chat_history
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response using Cohere API.
        
        Args:
            messages: List of conversation messages
            model: Model name to use
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional model parameters
        
        Returns:
            ModelResponse with generated text and metadata
        """
        model = model or "command-r"
        
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported by Cohere provider")
        
        model_info = self.SUPPORTED_MODELS[model]
        max_tokens = max_tokens or 1024
        
        # Format messages for Cohere
        current_message, preamble, chat_history = self._format_messages(messages)
        
        if not current_message:
            raise ValueError("No user message found in conversation")
        
        try:
            if stream:
                return await self._generate_streaming(
                    message=current_message,
                    model=model,
                    preamble=preamble,
                    chat_history=chat_history,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                return await self._generate_non_streaming(
                    message=current_message,
                    model=model,
                    preamble=preamble,
                    chat_history=chat_history,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
        
        except cohere.errors.CohereError as e:
            logger.error(f"Cohere API error: {e}")
            raise RuntimeError(f"Cohere API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Cohere generation: {e}")
            raise
    
    async def _generate_non_streaming(
        self,
        message: str,
        model: str,
        preamble: Optional[str],
        chat_history: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ModelResponse:
        """Generate non-streaming response."""
        response = await self.async_client.chat(
            message=message,
            model=model,
            preamble=preamble,
            chat_history=chat_history if chat_history else None,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Extract token usage
        token_count = response.meta.tokens if response.meta else None
        input_tokens = token_count.input_tokens if token_count else 0
        output_tokens = token_count.output_tokens if token_count else 0
        
        # Calculate cost
        model_info = self.SUPPORTED_MODELS[model]
        cost = (
            (input_tokens / 1000) * model_info["cost_per_1k_input"] +
            (output_tokens / 1000) * model_info["cost_per_1k_output"]
        )
        
        return ModelResponse(
            content=response.text,
            model=model,
            provider=self.provider_name,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            metadata={
                "generation_id": response.generation_id,
                "finish_reason": "complete"
            }
        )
    
    async def _generate_streaming(
        self,
        message: str,
        model: str,
        preamble: Optional[str],
        chat_history: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ModelResponse:
        """Generate streaming response."""
        full_content = ""
        input_tokens = 0
        output_tokens = 0
        generation_id = None
        
        stream = await self.async_client.chat_stream(
            message=message,
            model=model,
            preamble=preamble,
            chat_history=chat_history if chat_history else None,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.event_type == "text-generation":
                full_content += chunk.text
            elif chunk.event_type == "stream-end":
                # Get final token counts
                if chunk.response and chunk.response.meta:
                    token_count = chunk.response.meta.tokens
                    if token_count:
                        input_tokens = token_count.input_tokens
                        output_tokens = token_count.output_tokens
                if chunk.response:
                    generation_id = chunk.response.generation_id
        
        # Calculate cost
        model_info = self.SUPPORTED_MODELS[model]
        cost = (
            (input_tokens / 1000) * model_info["cost_per_1k_input"] +
            (output_tokens / 1000) * model_info["cost_per_1k_output"]
        )
        
        return ModelResponse(
            content=full_content,
            model=model,
            provider=self.provider_name,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            metadata={
                "generation_id": generation_id,
                "finish_reason": "complete",
                "streaming": True
            }
        )
    
    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response generation token by token.
        
        Yields:
            str: Generated text chunks
        """
        model = model or "command-r"
        
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not supported by Cohere provider")
        
        max_tokens = max_tokens or 1024
        
        # Format messages
        current_message, preamble, chat_history = self._format_messages(messages)
        
        if not current_message:
            raise ValueError("No user message found in conversation")
        
        try:
            stream = await self.async_client.chat_stream(
                message=current_message,
                model=model,
                preamble=preamble,
                chat_history=chat_history if chat_history else None,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.event_type == "text-generation":
                    yield chunk.text
        
        except cohere.errors.CohereError as e:
            logger.error(f"Cohere streaming error: {e}")
            raise RuntimeError(f"Cohere streaming error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Cohere streaming: {e}")
            raise
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} not found")
        
        return self.SUPPORTED_MODELS[model].copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Cohere API.
        
        Returns:
            Dict with health status and available models
        """
        try:
            # Test API connectivity
            is_available = self.is_available()
            
            return {
                "provider": self.provider_name,
                "status": "healthy" if is_available else "unhealthy",
                "available": is_available,
                "models": self.get_available_models(),
                "model_count": len(self.SUPPORTED_MODELS)
            }
        except Exception as e:
            logger.error(f"Cohere health check failed: {e}")
            return {
                "provider": self.provider_name,
                "status": "unhealthy",
                "available": False,
                "error": str(e)
            }
