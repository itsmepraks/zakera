"""
Conversation Statistics endpoints.

Provides rich aggregate and per-conversation analytics that go beyond
the simple counts already exposed in ``conversations.py``.

Route summary
-------------
GET  /stats/conversations          – aggregate stats across all user conversations
GET  /stats/conversations/{id}     – detailed stats for a single conversation

The prefix ``/stats`` keeps these routes separate from the CRUD routes
registered under ``/conversations`` in ``conversations.py``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Conversation, Message, User

router = APIRouter(prefix="/stats", tags=["conversation-stats"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class DailyCount(BaseModel):
    """Conversations or messages created on a specific calendar day."""

    date: str = Field(..., description="ISO-8601 date string, e.g. '2026-03-01'")
    count: int


class ProviderUsage(BaseModel):
    """How many messages were handled by a particular model/provider."""

    provider: str = Field(..., description="Model name as stored on the Message row")
    message_count: int
    token_count: int
    total_cost: float = Field(..., description="Estimated USD cost")


class HourlyActivity(BaseModel):
    """Message volume bucketed by hour-of-day (0-23, UTC)."""

    hour: int = Field(..., ge=0, le=23, description="UTC hour of day")
    message_count: int


class AggregateConversationStats(BaseModel):
    """
    Aggregate statistics across all conversations belonging to the
    authenticated user.
    """

    # Totals
    total_conversations: int
    active_conversations: int
    archived_conversations: int
    total_messages: int
    total_tokens: int
    total_cost_usd: float

    # Averages
    avg_messages_per_conversation: float = Field(
        ..., description="Mean number of messages per conversation"
    )
    avg_tokens_per_conversation: float = Field(
        ..., description="Mean tokens consumed per conversation"
    )
    avg_tokens_per_message: float = Field(
        ..., description="Mean tokens per individual message"
    )
    avg_response_latency_ms: Optional[float] = Field(
        None,
        description="Mean assistant response latency in ms; None if not tracked",
    )

    # Trend: conversations created per day for the last *days* days
    conversations_per_day: List[DailyCount] = Field(
        default_factory=list,
        description="Daily new-conversation counts over the requested window",
    )

    # Hourly activity heatmap
    hourly_activity: List[HourlyActivity] = Field(
        default_factory=list,
        description="Message counts bucketed by UTC hour-of-day",
    )

    # Provider breakdown
    provider_usage: List[ProviderUsage] = Field(
        default_factory=list,
        description="Per-model usage breakdown sorted by message count desc",
    )

    # Window metadata
    window_days: int = Field(..., description="Number of days this report covers")
    generated_at: datetime


class PerConversationStats(BaseModel):
    """
    Detailed statistics for a single conversation.
    """

    conversation_id: str
    title: str

    # Counts
    total_messages: int
    user_messages: int
    assistant_messages: int
    system_messages: int
    tool_messages: int

    # Token / cost
    total_tokens: int
    total_cost_usd: float
    avg_tokens_per_message: float
    avg_tokens_per_assistant_message: float

    # Timing
    created_at: datetime
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    duration_minutes: Optional[float] = Field(
        None,
        description="Wall-clock time from first to last message in minutes",
    )
    avg_response_latency_ms: Optional[float] = Field(
        None,
        description="Mean latency of assistant messages in ms; None if not tracked",
    )

    # Provider breakdown
    models_used: List[ProviderUsage] = Field(
        default_factory=list,
        description="Per-model breakdown within this conversation",
    )

    # Hourly activity for this conversation
    hourly_activity: List[HourlyActivity] = Field(
        default_factory=list,
        description="Message counts bucketed by UTC hour-of-day",
    )

    generated_at: datetime


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _build_daily_counts(
    conversations: list[Conversation],
    window_days: int,
) -> List[DailyCount]:
    """
    Return a :class:`DailyCount` entry for every day in the last *window_days*
    days, even those with zero new conversations.
    """
    today = datetime.utcnow().date()
    # Bucket conversations by date
    bucket: Dict[str, int] = defaultdict(int)
    for conv in conversations:
        day_str = conv.created_at.date().isoformat()
        bucket[day_str] += 1

    result: List[DailyCount] = []
    for offset in range(window_days - 1, -1, -1):
        day = today - timedelta(days=offset)
        day_str = day.isoformat()
        result.append(DailyCount(date=day_str, count=bucket.get(day_str, 0)))
    return result


def _build_hourly_activity(messages: list[Message]) -> List[HourlyActivity]:
    """
    Count messages by UTC hour-of-day and return all 24 slots (zero-filled).
    """
    bucket: Dict[int, int] = defaultdict(int)
    for msg in messages:
        if msg.created_at:
            bucket[msg.created_at.hour] += 1
    return [HourlyActivity(hour=h, message_count=bucket.get(h, 0)) for h in range(24)]


def _build_provider_usage(messages: list[Message]) -> List[ProviderUsage]:
    """
    Aggregate message count, token count, and cost by ``model_name``.
    Models with a ``None`` name are grouped under ``"unknown"``.
    Results are sorted by message count descending.
    """
    stats: Dict[str, Dict] = defaultdict(
        lambda: {"message_count": 0, "token_count": 0, "total_cost": 0.0}
    )
    for msg in messages:
        key = msg.model_name or "unknown"
        stats[key]["message_count"] += 1
        stats[key]["token_count"] += msg.tokens_used or 0
        stats[key]["total_cost"] += msg.cost or 0.0

    return sorted(
        [
            ProviderUsage(
                provider=k,
                message_count=v["message_count"],
                token_count=v["token_count"],
                total_cost=round(v["total_cost"], 6),
            )
            for k, v in stats.items()
        ],
        key=lambda p: p.message_count,
        reverse=True,
    )


def _safe_avg(total: float, count: int) -> float:
    """Return *total* / *count* rounded to 2 dp, or 0.0 when *count* is zero."""
    return round(total / count, 2) if count else 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/conversations",
    response_model=AggregateConversationStats,
    summary="Aggregate conversation statistics",
    response_description="Aggregate metrics across all user conversations",
)
def get_aggregate_stats(
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Rolling window in days for trend and activity data",
    ),
    include_archived: bool = Query(
        True,
        description="Include archived conversations in totals",
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AggregateConversationStats:
    """
    Return aggregate statistics across **all** conversations belonging to the
    authenticated user.

    ### Included metrics
    - Conversation and message totals, split by active / archived
    - Token consumption and estimated cost
    - Averages per conversation and per message
    - Mean assistant response latency (when ``Message.latency_ms`` is recorded)
    - New-conversation counts for each of the last *days* days
    - Message volume by UTC hour-of-day (activity heatmap)
    - Per-model/provider usage breakdown
    """
    # ------------------------------------------------------------------ #
    # 1.  Load all non-deleted conversations for this user                #
    # ------------------------------------------------------------------ #
    conv_query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_deleted == False,  # noqa: E712
    )
    if not include_archived:
        conv_query = conv_query.filter(Conversation.is_archived == False)  # noqa: E712

    all_conversations: list[Conversation] = conv_query.all()

    total_conversations = len(all_conversations)
    active_conversations = sum(1 for c in all_conversations if not c.is_archived)
    archived_conversations = total_conversations - active_conversations

    # Denormalised sums stored on the Conversation row
    total_tokens = sum(c.total_tokens or 0 for c in all_conversations)
    total_cost = sum(c.total_cost or 0.0 for c in all_conversations)
    total_messages_from_conv = sum(c.message_count or 0 for c in all_conversations)

    # ------------------------------------------------------------------ #
    # 2.  Load all messages for detailed per-message metrics              #
    # ------------------------------------------------------------------ #
    conv_ids = [c.id for c in all_conversations]

    messages: list[Message] = []
    if conv_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conv_ids))
            .all()
        )

    total_messages = len(messages) or total_messages_from_conv

    # Latency: only consider assistant messages with a recorded latency
    latency_samples = [
        msg.latency_ms
        for msg in messages
        if msg.role == "assistant" and msg.latency_ms is not None
    ]
    avg_latency = (
        round(sum(latency_samples) / len(latency_samples), 1)
        if latency_samples
        else None
    )

    # Token average per message (use Message rows when available, else
    # fall back to the conversation-level total)
    token_sum_from_msgs = sum(msg.tokens_used or 0 for msg in messages)
    effective_total_tokens = token_sum_from_msgs if token_sum_from_msgs else total_tokens

    # ------------------------------------------------------------------ #
    # 3.  Trend: conversations created in the rolling window              #
    # ------------------------------------------------------------------ #
    window_start = datetime.utcnow() - timedelta(days=days)
    windowed_conversations = [
        c for c in all_conversations if c.created_at >= window_start
    ]
    conversations_per_day = _build_daily_counts(windowed_conversations, days)

    # ------------------------------------------------------------------ #
    # 4.  Hourly activity heatmap (all messages)                          #
    # ------------------------------------------------------------------ #
    hourly_activity = _build_hourly_activity(messages)

    # ------------------------------------------------------------------ #
    # 5.  Provider / model usage breakdown                                #
    # ------------------------------------------------------------------ #
    provider_usage = _build_provider_usage(messages)

    return AggregateConversationStats(
        total_conversations=total_conversations,
        active_conversations=active_conversations,
        archived_conversations=archived_conversations,
        total_messages=total_messages,
        total_tokens=effective_total_tokens,
        total_cost_usd=round(total_cost, 6),
        avg_messages_per_conversation=_safe_avg(total_messages, total_conversations),
        avg_tokens_per_conversation=_safe_avg(
            effective_total_tokens, total_conversations
        ),
        avg_tokens_per_message=_safe_avg(effective_total_tokens, total_messages),
        avg_response_latency_ms=avg_latency,
        conversations_per_day=conversations_per_day,
        hourly_activity=hourly_activity,
        provider_usage=provider_usage,
        window_days=days,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=PerConversationStats,
    summary="Per-conversation statistics",
    response_description="Detailed metrics for a single conversation",
)
def get_per_conversation_stats(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PerConversationStats:
    """
    Return detailed statistics for a **single** conversation.

    ### Included metrics
    - Message counts broken down by role (user / assistant / system / tool)
    - Token usage and cost totals and averages
    - Duration from first to last message
    - Mean assistant response latency (when ``Message.latency_ms`` is recorded)
    - Per-model/provider breakdown within this conversation
    - Message-volume heatmap by UTC hour-of-day

    Returns **404** if the conversation does not exist or belongs to a
    different user.
    """
    # ------------------------------------------------------------------ #
    # 1.  Verify ownership                                                #
    # ------------------------------------------------------------------ #
    conversation: Optional[Conversation] = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # ------------------------------------------------------------------ #
    # 2.  Load messages ordered by creation time                          #
    # ------------------------------------------------------------------ #
    messages: list[Message] = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )

    # ------------------------------------------------------------------ #
    # 3.  Role counts                                                      #
    # ------------------------------------------------------------------ #
    role_counter: Counter = Counter(msg.role for msg in messages)
    total_messages = len(messages)
    user_messages = role_counter.get("user", 0)
    assistant_messages = role_counter.get("assistant", 0)
    system_messages = role_counter.get("system", 0)
    tool_messages = role_counter.get("tool", 0)

    # ------------------------------------------------------------------ #
    # 4.  Token / cost aggregates                                          #
    # ------------------------------------------------------------------ #
    token_sum = sum(msg.tokens_used or 0 for msg in messages)
    cost_sum = sum(msg.cost or 0.0 for msg in messages)

    # Fall back to conversation-level totals if per-message data is absent
    effective_tokens = token_sum if token_sum else (conversation.total_tokens or 0)
    effective_cost = cost_sum if cost_sum else (conversation.total_cost or 0.0)

    assistant_msgs = [msg for msg in messages if msg.role == "assistant"]
    assistant_token_sum = sum(msg.tokens_used or 0 for msg in assistant_msgs)

    # ------------------------------------------------------------------ #
    # 5.  Timing                                                           #
    # ------------------------------------------------------------------ #
    first_message_at: Optional[datetime] = messages[0].created_at if messages else None
    last_message_at: Optional[datetime] = messages[-1].created_at if messages else None

    duration_minutes: Optional[float] = None
    if first_message_at and last_message_at and first_message_at != last_message_at:
        duration_minutes = round(
            (last_message_at - first_message_at).total_seconds() / 60, 2
        )

    latency_samples = [
        msg.latency_ms
        for msg in assistant_msgs
        if msg.latency_ms is not None
    ]
    avg_latency: Optional[float] = (
        round(sum(latency_samples) / len(latency_samples), 1)
        if latency_samples
        else None
    )

    # ------------------------------------------------------------------ #
    # 6.  Provider breakdown and hourly heatmap                            #
    # ------------------------------------------------------------------ #
    models_used = _build_provider_usage(messages)
    hourly_activity = _build_hourly_activity(messages)

    return PerConversationStats(
        conversation_id=conversation.id,
        title=conversation.title,
        total_messages=total_messages,
        user_messages=user_messages,
        assistant_messages=assistant_messages,
        system_messages=system_messages,
        tool_messages=tool_messages,
        total_tokens=effective_tokens,
        total_cost_usd=round(effective_cost, 6),
        avg_tokens_per_message=_safe_avg(effective_tokens, total_messages),
        avg_tokens_per_assistant_message=_safe_avg(
            assistant_token_sum, len(assistant_msgs)
        ),
        created_at=conversation.created_at,
        first_message_at=first_message_at,
        last_message_at=last_message_at,
        duration_minutes=duration_minutes,
        avg_response_latency_ms=avg_latency,
        models_used=models_used,
        hourly_activity=hourly_activity,
        generated_at=datetime.utcnow(),
    )
