"""
Shared test fixtures and utilities for Zakera test suite.

This module provides common fixtures for database setup, test data,
authentication, and mock services used across all test modules.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Generator, List

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Import application components
try:
    from src.api.auth import create_access_token, get_password_hash
    from src.api.database import Base, get_db
    from src.api.main import app
    from src.api.models import Conversation, Message, User, UserPreferences
except ImportError:
    # Gracefully handle missing imports for initial setup
    pass


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db_engine():
    """
    Create a test database engine using in-memory SQLite.
    Each test gets a fresh database.
    """
    # Use in-memory SQLite for fast tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db_session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client with database dependency override.
    """
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(test_db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing async endpoints.
    """
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# ============================================================================
# User & Authentication Fixtures
# ============================================================================

@pytest.fixture
def test_password() -> str:
    """Standard test password."""
    return "TestPassword123!"


@pytest.fixture
def test_user_data(test_password: str) -> Dict:
    """Test user registration data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": test_password,
        "full_name": "Test User"
    }


@pytest.fixture
def test_user(test_db_session: Session, test_user_data: Dict) -> User:
    """
    Create and persist a test user in the database.
    """
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        full_name=test_user_data.get("full_name"),
        is_active=True,
        created_at=datetime.utcnow()
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """
    Create a valid JWT token for the test user.
    """
    return create_access_token(
        data={"sub": test_user.username, "user_id": str(test_user.id)}
    )


@pytest.fixture
def auth_headers(test_user_token: str) -> Dict[str, str]:
    """
    Create authorization headers with valid token.
    """
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def multiple_test_users(test_db_session: Session, test_password: str) -> List[User]:
    """
    Create multiple test users for testing user interactions.
    """
    users = []
    for i in range(3):
        user = User(
            username=f"testuser{i}",
            email=f"test{i}@example.com",
            hashed_password=get_password_hash(test_password),
            full_name=f"Test User {i}",
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db_session.add(user)
        users.append(user)
    
    test_db_session.commit()
    for user in users:
        test_db_session.refresh(user)
    
    return users


# ============================================================================
# Conversation & Message Fixtures
# ============================================================================

@pytest.fixture
def test_conversation(test_db_session: Session, test_user: User) -> Conversation:
    """
    Create a test conversation for the test user.
    """
    conversation = Conversation(
        user_id=test_user.id,
        title="Test Conversation",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_pinned=False,
        is_archived=False
    )
    test_db_session.add(conversation)
    test_db_session.commit()
    test_db_session.refresh(conversation)
    return conversation


@pytest.fixture
def test_conversations(test_db_session: Session, test_user: User) -> List[Conversation]:
    """
    Create multiple test conversations with different states.
    """
    conversations = []
    
    # Regular conversation
    conv1 = Conversation(
        user_id=test_user.id,
        title="Regular Conversation",
        created_at=datetime.utcnow() - timedelta(days=3),
        updated_at=datetime.utcnow() - timedelta(days=1),
        is_pinned=False,
        is_archived=False
    )
    conversations.append(conv1)
    
    # Pinned conversation
    conv2 = Conversation(
        user_id=test_user.id,
        title="Pinned Conversation",
        created_at=datetime.utcnow() - timedelta(days=2),
        updated_at=datetime.utcnow(),
        is_pinned=True,
        is_archived=False
    )
    conversations.append(conv2)
    
    # Archived conversation
    conv3 = Conversation(
        user_id=test_user.id,
        title="Archived Conversation",
        created_at=datetime.utcnow() - timedelta(days=5),
        updated_at=datetime.utcnow() - timedelta(days=4),
        is_pinned=False,
        is_archived=True
    )
    conversations.append(conv3)
    
    for conv in conversations:
        test_db_session.add(conv)
    
    test_db_session.commit()
    for conv in conversations:
        test_db_session.refresh(conv)
    
    return conversations


@pytest.fixture
def test_messages(test_db_session: Session, test_conversation: Conversation) -> List[Message]:
    """
    Create test messages in a conversation.
    """
    messages = []
    
    # User message
    msg1 = Message(
        conversation_id=test_conversation.id,
        role="user",
        content="Hello, this is a test message.",
        created_at=datetime.utcnow() - timedelta(minutes=10),
        tokens_used=10
    )
    messages.append(msg1)
    
    # Assistant message
    msg2 = Message(
        conversation_id=test_conversation.id,
        role="assistant",
        content="Hello! This is a test response from the assistant.",
        created_at=datetime.utcnow() - timedelta(minutes=9),
        tokens_used=15
    )
    messages.append(msg2)
    
    # Another user message
    msg3 = Message(
        conversation_id=test_conversation.id,
        role="user",
        content="Can you help me with something?",
        created_at=datetime.utcnow() - timedelta(minutes=5),
        tokens_used=8
    )
    messages.append(msg3)
    
    for msg in messages:
        test_db_session.add(msg)
    
    test_db_session.commit()
    for msg in messages:
        test_db_session.refresh(msg)
    
    return messages


@pytest.fixture
def test_message_data() -> Dict:
    """
    Sample message data for creating new messages.
    """
    return {
        "content": "This is a test message content.",
        "role": "user"
    }


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_response() -> Dict:
    """
    Mock OpenAI API response for testing.
    """
    return {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mocked AI response."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }


@pytest.fixture
def mock_streaming_response() -> List[Dict]:
    """
    Mock streaming response chunks from AI provider.
    """
    return [
        {"choices": [{"delta": {"content": "Hello"}, "index": 0}]},
        {"choices": [{"delta": {"content": " world"}, "index": 0}]},
        {"choices": [{"delta": {"content": "!"}, "index": 0}]},
        {"choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]}
    ]


# ============================================================================
# Environment & Configuration Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def test_env_vars():
    """
    Set up test environment variables.
    Automatically used for all tests.
    """
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ.update({
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GOOGLE_API_KEY": "test-google-key",
        "REDIS_URL": "redis://localhost:6379/0",
        "DEBUG": "true",
        "ENABLE_RATE_LIMITING": "false",
        "MAX_REQUESTS_PER_MINUTE": "1000"
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def test_config() -> Dict:
    """
    Test configuration dictionary.
    """
    return {
        "model_provider": "openai",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000,
        "stream": False
    }


# ============================================================================
# Utility Functions
# ============================================================================

def create_test_user_in_db(
    session: Session,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "TestPassword123!"
) -> User:
    """
    Utility function to create a user in the test database.
    """
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_test_conversation_in_db(
    session: Session,
    user_id: int,
    title: str = "Test Conversation"
) -> Conversation:
    """
    Utility function to create a conversation in the test database.
    """
    conversation = Conversation(
        user_id=user_id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def assert_valid_timestamp(timestamp_str: str) -> bool:
    """
    Validate that a string is a valid ISO format timestamp.
    """
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def assert_valid_uuid(uuid_str: str) -> bool:
    """
    Validate that a string is a valid UUID.
    """
    import uuid
    try:
        uuid.UUID(str(uuid_str))
        return True
    except (ValueError, AttributeError):
        return False
