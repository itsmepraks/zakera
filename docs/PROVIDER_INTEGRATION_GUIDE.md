# Provider Integration Guide

This guide walks you through adding a **new model provider** to Zakera.
Following these conventions keeps the codebase consistent and makes it easy
for contributors to review, test, and maintain provider code.

---

## Table of Contents

1. [Overview](#overview)
2. [File & Module Conventions](#file--module-conventions)
3. [Required Interface](#required-interface)
4. [Configuration & Environment Variables](#configuration--environment-variables)
5. [Error Hierarchy](#error-hierarchy)
6. [Registering the Provider](#registering-the-provider)
7. [Writing Tests](#writing-tests)
8. [Minimal Code Scaffold](#minimal-code-scaffold)
9. [Checklist](#checklist)

---

## Overview

Zakera supports multiple AI model providers through a **provider module**
pattern. Each provider lives in `src/model/providers_<name>.py` and exposes
an async class that the `ModelManager` (in `src/model/model_manager.py`)
instantiates at runtime based on configuration.

Current providers as of March 2026:

| Provider | Module | Notes |
|---|---|---|
| OpenAI | `providers_openai.py` | GPT-4o, o1, etc. |
| Anthropic | `providers_anthropic.py` | Claude 3.5 Sonnet etc. |
| Google Gemini | `providers_gemini.py` / `providers_gemini2.py` | Gemini 1.5, 2.0 |
| xAI Grok | `providers_xai.py` / `providers_xai_grok2.py` | Grok-2, Grok-2-Vision |
| Groq | `providers_groq.py` | Ultra-fast inference |
| Mistral | `providers_mistral.py` / `providers_mistral_codestral.py` | |
| AWS Bedrock | `providers_bedrock.py` | Multi-model |
| Azure OpenAI | `providers_azure.py` | |
| Ollama (local) | `providers_ollama.py` / `providers_ollama_local.py` | |
| DeepSeek | `providers_deepseek.py` | |
| Cohere | `providers_cohere.py` | |
| HuggingFace | `providers_huggingface.py` | |
| Together AI | `providers_together.py` | |
| OpenRouter | `providers_openrouter.py` | |
| Perplexity | `providers_perplexity.py` | |

---

## File & Module Conventions

```
src/model/
  providers_<provider_name>.py   ← provider implementation
tests/
  test_providers_<provider_name>.py  ← corresponding test file
```

- Use **snake_case** for both file and class names.
- Provider class name: `<ProviderName>Provider`  
  e.g., `MyCoolProvider` in `providers_mycool.py`.
- Config dataclass: `<ProviderName>Config`  
  e.g., `MyCoolConfig`.
- Keep all provider-specific imports inside the module — don't add new
  top-level dependencies to `requirements.txt` without discussion.

---

## Required Interface

Every provider **must** implement the following async methods:

```python
async def complete(
    self,
    messages: list[dict],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    system_prompt: str | None = None,
    **kwargs,
) -> ProviderResponse:
    """Non-streaming completion. Returns a ProviderResponse dataclass."""
    ...

async def stream(
    self,
    messages: list[dict],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    system_prompt: str | None = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """Streaming completion. Yields text delta chunks."""
    ...

async def health_check(self) -> bool:
    """Lightweight connectivity + auth check. Returns True on success."""
    ...

async def close(self) -> None:
    """Release HTTP client and any other resources."""
    ...
```

### ProviderResponse dataclass

Your provider's response dataclass must contain at minimum:

```python
@dataclass
class MyCoolResponse:
    content: str          # The assistant's reply text
    model: str            # The model identifier actually used
    usage: MyCoolUsage    # Token counts (see below)
    finish_reason: str    # "stop", "length", "tool_calls", etc.
    raw: dict | None      # The unmodified API response body

@dataclass
class MyCoolUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

---

## Configuration & Environment Variables

Add your provider's settings to `src/api/config.py` (the Pydantic
`Settings` class) and document them in `.env.example`.

```python
# src/api/config.py (add to existing Settings class)
mycool_api_key: str = Field("", env="MYCOOL_API_KEY")
mycool_base_url: str = Field("https://api.mycool.ai/v1", env="MYCOOL_BASE_URL")
mycool_model: str = Field("mycool-7b", env="MYCOOL_MODEL")
```

```bash
# .env.example (add near other provider keys)
MYCOOL_API_KEY=
MYCOOL_BASE_URL=https://api.mycool.ai/v1
MYCOOL_MODEL=mycool-7b
```

---

## Error Hierarchy

Define a provider-specific exception hierarchy so callers can handle
errors precisely:

```
MyCoolProviderError       ← base exception
├── MyCoolAuthError       ← 401 / invalid key
├── MyCoolRateLimitError  ← 429 (include retry_after if available)
├── MyCoolContextLengthError  ← 400 context exceeded
└── MyCoolServiceError    ← 5xx
```

Map HTTP status codes to these in a `_raise_for_status(response)` static
method — see `providers_xai_grok2.py` for a reference implementation.

---

## Registering the Provider

1. Open `src/model/model_manager.py`.
2. Import your provider class and config.
3. Add a branch to `ModelManager.get_provider()` / `_build_provider()`:

```python
# src/model/model_manager.py
from .providers_mycool import MyCoolProvider, MyCoolConfig

PROVIDER_MAP = {
    # ... existing entries ...
    "mycool": (MyCoolProvider, MyCoolConfig),
}
```

4. Update the `ProviderType` enum (if one exists) and any Pydantic
   validation models in `src/api/models.py`.

---

## Writing Tests

Create `tests/test_providers_<name>.py`. Tests must:

- **Not** make real network calls — mock the HTTP client.
- Cover the happy path for `complete()` and `stream()`.
- Cover every exception type in your error hierarchy.
- Test `health_check()` for both success and failure.
- Verify that retries happen the expected number of times for
  retryable errors (e.g. 429, 5xx).
- Test the async context-manager (`async with Provider(config) as p`).

```bash
# Run only your provider's tests
pytest tests/test_providers_mycool.py -v

# Run with coverage
pytest tests/test_providers_mycool.py --cov=src/model/providers_mycool --cov-report=term-missing
```

---

## Minimal Code Scaffold

Copy-paste this scaffold into `src/model/providers_mycool.py` and fill in
the blanks:

```python
"""MyCool AI provider for Zakera."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

MYCOOL_API_BASE = "https://api.mycool.ai/v1"
DEFAULT_MODEL = "mycool-7b"

@dataclass
class MyCoolConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: float = 60.0
    max_retries: int = 3
    base_url: str = MYCOOL_API_BASE

@dataclass
class MyCoolUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class MyCoolResponse:
    content: str
    model: str
    usage: MyCoolUsage
    finish_reason: str = "stop"
    raw: Optional[Dict[str, Any]] = None

class MyCoolProviderError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class MyCoolAuthError(MyCoolProviderError): pass
class MyCoolRateLimitError(MyCoolProviderError): pass
class MyCoolContextLengthError(MyCoolProviderError): pass
class MyCoolServiceError(MyCoolProviderError): pass


class MyCoolProvider:
    def __init__(self, config: MyCoolConfig) -> None:
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
        return self._client

    async def complete(self, messages: List[Dict], **kwargs) -> MyCoolResponse:
        # TODO: implement
        raise NotImplementedError

    async def stream(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        # TODO: implement
        raise NotImplementedError
        yield  # make this an async generator

    async def health_check(self) -> bool:
        try:
            await self.complete([{"role": "user", "content": "ping"}], max_tokens=1)
            return True
        except Exception as exc:
            logger.error("MyCool health check failed: %s", exc)
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self): return self
    async def __aexit__(self, *_): await self.close()
```

---

## Checklist

Before opening a PR for a new provider, make sure:

- [ ] `src/model/providers_<name>.py` created with full interface
- [ ] `tests/test_providers_<name>.py` created, all tests pass locally
- [ ] No real API calls in tests (mocked)
- [ ] `MYCOOL_API_KEY` and friends added to `src/api/config.py` and `.env.example`
- [ ] Provider registered in `src/model/model_manager.py`
- [ ] `CHANGELOG.md` updated under **Unreleased**
- [ ] PR description includes: provider name, supported models, any notable limitations

---

*Last updated: March 2026 — Zakera AI*
