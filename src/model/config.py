"""
Configuration schema for model providers in Zakera.

All values are read from environment variables. Copy ``.env.example`` to
``.env`` and populate the keys for every provider you intend to use.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelConfig:
    """
    Runtime configuration snapshot.

    Populated once at startup via :func:`load_config`.
    """

    # ---- OpenAI -------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # ---- Anthropic ----------------------------------------------------
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # ---- Google Gemini ------------------------------------------------
    google_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"
    gemini2_model: str = "gemini-2.0-flash"

    # ---- Groq ---------------------------------------------------------
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ---- Mistral ------------------------------------------------------
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"

    # ---- Mistral Codestral (code generation) --------------------------
    mistral_codestral_api_key: str = ""
    codestral_model: str = "codestral-latest"
    codestral_fim_stop: list = field(default_factory=lambda: ["\n\n"])

    # ---- DeepSeek -----------------------------------------------------
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-reasoner"
    DEEPSEEK_V3_MODEL: str = "deepseek-chat"

    # ---- Cohere -------------------------------------------------------
    cohere_api_key: str = ""
    cohere_model: str = "command-r-plus"

    # ---- HuggingFace --------------------------------------------------
    huggingface_api_key: str = ""
    huggingface_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"

    # ---- Ollama -------------------------------------------------------
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # ---- Ollama Local -------------------------------------------------
    ollama_local_base_url: str = "http://localhost:11434"
    ollama_local_model: str = "llama3.2"

    # ---- OpenRouter ---------------------------------------------------
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # ---- Together AI --------------------------------------------------
    together_api_key: str = ""
    together_model: str = "meta-llama/Llama-3-70b-chat-hf"

    # ---- Perplexity ---------------------------------------------------
    perplexity_api_key: str = ""
    perplexity_model: str = "llama-3.1-sonar-large-128k-online"

    # ---- xAI ----------------------------------------------------------
    xai_api_key: str = ""
    xai_model: str = "grok-2-latest"

    # ---- Azure OpenAI -------------------------------------------------
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-10-21"

    # ---- Shared defaults ----------------------------------------------
    default_provider: str = "anthropic"
    max_tokens: int = 4096
    temperature: float = 0.7
    request_timeout: float = 120.0
    max_retries: int = 3


def load_config() -> ModelConfig:
    """Read all provider settings from environment variables."""
    return ModelConfig(
        # OpenAI
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_model=_env("OPENAI_MODEL", "gpt-4o"),
        # Anthropic
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        anthropic_model=_env("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        # Google
        google_api_key=_env("GOOGLE_API_KEY"),
        gemini_model=_env("GEMINI_MODEL", "gemini-1.5-pro"),
        gemini2_model=_env("GEMINI2_MODEL", "gemini-2.0-flash"),
        # Groq
        groq_api_key=_env("GROQ_API_KEY"),
        groq_model=_env("GROQ_MODEL", "llama-3.3-70b-versatile"),
        # Mistral
        mistral_api_key=_env("MISTRAL_API_KEY"),
        mistral_model=_env("MISTRAL_MODEL", "mistral-large-latest"),
        # Codestral
        mistral_codestral_api_key=_env("MISTRAL_CODESTRAL_API_KEY"),
        codestral_model=_env("CODESTRAL_MODEL", "codestral-latest"),
        # DeepSeek
        deepseek_api_key=_env("DEEPSEEK_API_KEY"),
        deepseek_model=_env("DEEPSEEK_MODEL", "deepseek-reasoner"),
        # Cohere
        cohere_api_key=_env("COHERE_API_KEY"),
        cohere_model=_env("COHERE_MODEL", "command-r-plus"),
        # HuggingFace
        huggingface_api_key=_env("HUGGINGFACE_API_KEY"),
        huggingface_model=_env("HUGGINGFACE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"),
        # Ollama
        ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=_env("OLLAMA_MODEL", "llama3.2"),
        # Ollama Local
        ollama_local_base_url=_env("OLLAMA_LOCAL_BASE_URL", "http://localhost:11434"),
        ollama_local_model=_env("OLLAMA_LOCAL_MODEL", "llama3.2"),
        # OpenRouter
        openrouter_api_key=_env("OPENROUTER_API_KEY"),
        openrouter_model=_env("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"),
        # Together
        together_api_key=_env("TOGETHER_API_KEY"),
        together_model=_env("TOGETHER_MODEL", "meta-llama/Llama-3-70b-chat-hf"),
        # Perplexity
        perplexity_api_key=_env("PERPLEXITY_API_KEY"),
        perplexity_model=_env("PERPLEXITY_MODEL", "llama-3.1-sonar-large-128k-online"),
        # xAI
        xai_api_key=_env("XAI_API_KEY"),
        xai_model=_env("XAI_MODEL", "grok-2-latest"),
        # Azure
        azure_openai_api_key=_env("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=_env("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=_env("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        azure_openai_api_version=_env("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        # Shared
        default_provider=_env("DEFAULT_PROVIDER", "anthropic"),
        max_tokens=int(_env("MAX_TOKENS", "4096")),
        temperature=float(_env("TEMPERATURE", "0.7")),
        request_timeout=float(_env("REQUEST_TIMEOUT", "120.0")),
        max_retries=int(_env("MAX_RETRIES", "3")),
    )


def _env(key: str, default: str = "") -> str:
    """Read env var, strip whitespace."""
    return os.environ.get(key, default).strip()
