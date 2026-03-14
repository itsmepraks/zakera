"""
usage_tracker.py
================
Per-user, per-provider token consumption tracking service.

Tracks prompt tokens, completion tokens, and estimated USD cost for every
LLM call made through Zakera.  All data lives in a bounded in-memory deque
(no external dependency) protected by an asyncio.Lock so it is safe to use
from concurrent async request handlers.

The module exposes a singleton ``usage_tracker`` that should be imported
by API route handlers; tests can instantiate UsageTracker directly.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Cost table  (USD per 1 000 tokens, [prompt, completion])
# Prices approximate as of early 2026 – update when providers change rates.
# ---------------------------------------------------------------------------
COST_PER_1K_TOKENS: Dict[str, Dict[str, tuple[float, float]]] = {
    # OpenAI
    "gpt-4o": {"openai": (0.005, 0.015)},
    "gpt-4o-mini": {"openai": (0.00015, 0.0006)},
    "gpt-4-turbo": {"openai": (0.01, 0.03)},
    "gpt-4": {"openai": (0.03, 0.06)},
    "gpt-3.5-turbo": {"openai": (0.0005, 0.0015)},
    # Anthropic
    "claude-3-opus-20240229": {"anthropic": (0.015, 0.075)},
    "claude-3-sonnet-20240229": {"anthropic": (0.003, 0.015)},
    "claude-3-haiku-20240307": {"anthropic": (0.00025, 0.00125)},
    "claude-3-5-sonnet-20241022": {"anthropic": (0.003, 0.015)},
    # Google Gemini
    "gemini-1.5-pro": {"google": (0.00125, 0.005)},
    "gemini-1.5-flash": {"google": (0.000075, 0.0003)},
    "gemini-2.0-flash": {"google": (0.0001, 0.0004)},
    # Groq (ultra-fast inference, very cheap)
    "llama3-70b-8192": {"groq": (0.00059, 0.00079)},
    "llama3-8b-8192": {"groq": (0.00005, 0.00008)},
    "mixtral-8x7b-32768": {"groq": (0.00024, 0.00024)},
    "gemma2-9b-it": {"groq": (0.0002, 0.0002)},
    # Mistral
    "mistral-large-latest": {"mistral": (0.004, 0.012)},
    "mistral-small-latest": {"mistral": (0.001, 0.003)},
    "open-mistral-7b": {"mistral": (0.00025, 0.00025)},
    # DeepSeek
    "deepseek-chat": {"deepseek": (0.00014, 0.00028)},
    "deepseek-reasoner": {"deepseek": (0.00055, 0.00219)},
    # Together AI (open-source models)
    "meta-llama/Llama-3-70b-chat-hf": {"together": (0.0009, 0.0009)},
    "meta-llama/Llama-3-8b-chat-hf": {"together": (0.0002, 0.0002)},
    "mistralai/Mixtral-8x7B-Instruct-v0.1": {"together": (0.0006, 0.0006)},
    "Qwen/Qwen2-72B-Instruct": {"together": (0.0009, 0.0009)},
    # xAI Grok
    "grok-2": {"xai": (0.002, 0.010)},
    "grok-2-mini": {"xai": (0.0002, 0.001)},
    "grok-beta": {"xai": (0.005, 0.015)},
    # Perplexity Sonar
    "llama-3.1-sonar-large-128k-online": {"perplexity": (0.001, 0.001)},
    "llama-3.1-sonar-small-128k-online": {"perplexity": (0.0002, 0.0002)},
}

# Flatten to a simple {model_name: (prompt_cost, completion_cost)} lookup
# so callers don't need to pass the provider for cost estimation.
_FLAT_COST: Dict[str, tuple[float, float]] = {
    model: list(providers.values())[0]
    for model, providers in COST_PER_1K_TOKENS.items()
}


@dataclass
class UsageRecord:
    """Immutable snapshot of a single LLM call's token usage."""

    user_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    conversation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
        }


