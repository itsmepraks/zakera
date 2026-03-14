"""
usage.py  –  /api/v1/usage routes
===================================
Exposes per-user and admin-level token usage & cost analytics endpoints.

All non-admin routes are scoped to the authenticated user extracted from
the JWT ``sub`` claim so users can only see their own data.

Admin routes require the JWT to carry an ``is_admin: true`` claim.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.auth import get_current_user
from src.api.services.usage_tracker import usage_tracker

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ModelUsageBucket(BaseModel):
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    call_count: int


class GrandTotal(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    call_count: int


class UsageSummaryResponse(BaseModel):
    by_model: List[ModelUsageBucket]
    grand_total: GrandTotal


class UsageRecordResponse(BaseModel):
    user_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    conversation_id: Optional[str] = None
    timestamp: str


class CostEstimateRequest(BaseModel):
    model: str = Field(..., examples=["gpt-4o"])
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)


class CostEstimateResponse(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float


class ResetResponse(BaseModel):
    deleted_records: int
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """Raise 403 if the JWT does not carry an is_admin claim."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


# ---------------------------------------------------------------------------
# User-scoped routes
# ---------------------------------------------------------------------------


@router.get(
    "/summary",
    response_model=UsageSummaryResponse,
    summary="Get the current user's token usage summary",
)
async def get_my_usage_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UsageSummaryResponse:
    """
    Returns aggregated prompt tokens, completion tokens, total tokens,
    and estimated USD cost broken down by (provider, model), plus a
    grand total across all providers.
    """
    user_id: str = current_user["sub"]
    summary = await usage_tracker.get_user_summary(user_id)
    return UsageSummaryResponse(**summary)


@router.get(
    "/records",
    response_model=List[UsageRecordResponse],
    summary="Get the current user's raw usage records",
)
async def get_my_usage_records(
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[UsageRecordResponse]:
    """Returns paginated raw usage records for the authenticated user, newest first."""
    user_id: str = current_user["sub"]
    records = await usage_tracker.get_recent_records(
        user_id=user_id, limit=limit, offset=offset
    )
    return [UsageRecordResponse(**r) for r in records]


@router.post(
    "/estimate",
    response_model=CostEstimateResponse,
    summary="Estimate cost for a hypothetical LLM call",
    status_code=status.HTTP_200_OK,
)
async def estimate_cost(
    body: CostEstimateRequest,
    _: Dict[str, Any] = Depends(get_current_user),
) -> CostEstimateResponse:
    """
    Calculates the estimated USD cost for a given model and token counts
    without recording any usage.  Useful for pre-flight budget checks.
    """
    cost = usage_tracker.estimate_cost(
        model=body.model,
        prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens,
    )
    return CostEstimateResponse(
        model=body.model,
        prompt_tokens=body.prompt_tokens,
        completion_tokens=body.completion_tokens,
        estimated_cost_usd=cost,
    )


@router.post(
    "/reset",
    response_model=ResetResponse,
    summary="Clear the current user's usage history",
)
async def reset_my_usage(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ResetResponse:
    """Deletes all stored usage records for the authenticated user."""
    user_id: str = current_user["sub"]
    deleted = await usage_tracker.reset_user(user_id)
    return ResetResponse(
        deleted_records=deleted,
        message=f"Successfully cleared {deleted} usage record(s) for user '{user_id}'.",
    )


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@router.get(
    "/admin/summary",
    response_model=UsageSummaryResponse,
    summary="[Admin] Global token usage summary across all users",
)
async def admin_global_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UsageSummaryResponse:
    """Returns the aggregated token usage and cost across every user."""
    _require_admin(current_user)
    summary = await usage_tracker.get_global_summary()
    return UsageSummaryResponse(**summary)


@router.get(
    "/admin/records",
    response_model=List[UsageRecordResponse],
    summary="[Admin] Paginated raw usage records across all users",
)
async def admin_global_records(
    user_id: Optional[str] = Query(None, description="Filter by a specific user_id"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[UsageRecordResponse]:
    """Retrieves raw usage records for all users, optionally filtered by user_id."""
    _require_admin(current_user)
    records = await usage_tracker.get_recent_records(
        user_id=user_id, limit=limit, offset=offset
    )
    return [UsageRecordResponse(**r) for r in records]
