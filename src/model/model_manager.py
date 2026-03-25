"""
Model Manager for Zakera AI Chat Agent.

Centralises provider instantiation, selection, and lifecycle management.
All providers are loaded lazily on first use and cached for the lifetime of
the process (or until ``reset()`` is called).

Provider registry keys
----------------------
openai          – OpenAI GPT-3.5 / GPT-4
anthropic       – Anthropic Claude
gemini          – Google Gemini (stable)
gemini2         – Google Gemini 2.x
groq            – Groq fast inference
mistral         – Mistral AI chat models
codestral       – Mistral Codestral (code generation + FIM)
deepseek        – DeepSeek R1 / V3
cohere          – Cohere Command R+
huggingface     – HuggingFace Inference API
ollama          – Ollama (remote)
ollama_local    – Ollama (local / self-hosted)
openrouter      – OpenRouter aggregator
together        – Together AI
perplexity      – Perplexity Sonar
xai             – xAI Grok
azure           – Azure OpenAI
vertex          – Google Vertex AI (Gemini 1.5 Pro / Flash via service account)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy provider registry
# ---------------------------------------------------------------------------

_PROVIDER_REGISTRY: Dict[str, Any] = {}


def _get_env(key: str, default: str = "") -> str:
    """Read an env var, stripping surrounding whitespace."""
    return os.environ.get(key, default).strip()


def get_provider(name: str) -> Any:
    """
    Return (and cache) the provider instance for *name*.

    Args:
        name: One of the keys listed in the module docstring.

    Returns:
        A provider instance with at minimum a ``stream_chat()`` or
        ``chat()`` method.

    Raises:
        ValueError: If *name* is not a recognised provider key.
        RuntimeError: If the required API key environment variable is unset.
    """
    if name in _PROVIDER_REGISTRY:
        return _PROVIDER_REGISTRY[name]

    provider = _build_provider(name)
    _PROVIDER_REGISTRY[name] = provider
    logger.info("Loaded provider: %s", name)
    return provider


def reset() -> None:
    """Clear the provider cache (useful in tests)."""
    _PROVIDER_REGISTRY.clear()


def list_providers() -> list[str]:
    """Return all supported provider keys."""
    return [
        "openai",
        "anthropic",
        "gemini",
        "gemini2",
        "groq",
        "mistral",
        "codestral",
        "deepseek",
        "cohere",
        "huggingface",
        "ollama",
        "ollama_local",
        "openrouter",
        "together",
        "perplexity",
        "xai",
        "azure",
        "vertex",
    ]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _build_provider(name: str) -> Any:  # noqa: C901 – acceptable complexity here
    """Instantiate the correct provider class based on *name*."""

    if name == "openai":
        from src.model.providers_openai import OpenAIProvider, OpenAIConfig
        return OpenAIProvider(
            OpenAIConfig(api_key=_require_env("OPENAI_API_KEY"))
        )

    if name == "anthropic":
        from src.model.providers_anthropic import AnthropicProvider
        return AnthropicProvider(api_key=_require_env("ANTHROPIC_API_KEY"))

    if name == "gemini":
        from src.model.providers_gemini import GeminiProvider
        return GeminiProvider(api_key=_require_env("GOOGLE_API_KEY"))

    if name == "gemini2":
        from src.model.providers_gemini2 import Gemini2Provider
        return Gemini2Provider(api_key=_require_env("GOOGLE_API_KEY"))

    if name == "groq":
        from src.model.providers_groq import GroqProvider, GroqConfig
        return GroqProvider(GroqConfig(api_key=_require_env("GROQ_API_KEY")))

    if name == "mistral":
        from src.model.providers_mistral import MistralProvider
        return MistralProvider(api_key=_require_env("MISTRAL_API_KEY"))

    if name == "codestral":
        from src.model.providers_mistral_codestral import MistralCodestralProvider
        return MistralCodestralProvider(
            api_key=_require_env("MISTRAL_CODESTRAL_API_KEY")
        )

    if name == "deepseek":
        from src.model.providers_deepseek import DeepSeekProvider
        return DeepSeekProvider(api_key=_require_env("DEEPSEEK_API_KEY"))

    if name == "cohere":
        from src.model.providers_cohere import CohereProvider
        return CohereProvider(api_key=_require_env("COHERE_API_KEY"))

    if name == "huggingface":
        from src.model.providers_huggingface import HuggingFaceProvider
        return HuggingFaceProvider(api_key=_require_env("HUGGINGFACE_API_KEY"))

    if name == "ollama":
        from src.model.providers_ollama import OllamaProvider
        return OllamaProvider(base_url=_get_env("OLLAMA_BASE_URL", "http://localhost:11434"))

    if name == "ollama_local":
        from src.model.providers_ollama_local import OllamaLocalProvider
        return OllamaLocalProvider(
            base_url=_get_env("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434")
        )

    if name == "openrouter":
        from src.model.providers_openrouter import OpenRouterProvider
        return OpenRouterProvider(api_key=_require_env("OPENROUTER_API_KEY"))

    if name == "together":
        from src.model.providers_together import TogetherProvider
        return TogetherProvider(api_key=_require_env("TOGETHER_API_KEY"))

    if name == "perplexity":
        from src.model.providers_perplexity import PerplexityProvider
        return PerplexityProvider(api_key=_require_env("PERPLEXITY_API_KEY"))

    if name == "xai":
        from src.model.providers_xai import XAIProvider
        return XAIProvider(api_key=_require_env("XAI_API_KEY"))

    if name == "azure":
        from src.model.providers_azure import AzureOpenAIProvider
        return AzureOpenAIProvider(
            api_key=_require_env("AZURE_OPENAI_API_KEY"),
            endpoint=_require_env("AZURE_OPENAI_ENDPOINT"),
            deployment=_get_env("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        )

    if name == "vertex":
        from src.model.providers_vertex import VertexAIProvider, VertexConfig
        return VertexAIProvider(
            VertexConfig(
                project_id=_require_env("GOOGLE_VERTEX_PROJECT"),
                sa_key_json=_require_env("GOOGLE_VERTEX_SA_KEY_JSON"),
                location=_get_env("GOOGLE_VERTEX_LOCATION", "us-central1"),
                default_model=_get_env(
                    "GOOGLE_VERTEX_MODEL", "gemini-1.5-pro-002"
                ),
            )
        )

    raise ValueError(
        f"Unknown provider '{name}'. Supported providers: {list_providers()}"
    )


def _require_env(key: str) -> str:
    """Return env var value or raise RuntimeError if unset."""
    value = _get_env(key)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            f"Please add it to your .env file."
        )
    return value