class UsageTracker:
    """
    In-memory sliding-window usage tracker.

    Parameters
    ----------
    max_records:
        Maximum number of ``UsageRecord`` objects to keep in memory.
        Oldest records are evicted automatically once the deque is full.
    webhook_callback:
        Optional async callable ``(record: UsageRecord) -> None`` that is
        awaited after each successful ``record()`` call.  Useful for
        forwarding usage data to an external analytics service.
    """

    def __init__(
        self,
        max_records: int = 10_000,
        webhook_callback: Optional[Callable[[UsageRecord], Any]] = None,
    ) -> None:
        self._records: deque[UsageRecord] = deque(maxlen=max_records)
        self._lock: asyncio.Lock = asyncio.Lock()
        self._webhook = webhook_callback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def record(
        self,
        user_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        conversation_id: Optional[str] = None,
    ) -> UsageRecord:
        """
        Persist a usage record and return it.

        Cost is estimated automatically from the built-in pricing table;
        unknown models get a cost of 0.0.
        """
        total = prompt_tokens + completion_tokens
        cost = self.estimate_cost(model, prompt_tokens, completion_tokens)
        rec = UsageRecord(
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=cost,
            conversation_id=conversation_id,
        )
        async with self._lock:
            self._records.append(rec)

        if self._webhook is not None:
            try:
                await self._webhook(rec)
            except Exception:  # noqa: BLE001
                pass  # webhook errors must never break the main request path

        return rec

    async def get_user_summary(
        self, user_id: str
    ) -> Dict[str, Any]:
        """
        Aggregate token usage and estimated cost for a single user,
        grouped by (provider, model).
        """
        async with self._lock:
            user_records = [r for r in self._records if r.user_id == user_id]

        return self._aggregate(user_records)

    async def get_global_summary(self) -> Dict[str, Any]:
        """Aggregate token usage and cost across ALL users (admin view)."""
        async with self._lock:
            all_records = list(self._records)

        return self._aggregate(all_records)

    async def get_recent_records(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Return paginated raw records, newest-first.

        Pass ``user_id`` to restrict to a single user; omit for global.
        """
        async with self._lock:
            filtered = [
                r
                for r in reversed(self._records)
                if user_id is None or r.user_id == user_id
            ]

        return [r.to_dict() for r in filtered[offset : offset + limit]]

    async def reset_user(self, user_id: str) -> int:
        """Delete all records for *user_id*. Returns the count removed."""
        async with self._lock:
            before = len(self._records)
            self._records = deque(
                (r for r in self._records if r.user_id != user_id),
                maxlen=self._records.maxlen,
            )
            return before - len(self._records)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_cost(
        model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """
        Return the estimated USD cost for a call.

        Returns 0.0 for unrecognised models so callers never get an error.
        """
        rates = _FLAT_COST.get(model)
        if rates is None:
            return 0.0
        prompt_cost, completion_cost = rates
        return round(
            (prompt_tokens / 1000) * prompt_cost
            + (completion_tokens / 1000) * completion_cost,
            8,
        )

    @staticmethod
    def _aggregate(records: List[UsageRecord]) -> Dict[str, Any]:
        """Produce a summary dict from a list of records."""
        totals: Dict[str, Dict[str, Any]] = {}
        grand_prompt = grand_completion = grand_total = 0
        grand_cost = 0.0

        for r in records:
            key = f"{r.provider}/{r.model}"
            if key not in totals:
                totals[key] = {
                    "provider": r.provider,
                    "model": r.model,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                    "call_count": 0,
                }
            bucket = totals[key]
            bucket["prompt_tokens"] += r.prompt_tokens
            bucket["completion_tokens"] += r.completion_tokens
            bucket["total_tokens"] += r.total_tokens
            bucket["estimated_cost_usd"] = round(
                bucket["estimated_cost_usd"] + r.estimated_cost_usd, 8
            )
            bucket["call_count"] += 1

            grand_prompt += r.prompt_tokens
            grand_completion += r.completion_tokens
            grand_total += r.total_tokens
            grand_cost = round(grand_cost + r.estimated_cost_usd, 8)

        return {
            "by_model": list(totals.values()),
            "grand_total": {
                "prompt_tokens": grand_prompt,
                "completion_tokens": grand_completion,
                "total_tokens": grand_total,
                "estimated_cost_usd": grand_cost,
                "call_count": len(records),
            },
        }


# Module-level singleton – import this in route handlers.
usage_tracker = UsageTracker()
