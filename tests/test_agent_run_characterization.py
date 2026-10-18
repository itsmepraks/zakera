"""Black-box characterization of the legacy agent-run boundary.

These tests record behavior that vNext must either preserve deliberately or
replace explicitly. They are not a claim that the legacy harness is the target
architecture.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.auth import get_current_active_user
from src.api.database import get_db
from src.api.models import AgentApproval, AgentRun, AgentStep, Conversation, Message, User
from src.api.routes import agent_runs
from src.api.services import agent_run_service as service_module
from src.api.services.agent_run_service import AgentRunService
from src.model.providers import ModelResponse
from src.tools.base import ToolResult


class RecordedProvider:
    def __init__(self, *responses: ModelResponse | Exception):
        self.responses = list(responses)

    async def generate(self, _messages, **_kwargs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class RecordedTools:
    def __init__(self):
        self.calls = []

    async def execute_tool(self, tool_name, parameters, *args, **kwargs):
        self.calls.append((tool_name, parameters))
        return ToolResult.success_result(
            data={"tool": tool_name, "parameters": parameters},
            execution_time=0.01,
        )


@pytest.fixture
def run_owner(test_db):
    user = User(
        username="run-owner",
        email="run-owner@example.com",
        hashed_password="hash",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def run_conversation(test_db, run_owner):
    conversation = Conversation(
        title="Characterization",
        user_id=run_owner.id,
        model_name="recorded-model",
    )
    test_db.add(conversation)
    test_db.commit()
    test_db.refresh(conversation)
    return conversation


@pytest.fixture
def run_api_client(test_db, test_user):
    app = FastAPI()
    app.include_router(agent_runs.router, prefix="/api/v1")

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: test_user

    with TestClient(app) as client:
        yield client


async def collect_events(service: AgentRunService, conversation: Conversation, user: User):
    return [
        event
        async for event in service.stream_chat(
            conversation=conversation,
            user=user,
            message="Record this behavior",
            tools_enabled=False,
        )
    ]


@pytest.mark.asyncio
async def test_completed_run_emits_ordered_public_events(
    test_db,
    run_owner,
    run_conversation,
):
    provider = RecordedProvider(
        ModelResponse(
            content="Recorded response",
            model="recorded-model",
            usage={"total_tokens": 7},
            finish_reason="stop",
        )
    )
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)

    events = await collect_events(service, run_conversation, run_owner)

    assert [event["type"] for event in events] == [
        "agent.run.started",
        "agent.step.begin",
        "agent.step.done",
        "agent.step.begin",
        "agent.step.done",
        "agent.response.chunk",
        "agent.step.begin",
        "agent.step.done",
        "agent.done",
    ]
    run_id = events[0]["run_id"]
    assert {event["run_id"] for event in events} == {run_id}
    assert events[-1] == {
        "type": "agent.done",
        "run_id": run_id,
        "status": "completed",
        "usage": {"total_tokens": 7},
    }

    run = test_db.query(AgentRun).filter(AgentRun.id == run_id).one()
    steps = (
        test_db.query(AgentStep)
        .filter(AgentStep.run_id == run_id)
        .order_by(AgentStep.sequence)
        .all()
    )
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.total_tokens == 7
    assert [step.sequence for step in steps] == [1, 2, 3]
    assert [step.step_type for step in steps] == ["memory_write", "model_call", "memory_write"]
    assert all(step.status == "completed" for step in steps)
    assert test_db.query(Message).filter(Message.conversation_id == run_conversation.id).count() == 2


@pytest.mark.asyncio
async def test_provider_failure_emits_terminal_error_and_persists_failed_run(
    test_db,
    run_owner,
    run_conversation,
):
    provider = RecordedProvider(RuntimeError("provider unavailable"))
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)

    events = await collect_events(service, run_conversation, run_owner)

    assert [event["type"] for event in events[-2:]] == ["agent.step.error", "agent.error"]
    assert events[-1]["status"] == "failed"
    assert events[-1]["error"] == "provider unavailable"

    run = test_db.query(AgentRun).filter(AgentRun.id == events[-1]["run_id"]).one()
    assert run.status == "failed"
    assert run.error == "provider unavailable"
    assert run.completed_at is not None
    assert run.assistant_message_id is None

    failed_step = (
        test_db.query(AgentStep)
        .filter(AgentStep.run_id == run.id, AgentStep.status == "failed")
        .one()
    )
    assert failed_step.step_type == "error"
    assert failed_step.error == "provider unavailable"
    stale_model_step = (
        test_db.query(AgentStep)
        .filter(
            AgentStep.run_id == run.id,
            AgentStep.step_type == "model_call",
            AgentStep.status == "started",
        )
        .one()
    )
    assert stale_model_step.completed_at is None


@pytest.mark.asyncio
async def test_multiple_approvals_block_execution_until_all_are_resolved(
    monkeypatch,
    test_db,
    run_owner,
    run_conversation,
):
    tools = RecordedTools()
    monkeypatch.setattr(service_module, "get_tool_manager", lambda: tools)
    provider = RecordedProvider(
        ModelResponse(
            content="",
            model="recorded-model",
            usage={"total_tokens": 5},
            finish_reason="tool_calls",
            tool_calls=[
                {
                    "id": "read-1",
                    "function": {
                        "name": "file_reader",
                        "arguments": '{"path":"README.md"}',
                    },
                },
                {
                    "id": "exec-1",
                    "function": {
                        "name": "code_executor",
                        "arguments": '{"code":"print(1)"}',
                    },
                },
            ],
        ),
        ModelResponse(
            content="Both approved actions completed",
            model="recorded-model",
            usage={"total_tokens": 11},
            finish_reason="stop",
        ),
    )
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)
    initial = await service.run_chat(
        conversation=run_conversation,
        user=run_owner,
        message="Use both tools",
        tools_enabled=True,
    )
    approvals = (
        test_db.query(AgentApproval)
        .filter(AgentApproval.run_id == initial.run.id)
        .order_by(AgentApproval.created_at, AgentApproval.id)
        .all()
    )

    first = await service.approve(initial.run, approvals[0], run_owner)

    assert first.approval_required is True
    assert initial.run.status == "waiting_for_approval"
    assert tools.calls == []

    completed = await service.approve(initial.run, approvals[1], run_owner)

    assert completed.run.status == "completed"
    assert completed.content == "Both approved actions completed"
    assert {name for name, _parameters in tools.calls} == {"file_reader", "code_executor"}
    assert len(tools.calls) == 2


def test_run_detail_is_owner_scoped_and_has_no_artifact_contract(
    run_api_client,
    test_db,
    test_user,
    test_user2,
    test_conversation,
):
    owned_run = AgentRun(
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        status="completed",
        model_name="recorded-model",
        tools_enabled=False,
    )
    other_conversation = Conversation(
        title="Other owner",
        user_id=test_user2.id,
        model_name="recorded-model",
    )
    test_db.add_all([owned_run, other_conversation])
    test_db.commit()
    test_db.refresh(other_conversation)
    other_run = AgentRun(
        conversation_id=other_conversation.id,
        user_id=test_user2.id,
        status="completed",
        model_name="recorded-model",
        tools_enabled=False,
    )
    test_db.add(other_run)
    test_db.commit()

    owned_response = run_api_client.get(f"/api/v1/agent-runs/{owned_run.id}")
    other_response = run_api_client.get(f"/api/v1/agent-runs/{other_run.id}")
    missing_response = run_api_client.get("/api/v1/agent-runs/missing-run-id")

    assert owned_response.status_code == 200
    assert owned_response.json()["id"] == owned_run.id
    assert "artifacts" not in owned_response.json()
    assert (other_response.status_code, other_response.json()) == (
        missing_response.status_code,
        missing_response.json(),
    ) == (404, {"detail": "Agent run not found"})


def test_agent_run_has_no_cancellation_endpoint(
    run_api_client,
    test_db,
    test_user,
    test_conversation,
):
    run = AgentRun(
        conversation_id=test_conversation.id,
        user_id=test_user.id,
        status="running",
        model_name="recorded-model",
        tools_enabled=False,
    )
    test_db.add(run)
    test_db.commit()

    response = run_api_client.post(f"/api/v1/agent-runs/{run.id}/cancel")

    agent_run_paths = {
        path
        for route in run_api_client.app.routes
        if (path := getattr(route, "path", "")).startswith("/api/v1/agent-runs")
    }
    assert not any("cancel" in path for path in agent_run_paths)
    assert response.status_code == 404
