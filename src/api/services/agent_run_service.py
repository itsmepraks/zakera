"""Agent run execution and trace persistence.

This service is intentionally small: it wraps the existing chat flow with
first-class run/step/approval records without introducing a full workflow
engine.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.api.models import AgentApproval, AgentRun, AgentStep, Conversation, Message, User
from src.model.memory import ConversationMemory
from src.model.providers import Message as ProviderMessage
from src.model.providers import ModelProvider
from src.tools.manager import get_tool_manager

logger = logging.getLogger(__name__)

RISKY_TOOL_NAMES = {"code_executor", "file_reader"}


@dataclass
class AgentRunResult:
    run: AgentRun
    content: str
    usage: Dict[str, int]
    approval_required: bool = False


def extract_tool_calls(model_response: Any) -> List[Dict[str, Any]]:
    """Return tool-call payloads from a provider response, if present."""
    tool_calls = getattr(model_response, "tool_calls", None) or []
    if tool_calls:
        return tool_calls

    metadata = getattr(model_response, "metadata", None)
    if isinstance(metadata, dict):
        return metadata.get("tool_calls") or []

    return []


def message_dict_to_provider_message(message: Dict[str, Any]) -> ProviderMessage:
    return ProviderMessage(
        role=message["role"],
        content=message["content"],
        name=message.get("name"),
        tool_calls=message.get("tool_calls"),
        tool_call_id=message.get("tool_call_id"),
    )


def coerce_tool_arguments(arguments: Any) -> Dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"input": arguments}

        if isinstance(parsed, dict):
            return parsed
        return {"input": parsed}

    return {}


def serialize_tool_content(payload: Any) -> str:
    if isinstance(payload, str):
        return payload

    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(payload)


def normalize_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue

        function = tool_call.get("function")
        if not isinstance(function, dict):
            function = {}

        name = function.get("name") or tool_call.get("name")
        if not name:
            continue

        raw_arguments = function.get(
            "arguments",
            tool_call.get("arguments", tool_call.get("parameters", {})),
        )
        specs.append(
            {
                "id": tool_call.get("id") or tool_call.get("tool_call_id"),
                "name": name,
                "parameters": coerce_tool_arguments(raw_arguments),
                "raw": tool_call,
            }
        )
    return specs


class AgentRunService:
    def __init__(
        self,
        db: Session,
        provider_factory: Callable[[str], ModelProvider],
    ):
        self.db = db
        self.provider_factory = provider_factory

    def _emit_step_event(self, event_type: str, step: AgentStep, **extra: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "type": event_type,
            "step_id": step.id,
            "run_id": step.run_id,
            "label": step.label,
            "status": step.status,
            "tool": step.tool_name,
        }
        if step.detail:
            payload["detail"] = step.detail
        if step.tokens is not None:
            payload["tokens"] = step.tokens
        if step.error:
            payload["error"] = step.error
        payload.update({k: v for k, v in extra.items() if v is not None})
        return payload

    def create_run(
        self,
        conversation: Conversation,
        user: User,
        tools_enabled: bool,
        gen_kwargs: Dict[str, Any],
    ) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation.id,
            user_id=user.id,
            status="running",
            model_name=conversation.model_name or "gpt-4-turbo-preview",
            tools_enabled=tools_enabled,
            extra_metadata={"gen_kwargs": gen_kwargs},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def begin_step(
        self,
        run: AgentRun,
        step_type: str,
        label: str,
        *,
        tool_name: Optional[str] = None,
        detail: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentStep:
        next_sequence = len(run.steps) + 1
        step = AgentStep(
            run_id=run.id,
            sequence=next_sequence,
            step_type=step_type,
            status="started",
            label=label,
            tool_name=tool_name,
            detail=detail,
            extra_metadata=metadata or {},
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        self.db.refresh(run)
        return step

    def finish_step(
        self,
        step: AgentStep,
        *,
        status_value: str = "completed",
        detail: Optional[str] = None,
        tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentStep:
        step.status = status_value
        step.completed_at = datetime.utcnow()
        if detail is not None:
            step.detail = detail
        if tokens is not None:
            step.tokens = tokens
        if latency_ms is not None:
            step.latency_ms = latency_ms
        if error is not None:
            step.error = error
        if metadata:
            merged = dict(step.extra_metadata or {})
            merged.update(metadata)
            step.extra_metadata = merged
        self.db.commit()
        self.db.refresh(step)
        return step

    def _set_run_status(
        self,
        run: AgentRun,
        status_value: str,
        *,
        error: Optional[str] = None,
        usage: Optional[Dict[str, int]] = None,
    ) -> AgentRun:
        run.status = status_value
        run.error = error
        run.updated_at = datetime.utcnow()
        if status_value in {"completed", "failed", "rejected"}:
            run.completed_at = datetime.utcnow()
        if usage:
            run.total_tokens = usage.get("total_tokens", run.total_tokens or 0)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _build_memory(self, conversation: Conversation, max_tokens: Optional[int] = None) -> ConversationMemory:
        return ConversationMemory(
            max_tokens=max_tokens or conversation.max_tokens or 4000,
            conversation_id=conversation.id,
            model=conversation.model_name or "gpt-4-turbo-preview",
            system_prompt=conversation.system_prompt,
            db=self.db,
        )

    def _latest_message_id(self, conversation_id: str, role: str) -> Optional[str]:
        message = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id, Message.role == role)
            .order_by(Message.created_at.desc())
            .first()
        )
        return message.id if message else None

    def _gen_kwargs(self, temperature: Optional[float], max_tokens: Optional[int], tools_enabled: bool) -> Dict[str, Any]:
        gen_kwargs: Dict[str, Any] = {}
        if temperature is not None:
            gen_kwargs["temperature"] = temperature
        if max_tokens is not None:
            gen_kwargs["max_tokens"] = max_tokens
        if tools_enabled:
            gen_kwargs["tools_enabled"] = True
        return gen_kwargs

    async def run_chat(
        self,
        *,
        conversation: Conversation,
        user: User,
        message: str,
        tools_enabled: bool,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AgentRunResult:
        events: List[Dict[str, Any]] = []
        async for event in self.stream_chat(
            conversation=conversation,
            user=user,
            message=message,
            tools_enabled=tools_enabled,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            events.append(event)

        run_id = next((e.get("run_id") for e in events if e.get("run_id")), None)
        run = self.db.query(AgentRun).filter(AgentRun.id == run_id).first() if run_id else None
        if not run:
            raise HTTPException(status_code=500, detail="Agent run was not created")

        chunks = [str(e.get("chunk", "")) for e in events if e.get("type") == "agent.response.chunk"]
        done = next((e for e in reversed(events) if e.get("type") == "agent.done"), {})
        usage = done.get("usage") if isinstance(done.get("usage"), dict) else {}
        approval_required = run.status == "waiting_for_approval"
        if run.status == "failed":
            raise HTTPException(status_code=502, detail=f"Model provider error: {run.error}")
        content = "".join(chunks)
        if approval_required and not content:
            content = "Approval required before Zakera can continue this run."
        return AgentRunResult(run=run, content=content, usage=usage, approval_required=approval_required)

    async def stream_chat(
        self,
        *,
        conversation: Conversation,
        user: User,
        message: str,
        tools_enabled: bool,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        gen_kwargs = self._gen_kwargs(temperature, max_tokens, tools_enabled)
        run = self.create_run(conversation, user, tools_enabled, gen_kwargs)
        yield {
            "type": "agent.run.started",
            "run_id": run.id,
            "status": run.status,
            "model": run.model_name,
        }

        memory = self._build_memory(conversation, max_tokens)
        save_user_step = self.begin_step(run, "memory_write", "Saving user message")
        yield self._emit_step_event("agent.step.begin", save_user_step)
        memory.add_turn("user", message)
        run.user_message_id = self._latest_message_id(conversation.id, "user")
        self.db.commit()
        self.finish_step(save_user_step)
        yield self._emit_step_event("agent.step.done", save_user_step)

        provider = self.provider_factory(run.model_name)
        provider_messages = [message_dict_to_provider_message(m) for m in memory.get_messages()]

        try:
            model_step = self.begin_step(run, "model_call", "Calling model")
            yield self._emit_step_event("agent.step.begin", model_step)
            started = time.perf_counter()
            model_response = await provider.generate(provider_messages, **gen_kwargs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = model_response.usage or {}
            self.finish_step(
                model_step,
                tokens=usage.get("total_tokens"),
                latency_ms=latency_ms,
                metadata={"finish_reason": getattr(model_response, "finish_reason", None)},
            )
            yield self._emit_step_event("agent.step.done", model_step)

            if tools_enabled:
                result = await self._handle_tool_calls(
                    run=run,
                    conversation=conversation,
                    user=user,
                    memory=memory,
                    provider=provider,
                    provider_messages=provider_messages,
                    model_response=model_response,
                    gen_kwargs=gen_kwargs,
                )
                async for event in result["events"]:
                    yield event
                if result["approval_required"]:
                    yield {
                        "type": "agent.done",
                        "run_id": run.id,
                        "status": "waiting_for_approval",
                        "usage": usage,
                    }
                    return
                assistant_content = result["content"]
                usage = result["usage"] or usage
            else:
                assistant_content = model_response.content

            for chunk in [assistant_content]:
                if chunk:
                    yield {"type": "agent.response.chunk", "run_id": run.id, "chunk": chunk}

            save_assistant_step = self.begin_step(run, "memory_write", "Saving response")
            yield self._emit_step_event("agent.step.begin", save_assistant_step)
            memory.add_turn("assistant", assistant_content)
            run.assistant_message_id = self._latest_message_id(conversation.id, "assistant")
            memory.update_conversation_stats(total_tokens=usage.get("total_tokens", 0))
            conversation.updated_at = datetime.utcnow()
            self.finish_step(save_assistant_step)
            self._set_run_status(run, "completed", usage=usage)
            yield self._emit_step_event("agent.step.done", save_assistant_step)
            yield {"type": "agent.done", "run_id": run.id, "status": run.status, "usage": usage}

        except Exception as exc:
            logger.exception("Agent run failed")
            failed_step = self.begin_step(run, "error", "Agent run failed")
            self.finish_step(failed_step, status_value="failed", error=str(exc))
            self._set_run_status(run, "failed", error=str(exc))
            yield self._emit_step_event("agent.step.error", failed_step)
            yield {"type": "agent.error", "run_id": run.id, "error": str(exc), "status": "failed"}

    async def _handle_tool_calls(
        self,
        *,
        run: AgentRun,
        conversation: Conversation,
        user: User,
        memory: ConversationMemory,
        provider: ModelProvider,
        provider_messages: List[ProviderMessage],
        model_response: Any,
        gen_kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        events: List[Dict[str, Any]] = []
        tool_specs = normalize_tool_calls(extract_tool_calls(model_response))
        if not tool_specs:
            return {
                "events": _event_iterator(events),
                "content": model_response.content,
                "usage": model_response.usage or {},
                "approval_required": False,
            }

        risky_specs = [spec for spec in tool_specs if spec["name"] in RISKY_TOOL_NAMES]
        if risky_specs:
            for spec in risky_specs:
                step = self.begin_step(
                    run,
                    "approval",
                    f"Waiting for approval: {spec['name']}",
                    tool_name=spec["name"],
                    metadata={"tool_call_id": spec.get("id")},
                )
                approval = AgentApproval(
                    run_id=run.id,
                    step_id=step.id,
                    user_id=user.id,
                    status="pending",
                    tool_name=spec["name"],
                    reason=f"Approval required before running {spec['name']}.",
                    requested_payload=spec,
                )
                self.db.add(approval)
                self.db.commit()
                self.db.refresh(approval)
                self.finish_step(step, status_value="waiting_for_approval")
                events.append(self._emit_step_event("agent.step.begin", step))
                events.append(
                    {
                        "type": "agent.approval.required",
                        "run_id": run.id,
                        "approval_id": approval.id,
                        "step_id": step.id,
                        "tool": spec["name"],
                        "label": step.label,
                        "reason": approval.reason,
                        "parameters": spec["parameters"],
                    }
                )

            run.extra_metadata = {
                **(run.extra_metadata or {}),
                "pending_model_content": model_response.content,
                "pending_usage": model_response.usage or {},
            }
            self._set_run_status(run, "waiting_for_approval", usage=model_response.usage or {})
            return {
                "events": _event_iterator(events),
                "content": "",
                "usage": model_response.usage or {},
                "approval_required": True,
            }

        tool_content, usage, tool_events = await self._execute_tool_specs(
            run=run,
            memory=memory,
            provider=provider,
            provider_messages=provider_messages,
            tool_specs=tool_specs,
            gen_kwargs=gen_kwargs,
            fallback_content=model_response.content,
            fallback_usage=model_response.usage or {},
        )
        return {
            "events": _event_iterator(tool_events),
            "content": tool_content,
            "usage": usage,
            "approval_required": False,
        }

    async def _execute_tool_specs(
        self,
        *,
        run: AgentRun,
        memory: ConversationMemory,
        provider: ModelProvider,
        provider_messages: List[ProviderMessage],
        tool_specs: List[Dict[str, Any]],
        gen_kwargs: Dict[str, Any],
        fallback_content: str,
        fallback_usage: Dict[str, int],
    ) -> tuple[str, Dict[str, int], List[Dict[str, Any]]]:
        events: List[Dict[str, Any]] = []
        tool_manager = get_tool_manager()

        tool_results_summary: List[Dict[str, Any]] = []
        for spec in tool_specs:
            step = self.begin_step(run, "tool_call", f"Running {spec['name']}", tool_name=spec["name"])
            events.append(self._emit_step_event("agent.step.begin", step))
            result = await tool_manager.execute_tool(spec["name"], spec["parameters"])
            tool_payload = result.data if result.success else {"error": result.error}
            tool_content = serialize_tool_content(tool_payload)
            tool_metadata = {
                "tool_call_id": spec.get("id"),
                "tool_name": spec["name"],
                "success": result.success,
                "execution_time": result.execution_time,
            }
            memory.add_turn("tool", tool_content, metadata=tool_metadata)
            provider_messages.append(
                ProviderMessage(
                    role="tool",
                    content=tool_content,
                    name=spec["name"],
                    tool_call_id=spec.get("id"),
                )
            )
            tool_results_summary.append(
                {
                    "id": spec.get("id"),
                    "tool": spec["name"],
                    "parameters": spec["parameters"],
                    "success": result.success,
                    "result": tool_payload,
                    "execution_time": result.execution_time,
                }
            )
            status_value = "completed" if result.success else "failed"
            self.finish_step(
                step,
                status_value=status_value,
                detail=serialize_tool_content(tool_payload),
                latency_ms=int((result.execution_time or 0) * 1000),
                error=result.error,
            )
            event_type = "agent.step.done" if result.success else "agent.step.error"
            events.append(self._emit_step_event(event_type, step))

        follow_step = self.begin_step(run, "model_call", "Calling model with tool results")
        events.append(self._emit_step_event("agent.step.begin", follow_step))
        try:
            started = time.perf_counter()
            final_response = await provider.generate(provider_messages, **gen_kwargs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = final_response.usage or fallback_usage
            self.finish_step(
                follow_step,
                tokens=usage.get("total_tokens"),
                latency_ms=latency_ms,
                metadata={"finish_reason": getattr(final_response, "finish_reason", None)},
            )
            events.append(self._emit_step_event("agent.step.done", follow_step))
            return final_response.content, usage, events
        except Exception as exc:
            logger.exception("Model provider error on post-tool follow-up call")
            self.finish_step(follow_step, status_value="failed", error=str(exc))
            events.append(self._emit_step_event("agent.step.error", follow_step))
            fallback = f"{fallback_content}\n\n[Tool results: {serialize_tool_content(tool_results_summary)}]"
            return fallback, fallback_usage, events

    async def approve(self, run: AgentRun, approval: AgentApproval, user: User) -> AgentRunResult:
        if approval.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval already resolved")
        approval.status = "approved"
        approval.resolved_by = user.id
        approval.resolved_at = datetime.utcnow()
        self.db.commit()

        pending = (
            self.db.query(AgentApproval)
            .filter(AgentApproval.run_id == run.id, AgentApproval.status == "pending")
            .count()
        )
        if pending:
            return AgentRunResult(run=run, content="", usage={}, approval_required=True)

        conversation = run.conversation
        memory = self._build_memory(conversation)
        provider = self.provider_factory(run.model_name)
        provider_messages = [message_dict_to_provider_message(m) for m in memory.get_messages()]
        approved = (
            self.db.query(AgentApproval)
            .filter(AgentApproval.run_id == run.id, AgentApproval.status == "approved")
            .order_by(AgentApproval.created_at)
            .all()
        )
        tool_specs = [a.requested_payload for a in approved if isinstance(a.requested_payload, dict)]
        metadata = run.extra_metadata or {}
        content, usage, _events = await self._execute_tool_specs(
            run=run,
            memory=memory,
            provider=provider,
            provider_messages=provider_messages,
            tool_specs=tool_specs,
            gen_kwargs=metadata.get("gen_kwargs") or {"tools_enabled": True},
            fallback_content=metadata.get("pending_model_content") or "",
            fallback_usage=metadata.get("pending_usage") or {},
        )

        save_step = self.begin_step(run, "memory_write", "Saving response")
        memory.add_turn("assistant", content)
        run.assistant_message_id = self._latest_message_id(conversation.id, "assistant")
        memory.update_conversation_stats(total_tokens=usage.get("total_tokens", 0))
        self.finish_step(save_step)
        self._set_run_status(run, "completed", usage=usage)
        return AgentRunResult(run=run, content=content, usage=usage)

    def reject(self, run: AgentRun, approval: AgentApproval, user: User) -> AgentRunResult:
        if approval.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approval already resolved")
        approval.status = "rejected"
        approval.resolved_by = user.id
        approval.resolved_at = datetime.utcnow()
        step = self.begin_step(run, "approval", f"Rejected {approval.tool_name}", tool_name=approval.tool_name)
        self.finish_step(step, status_value="rejected", detail="User rejected tool execution.")
        self._set_run_status(run, "rejected", error="User rejected tool execution.")
        self.db.commit()
        return AgentRunResult(run=run, content="", usage={})


async def _event_iterator(events: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:
    for event in events:
        yield event
