"""Tests for the v1 agent harness run service."""

from __future__ import annotations

import pytest

from src.api.models import AgentApproval, AgentRun, AgentStep, Conversation, Message, User
from src.api.services import agent_run_service as service_module
from src.api.services.agent_run_service import AgentRunService
from src.model.providers import ModelResponse
from src.tools.base import ToolResult


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if not self.responses:
            return ModelResponse(
                content="fallback",
                model="fake-model",
                usage={"total_tokens": 1},
                finish_reason="stop",
            )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def stream_generate(self, messages, **kwargs):
        yield "unused"


class FakeToolManager:
    def __init__(self):
        self.calls = []

    async def execute_tool(self, tool_name, parameters, *args, **kwargs):
        self.calls.append((tool_name, parameters))
        return ToolResult.success_result(
            data={"tool": tool_name, "parameters": parameters},
            execution_time=0.01,
        )


@pytest.fixture
def harness_user(test_db):
    user = User(
        username="harness",
        email="harness@example.com",
        hashed_password="hash",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def harness_conversation(test_db, harness_user):
    conversation = Conversation(
        title="Harness test",
        user_id=harness_user.id,
        model_name="fake-model",
    )
    test_db.add(conversation)
    test_db.commit()
    test_db.refresh(conversation)
    return conversation


@pytest.mark.asyncio
async def test_chat_without_tools_creates_completed_run(test_db, harness_user, harness_conversation):
    provider = FakeProvider([
        ModelResponse(
            content="Hello from harness",
            model="fake-model",
            usage={"total_tokens": 12},
            finish_reason="stop",
        )
    ])
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)

    result = await service.run_chat(
        conversation=harness_conversation,
        user=harness_user,
        message="Hi",
        tools_enabled=False,
    )

    assert result.run.status == "completed"
    assert result.content == "Hello from harness"
    assert test_db.query(AgentRun).count() == 1
    assert test_db.query(AgentStep).count() >= 3
    assert test_db.query(Message).filter(Message.role == "assistant").count() == 1


@pytest.mark.asyncio
async def test_safe_tool_call_records_tool_step(monkeypatch, test_db, harness_user, harness_conversation):
    fake_tools = FakeToolManager()
    monkeypatch.setattr(service_module, "get_tool_manager", lambda: fake_tools)
    provider = FakeProvider([
        ModelResponse(
            content="",
            model="fake-model",
            usage={"total_tokens": 5},
            finish_reason="tool_calls",
            tool_calls=[
                {
                    "id": "call_1",
                    "function": {
                        "name": "calculator",
                        "arguments": '{"expression":"2+2"}',
                    },
                }
            ],
        ),
        ModelResponse(
            content="4",
            model="fake-model",
            usage={"total_tokens": 9},
            finish_reason="stop",
        ),
    ])
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)

    result = await service.run_chat(
        conversation=harness_conversation,
        user=harness_user,
        message="Calculate",
        tools_enabled=True,
    )

    assert result.run.status == "completed"
    assert fake_tools.calls == [("calculator", {"expression": "2+2"})]
    tool_step = test_db.query(AgentStep).filter(AgentStep.step_type == "tool_call").one()
    assert tool_step.tool_name == "calculator"
    assert tool_step.status == "completed"


@pytest.mark.asyncio
async def test_risky_tool_requires_approval_without_execution(
    monkeypatch,
    test_db,
    harness_user,
    harness_conversation,
):
    fake_tools = FakeToolManager()
    monkeypatch.setattr(service_module, "get_tool_manager", lambda: fake_tools)
    provider = FakeProvider([
        ModelResponse(
            content="",
            model="fake-model",
            usage={"total_tokens": 5},
            finish_reason="tool_calls",
            tool_calls=[
                {
                    "id": "call_1",
                    "function": {
                        "name": "file_reader",
                        "arguments": '{"path":"README.md"}',
                    },
                }
            ],
        )
    ])
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)

    result = await service.run_chat(
        conversation=harness_conversation,
        user=harness_user,
        message="Read a file",
        tools_enabled=True,
    )

    assert result.run.status == "waiting_for_approval"
    assert result.approval_required is True
    assert fake_tools.calls == []
    approval = test_db.query(AgentApproval).one()
    assert approval.status == "pending"
    assert approval.tool_name == "file_reader"


@pytest.mark.asyncio
async def test_approve_risky_tool_resumes_and_completes(
    monkeypatch,
    test_db,
    harness_user,
    harness_conversation,
):
    fake_tools = FakeToolManager()
    monkeypatch.setattr(service_module, "get_tool_manager", lambda: fake_tools)
    provider = FakeProvider([
        ModelResponse(
            content="",
            model="fake-model",
            usage={"total_tokens": 5},
            finish_reason="tool_calls",
            tool_calls=[
                {
                    "id": "call_1",
                    "function": {
                        "name": "file_reader",
                        "arguments": '{"path":"README.md"}',
                    },
                }
            ],
        ),
        ModelResponse(
            content="File read complete",
            model="fake-model",
            usage={"total_tokens": 13},
            finish_reason="stop",
        ),
    ])
    service = AgentRunService(test_db, provider_factory=lambda _model: provider)
    initial = await service.run_chat(
        conversation=harness_conversation,
        user=harness_user,
        message="Read a file",
        tools_enabled=True,
    )
    approval = test_db.query(AgentApproval).one()

    result = await service.approve(initial.run, approval, harness_user)

    assert result.run.status == "completed"
    assert result.content == "File read complete"
    assert fake_tools.calls == [("file_reader", {"path": "README.md"})]
    assert approval.status == "approved"


def test_reject_risky_tool_marks_run_rejected(test_db, harness_user, harness_conversation):
    run = AgentRun(
        conversation_id=harness_conversation.id,
        user_id=harness_user.id,
        status="waiting_for_approval",
        model_name="fake-model",
        tools_enabled=True,
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    approval = AgentApproval(
        run_id=run.id,
        user_id=harness_user.id,
        status="pending",
        tool_name="code_executor",
        requested_payload={"name": "code_executor", "parameters": {"code": "print(1)"}},
    )
    test_db.add(approval)
    test_db.commit()
    test_db.refresh(approval)
    service = AgentRunService(test_db, provider_factory=lambda _model: FakeProvider([]))

    result = service.reject(run, approval, harness_user)

    assert result.run.status == "rejected"
    assert approval.status == "rejected"
    assert test_db.query(AgentStep).filter(AgentStep.status == "rejected").count() == 1
