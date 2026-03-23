"""
Tests for GET /api/v1/conversations/{conversation_id}/token-usage
=================================================================
Covers happy-path, edge cases, auth, and the pricing helper functions.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers to build fake DB objects
# ---------------------------------------------------------------------------


def _fake_user(user_id: str = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or str(uuid.uuid4())
    u.username = "testuser"
    u.is_active = True
    return u


def _fake_conversation(
    conv_id: str = None,
    user_id: str = None,
    model_name: str = "gpt-4-turbo-preview",
    title: str = "Test Conversation",
    is_deleted: bool = False,
) -> MagicMock:
    c = MagicMock()
    c.id = conv_id or str(uuid.uuid4())
    c.user_id = user_id or str(uuid.uuid4())
    c.title = title
    c.model_name = model_name
    c.is_deleted = is_deleted
    return c


def _fake_message(
    conv_id: str,
    role: str,
    tokens: int,
    model_name: str = None,
    created_at=None,
) -> MagicMock:
    from datetime import datetime, timezone

    m = MagicMock()
    m.id = str(uuid.uuid4())
    m.conversation_id = conv_id
    m.role = role
    m.tokens_used = tokens
    m.model_name = model_name
    m.created_at = created_at or datetime(2026, 3, 22, 0, 0, 0, tzinfo=timezone.utc)
    return m


# ---------------------------------------------------------------------------
# Pricing helper unit tests (no HTTP layer needed)
# ---------------------------------------------------------------------------


def test_resolve_pricing_exact_match():
    """Known model names resolve to their correct per-1k pricing."""
    from src.api.routes.token_usage import _resolve_pricing

    p = _resolve_pricing("gpt-4o")
    assert p.prompt == pytest.approx(0.005)
    assert p.completion == pytest.approx(0.015)
    assert p.provider == "openai"


def test_resolve_pricing_anthropic():
    from src.api.routes.token_usage import _resolve_pricing

    p = _resolve_pricing("claude-3-opus-20240229")
    assert p.provider == "anthropic"
    assert p.prompt == pytest.approx(0.015)


def test_resolve_pricing_prefix_fallback():
    """A versioned suffix that isn't in the table should match via prefix."""
    from src.api.routes.token_usage import _resolve_pricing

    p = _resolve_pricing("gpt-4-turbo-preview-2024-04-09")
    assert p.provider == "openai"


def test_resolve_pricing_ollama_keyword():
    from src.api.routes.token_usage import _resolve_pricing

    p = _resolve_pricing("ollama:llama3:8b")
    assert p.prompt == 0.0
    assert p.completion == 0.0
    assert p.provider == "local"


def test_resolve_pricing_unknown_returns_zero():
    from src.api.routes.token_usage import _resolve_pricing

    p = _resolve_pricing("some-totally-unknown-model-xyz")
    assert p.prompt == 0.0
    assert p.completion == 0.0
    assert p.provider == "unknown"


def test_estimate_cost_basic():
    from src.api.routes.token_usage import ModelPricing, _estimate_cost

    pricing = ModelPricing(prompt=0.01, completion=0.03, provider="openai")
    # 1 000 prompt + 500 completion
    cost = _estimate_cost(1000, 500, pricing)
    assert cost == pytest.approx(0.01 * 1 + 0.03 * 0.5)   # $0.025


def test_estimate_cost_zero_for_local():
    from src.api.routes.token_usage import ModelPricing, _estimate_cost

    pricing = ModelPricing(prompt=0.0, completion=0.0, provider="local")
    assert _estimate_cost(50_000, 50_000, pricing) == 0.0


