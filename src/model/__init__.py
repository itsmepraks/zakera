"""
Zakera model layer — public exports.

Only eagerly imports providers that are known to work. Other providers
are loaded lazily by model_manager when actually requested.
"""

from .providers import (
    Message,
    ModelProvider,
    ModelResponse,
    OpenAIProvider,
    GeminiProvider,
    LocalModelProvider,
)
from .memory import ConversationMemory  # noqa: F401
from .prompts import PromptTemplate, TOOL_AGENT_PROMPT  # noqa: F401
from .config import ModelConfig  # noqa: F401

__all__ = [
    "Message",
    "ModelProvider",
    "ModelResponse",
    "OpenAIProvider",
    "GeminiProvider",
    "LocalModelProvider",
    "ConversationMemory",
    "ModelConfig",
    "PromptTemplate",
    "TOOL_AGENT_PROMPT",
]
