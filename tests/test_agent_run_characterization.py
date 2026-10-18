"""Black-box characterization of the legacy agent-run boundary.

These tests record behavior that vNext must either preserve deliberately or
replace explicitly. They are not a claim that the legacy harness is the target
architecture.
"""

from __future__ import annotations

import pytest

from src.api.models import AgentRun, AgentStep, Conversation, Message, User
from src.api.services.agent_run_service import AgentRunService
from src.model.providers import ModelResponse


class RecordedProvider:
    def __init__(self, *responses: ModelResponse | Exception):
        self.responses = list(responses)

    async def generate(self, _messages, **_kwargs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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
    steps = test_db.query(AgentStep).filter(AgentStep.run_id == run_id).all()
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

