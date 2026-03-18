"""
Model provider configuration loader.

Reads provider credentials and settings from environment variables
or an explicit config dict, and returns a ProviderConfig instance
ready to be passed to any BaseModelProvider subclass.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProviderConfig:
    """Typed configuration for a single model provider."""

    api_key: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Environment variable names per provider
# ---------------------------------------------------------------------------

_ENV_MAP: Dict[str, str] = {
    "openai":       "OPENAI_API_KEY",
    "anthropic":    "ANTHROPIC_API_KEY",
    "gemini":       "GOOGLE_API_KEY",
    "gemini_flash": "GOOGLE_API_KEY",
    "deepseek":     "DEEPSEEK_API_KEY",
    "together":     "TOGETHER_API_KEY",
    "perplexity":   "PERPLEXITY_API_KEY",
    "openrouter":   "OPENROUTER_API_KEY",
    "azure":        "AZURE_OPENAI_API_KEY",
    "ollama":       "",  # Ollama is local, no key required
}

_DEFAULT_MODELS: Dict[str, str] = {
    "openai":       "gpt-4o",
    "anthropic":    "claude-3-5-sonnet-20241022",
    "gemini":       "gemini-1.5-pro",
    "gemini_flash": "gemini-2.0-flash-exp",
    "deepseek":     "deepseek-chat",
    "together":     "meta-llama/Llama-3-70b-chat-hf",
    "perplexity":   "llama-3.1-sonar-large-128k-online",
    "openrouter":   "openai/gpt-4o",
    "azure":        "gpt-4o",
    "ollama":       "llama3.2",
}


def load_provider_config(
    provider_id: str,
    override: Optional[Dict[str, Any]] = None,
) -> ProviderConfig:
    """
    Build a ProviderConfig for the given provider.

    Parameters
    ----------
    provider_id:
        One of the keys in _ENV_MAP (e.g. ``"gemini_flash"``).
    override:
        Optional dict of values to override env-var defaults.
        Accepted keys: ``api_key``, ``model``, ``base_url``,
        ``timeout``, ``max_retries``, ``extra``.

    Raises
    ------
    ValueError
        If the provider is unknown or the API key is missing.
    """
    if provider_id not in _ENV_MAP:
        raise ValueError(
            f"Unknown provider '{provider_id}'. "
            f"Known providers: {sorted(_ENV_MAP.keys())}"
        )

    override = override or {}

    env_var = _ENV_MAP[provider_id]
    api_key = override.get("api_key") or (os.getenv(env_var) if env_var else "local")
    if not api_key:
        raise ValueError(
            f"API key for provider '{provider_id}' is missing. "
            f"Set the {env_var!r} environment variable or pass api_key in override."
        )

    return ProviderConfig(
        api_key=api_key,
        model=override.get("model") or _DEFAULT_MODELS.get(provider_id),
        base_url=override.get("base_url"),
        timeout=float(override.get("timeout", 60.0)),
        max_retries=int(override.get("max_retries", 3)),
        extra=override.get("extra", {}),
    )
