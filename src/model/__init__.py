"""Model package initialization.

This package provides model providers and configurations for the AI chat agent.
"""

from .config import ModelConfig
from .providers import ModelProvider, ModelResponse, StreamChunk
from .providers_anthropic import AnthropicProvider
from .providers_gemini import GeminiProvider
from .providers_gemini2 import Gemini2Provider
from .providers_openrouter import OpenRouterProvider
from .model_manager import ModelManager

__all__ = [
    "ModelConfig",
    "ModelProvider",
    "ModelResponse",
    "StreamChunk",
    "AnthropicProvider",
    "GeminiProvider",
    "Gemini2Provider",
    "OpenRouterProvider",
    "ModelManager",
]
