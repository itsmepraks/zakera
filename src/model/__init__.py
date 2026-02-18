"""Model package for AI chat agent.

Provides multi-provider LLM support including:
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Google (Gemini)
- Mistral AI
- Ollama (Local models)
- HuggingFace (Transformers)
"""

from .providers import OpenAIProvider, AnthropicProvider, GoogleProvider
from .providers_mistral import MistralProvider
from .model_manager import ModelManager

__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "MistralProvider",
    "ModelManager",
]
