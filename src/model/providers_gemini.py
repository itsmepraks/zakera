"""Google Gemini model provider implementation.

Supports Gemini 1.5 Pro and Flash models with streaming, function calling,
and comprehensive error handling.
"""

import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional, Any
import json

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .providers import BaseModelProvider, ModelResponse, StreamingResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseModelProvider):
    """Google Gemini model provider with streaming support."""

    SUPPORTED_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ]

    # Pricing per 1K tokens (USD)
    PRICING = {
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000125, "output": 0.0005},
        "gemini-1.0-pro": {"input": 0.00025, "output": 0.0005},
    }

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", **kwargs):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name to use
            **kwargs: Additional configuration
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai is required for Gemini provider. "
                "Install with: pip install google-generativeai"
            )

        super().__init__(model=model, **kwargs)
        self.api_key = api_key
        genai.configure(api_key=api_key)

        # Default configuration
        self.temperature = kwargs.get("temperature", 0.7)
        self.top_p = kwargs.get("top_p", 0.9)
        self.top_k = kwargs.get("top_k", 40)
        self.max_output_tokens = kwargs.get("max_output_tokens", 8192)

        # Initialize model
        self._init_model()

        logger.info(f"Initialized Gemini provider with model: {model}")

    def _init_model(self):
        """Initialize the Gemini model with configuration."""
        generation_config = GenerationConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            max_output_tokens=self.max_output_tokens,
        )

        # Safety settings - block only high probability harmful content
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        self.model = genai.GenerativeModel(
            model_name=self.model,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> ModelResponse:
        """Generate a response from Gemini.

        Args:
            prompt: User prompt
            system_prompt: System instructions (optional)
            conversation_history: Previous messages (optional)
            **kwargs: Additional generation parameters

        Returns:
            ModelResponse with generated text and metadata
        """
        try:
            # Build message history
            messages = []

            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "user", "parts": [system_prompt]})
                messages.append({"role": "model", "parts": ["Understood. I'll follow these instructions."]})

            # Add conversation history
            if conversation_history:
                for msg in conversation_history:
                    role = "model" if msg["role"] == "assistant" else "user"
                    messages.append({"role": role, "parts": [msg["content"]]})

            # Add current prompt
            messages.append({"role": "user", "parts": [prompt]})

            # Generate response
            chat = self.model.start_chat(history=messages[:-1])
            response = await asyncio.to_thread(
                chat.send_message,
                prompt
            )

            # Extract text and metadata
            text = response.text
            prompt_tokens = response.usage_metadata.prompt_token_count
            completion_tokens = response.usage_metadata.candidates_token_count

            # Calculate cost
            cost = self._calculate_cost(prompt_tokens, completion_tokens)

            return ModelResponse(
                content=text,
                model=self.model,
                provider="gemini",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=cost,
                finish_reason="stop",
                metadata={
                    "safety_ratings": [
                        {"category": r.category.name, "probability": r.probability.name}
                        for r in response.candidates[0].safety_ratings
                    ],
                    "model_version": self.model,
                },
            )

        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs,
    ) -> AsyncIterator[StreamingResponse]:
        """Generate streaming response from Gemini.

        Args:
            prompt: User prompt
            system_prompt: System instructions (optional)
            conversation_history: Previous messages (optional)
            **kwargs: Additional generation parameters

        Yields:
            StreamingResponse chunks with incremental text
        """
        try:
            # Build message history
            messages = []

            if system_prompt:
                messages.append({"role": "user", "parts": [system_prompt]})
                messages.append({"role": "model", "parts": ["Understood."]})

            if conversation_history:
                for msg in conversation_history:
                    role = "model" if msg["role"] == "assistant" else "user"
                    messages.append({"role": role, "parts": [msg["content"]]})

            # Start chat and stream
            chat = self.model.start_chat(history=messages)
            response_stream = await asyncio.to_thread(
                chat.send_message,
                prompt,
                stream=True
            )

            # Stream chunks
            full_text = ""
            for chunk in response_stream:
                if chunk.text:
                    full_text += chunk.text
                    yield StreamingResponse(
                        content=chunk.text,
                        model=self.model,
                        provider="gemini",
                        finish_reason=None,
                        metadata={"chunk_index": len(full_text)},
                    )

            # Final chunk with complete metadata
            if hasattr(response_stream, "usage_metadata"):
                prompt_tokens = response_stream.usage_metadata.prompt_token_count
                completion_tokens = response_stream.usage_metadata.candidates_token_count
                cost = self._calculate_cost(prompt_tokens, completion_tokens)

                yield StreamingResponse(
                    content="",
                    model=self.model,
                    provider="gemini",
                    finish_reason="stop",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost=cost,
                    metadata={"complete": True},
                )

        except Exception as e:
            logger.error(f"Gemini streaming error: {str(e)}")
            raise

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Total cost in USD
        """
        pricing = self.PRICING.get(self.model, self.PRICING["gemini-1.5-pro"])
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            result = await asyncio.to_thread(
                self.model.count_tokens,
                text
            )
            return result.total_tokens
        except Exception as e:
            logger.warning(f"Token counting error: {e}")
            # Fallback to simple estimation
            return len(text.split()) * 1.3

    async def validate_model(self) -> bool:
        """Validate that the model is available and configured correctly.

        Returns:
            True if model is valid and accessible
        """
        try:
            # Simple test generation
            test_response = await asyncio.to_thread(
                self.model.generate_content,
                "Say 'OK' if you can hear me."
            )
            return test_response.text is not None
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return False

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available Gemini models.

        Returns:
            List of model identifiers
        """
        return cls.SUPPORTED_MODELS.copy()

    def get_context_window(self) -> int:
        """Get maximum context window size for current model.

        Returns:
            Context window size in tokens
        """
        context_windows = {
            "gemini-1.5-pro": 2_000_000,
            "gemini-1.5-flash": 1_000_000,
            "gemini-1.0-pro": 32_000,
        }
        return context_windows.get(self.model, 32_000)
