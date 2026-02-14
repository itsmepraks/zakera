"""
Test configuration and shared fixtures for the Zakera test suite.

This module provides:
- Database setup and teardown
- Test client fixtures
- Authentication fixtures
- Sample data factories
"""
import pytest
import os
import tempfile
from typing import Generator
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from src.api.database import Base, get_db
from src.api.main import app
from src.api.models import User, UserPreferences, Conversation, Message, ConversationShare
from src.api.auth import get_password_hash, create_access_token

# Test database URL - use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    
    All tables are created before the test and dropped after.
    This ensures test isolation.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database override.
    
    This allows API tests to use the test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_user2(db_session: Session) -> User:
    """Create a second test user for sharing tests."""
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password=get_password_hash("testpassword2"),
        full_name="Test User 2",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_superuser(db_session: Session) -> User:
    """Create a test superuser."""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create an authentication token for test user."""
    return create_access_token(data={"sub": test_user.username})

@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Create authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}

# ============================================================================
# Conversation Fixtures
# ============================================================================

@pytest.fixture
def test_conversation(db_session: Session, test_user: User) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(
        user_id=test_user.id,
        title="Test Conversation",
        system_prompt="You are a helpful assistant.",
        model_name="gpt-4-turbo-preview",
        temperature=0.7,
        max_tokens=4000,
        tags=["test", "sample"]
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation

@pytest.fixture
def test_conversations(db_session: Session, test_user: User) -> list[Conversation]:
    """Create multiple test conversations."""
    conversations = []
    for i in range(5):
        conv = Conversation(
            user_id=test_user.id,
            title=f"Test Conversation {i+1}",
            system_prompt="You are a helpful assistant.",
            model_name="gpt-4-turbo-preview",
            temperature=0.7,
            is_archived=(i % 2 == 0),  # Archive every other one
            is_pinned=(i == 0),  # Pin the first one
            tags=["test"] if i < 3 else ["sample"]
        )
        db_session.add(conv)
        conversations.append(conv)
    
    db_session.commit()
    for conv in conversations:
        db_session.refresh(conv)
    
    return conversations

@pytest.fixture
def test_conversation_with_messages(db_session: Session, test_user: User) -> Conversation:
    """Create a conversation with messages."""
    conversation = Conversation(
        user_id=test_user.id,
        title="Conversation with Messages",
        system_prompt="You are a helpful assistant.",
        model_name="gpt-4-turbo-preview"
    )
    db_session.add(conversation)
    db_session.flush()
    
    # Add messages
    messages_data = [
        ("user", "Hello, how are you?"),
        ("assistant", "I'm doing well, thank you for asking!"),
        ("user", "What's the weather like?"),
        ("assistant", "I don't have access to real-time weather data."),
    ]
    
    for role, content in messages_data:
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            tokens_used=len(content.split()),
            model_name="gpt-4-turbo-preview"
        )
        db_session.add(message)
    
    conversation.message_count = len(messages_data)
    
    db_session.commit()
    db_session.refresh(conversation)
    return conversation

# ============================================================================
# Message Fixtures
# ============================================================================

@pytest.fixture
def test_message(db_session: Session, test_conversation: Conversation) -> Message:
    """Create a test message."""
    message = Message(
        conversation_id=test_conversation.id,
        role="user",
        content="This is a test message.",
        tokens_used=5,
        model_name="gpt-4-turbo-preview"
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message

# ============================================================================
# Share Fixtures
# ============================================================================

@pytest.fixture
def test_share(db_session: Session, test_conversation: Conversation, test_user: User) -> ConversationShare:
    """Create a test conversation share."""
    share = ConversationShare(
        conversation_id=test_conversation.id,
        share_token="test-share-token-123",
        shared_by=test_user.id,
        is_public=True,
        can_edit=False,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db_session.add(share)
    db_session.commit()
    db_session.refresh(share)
    return share

# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4-turbo-preview",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a mock response from the AI."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }

# ============================================================================
# Helper Functions
# ============================================================================

def create_test_user(db_session: Session, username: str = None, email: str = None) -> User:
    """Helper to create a test user with custom values."""
    username = username or f"user_{datetime.utcnow().timestamp()}"
    email = email or f"{username}@example.com"
    
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash("password123"),
        full_name=f"Test {username}"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def create_test_conversation(
    db_session: Session,
    user: User,
    title: str = "Test Conversation",
    **kwargs
) -> Conversation:
    """Helper to create a test conversation with custom values."""
    conversation = Conversation(
        user_id=user.id,
        title=title,
        system_prompt=kwargs.get("system_prompt", "You are a helpful assistant."),
        model_name=kwargs.get("model_name", "gpt-4-turbo-preview"),
        temperature=kwargs.get("temperature", 0.7),
        **{k: v for k, v in kwargs.items() if k not in ["system_prompt", "model_name", "temperature"]}
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation

def create_test_message(
    db_session: Session,
    conversation: Conversation,
    role: str = "user",
    content: str = "Test message",
    **kwargs
) -> Message:
    """Helper to create a test message with custom values."""
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        tokens_used=kwargs.get("tokens_used", len(content.split())),
        **{k: v for k, v in kwargs.items() if k != "tokens_used"}
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message

# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(autouse=True)
def reset_database_state(db_session):
    """Reset database state before each test."""
    # This fixture runs before each test automatically
    # The db_session fixture already handles cleanup
    yield

# Markers for test organization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
