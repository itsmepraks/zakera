"""
Token Usage & Cost Breakdown API
=================================
Provides per-conversation token accounting and estimated USD cost.

Pricing is sourced from provider public pricing pages as of March 2026 and
stored in the MODEL_PRICING table below.  All costs are expressed in USD per
1 000 tokens.  Actual billing may differ; these are best-effort estimates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Conversation, Message, User

router = APIRouter()

# ---------------------------------------------------------------------------
# Pricing table  (USD per 1 000 tokens)
# ---------------------------------------------------------------------------

@dataclass
class ModelPricing:
    """Per-1k-token pricing for a model (prompt & completion)."""
    prompt: float      # cost per 1 000 prompt tokens in USD
    completion: float  # cost per 1 000 completion tokens in USD
    provider: str


MODEL_PRICING: Dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o":                   ModelPricing(prompt=0.005,   completion=0.015,  provider="openai"),
    "gpt-4o-mini":              ModelPricing(prompt=0.00015, completion=0.0006, provider="openai"),
    "gpt-4-turbo":              ModelPricing(prompt=0.01,    completion=0.03,   provider="openai"),
    "gpt-4-turbo-preview":      ModelPricing(prompt=0.01,    completion=0.03,   provider="openai"),
    "gpt-4":                    ModelPricing(prompt=0.03,    completion=0.06,   provider="openai"),
    "gpt-3.5-turbo":            ModelPricing(prompt=0.0005,  completion=0.0015, provider="openai"),
    "o1":                       ModelPricing(prompt=0.015,   completion=0.06,   provider="openai"),
    "o1-mini":                  ModelPricing(prompt=0.003,   completion=0.012,  provider="openai"),
    "o3-mini":                  ModelPricing(prompt=0.0011,  completion=0.0044, provider="openai"),
    # Anthropic
    "claude-3-5-sonnet-20241022": ModelPricing(prompt=0.003, completion=0.015, provider="anthropic"),
    "claude-3-5-haiku-20241022":  ModelPricing(prompt=0.0008,completion=0.004, provider="anthropic"),
    "claude-3-opus-20240229":     ModelPricing(prompt=0.015, completion=0.075, provider="anthropic"),
    "claude-3-sonnet-20240229":   ModelPricing(prompt=0.003, completion=0.015, provider="anthropic"),
    "claude-3-haiku-20240307":    ModelPricing(prompt=0.00025,completion=0.00125,provider="anthropic"),
    # Google Gemini
    "gemini-1.5-pro":           ModelPricing(prompt=0.0035,  completion=0.0105, provider="google"),
    "gemini-1.5-flash":         ModelPricing(prompt=0.000075,completion=0.0003, provider="google"),
    "gemini-2.0-flash":         ModelPricing(prompt=0.0001,  completion=0.0004, provider="google"),
    "gemini-pro":               ModelPricing(prompt=0.000125,completion=0.000375,provider="google"),
    # Groq (inference pricing)
    "llama-3.3-70b-versatile":  ModelPricing(prompt=0.00059, completion=0.00079,provider="groq"),
    "llama-3.1-8b-instant":     ModelPricing(prompt=0.000059,completion=0.000079,provider="groq"),
    "mixtral-8x7b-32768":       ModelPricing(prompt=0.00024, completion=0.00024,provider="groq"),
    "gemma2-9b-it":             ModelPricing(prompt=0.0002,  completion=0.0002, provider="groq"),
    # Mistral
    "mistral-large-latest":     ModelPricing(prompt=0.003,   completion=0.009,  provider="mistral"),
    "mistral-small-latest":     ModelPricing(prompt=0.0002,  completion=0.0006, provider="mistral"),
    "codestral-latest":         ModelPricing(prompt=0.001,   completion=0.003,  provider="mistral"),
    "open-mistral-nemo":        ModelPricing(prompt=0.00015, completion=0.00015,provider="mistral"),
    # DeepSeek
    "deepseek-chat":            ModelPricing(prompt=0.00027, completion=0.0011, provider="deepseek"),
    "deepseek-reasoner":        ModelPricing(prompt=0.00055, completion=0.00219,provider="deepseek"),
    # xAI
    "grok-2":                   ModelPricing(prompt=0.002,   completion=0.01,   provider="xai"),
    "grok-2-mini":              ModelPricing(prompt=0.0002,  completion=0.001,  provider="xai"),
    # Local / Ollama (free)
    "ollama": ModelPricing(prompt=0.0, completion=0.0, provider="local"),
}

_UNKNOWN_PRICING = ModelPricing(prompt=0.0, completion=0.0, provider="unknown")


def _resolve_pricing(model_name: Optional[str]) -> ModelPricing:
    """Return pricing for a model, falling back to unknown (zero cost)."""
    if not model_name:
        return _UNKNOWN_PRICING
    # Exact match first
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]
    # Prefix / substring match (handle versioned or aliased names)
    lower = model_name.lower()
    for key, pricing in MODEL_PRICING.items():
        if lower.startswith(key.lower()):
            return pricing
    if "ollama" in lower or "local" in lower:
        return MODEL_PRICING["ollama"]
    return _UNKNOWN_PRICING


def _estimate_cost(prompt_tokens: int, completion_tokens: int, pricing: ModelPricing) -> float:
    """Calculate cost in USD given token counts and per-1k pricing."""
    return (
        prompt_tokens * pricing.prompt / 1000.0
        + completion_tokens * pricing.completion / 1000.0
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MessageTokenDetail(BaseModel):
    message_id: str
    role: str
    tokens: int
    model_name: Optional[str]
    estimated_cost_usd: float
    created_at: str


class RoleBreakdown(BaseModel):
    role: str
    message_count: int
    total_tokens: int
    estimated_cost_usd: float


class ProviderBreakdown(BaseModel):
    provider: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float


class TokenUsageResponse(BaseModel):
    conversation_id: str
    conversation_title: str
    model_name: Optional[str]
    # Aggregate totals
    total_messages: int
    total_tokens: int
    prompt_tokens: int       # tokens attributed to user/system messages
    completion_tokens: int   # tokens attributed to assistant messages
    estimated_cost_usd: float
    # Breakdowns
    by_role: List[RoleBreakdown]
    by_provider: List[ProviderBreakdown]
    # Per-message timeline
    message_timeline: List[MessageTokenDetail]
    # Stats
    avg_user_tokens_per_message: float
    avg_assistant_tokens_per_message: float
    # Pricing snapshot used for estimation
    pricing_info: Dict[str, float]   # {"prompt_per_1k": ..., "completion_per_1k": ...}
    pricing_provider: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/conversations/{conversation_id}/token-usage",
    response_model=TokenUsageResponse,
    summary="Per-conversation token usage and cost breakdown",
    description=(
        "Returns a detailed breakdown of token consumption and estimated USD cost "
        "for every message in the conversation. Pricing is based on the model "
        "recorded on each message (falls back to conversation default model). "
        "Local/Ollama models are shown as zero cost."
    ),
)
async def get_token_usage(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> TokenUsageResponse:
    """Return token-usage breakdown for a conversation owned by the current user."""

    # --- Authorisation: conversation must belong to the requesting user ---
    conversation: Optional[Conversation] = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
            Conversation.is_deleted.is_(False),
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages: List[Message] = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # --- Per-message accounting ---
    timeline: List[MessageTokenDetail] = []
    role_buckets: Dict[str, Dict] = {}    # role -> {count, tokens, cost}
    provider_buckets: Dict[str, Dict] = {}  # provider -> {total, prompt, completion, cost}

    total_prompt_tokens = 0
    total_completion_tokens = 0

    for msg in messages:
        model = msg.model_name or conversation.model_name or "gpt-4-turbo-preview"
        pricing = _resolve_pricing(model)
        tokens = msg.tokens_used or 0

        # Classify prompt vs completion tokens by role
        is_completion = msg.role == "assistant"
        prompt_t = 0 if is_completion else tokens
        completion_t = tokens if is_completion else 0

        cost = _estimate_cost(prompt_t, completion_t, pricing)

        total_prompt_tokens += prompt_t
        total_completion_tokens += completion_t

        # Role bucket
        if msg.role not in role_buckets:
            role_buckets[msg.role] = {"count": 0, "tokens": 0, "cost": 0.0}
        role_buckets[msg.role]["count"] += 1
        role_buckets[msg.role]["tokens"] += tokens
        role_buckets[msg.role]["cost"] += cost

        # Provider bucket
        pname = pricing.provider
        if pname not in provider_buckets:
            provider_buckets[pname] = {
                "total": 0, "prompt": 0, "completion": 0, "cost": 0.0
            }
        provider_buckets[pname]["total"] += tokens
        provider_buckets[pname]["prompt"] += prompt_t
        provider_buckets[pname]["completion"] += completion_t
        provider_buckets[pname]["cost"] += cost

        timeline.append(
            MessageTokenDetail(
                message_id=msg.id,
                role=msg.role,
                tokens=tokens,
                model_name=model,
                estimated_cost_usd=round(cost, 8),
                created_at=msg.created_at.isoformat() if msg.created_at else "",
            )
        )

    total_tokens = total_prompt_tokens + total_completion_tokens
    total_cost = sum(p["cost"] for p in provider_buckets.values())

    # --- Aggregate pricing info (use conversation-level model for the summary) ---
    conv_pricing = _resolve_pricing(conversation.model_name)

    # Average tokens helpers
    user_msgs = role_buckets.get("user", {"count": 1, "tokens": 0})
    asst_msgs = role_buckets.get("assistant", {"count": 1, "tokens": 0})
    avg_user = user_msgs["tokens"] / max(user_msgs["count"], 1)
    avg_asst = asst_msgs["tokens"] / max(asst_msgs["count"], 1)

    return TokenUsageResponse(
        conversation_id=conversation.id,
        conversation_title=conversation.title,
        model_name=conversation.model_name,
        total_messages=len(messages),
        total_tokens=total_tokens,
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
        estimated_cost_usd=round(total_cost, 6),
        by_role=[
            RoleBreakdown(
                role=role,
                message_count=data["count"],
                total_tokens=data["tokens"],
                estimated_cost_usd=round(data["cost"], 6),
            )
            for role, data in sorted(role_buckets.items())
        ],
        by_provider=[
            ProviderBreakdown(
                provider=pname,
                total_tokens=data["total"],
                prompt_tokens=data["prompt"],
                completion_tokens=data["completion"],
                estimated_cost_usd=round(data["cost"], 6),
            )
            for pname, data in sorted(provider_buckets.items())
        ],
        message_timeline=timeline,
        avg_user_tokens_per_message=round(avg_user, 1),
        avg_assistant_tokens_per_message=round(avg_asst, 1),
        pricing_info={
            "prompt_per_1k_usd": conv_pricing.prompt,
            "completion_per_1k_usd": conv_pricing.completion,
        },
        pricing_provider=conv_pricing.provider,
    )
