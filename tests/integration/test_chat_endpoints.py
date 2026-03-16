"""
Integration tests for the chat endpoints:
  POST /chat
  POST /chat/stream
  WebSocket /ws/chat/{conversation_id}

The AI provider is mocked so no real API keys are needed.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import status

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

FAKE_USAGE = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
FAKE_RESPONSE_CONTENT = "This is a mocked AI response."


def _make_model_response(content: str = FAKE_RESPONSE_CONTENT):
    """Return a ModelResponse-like object that the mock will return."""
    from src.model.providers import ModelResponse
    return ModelResponse(
        content=content,
        model="gpt-4-turbo-preview",
        usage=FAKE_USAGE,
        finish_reason="stop",
    )


@pytest.fixture()
def app():
    """Import and return the FastAPI app."""
    from src.api.main import app as fastapi_app
    return fastapi_app


@pytest.fixture()
async def async_client(app):
    """Async HTTP test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def auth_headers(async_client):
    """Register a user, log in, and return Bearer auth headers.

    Falls back to a direct token-creation helper if the auth routes differ.
    """
    # We create the token directly to avoid depending on the exact auth flow.
    from src.api.auth import create_access_token
    token = create_access_token(data={"sub": "testuser_chat"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def mock_provider_generate():
    """Patch _get_provider so generate() returns a mocked response."""
    mock = AsyncMock(return_value=_make_model_response())
    with patch(
        "src.api.routes.chat._get_provider",
        return_value=MagicMock(
            generate=mock,
            stream_generate=AsyncMock(return_value=iter(["Hello ", "world"])),
            supports_tools=MagicMock(return_value=False),
        ),
    ):
        yield mock


# ---------------------------------------------------------------------------
# POST /chat — basic scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_unauthenticated(async_client):
    """Unauthenticated request should return 401 or 403."""
    response = await async_client.post(
        "/chat",
        json={"conversation_id": "does-not-matter", "message": "hi"},
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.asyncio
async def test_chat_conversation_not_found(async_client, auth_headers, mock_provider_generate):
    """A valid auth token with a non-existent conversation_id → 404."""
    response = await async_client.post(
        "/chat",
        json={"conversation_id": "00000000-0000-0000-0000-000000000000", "message": "hello"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_chat_returns_assistant_message(async_client, auth_headers, mock_provider_generate, db_with_conversation):
    """POST /chat should return an assistant message with correct structure."""
    conv_id = db_with_conversation  # fixture that seeds a conversation for testuser_chat
    response = await async_client.post(
        "/chat",
        json={"conversation_id": conv_id, "message": "What is the capital of France?"},
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["conversation_id"] == conv_id
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == FAKE_RESPONSE_CONTENT
    assert body["usage"]["total_tokens"] == FAKE_USAGE["total_tokens"]


@pytest.mark.asyncio
async def test_chat_provider_error_returns_502(async_client, auth_headers, db_with_conversation):
    """If the provider raises an exception, the endpoint should return 502."""
    conv_id = db_with_conversation
    with patch(
        "src.api.routes.chat._get_provider",
        return_value=MagicMock(
            generate=AsyncMock(side_effect=RuntimeError("API timeout")),
            supports_tools=MagicMock(return_value=False),
        ),
    ):
        response = await async_client.post(
            "/chat",
            json={"conversation_id": conv_id, "message": "trigger error"},
            headers=auth_headers,
        )
    assert response.status_code == status.HTTP_502_BAD_GATEWAY


# ---------------------------------------------------------------------------
# POST /chat/stream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_stream_content_type(async_client, auth_headers, db_with_conversation):
    """POST /chat/stream should respond with text/event-stream."""
    conv_id = db_with_conversation

    async def _fake_stream(*args, **kwargs):
        for chunk in ["Hello ", "world", "!"]:
            yield chunk

    with patch(
        "src.api.routes.chat._get_provider",
        return_value=MagicMock(
            stream_generate=_fake_stream,
            supports_tools=MagicMock(return_value=False),
        ),
    ):
        response = await async_client.post(
            "/chat/stream",
            json={"conversation_id": conv_id, "message": "stream test", "stream": True},
            headers=auth_headers,
        )
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_chat_stream_emits_chunks(async_client, auth_headers, db_with_conversation):
    """Streamed response should contain SSE chunk lines."""
    conv_id = db_with_conversation
    chunks = ["Chunk1 ", "Chunk2 ", "Chunk3"]

    async def _fake_stream(*args, **kwargs):
        for c in chunks:
            yield c

    with patch(
        "src.api.routes.chat._get_provider",
        return_value=MagicMock(
            stream_generate=_fake_stream,
            supports_tools=MagicMock(return_value=False),
        ),
    ):
        response = await async_client.post(
            "/chat/stream",
            json={"conversation_id": conv_id, "message": "stream chunks"},
            headers=auth_headers,
        )
    body = response.text
    # Each chunk emitted as an SSE data line
    for chunk in chunks:
        assert chunk in body
    # Final "done" event should be present
    assert '"type": "done"' in body or '"type":"done"' in body


# ---------------------------------------------------------------------------
# WebSocket /ws/chat/{conversation_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_missing_token(app, db_with_conversation):
    """WebSocket with no token in the first message should close with error."""
    from httpx_ws import aconnect_ws

    conv_id = db_with_conversation
    async with aconnect_ws(f"/ws/chat/{conv_id}", app) as ws:
        await ws.send_text(json.dumps({}))  # no "token" key
        msg = json.loads(await ws.receive_text())
        assert msg["type"] == "error"
        assert "Authentication" in msg["message"] or "authentication" in msg["message"].lower()


@pytest.mark.asyncio
async def test_websocket_invalid_token(app, db_with_conversation):
    """WebSocket with an invalid JWT should close with error."""
    from httpx_ws import aconnect_ws

    conv_id = db_with_conversation
    async with aconnect_ws(f"/ws/chat/{conv_id}", app) as ws:
        await ws.send_text(json.dumps({"token": "totally.invalid.token"}))
        msg = json.loads(await ws.receive_text())
        assert msg["type"] == "error"


@pytest.mark.asyncio
async def test_websocket_authenticated_flow(app, auth_headers, db_with_conversation):
    """Valid token → authenticated ack → send message → receive complete event."""
    from httpx_ws import aconnect_ws
    from src.api.auth import create_access_token

    conv_id = db_with_conversation
    token = create_access_token(data={"sub": "testuser_chat"})

    chunks = ["Mock ", "response."]

    async def _fake_stream(*args, **kwargs):
        for c in chunks:
            yield c

    with patch(
        "src.api.routes.chat._get_provider",
        return_value=MagicMock(
            stream_generate=_fake_stream,
            supports_tools=MagicMock(return_value=False),
        ),
    ):
        async with aconnect_ws(f"/ws/chat/{conv_id}", app) as ws:
            await ws.send_text(json.dumps({"token": token}))
            auth_msg = json.loads(await ws.receive_text())
            assert auth_msg["type"] == "authenticated"

            await ws.send_text(json.dumps({"message": "Hello via WebSocket"}))
            received = []
            while True:
                raw = await ws.receive_text()
                data = json.loads(raw)
                received.append(data)
                if data.get("type") == "complete":
                    break

            types = [m["type"] for m in received]
            assert "complete" in types
            complete_msg = next(m for m in received if m["type"] == "complete")
            assert complete_msg["message"]["role"] == "assistant"
            assert "Mock " in complete_msg["message"]["content"]


# ---------------------------------------------------------------------------
# Fixture: db_with_conversation
# (Seeds a conversation owned by testuser_chat so tests can reference it)
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_with_conversation():
    """
    Create a test user + conversation in the test DB and return the conversation ID.
    Relies on conftest.py providing a `db` session fixture wired to the test database.
    """
    from src.api.database import SessionLocal
    from src.api.models import User, Conversation
    from src.api.auth import get_password_hash
    import uuid

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "testuser_chat").first()
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                username="testuser_chat",
                email="testuser_chat@example.com",
                hashed_password=get_password_hash("testpassword"),
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title="Test Conversation",
            model_name="gpt-4-turbo-preview",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv.id
    finally:
        db.close()
