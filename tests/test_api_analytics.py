"""
Pytest suite for src/api/routes/analytics.py.

Follows the fixture and assertion conventions established in:
  - tests/conftest.py
  - tests/test_api_conversations.py
  - tests/test_token_usage.py

All DB interactions use the in-memory SQLite `test_db` fixture from
conftest.py, which is torn down after each test function.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta
from typing import List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import Conversation, Message, User
from src.api.auth import get_password_hash, create_access_token


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def make_user(
    db: Session,
    username: str = "analytics_user",
    email: str = "analytics@example.com",
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash("securepass!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_conversation(
    db: Session,
    user: User,
    *,
    title: str = "Test Chat",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Conversation:
    now = datetime.utcnow()
    conv = Conversation(
        title=title,
        user_id=user.id,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def make_messages(
    db: Session,
    conversation: Conversation,
    pairs: int = 2,
    first_at: datetime | None = None,
) -> List[Message]:
    """Create `pairs` user+assistant message pairs in the conversation."""
    base = first_at or datetime.utcnow()
    msgs: List[Message] = []
    for i in range(pairs):
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=f"User message {i + 1}",
            created_at=base + timedelta(minutes=i * 2),
        )
        asst_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"Assistant reply {i + 1}, with a bit more text here.",
            created_at=base + timedelta(minutes=i * 2 + 1),
        )
        db.add(user_msg)
        db.add(asst_msg)
        msgs.extend([user_msg, asst_msg])
    db.commit()
    for m in msgs:
        db.refresh(m)
    return msgs


def auth_headers(user: User) -> dict:
    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /analytics/overview
# ---------------------------------------------------------------------------


class TestAnalyticsOverview:
    """Tests for GET /api/v1/analytics/overview."""

    def test_returns_200_with_correct_schema(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        make_messages(test_db, conv, pairs=3)

        resp = client.get("/api/v1/analytics/overview", headers=auth_headers(user))

        assert resp.status_code == 200
        data = resp.json()

        # Schema keys expected from OverallAnalytics
        for key in (
            "total_conversations",
            "total_messages",
            "avg_messages_per_conversation",
            "total_tokens_used",
            "active_conversations_today",
            "active_conversations_week",
            "top_conversation_topics",
            "conversation_stats",
        ):
            assert key in data, f"Missing key: {key}"

    def test_counts_only_current_users_conversations(self, client: TestClient, test_db: Session):
        user_a = make_user(test_db, username="user_a", email="a@test.com")
        user_b = make_user(test_db, username="user_b", email="b@test.com")

        make_conversation(test_db, user_a, title="A conv 1")
        make_conversation(test_db, user_a, title="A conv 2")
        make_conversation(test_db, user_b, title="B conv 1")

        resp = client.get("/api/v1/analytics/overview", headers=auth_headers(user_a))

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_conversations"] == 2

    def test_zero_totals_for_user_with_no_conversations(self, client: TestClient, test_db: Session):
        user = make_user(test_db)

        resp = client.get("/api/v1/analytics/overview", headers=auth_headers(user))

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_conversations"] == 0
        assert data["total_messages"] == 0
        assert data["avg_messages_per_conversation"] == 0.0

    def test_days_parameter_filters_by_created_at(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        recent = datetime.utcnow() - timedelta(days=5)
        old = datetime.utcnow() - timedelta(days=60)

        make_conversation(test_db, user, title="Recent", created_at=recent)
        make_conversation(test_db, user, title="Old", created_at=old)

        resp = client.get(
            "/api/v1/analytics/overview",
            headers=auth_headers(user),
            params={"days": 30},
        )

        assert resp.status_code == 200
        data = resp.json()
        # Only the recent conversation falls within the 30-day window
        assert data["total_conversations"] == 1

    def test_active_today_reflects_updated_at(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        today = datetime.utcnow()
        yesterday = today - timedelta(days=2)

        make_conversation(test_db, user, title="Active today", updated_at=today)
        make_conversation(test_db, user, title="Inactive", updated_at=yesterday)

        resp = client.get("/api/v1/analytics/overview", headers=auth_headers(user))

        assert resp.status_code == 200
        data = resp.json()
        assert data["active_conversations_today"] >= 1

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/analytics/overview")
        assert resp.status_code == 401

    def test_days_out_of_range_returns_422(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/overview",
            headers=auth_headers(user),
            params={"days": 0},  # ge=1 constraint
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /analytics/conversations/{id}/stats
# ---------------------------------------------------------------------------


class TestConversationStats:
    """Tests for GET /api/v1/analytics/conversations/{id}/stats."""

    def test_returns_correct_stats(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        first_at = datetime.utcnow() - timedelta(minutes=30)
        make_messages(test_db, conv, pairs=3, first_at=first_at)

        resp = client.get(
            f"/api/v1/analytics/conversations/{conv.id}/stats",
            headers=auth_headers(user),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["conversation_id"] == conv.id
        assert data["message_count"] == 6  # 3 pairs == 6 messages
        assert data["avg_message_length"] > 0
        assert data["duration_minutes"] > 0
        assert "first_message_at" in data
        assert "last_message_at" in data

    def test_avg_message_length_is_correct(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)

        # Add messages with known lengths
        msgs = [
            Message(conversation_id=conv.id, role="user", content="Hi"),       # 2 chars
            Message(conversation_id=conv.id, role="assistant", content="Hello"),  # 5 chars
        ]
        for m in msgs:
            test_db.add(m)
        test_db.commit()

        resp = client.get(
            f"/api/v1/analytics/conversations/{conv.id}/stats",
            headers=auth_headers(user),
        )

        assert resp.status_code == 200
        # (2 + 5) / 2 == 3.5
        assert resp.json()["avg_message_length"] == pytest.approx(3.5, rel=1e-3)

    def test_returns_404_for_other_users_conversation(self, client: TestClient, test_db: Session):
        owner = make_user(test_db, username="owner", email="owner@test.com")
        intruder = make_user(test_db, username="intruder", email="intruder@test.com")
        conv = make_conversation(test_db, owner)
        make_messages(test_db, conv, pairs=1)

        resp = client.get(
            f"/api/v1/analytics/conversations/{conv.id}/stats",
            headers=auth_headers(intruder),
        )

        assert resp.status_code == 404

    def test_returns_404_for_nonexistent_conversation(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/conversations/nonexistent-id-9999/stats",
            headers=auth_headers(user),
        )
        assert resp.status_code == 404

    def test_returns_404_when_conversation_has_no_messages(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        # No messages added

        resp = client.get(
            f"/api/v1/analytics/conversations/{conv.id}/stats",
            headers=auth_headers(user),
        )

        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        resp = client.get(
            f"/api/v1/analytics/conversations/{conv.id}/stats",
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /analytics/export/conversations
# ---------------------------------------------------------------------------


class TestExportConversations:
    """Tests for GET /api/v1/analytics/export/conversations."""

    def test_json_export_returns_correct_list(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        make_conversation(test_db, user, title="Chat Alpha")
        make_conversation(test_db, user, title="Chat Beta")

        resp = client.get(
            "/api/v1/analytics/export/conversations",
            headers=auth_headers(user),
            params={"format": "json"},
        )

        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        titles = {item["title"] for item in data}
        assert "Chat Alpha" in titles
        assert "Chat Beta" in titles

    def test_csv_export_has_correct_headers_and_rows(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        make_conversation(test_db, user, title="CSV Conversation")

        resp = client.get(
            "/api/v1/analytics/export/conversations",
            headers=auth_headers(user),
            params={"format": "csv"},
        )

        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert rows[0] == ["ID", "Title", "Created At", "Updated At", "Message Count"]
        assert len(rows) == 2  # header + 1 data row
        assert rows[1][1] == "CSV Conversation"

    def test_unknown_format_returns_422(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/export/conversations",
            headers=auth_headers(user),
            params={"format": "xlsx"},
        )
        assert resp.status_code == 422

    def test_start_date_filter_excludes_older_conversations(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        recent_dt = datetime.utcnow() - timedelta(days=2)
        old_dt = datetime.utcnow() - timedelta(days=90)

        make_conversation(test_db, user, title="Recent", created_at=recent_dt)
        make_conversation(test_db, user, title="Old", created_at=old_dt)

        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        resp = client.get(
            "/api/v1/analytics/export/conversations",
            headers=auth_headers(user),
            params={"format": "json", "start_date": cutoff},
        )

        assert resp.status_code == 200
        data = resp.json()
        titles = [item["title"] for item in data]
        assert "Recent" in titles
        assert "Old" not in titles

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/analytics/export/conversations")
        assert resp.status_code == 401

    def test_json_export_contains_required_fields(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        make_conversation(test_db, user, title="Field check")

        resp = client.get(
            "/api/v1/analytics/export/conversations",
            headers=auth_headers(user),
            params={"format": "json"},
        )

        data = resp.json()
        assert len(data) == 1
        entry = data[0]
        for field in ("id", "title", "created_at", "updated_at"):
            assert field in entry, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# GET /analytics/export/conversation/{id}
# ---------------------------------------------------------------------------


class TestExportSingleConversation:
    """Tests for GET /api/v1/analytics/export/conversation/{id}."""

    def test_json_export_includes_messages(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user, title="Deep Dive")
        make_messages(test_db, conv, pairs=2)

        resp = client.get(
            f"/api/v1/analytics/export/conversation/{conv.id}",
            headers=auth_headers(user),
            params={"format": "json"},
        )

        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
        data = resp.json()
        assert data["conversation_id"] == conv.id
        assert data["title"] == "Deep Dive"
        assert "messages" in data
        assert len(data["messages"]) == 4  # 2 pairs == 4 messages
        for msg in data["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg

    def test_txt_export_contains_role_headers(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user, title="Text Export Test")
        make_messages(test_db, conv, pairs=1)

        resp = client.get(
            f"/api/v1/analytics/export/conversation/{conv.id}",
            headers=auth_headers(user),
            params={"format": "txt"},
        )

        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "USER:" in body
        assert "ASSISTANT:" in body
        assert "Text Export Test" in body

    def test_returns_404_for_other_users_conversation(self, client: TestClient, test_db: Session):
        owner = make_user(test_db, username="owner2", email="owner2@test.com")
        intruder = make_user(test_db, username="intruder2", email="intruder2@test.com")
        conv = make_conversation(test_db, owner)
        make_messages(test_db, conv, pairs=1)

        resp = client.get(
            f"/api/v1/analytics/export/conversation/{conv.id}",
            headers=auth_headers(intruder),
        )

        assert resp.status_code == 404

    def test_returns_404_for_nonexistent_id(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/export/conversation/no-such-id",
            headers=auth_headers(user),
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        resp = client.get(
            f"/api/v1/analytics/export/conversation/{conv.id}",
        )
        assert resp.status_code == 401

    def test_json_content_disposition_header_present(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        make_messages(test_db, conv, pairs=1)

        resp = client.get(
            f"/api/v1/analytics/export/conversation/{conv.id}",
            headers=auth_headers(user),
            params={"format": "json"},
        )

        assert resp.status_code == 200
        assert "content-disposition" in resp.headers
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert ".json" in cd


# ---------------------------------------------------------------------------
# GET /analytics/sentiment
# ---------------------------------------------------------------------------


class TestSentimentEndpoint:
    """Tests for GET /api/v1/analytics/sentiment."""

    def test_returns_200_with_sentiment_schema(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/sentiment",
            headers=auth_headers(user),
        )

        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "positive_count",
            "neutral_count",
            "negative_count",
            "avg_sentiment_score",
        ):
            assert field in data, f"Missing field: {field}"

    def test_sentiment_counts_are_non_negative(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/sentiment",
            headers=auth_headers(user),
        )
        data = resp.json()
        assert data["positive_count"] >= 0
        assert data["neutral_count"] >= 0
        assert data["negative_count"] >= 0

    def test_avg_sentiment_score_in_valid_range(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        resp = client.get(
            "/api/v1/analytics/sentiment",
            headers=auth_headers(user),
        )
        score = resp.json()["avg_sentiment_score"]
        assert -1.0 <= score <= 1.0

    def test_optional_conversation_id_param_accepted(self, client: TestClient, test_db: Session):
        user = make_user(test_db)
        conv = make_conversation(test_db, user)
        resp = client.get(
            "/api/v1/analytics/sentiment",
            headers=auth_headers(user),
            params={"conversation_id": conv.id},
        )
        assert resp.status_code == 200

    def test_unauthenticated_returns_401(self, client: TestClient):
        resp = client.get("/api/v1/analytics/sentiment")
        assert resp.status_code == 401
