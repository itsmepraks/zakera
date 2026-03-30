"""
Provider registry for Zakera AI Chat Agent.

All model providers are registered here so the ModelManager and
the provider-selector API endpoint can discover them by key name.
"""

from __future__ import annotations

from typing import Dict, Type

# ---------------------------------------------------------------------------
# Lazy imports — only the registry dict lives here so that importing this
# module does not force every provider's heavy dependencies to load.
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: Dict[str, str] = {
    # key → fully qualified class path
    "openai":        "src.model.providers.openai_provider.OpenAIProvider",
    "anthropic":     "src.model.providers_anthropic.AnthropicProvider",
    "gemini":        "src.model.providers_gemini.GeminiProvider",
    "gemini2":       "src.model.providers_gemini2.Gemini2Provider",
    "gemini_flash":  "src.model.providers.gemini_flash.GeminiFlashProvider",
    "groq":          "src.model.providers_groq.GroqProvider",
    "mistral":       "src.model.providers_mistral.MistralProvider",
    "mistral_large": "src.model.providers.mistral_large.MistralLargeProvider",
    "deepseek":      "src.model.providers_deepseek.DeepSeekProvider",
    "cohere":        "src.model.providers_cohere.CohereProvider",
    "together":      "src.model.providers_together.TogetherProvider",
    "openrouter":    "src.model.providers_openrouter.OpenRouterProvider",
    "perplexity":    "src.model.providers_perplexity.PerplexityProvider",
    "azure":         "src.model.providers_azure.AzureProvider",
    "huggingface":   "src.model.providers_huggingface.HuggingFaceProvider",
    "ollama":        "src.model.providers_ollama.OllamaProvider",
    "ollama_local":  "src.model.providers_ollama_local.OllamaLocalProvider",
    "xai":           "src.model.providers_xai.XAIProvider",
    "cerebras":      "src.model.providers_cerebras.CerebrasProvider",
}


def load_provider_config(provider_key: str) -> Dict[str, object]:
    """
    Return the default configuration dict for *provider_key*.

    Raises
    ------
    ValueError
        If a required environment variable is absent.
    KeyError
        If *provider_key* is not in PROVIDER_REGISTRY.
    """
    import os  # local import to keep module-level imports minimal

    configs: Dict[str, Dict[str, object]] = {
        "mistral_large": {
            "model_name": "mistral-large-latest",
            "api_key": _require_env("MISTRAL_API_KEY", provider_key),
            "timeout": 120.0,
        },
        "gemini_flash": {
            "model_name": "gemini-2.0-flash-exp",
            "api_key": _require_env("GOOGLE_API_KEY", provider_key),
        },
        "cerebras": {
            "model_name": "llama3.3-70b",
            "api_key": _require_env("CEREBRAS_API_KEY", provider_key),
        },
        # Other providers use their own config loaders; listed here for
        # discoverability only — returning an empty dict is acceptable.
    }

    if provider_key not in PROVIDER_REGISTRY:
        raise KeyError(f"Unknown provider '{provider_key}'. Available: {list(PROVIDER_REGISTRY)}")

    return configs.get(provider_key, {})


def _require_env(var_name: str, provider_key: str) -> str:
    import os
    value = os.environ.get(var_name, "")
    if not value:
        raise ValueError(
            f"Provider '{provider_key}' requires the {var_name} environment variable. "
            "Add it to your .env file and restart the server."
        )
    return value


__all__ = ["PROVIDER_REGISTRY", "load_provider_config"]
