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
llama3          – Meta Llama 3 via Groq inference API
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

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .providers_llama3 import LlamaProvider as Llama3Provider

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
        "llama3",
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
# Provider health tracking
# ---------------------------------------------------------------------------

@dataclass
class _ProviderHealth:
    """Mutable health record for a single provider."""

    failure_count: int = 0
    last_failure_ts: float = 0.0       # epoch seconds of most-recent failure
    cooling_down: bool = False          # True while the provider is in cooldown


class ProviderHealthTracker:
    """
    Tracks per-provider failure counts and cooldown state.

    A provider enters *cooldown* once its consecutive failure count reaches
    ``failure_threshold``.  It is automatically eligible for retry after
    ``cooldown_seconds`` have elapsed since the last recorded failure.

    Usage::

        tracker = ProviderHealthTracker()
        tracker.record_failure("openai")
        if tracker.is_healthy("openai"):
            ...
        tracker.reset_provider("openai")

    This class is intentionally **not** thread-safe by default.  Wrap
    accesses in a lock if you share a single instance across threads.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
    ) -> None:
        """
        Initialise the tracker.

        Args:
            failure_threshold: Number of consecutive failures before a
                               provider is placed into cooldown.
            cooldown_seconds:  How long (seconds) to wait before considering
                               a cooling-down provider healthy again.
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if cooldown_seconds <= 0:
            raise ValueError("cooldown_seconds must be > 0")

        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._health: Dict[str, _ProviderHealth] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, provider: str) -> _ProviderHealth:
        if provider not in self._health:
            self._health[provider] = _ProviderHealth()
        return self._health[provider]

    def _auto_recover(self, health: _ProviderHealth) -> None:
        """Clear cooldown flag if the cooldown window has passed."""
        if (
            health.cooling_down
            and health.last_failure_ts > 0
            and (time.monotonic() - health.last_failure_ts) >= self.cooldown_seconds
        ):
            health.cooling_down = False
            health.failure_count = 0
            logger.debug("Provider auto-recovered after cooldown.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_failure(self, provider: str) -> None:
        """
        Record a failure for *provider*.

        If the failure count reaches ``failure_threshold`` the provider is
        placed into cooldown and will not be considered healthy until
        ``cooldown_seconds`` have elapsed.

        Args:
            provider: Provider name (e.g. ``"openai"``).
        """
        health = self._get_or_create(provider)
        health.failure_count += 1
        health.last_failure_ts = time.monotonic()

        if health.failure_count >= self.failure_threshold:
            if not health.cooling_down:
                health.cooling_down = True
                logger.warning(
                    "Provider '%s' reached %d consecutive failures — "
                    "entering %.0fs cooldown.",
                    provider,
                    health.failure_count,
                    self.cooldown_seconds,
                )

    def record_success(self, provider: str) -> None:
        """
        Record a successful call for *provider*, resetting its failure count.

        Args:
            provider: Provider name.
        """
        health = self._get_or_create(provider)
        if health.failure_count > 0 or health.cooling_down:
            logger.info(
                "Provider '%s' recovered after success (was %d failures).",
                provider,
                health.failure_count,
            )
        health.failure_count = 0
        health.cooling_down = False
        health.last_failure_ts = 0.0

    def is_healthy(self, provider: str) -> bool:
        """
        Return *True* if *provider* is currently eligible to receive requests.

        A provider is healthy when it is either:
        - Unknown to the tracker (never failed), or
        - Not in cooldown, or
        - In cooldown but the cooldown window has expired.

        Args:
            provider: Provider name.

        Returns:
            ``True`` if the provider should be tried, ``False`` otherwise.
        """
        if provider not in self._health:
            return True
        health = self._health[provider]
        self._auto_recover(health)
        return not health.cooling_down

    def reset_provider(self, provider: str) -> None:
        """
        Manually clear all failure state for *provider*.

        Useful after confirming that a provider's underlying issue has been
        resolved (e.g. API key rotated, quota renewed).

        Args:
            provider: Provider name.
        """
        if provider in self._health:
            self._health[provider] = _ProviderHealth()
            logger.info("Health state for provider '%s' manually reset.", provider)

    def get_status(self, provider: str) -> Dict[str, Any]:
        """
        Return a snapshot of *provider*'s current health state.

        Args:
            provider: Provider name.

        Returns:
            Dict with keys ``provider``, ``failure_count``,
            ``cooling_down``, ``seconds_until_recovery``.
        """
        if provider not in self._health:
            return {
                "provider": provider,
                "failure_count": 0,
                "cooling_down": False,
                "seconds_until_recovery": 0.0,
            }
        health = self._health[provider]
        self._auto_recover(health)

        seconds_until_recovery = 0.0
        if health.cooling_down and health.last_failure_ts > 0:
            elapsed = time.monotonic() - health.last_failure_ts
            seconds_until_recovery = max(0.0, self.cooldown_seconds - elapsed)

        return {
            "provider": provider,
            "failure_count": health.failure_count,
            "cooling_down": health.cooling_down,
            "seconds_until_recovery": round(seconds_until_recovery, 1),
        }

    def all_statuses(self) -> List[Dict[str, Any]]:
        """Return health snapshots for every tracked provider."""
        return [self.get_status(p) for p in self._health]


# ---------------------------------------------------------------------------
# Module-level default tracker (shared across the process)
# ---------------------------------------------------------------------------

#: Default :class:`ProviderHealthTracker` used by :func:`invoke_with_fallback`.
#: Override or replace it for custom thresholds / testing.
default_health_tracker = ProviderHealthTracker(
    failure_threshold=3,
    cooldown_seconds=60.0,
)


# ---------------------------------------------------------------------------
# Fallback chain invocation
# ---------------------------------------------------------------------------

async def invoke_with_fallback(
    provider_chain: List[str],
    invoke_fn: Callable[[Any], Any],
    *,
    retry_attempts: int = 3,
    base_backoff: float = 1.0,
    health_tracker: Optional[ProviderHealthTracker] = None,
) -> Any:
    """
    Try each provider in *provider_chain* in order, retrying on failure.

    For every provider in the chain the function:

    1. Skips the provider if the health tracker considers it unhealthy.
    2. Calls ``invoke_fn(provider_instance)`` up to *retry_attempts* times,
       applying exponential back-off between retries
       (``base_backoff * 2 ** attempt`` seconds).
    3. On success, records a success with the health tracker and returns
       the result immediately.
    4. On failure, records a failure with the health tracker and moves on
       to the next provider in the chain.

    Args:
        provider_chain:  Ordered list of provider keys to try.  The first
                         healthy provider that succeeds is used.
        invoke_fn:       Async or sync callable that accepts a single
                         provider instance and performs the model call.
                         Should raise an exception on failure.
        retry_attempts:  Maximum number of call attempts per provider
                         before declaring it failed.  Defaults to ``3``.
        base_backoff:    Base delay in seconds for exponential back-off.
                         Delay for attempt *n* is
                         ``base_backoff * 2 ** n`` seconds.
                         Defaults to ``1.0``.
        health_tracker:  :class:`ProviderHealthTracker` to use.  Defaults
                         to :data:`default_health_tracker`.

    Returns:
        The return value of the first successful ``invoke_fn`` call.

    Raises:
        RuntimeError: If every provider in the chain fails or is unhealthy.

    Example::

        async def call(provider):
            return await provider.chat(messages=[...])

        result = await invoke_with_fallback(
            provider_chain=["openai", "anthropic", "groq"],
            invoke_fn=call,
        )
    """
    if not provider_chain:
        raise ValueError("provider_chain must not be empty.")
    if retry_attempts < 1:
        raise ValueError("retry_attempts must be >= 1.")

    tracker = health_tracker or default_health_tracker
    errors: List[str] = []

    for provider_name in provider_chain:
        if not tracker.is_healthy(provider_name):
            status = tracker.get_status(provider_name)
            logger.info(
                "Skipping provider '%s' — in cooldown, %.1fs remaining.",
                provider_name,
                status["seconds_until_recovery"],
            )
            errors.append(
                f"{provider_name}: skipped (cooldown "
                f"{status['seconds_until_recovery']}s remaining)"
            )
            continue

        try:
            provider = get_provider(provider_name)
        except (ValueError, RuntimeError) as exc:
            logger.warning(
                "Cannot load provider '%s': %s — skipping.", provider_name, exc
            )
            errors.append(f"{provider_name}: load error — {exc}")
            continue

        last_exc: Optional[Exception] = None

        for attempt in range(retry_attempts):
            if attempt > 0:
                delay = base_backoff * (2 ** (attempt - 1))
                logger.info(
                    "Retry %d/%d for provider '%s' after %.1fs back-off.",
                    attempt,
                    retry_attempts - 1,
                    provider_name,
                    delay,
                )
                await asyncio.sleep(delay)

            try:
                if asyncio.iscoroutinefunction(invoke_fn):
                    result = await invoke_fn(provider)
                else:
                    result = invoke_fn(provider)

                tracker.record_success(provider_name)
                logger.info(
                    "Provider '%s' succeeded on attempt %d.",
                    provider_name,
                    attempt + 1,
                )
                return result

            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(
                    "Provider '%s' attempt %d/%d failed: %s",
                    provider_name,
                    attempt + 1,
                    retry_attempts,
                    exc,
                )

        # All retry attempts for this provider exhausted
        tracker.record_failure(provider_name)
        errors.append(
            f"{provider_name}: all {retry_attempts} attempts failed — "
            f"{last_exc}"
        )
        logger.error(
            "Provider '%s' exhausted all %d attempt(s). Moving to next in chain.",
            provider_name,
            retry_attempts,
        )

    raise RuntimeError(
        "All providers in the fallback chain failed or were unavailable.\n"
        + "\n".join(f"  • {e}" for e in errors)
    )


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

    if name == "llama3":
        return Llama3Provider(
            api_key=_require_env("GROQ_API_KEY"),
            default_model="llama3-70b-8192",
        )

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