# ---------------------------------------------------------------------------
# Endpoint tests via FastAPI TestClient with mocked DB
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Return a TestClient for the full app."""
    from src.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def _auth_headers(user: MagicMock) -> Dict[str, str]:
    """Create a valid JWT for the given mock user."""
    from src.api.auth import create_access_token

    token = create_access_token(data={"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


# --- Happy path ---


def test_token_usage_happy_path(client: TestClient):
    """Successful request returns correct aggregated token counts and cost."""
    user = _fake_user()
    conv = _fake_conversation(user_id=user.id, model_name="gpt-4o")

    # 3 messages: system (50 tok), user (100 tok), assistant (200 tok)
    msgs = [
        _fake_message(conv.id, "system",    50,  "gpt-4o"),
        _fake_message(conv.id, "user",      100, "gpt-4o"),
        _fake_message(conv.id, "assistant", 200, "gpt-4o"),
    ]

    with (
        patch("src.api.routes.token_usage.get_current_active_user", return_value=user),
        patch("src.api.routes.token_usage.get_db") as mock_get_db,
    ):
        db = MagicMock()
        mock_get_db.return_value = iter([db])

        # Conversation query
        conv_q = MagicMock()
        conv_q.filter.return_value = conv_q
        conv_q.first.return_value = conv

        # Messages query
        msg_q = MagicMock()
        msg_q.filter.return_value = msg_q
        msg_q.order_by.return_value = msg_q
        msg_q.all.return_value = msgs

        db.query.side_effect = lambda model: (
            conv_q if model.__name__ == "Conversation" else msg_q
        )

        resp = client.get(
            f"/api/v1/conversations/{conv.id}/token-usage",
            headers=_auth_headers(user),
        )

    assert resp.status_code == 200
    body = resp.json()

    # Totals: 50 + 100 = 150 prompt tokens; 200 completion tokens
    assert body["total_tokens"] == 350
    assert body["prompt_tokens"] == 150      # system + user roles
    assert body["completion_tokens"] == 200  # assistant role
    assert body["total_messages"] == 3
    assert body["conversation_id"] == conv.id

    # Cost should be > 0 (gpt-4o is a paid model)
    assert body["estimated_cost_usd"] > 0

    # Role breakdown must include all three roles
    roles_present = {r["role"] for r in body["by_role"]}
    assert {"system", "user", "assistant"} == roles_present

    # Provider must be openai
    providers = {p["provider"] for p in body["by_provider"]}
    assert "openai" in providers


# --- Multi-model conversation ---


def test_token_usage_multi_model(client: TestClient):
    """Messages with different model_name values are bucketed by provider."""
    user = _fake_user()
    conv = _fake_conversation(user_id=user.id, model_name="gpt-4o")

    msgs = [
        _fake_message(conv.id, "user",      100, "gpt-4o"),
        _fake_message(conv.id, "assistant", 200, "claude-3-5-sonnet-20241022"),
    ]

    with (
        patch("src.api.routes.token_usage.get_current_active_user", return_value=user),
        patch("src.api.routes.token_usage.get_db") as mock_get_db,
    ):
        db = MagicMock()
        mock_get_db.return_value = iter([db])
        conv_q = MagicMock()
        conv_q.filter.return_value = conv_q
        conv_q.first.return_value = conv
        msg_q = MagicMock()
        msg_q.filter.return_value = msg_q
        msg_q.order_by.return_value = msg_q
        msg_q.all.return_value = msgs
        db.query.side_effect = lambda m: conv_q if m.__name__ == "Conversation" else msg_q

        resp = client.get(
            f"/api/v1/conversations/{conv.id}/token-usage",
            headers=_auth_headers(user),
        )

    assert resp.status_code == 200
    body = resp.json()
    providers = {p["provider"] for p in body["by_provider"]}
    assert "openai" in providers
    assert "anthropic" in providers


# --- Zero-cost local model ---


def test_token_usage_local_model_zero_cost(client: TestClient):
    """Conversations using a local/Ollama model report zero estimated cost."""
    user = _fake_user()
    conv = _fake_conversation(user_id=user.id, model_name="ollama:llama3:8b")

    msgs = [
        _fake_message(conv.id, "user",      200, "ollama:llama3:8b"),
        _fake_message(conv.id, "assistant", 500, "ollama:llama3:8b"),
    ]

    with (
        patch("src.api.routes.token_usage.get_current_active_user", return_value=user),
        patch("src.api.routes.token_usage.get_db") as mock_get_db,
    ):
        db = MagicMock()
        mock_get_db.return_value = iter([db])
        conv_q = MagicMock()
        conv_q.filter.return_value = conv_q
        conv_q.first.return_value = conv
        msg_q = MagicMock()
        msg_q.filter.return_value = msg_q
        msg_q.order_by.return_value = msg_q
        msg_q.all.return_value = msgs
        db.query.side_effect = lambda m: conv_q if m.__name__ == "Conversation" else msg_q

        resp = client.get(
            f"/api/v1/conversations/{conv.id}/token-usage",
            headers=_auth_headers(user),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["estimated_cost_usd"] == 0.0
    assert body["pricing_provider"] == "local"


# --- Empty conversation ---


def test_token_usage_empty_conversation(client: TestClient):
    """A conversation with no messages returns zero for all numeric fields."""
    user = _fake_user()
    conv = _fake_conversation(user_id=user.id)

    with (
        patch("src.api.routes.token_usage.get_current_active_user", return_value=user),
        patch("src.api.routes.token_usage.get_db") as mock_get_db,
    ):
        db = MagicMock()
        mock_get_db.return_value = iter([db])
        conv_q = MagicMock()
        conv_q.filter.return_value = conv_q
        conv_q.first.return_value = conv
        msg_q = MagicMock()
        msg_q.filter.return_value = msg_q
        msg_q.order_by.return_value = msg_q
        msg_q.all.return_value = []
        db.query.side_effect = lambda m: conv_q if m.__name__ == "Conversation" else msg_q

        resp = client.get(
            f"/api/v1/conversations/{conv.id}/token-usage",
            headers=_auth_headers(user),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tokens"] == 0
    assert body["total_messages"] == 0
    assert body["estimated_cost_usd"] == 0.0
    assert body["message_timeline"] == []
    assert body["by_role"] == []


# --- 404 for missing conversation ---


def test_token_usage_not_found(client: TestClient):
    """A non-existent or soft-deleted conversation returns 404."""
    user = _fake_user()

    with (
        patch("src.api.routes.token_usage.get_current_active_user", return_value=user),
        patch("src.api.routes.token_usage.get_db") as mock_get_db,
    ):
        db = MagicMock()
        mock_get_db.return_value = iter([db])
        conv_q = MagicMock()
        conv_q.filter.return_value = conv_q
        conv_q.first.return_value = None  # not found
        db.query.return_value = conv_q

        resp = client.get(
            f"/api/v1/conversations/{uuid.uuid4()}/token-usage",
            headers=_auth_headers(user),
        )

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# --- 401 without auth ---


def test_token_usage_unauthenticated(client: TestClient):
    """Missing Authorization header returns 401."""
    resp = client.get(f"/api/v1/conversations/{uuid.uuid4()}/token-usage")
    assert resp.status_code == 401


# --- Average tokens per message ---


def test_token_usage_averages(client: TestClient):
    """avg_user_tokens_per_message and avg_assistant_tokens_per_message are correct."""
    user = _fake_user()
    conv = _fake_conversation(user_id=user.id, model_name="gpt-3.5-turbo")

    msgs = [
        _fake_message(conv.id, "user",      50,  "gpt-3.5-turbo"),
        _fake_message(conv.id, "user",      150, "gpt-3.5-turbo"),
        _fake_message(conv.id, "assistant", 300, "gpt-3.5-turbo"),
        _fake_message(conv.id, "assistant", 100, "gpt-3.5-turbo"),
    ]

    with (
        patch("src.api.routes.token_usage.get_current_active_user", return_value=user),
        patch("src.api.routes.token_usage.get_db") as mock_get_db,
    ):
        db = MagicMock()
        mock_get_db.return_value = iter([db])
        conv_q = MagicMock()
        conv_q.filter.return_value = conv_q
        conv_q.first.return_value = conv
        msg_q = MagicMock()
        msg_q.filter.return_value = msg_q
        msg_q.order_by.return_value = msg_q
        msg_q.all.return_value = msgs
        db.query.side_effect = lambda m: conv_q if m.__name__ == "Conversation" else msg_q

        resp = client.get(
            f"/api/v1/conversations/{conv.id}/token-usage",
            headers=_auth_headers(user),
        )

    assert resp.status_code == 200
    body = resp.json()
    # (50 + 150) / 2 = 100
    assert body["avg_user_tokens_per_message"] == pytest.approx(100.0)
    # (300 + 100) / 2 = 200
    assert body["avg_assistant_tokens_per_message"] == pytest.approx(200.0)
