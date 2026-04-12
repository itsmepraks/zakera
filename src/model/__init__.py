"""
Zakera model layer — public exports.

All model providers and supporting classes are re-exported from this package
so application code can do simple imports::

    from src.model import OpenAIProvider, TogetherAIProvider, PromptTemplate
"""

from .providers import (
    Message,
    ModelProvider,
    ModelResponse,
    OpenAIProvider,
    GeminiProvider,
    LocalModelProvider,
)
from .providers_anthropic import AnthropicProvider, AnthropicStreamingProvider  # noqa: F401
from .providers_azure import AzureOpenAIProvider  # noqa: F401
from .providers_cohere import CohereProvider  # noqa: F401
from .providers_deepseek import DeepSeekProvider  # noqa: F401
from .providers_gemini import GeminiProProvider  # noqa: F401
from .providers_groq import GroqProvider  # noqa: F401
from .providers_huggingface import HuggingFaceProvider  # noqa: F401
from .providers_jina import JinaAIProvider  # noqa: F401
from .providers_mistral import MistralProvider  # noqa: F401
from .providers_ollama import OllamaProvider  # noqa: F401
from .providers_openrouter import OpenRouterProvider  # noqa: F401
from .providers_perplexity import PerplexityProvider  # noqa: F401
from .providers_together import TogetherAIProvider, TOGETHER_MODELS  # noqa: F401
from .providers_xai import XAIProvider  # noqa: F401
from .memory import ConversationMemory  # noqa: F401
from .memory_enhanced import EnhancedMemory  # noqa: F401
from .memory_vector import VectorMemory  # noqa: F401
from .model_manager import ModelManager  # noqa: F401
from .prompts import PromptTemplate, TOOL_AGENT_PROMPT  # noqa: F401
from .config import ModelConfig  # noqa: F401

__all__ = [
    # Base types
    "Message",
    "ModelProvider",
    "ModelResponse",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "AnthropicStreamingProvider",
    "GeminiProvider",
    "GeminiProProvider",
    "AzureOpenAIProvider",
    "CohereProvider",
    "DeepSeekProvider",
    "GroqProvider",
    "HuggingFaceProvider",
    "JinaAIProvider",
    "LocalModelProvider",
    "MistralProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "PerplexityProvider",
    "TogetherAIProvider",
    "XAIProvider",
    # Model catalogues
    "TOGETHER_MODELS",
    # Memory
    "ConversationMemory",
    "EnhancedMemory",
    "VectorMemory",
    # Utilities
    "ModelManager",
    "ModelConfig",
    "PromptTemplate",
    "TOOL_AGENT_PROMPT",
]
