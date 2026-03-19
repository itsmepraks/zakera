"""
Conversation summarization service for Zakera AI Chat Agent.

Calls the active model provider to produce a structured summary
(title + bullet points) for a conversation, then persists the result.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SummaryBullet:
    text: str
    importance: float = 1.0  # 0.0 – 1.0, higher = more important


@dataclass
class SummaryResult:
    conversation_id: str
    title: str
    bullets: List[SummaryBullet] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = ""
    cached: bool = False


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ConversationSummarizationService:
    """
    Generates and persists structured summaries for conversations.

    Parameters
    ----------
    cache_ttl_seconds:
        How long (seconds) a summary is considered fresh in Redis.
        Default is 3600 (1 hour).
    max_messages_to_summarize:
        Cap on how many messages are fed to the LLM to avoid blowing
        the context window. Oldest messages are trimmed first.
    """

    SYSTEM_PROMPT = (
        "You are a concise summarization assistant. "
        "Given a conversation transcript, return ONLY a JSON object with two keys:\n"
        "  \"title\": a short, descriptive title for the conversation (max 10 words)\n"
        "  \"bullets\": a list of up to 5 concise bullet-point strings that capture "
        "the key topics, decisions, or outcomes. Each bullet must be < 20 words.\n"
        "Respond with raw JSON only — no markdown fences, no commentary."
    )

    def __init__(
        self,
        cache_ttl_seconds: int = 3600,
        max_messages_to_summarize: int = 50,
    ) -> None:
        self.cache_ttl = cache_ttl_seconds
        self.max_messages = max_messages_to_summarize

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def summarize(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        model_manager: Any,  # ModelManager instance from src.model
        model_override: Optional[str] = None,
        redis_client: Optional[Any] = None,
    ) -> SummaryResult:
        """
        Generate a summary for *conversation_id*.

        1. Check Redis cache — return early if still fresh.
        2. Trim messages to self.max_messages.
        3. Build a summarization prompt.
        4. Call the model provider.
        5. Parse and validate LLM output.
        6. Persist to cache.
        7. Return SummaryResult.
        """
        # --- Cache check ---
        cache_key = f"summary:{conversation_id}"
        if redis_client is not None:
            cached_raw = await self._cache_get(redis_client, cache_key)
            if cached_raw:
                try:
                    result = self._deserialize(cached_raw, conversation_id)
                    result.cached = True
                    logger.debug("Cache hit for conversation %s", conversation_id)
                    return result
                except Exception:  # noqa: BLE001
                    logger.warning("Failed to deserialize cached summary, regenerating.")

        if not messages:
            raise ValueError(
                f"Conversation '{conversation_id}' has no messages to summarize."
            )

        # --- Trim ---
        trimmed = messages[-self.max_messages :]

        # --- Build prompt ---
        user_message = self._build_summarize_prompt(trimmed)

        # --- LLM call ---
        try:
            response = await model_manager.generate(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=self.SYSTEM_PROMPT,
                model_override=model_override,
                temperature=0.3,
                max_tokens=512,
                json_mode=True,
            )
            raw_content = response.get("content", "")
            model_used = response.get("model", model_override or "default")
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM summarization failed: %s", exc)
            raise RuntimeError(f"Summarization failed: {exc}") from exc

        # --- Parse ---
        result = self._parse_llm_output(
            raw=raw_content,
            conversation_id=conversation_id,
            model_used=model_used,
            fallback_title=self._first_user_line(messages),
        )

        # --- Cache store ---
        if redis_client is not None:
            await self._cache_set(
                redis_client,
                cache_key,
                self._serialize(result),
                ttl=self.cache_ttl,
            )

        return result

    async def get_cached(
        self,
        conversation_id: str,
        redis_client: Any,
    ) -> Optional[SummaryResult]:
        """
        Return the cached summary without triggering a new LLM call.
        Returns None if no cached summary exists.
        """
        cache_key = f"summary:{conversation_id}"
        raw = await self._cache_get(redis_client, cache_key)
        if raw is None:
            return None
        result = self._deserialize(raw, conversation_id)
        result.cached = True
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summarize_prompt(messages: List[Dict[str, Any]]) -> str:
        """Convert a messages list into a plain-text transcript for the LLM."""
        lines = ["Here is the conversation transcript:\n"]
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            if isinstance(content, list):
                # Multimodal content — extract text parts only
                content = " ".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            lines.append(f"[{role}]: {content}")
        lines.append("\nPlease summarise the above conversation.")
        return "\n".join(lines)

    @staticmethod
    def _parse_llm_output(
        raw: str,
        conversation_id: str,
        model_used: str,
        fallback_title: str,
    ) -> SummaryResult:
        """
        Parse the LLM's JSON response into a SummaryResult.

        Falls back gracefully when the model returns malformed JSON.
        """
        # Strip any accidental markdown fences
        cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE).strip()
        cleaned = cleaned.rstrip("`").strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract just the JSON object with a regex
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        title = str(data.get("title", "")).strip() or fallback_title
        raw_bullets = data.get("bullets", [])

        bullets: List[SummaryBullet] = []
        for item in raw_bullets[:5]:  # cap at 5
            if isinstance(item, str):
                bullets.append(SummaryBullet(text=item.strip()))
            elif isinstance(item, dict):
                bullets.append(
                    SummaryBullet(
                        text=str(item.get("text", "")).strip(),
                        importance=float(item.get("importance", 1.0)),
                    )
                )

        return SummaryResult(
            conversation_id=conversation_id,
            title=title,
            bullets=bullets,
            model_used=model_used,
        )

    @staticmethod
    def _first_user_line(messages: List[Dict[str, Any]]) -> str:
        """Derive a fallback title from the first user message."""
        for msg in messages:
            if msg.get("role") == "user":
                content = str(msg.get("content", ""))
                # Truncate to ≤ 60 chars
                return (content[:57] + "...") if len(content) > 60 else content
        return "Untitled Conversation"

    # ------------------------------------------------------------------
    # Cache helpers (thin wrappers — makes unit testing easier)
    # ------------------------------------------------------------------

    @staticmethod
    async def _cache_get(redis_client: Any, key: str) -> Optional[str]:
        try:
            return await redis_client.get(key)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    async def _cache_set(redis_client: Any, key: str, value: str, ttl: int) -> None:
        try:
            await redis_client.setex(key, ttl, value)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to write summary to Redis cache (key=%s).", key)

    @staticmethod
    def _serialize(result: SummaryResult) -> str:
        return json.dumps({
            "title": result.title,
            "bullets": [
                {"text": b.text, "importance": b.importance}
                for b in result.bullets
            ],
            "generated_at": result.generated_at.isoformat(),
            "model_used": result.model_used,
        })

    @staticmethod
    def _deserialize(raw: str, conversation_id: str) -> SummaryResult:
        data = json.loads(raw)
        bullets = [
            SummaryBullet(text=b["text"], importance=b.get("importance", 1.0))
            for b in data.get("bullets", [])
        ]
        return SummaryResult(
            conversation_id=conversation_id,
            title=data["title"],
            bullets=bullets,
            generated_at=datetime.fromisoformat(data["generated_at"]),
            model_used=data.get("model_used", ""),
        )
