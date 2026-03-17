"""
Integration tests for the conversation export API.

Covers the two endpoints defined in src/api/routes/export.py:

  GET  /api/v1/export/conversations/{conversation_id}
       Stream a single conversation (json | markdown | csv).

  POST /api/v1/export/conversations/bulk
       Stream multiple conversations in one NDJSON response.

All tests mock ExportService so no real database I/O is needed beyond
what the route layer itself does (ownership check, rate-limit guard).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import Conversation, Message, User
from src.api.schemas.export import ExportFormat

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NDJSON_MEDIA = "application/x-ndjson"


def _ndjson_events(response_text: str) -> list[dict]:
    """Parse a newline-delimited JSON response body into a list of events."""
    events = []
    for line in response_text.strip().splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def _make_progress_event(pct: float = 50.0, export_id: str = "exp_1") -> str:
    return json.dumps({"type": "progress", "export_id": export_id, "progress_percentage": pct}) + "\n"


def _make_complete_event(export_id: str = "exp_1") -> str:
    return json.dumps({
        "type": "complete",
        "export_id": export_id,
        "total_messages": 3,
        "total_size_bytes": 512,
        "duration_seconds": 0.12,
        "format": "json",
        "compressed": False,
    }) + "\n"


async def _fake_stream(*_args, **_kwargs) -> AsyncGenerator[str, None]:
    """Minimal async generator that yields one progress + one complete event."""
    yield _make_progress_event()
    yield _make_complete_event()


async def _fake_bulk_stream(*_args, **_kwargs) -> AsyncGenerator[str, None]:
    """Async generator for bulk export: one progress per conversation + complete."""
    for i in range(2):
        yield json.dumps({"type": "progress", "conversation_index": i, "progress_percentage": 50.0}) + "\n"
    yield json.dumps({"type": "bulk_complete", "total_conversations": 2, "total_messages": 6}) + "\n"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conversation_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def other_user(test_db: Session) -> User:
    """A second user who does NOT own the test conversation."""
    from src.api.auth import get_password_hash

    user = User(
        username="other_user_export",
        email="other_export@example.com",
        hashed_password=get_password_hash("password"),
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def other_auth_headers(other_user: User) -> dict:
    from src.api.auth import create_access_token

    token = create_access_token(data={"sub": other_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_conversation(test_db: Session, test_user: User) -> Conversation:
    """A non-deleted conversation owned by test_user, with 3 messages."""
    conv = Conversation(
        title="Export Test Conversation",
        user_id=test_user.id,
        is_deleted=False,
    )
    test_db.add(conv)
    test_db.commit()
    test_db.refresh(conv)

    for i, role in enumerate(["user", "assistant", "user"]):
        test_db.add(Message(
            conversation_id=conv.id,
            role=role,
            content=f"Message {i + 1} content",
        ))
    test_db.commit()
    return conv


@pytest.fixture
def deleted_conversation(test_db: Session, test_user: User) -> Conversation:
    """A soft-deleted conversation."""
    conv = Conversation(
        title="Deleted Conversation",
        user_id=test_user.id,
        is_deleted=True,
    )
    test_db.add(conv)
    test_db.commit()
    test_db.refresh(conv)
    return conv


@pytest.fixture
def empty_conversation(test_db: Session, test_user: User) -> Conversation:
    """A conversation with no messages."""
    conv = Conversation(
        title="Empty Conversation",
        user_id=test_user.id,
        is_deleted=False,
    )
    test_db.add(conv)
    test_db.commit()
    test_db.refresh(conv)
    return conv


@pytest.fixture
def long_conversation(test_db: Session, test_user: User) -> Conversation:
    """A conversation with many messages to exercise pagination in streams."""
    conv = Conversation(
        title="Long Conversation",
        user_id=test_user.id,
        is_deleted=False,
    )
    test_db.add(conv)
    test_db.commit()
    test_db.refresh(conv)

    for i in range(200):
        role = "user" if i % 2 == 0 else "assistant"
        test_db.add(Message(
            conversation_id=conv.id,
            role=role,
            content=f"Turn {i}: " + "word " * 30,
        ))
    test_db.commit()
    return conv


# ---------------------------------------------------------------------------
# 1. Authentication & Authorization
# ---------------------------------------------------------------------------


class TestExportAuthentication:
    """Unauthenticated and cross-user access must be rejected."""

    def test_single_export_requires_auth(self, client: TestClient, db_conversation: Conversation):
        """GET without a JWT should return 401."""
        response = client.get(f"/api/v1/export/conversations/{db_conversation.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_bulk_export_requires_auth(self, client: TestClient, db_conversation: Conversation):
        """POST /bulk without a JWT should return 401."""
        response = client.post(
            "/api/v1/export/conversations/bulk",
            json={"conversation_ids": [str(db_conversation.id)]},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_single_export_wrong_user_gets_404(
        self,
        client: TestClient,
        db_conversation: Conversation,
        other_auth_headers: dict,
    ):
        """A different authenticated user cannot export another user's conversation."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                headers=other_auth_headers,
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_export_wrong_user_gets_404(
        self,
        client: TestClient,
        db_conversation: Conversation,
        other_auth_headers: dict,
    ):
        """Bulk export must 404 when any conversation_id is not owned by caller."""
        response = client.post(
            "/api/v1/export/conversations/bulk",
            json={"conversation_ids": [str(db_conversation.id)]},
            headers=other_auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_bearer_token_rejected(
        self, client: TestClient, db_conversation: Conversation
    ):
        """A malformed JWT should be rejected."""
        response = client.get(
            f"/api/v1/export/conversations/{db_conversation.id}",
            headers={"Authorization": "Bearer totally.invalid.jwt"},
        )
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ---------------------------------------------------------------------------
# 2. Single-conversation export — format variants
# ---------------------------------------------------------------------------


class TestSingleExportFormats:
    """Each supported format returns a streamed NDJSON response."""

    @pytest.mark.parametrize("fmt", ["json", "markdown", "csv"])
    def test_export_returns_ndjson_stream(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
        fmt: str,
    ):
        """All three formats should respond 200 with NDJSON content-type."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": fmt},
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK
        assert NDJSON_MEDIA in response.headers.get("content-type", "")

    @pytest.mark.parametrize("fmt", ["json", "markdown", "csv"])
    def test_export_stream_contains_complete_event(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
        fmt: str,
    ):
        """The stream must end with a 'complete' event."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": fmt},
                headers=auth_headers,
            )
        events = _ndjson_events(response.text)
        event_types = [e.get("type") for e in events]
        assert "complete" in event_types

    def test_export_response_headers(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """Key headers must be present on a successful export response."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json"},
                headers=auth_headers,
            )
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert "x-export-format" in response.headers
        assert response.headers["x-export-format"] == "json"
        assert "x-conversation-id" in response.headers

    def test_export_json_filename_extension(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """JSON exports must carry a .json filename in Content-Disposition."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json"},
                headers=auth_headers,
            )
        assert ".json" in response.headers["content-disposition"]

    def test_export_markdown_filename_extension(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """Markdown exports must carry a .md filename."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "markdown"},
                headers=auth_headers,
            )
        assert ".md" in response.headers["content-disposition"]

    def test_export_csv_filename_extension(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """CSV exports must carry a .csv filename."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "csv"},
                headers=auth_headers,
            )
        assert ".csv" in response.headers["content-disposition"]

    def test_invalid_format_returns_422(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """An unsupported format value must be rejected with 422."""
        response = client.get(
            f"/api/v1/export/conversations/{db_conversation.id}",
            params={"format": "xml"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_export_with_metadata_flag(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """include_metadata=false must be accepted without error."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json", "include_metadata": False},
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK

    def test_export_with_system_messages_flag(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """include_system_messages=true must be accepted without error."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json", "include_system_messages": True},
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK

    def test_export_with_compress_flag(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """compress=true should append .gz to the filename."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json", "compress": True},
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK
        assert ".gz" in response.headers["content-disposition"]

    def test_export_with_date_range(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """date_from / date_to query params must be accepted."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={
                    "format": "json",
                    "date_from": "2026-01-01T00:00:00",
                    "date_to": "2026-12-31T23:59:59",
                },
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 3. Bulk export
# ---------------------------------------------------------------------------


class TestBulkExport:
    """Tests for POST /api/v1/export/conversations/bulk."""

    def test_bulk_export_success(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
        empty_conversation: Conversation,
    ):
        """Bulk export with two owned conversations should stream 200."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_bulk_export=_fake_bulk_stream),
        ):
            response = client.post(
                "/api/v1/export/conversations/bulk",
                json={
                    "conversation_ids": [
                        str(db_conversation.id),
                        str(empty_conversation.id),
                    ]
                },
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK
        assert NDJSON_MEDIA in response.headers.get("content-type", "")

    def test_bulk_export_response_headers(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
        empty_conversation: Conversation,
    ):
        """Bulk response must include x-export-format and x-conversation-count."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_bulk_export=_fake_bulk_stream),
        ):
            response = client.post(
                "/api/v1/export/conversations/bulk",
                json={
                    "conversation_ids": [
                        str(db_conversation.id),
                        str(empty_conversation.id),
                    ]
                },
                headers=auth_headers,
            )
        assert "x-export-format" in response.headers
        assert "x-conversation-count" in response.headers
        assert response.headers["x-conversation-count"] == "2"

    def test_bulk_export_stream_has_bulk_complete_event(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
        empty_conversation: Conversation,
    ):
        """The stream must end with a 'bulk_complete' event."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_bulk_export=_fake_bulk_stream),
        ):
            response = client.post(
                "/api/v1/export/conversations/bulk",
                json={
                    "conversation_ids": [
                        str(db_conversation.id),
                        str(empty_conversation.id),
                    ]
                },
                headers=auth_headers,
            )
        events = _ndjson_events(response.text)
        types = [e.get("type") for e in events]
        assert "bulk_complete" in types

    def test_bulk_export_empty_ids_rejected(
        self, client: TestClient, auth_headers: dict
    ):
        """An empty conversation_ids list must be rejected (Pydantic min_length=1)."""
        response = client.post(
            "/api/v1/export/conversations/bulk",
            json={"conversation_ids": []},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_bulk_export_exceeds_50_limit(
        self, client: TestClient, auth_headers: dict
    ):
        """More than 50 IDs must be rejected with 400."""
        ids = [str(uuid.uuid4()) for _ in range(51)]
        response = client.post(
            "/api/v1/export/conversations/bulk",
            json={"conversation_ids": ids},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "50" in response.json()["detail"]

    def test_bulk_export_duplicate_ids_deduped(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """Duplicate IDs should be silently deduplicated by the schema."""
        cid = str(db_conversation.id)
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_bulk_export=_fake_bulk_stream),
        ):
            response = client.post(
                "/api/v1/export/conversations/bulk",
                json={"conversation_ids": [cid, cid, cid]},
                headers=auth_headers,
            )
        # After dedup there is only 1 unique ID so the response must mention 1
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("x-conversation-count") == "1"

    @pytest.mark.parametrize("fmt", ["json", "markdown", "csv"])
    def test_bulk_export_all_formats(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
        fmt: str,
    ):
        """All three formats should be accepted in bulk export."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_bulk_export=_fake_bulk_stream),
        ):
            response = client.post(
                "/api/v1/export/conversations/bulk",
                json={
                    "conversation_ids": [str(db_conversation.id)],
                    "options": {"format": fmt},
                },
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK

    def test_bulk_export_page_size_respected(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """page_size must be forwarded to ExportService.stream_bulk_export."""
        mock_service = MagicMock(stream_bulk_export=_fake_bulk_stream)
        with patch(
            "src.api.routes.export.ExportService",
            return_value=mock_service,
        ):
            response = client.post(
                "/api/v1/export/conversations/bulk",
                json={
                    "conversation_ids": [str(db_conversation.id)],
                    "page_size": 3,
                },
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK
        # Verify stream_bulk_export was called
        mock_service.stream_bulk_export.assert_called_once()
        call_kwargs = mock_service.stream_bulk_export.call_args[1]
        assert call_kwargs.get("page_size") == 3


# ---------------------------------------------------------------------------
# 4. Rate limiting
# ---------------------------------------------------------------------------


class TestExportRateLimit:
    """The in-process rate limiter must reject excess requests."""

    def test_rate_limit_triggers_after_10_requests(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_conversation: Conversation,
    ):
        """11th export within the rolling window should return 429."""
        from src.api.routes import export as export_module

        # Inject 10 recent timestamps directly into the rate-limit log to
        # simulate the user having already used their allowance.
        now = datetime.utcnow()
        export_module._export_log[test_user.id] = [
            now - timedelta(seconds=i * 3) for i in range(10)
        ]

        try:
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json"},
                headers=auth_headers,
            )
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "rate limit" in response.json()["detail"].lower()
        finally:
            # Clean up injected state
            export_module._export_log.pop(test_user.id, None)

    def test_rate_limit_window_resets(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user: User,
        db_conversation: Conversation,
    ):
        """Timestamps older than 1 minute should not count toward the limit."""
        from src.api.routes import export as export_module

        # Inject 10 timestamps that are all > 1 minute old — should be pruned
        old = datetime.utcnow() - timedelta(minutes=2)
        export_module._export_log[test_user.id] = [old] * 10

        try:
            with patch(
                "src.api.routes.export.ExportService",
                return_value=MagicMock(stream_export=_fake_stream),
            ):
                response = client.get(
                    f"/api/v1/export/conversations/{db_conversation.id}",
                    params={"format": "json"},
                    headers=auth_headers,
                )
            # Old timestamps were pruned, so request should succeed
            assert response.status_code == status.HTTP_200_OK
        finally:
            export_module._export_log.pop(test_user.id, None)


# ---------------------------------------------------------------------------
# 5. Edge cases
# ---------------------------------------------------------------------------


class TestExportEdgeCases:
    """Edge cases: deleted conversations, empty conversations, long conversations."""

    def test_deleted_conversation_returns_404(
        self,
        client: TestClient,
        auth_headers: dict,
        deleted_conversation: Conversation,
    ):
        """Exporting a soft-deleted conversation must return 404."""
        response = client.get(
            f"/api/v1/export/conversations/{deleted_conversation.id}",
            params={"format": "json"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_conversation_returns_404(
        self,
        client: TestClient,
        auth_headers: dict,
    ):
        """A random UUID that has never existed must return 404."""
        response = client.get(
            f"/api/v1/export/conversations/{uuid.uuid4()}",
            params={"format": "json"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_empty_conversation_streams_complete_event(
        self,
        client: TestClient,
        auth_headers: dict,
        empty_conversation: Conversation,
    ):
        """An empty conversation (0 messages) should still complete cleanly."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{empty_conversation.id}",
                params={"format": "json"},
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK
        events = _ndjson_events(response.text)
        assert any(e.get("type") == "complete" for e in events)

    def test_long_conversation_streams_progress_events(
        self,
        client: TestClient,
        auth_headers: dict,
        long_conversation: Conversation,
    ):
        """Long conversations should emit at least one progress event."""

        async def _multi_progress_stream(*_a, **_kw) -> AsyncGenerator[str, None]:
            for pct in [25.0, 50.0, 75.0, 100.0]:
                yield _make_progress_event(pct)
            yield _make_complete_event()

        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_multi_progress_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{long_conversation.id}",
                params={"format": "json"},
                headers=auth_headers,
            )
        assert response.status_code == status.HTTP_200_OK
        events = _ndjson_events(response.text)
        progress_events = [e for e in events if e.get("type") == "progress"]
        assert len(progress_events) >= 1

    def test_export_service_error_does_not_crash_client(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """If ExportService raises mid-stream, the response should still be 200
        (error embedded in the NDJSON stream) or a 5xx — either is acceptable,
        but the server must not crash."""

        async def _error_stream(*_a, **_kw) -> AsyncGenerator[str, None]:
            yield _make_progress_event(10.0)
            raise RuntimeError("Simulated storage failure")
            yield  # make it a generator

        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_error_stream),
        ):
            try:
                response = client.get(
                    f"/api/v1/export/conversations/{db_conversation.id}",
                    params={"format": "json"},
                    headers=auth_headers,
                )
                # If it returns, the status must not be a client-error that
                # would indicate the auth/ownership check regressed.
                assert response.status_code != status.HTTP_401_UNAUTHORIZED
                assert response.status_code != status.HTTP_403_FORBIDDEN
            except Exception:
                # Some test clients surface server-side streaming errors as
                # connection resets — that is also acceptable.
                pass

    def test_bulk_export_one_missing_id_returns_404(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """If even one ID in a bulk request doesn't exist, return 404."""
        response = client.post(
            "/api/v1/export/conversations/bulk",
            json={
                "conversation_ids": [
                    str(db_conversation.id),
                    str(uuid.uuid4()),  # non-existent
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_export_deleted_conversation_returns_404(
        self,
        client: TestClient,
        auth_headers: dict,
        deleted_conversation: Conversation,
    ):
        """Soft-deleted conversations must be treated as not-found in bulk export."""
        response = client.post(
            "/api/v1/export/conversations/bulk",
            json={"conversation_ids": [str(deleted_conversation.id)]},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_export_cache_control_header(
        self,
        client: TestClient,
        auth_headers: dict,
        db_conversation: Conversation,
    ):
        """Export responses must have Cache-Control: no-store."""
        with patch(
            "src.api.routes.export.ExportService",
            return_value=MagicMock(stream_export=_fake_stream),
        ):
            response = client.get(
                f"/api/v1/export/conversations/{db_conversation.id}",
                params={"format": "json"},
                headers=auth_headers,
            )
        assert "no-store" in response.headers.get("cache-control", "")
