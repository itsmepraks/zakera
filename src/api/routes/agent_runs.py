"""Agent run inspection and approval endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_active_user
from src.api.database import get_db
from src.api.models import AgentApproval, AgentRun, AgentStep, Conversation, User
from src.api.routes.chat import _get_provider
from src.api.services.agent_run_service import AgentRunService

router = APIRouter()


class AgentStepResponse(BaseModel):
    id: str
    run_id: str
    sequence: int
    step_type: str
    status: str
    label: str
    detail: Optional[str] = None
    tool_name: Optional[str] = None
    tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentApprovalResponse(BaseModel):
    id: str
    run_id: str
    step_id: Optional[str] = None
    status: str
    tool_name: str
    reason: Optional[str] = None
    requested_payload: Dict[str, Any] = Field(default_factory=dict)
    resolved_at: Optional[str] = None
    created_at: Optional[str] = None


class AgentRunListItem(BaseModel):
    id: str
    conversation_id: str
    status: str
    model_name: str
    tools_enabled: bool
    error: Optional[str] = None
    total_tokens: Optional[int] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentRunDetail(AgentRunListItem):
    user_id: str
    user_message_id: Optional[str] = None
    assistant_message_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    steps: List[AgentStepResponse] = Field(default_factory=list)
    approvals: List[AgentApprovalResponse] = Field(default_factory=list)


class ApprovalActionResponse(BaseModel):
    run: AgentRunDetail
    content: str = ""
    usage: Dict[str, int] = Field(default_factory=dict)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _step_response(step: AgentStep) -> AgentStepResponse:
    return AgentStepResponse(
        id=step.id,
        run_id=step.run_id,
        sequence=step.sequence,
        step_type=step.step_type,
        status=step.status,
        label=step.label,
        detail=step.detail,
        tool_name=step.tool_name,
        tokens=step.tokens,
        latency_ms=step.latency_ms,
        error=step.error,
        metadata=step.extra_metadata or {},
        started_at=_iso(step.started_at),
        completed_at=_iso(step.completed_at),
    )


def _approval_response(approval: AgentApproval) -> AgentApprovalResponse:
    return AgentApprovalResponse(
        id=approval.id,
        run_id=approval.run_id,
        step_id=approval.step_id,
        status=approval.status,
        tool_name=approval.tool_name,
        reason=approval.reason,
        requested_payload=approval.requested_payload or {},
        resolved_at=_iso(approval.resolved_at),
        created_at=_iso(approval.created_at),
    )


def _run_list_item(run: AgentRun) -> AgentRunListItem:
    return AgentRunListItem(
        id=run.id,
        conversation_id=run.conversation_id,
        status=run.status,
        model_name=run.model_name,
        tools_enabled=run.tools_enabled,
        error=run.error,
        total_tokens=run.total_tokens,
        created_at=_iso(run.created_at),
        completed_at=_iso(run.completed_at),
    )


def _run_detail(run: AgentRun) -> AgentRunDetail:
    base = _run_list_item(run)
    return AgentRunDetail(
        **base.dict(),
        user_id=run.user_id,
        user_message_id=run.user_message_id,
        assistant_message_id=run.assistant_message_id,
        metadata=run.extra_metadata or {},
        steps=[_step_response(step) for step in run.steps],
        approvals=[_approval_response(approval) for approval in run.approvals],
    )


def _get_owned_run(db: Session, run_id: str, user: User) -> AgentRun:
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.user_id == user.id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return run


@router.get("/agent-runs", response_model=List[AgentRunListItem])
async def list_agent_runs(
    conversation_id: str = Query(..., description="Conversation to list runs for."),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    runs = (
        db.query(AgentRun)
        .filter(AgentRun.conversation_id == conversation_id, AgentRun.user_id == current_user.id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_run_list_item(run) for run in runs]


@router.get("/agent-runs/{run_id}", response_model=AgentRunDetail)
async def get_agent_run(
    run_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return _run_detail(_get_owned_run(db, run_id, current_user))


@router.post(
    "/agent-runs/{run_id}/approvals/{approval_id}/approve",
    response_model=ApprovalActionResponse,
)
async def approve_agent_run_action(
    run_id: str,
    approval_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    run = _get_owned_run(db, run_id, current_user)
    approval = (
        db.query(AgentApproval)
        .filter(AgentApproval.id == approval_id, AgentApproval.run_id == run.id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")

    service = AgentRunService(db=db, provider_factory=_get_provider)
    result = await service.approve(run, approval, current_user)
    return ApprovalActionResponse(run=_run_detail(result.run), content=result.content, usage=result.usage)


@router.post(
    "/agent-runs/{run_id}/approvals/{approval_id}/reject",
    response_model=ApprovalActionResponse,
)
async def reject_agent_run_action(
    run_id: str,
    approval_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    run = _get_owned_run(db, run_id, current_user)
    approval = (
        db.query(AgentApproval)
        .filter(AgentApproval.id == approval_id, AgentApproval.run_id == run.id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")

    service = AgentRunService(db=db, provider_factory=_get_provider)
    result = service.reject(run, approval, current_user)
    return ApprovalActionResponse(run=_run_detail(result.run), content=result.content, usage=result.usage)
