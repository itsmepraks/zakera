"""Pytest configuration and shared fixtures."""

import asyncio
import pytest
from typing import AsyncGenerator, Generator, Optional, Union
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.database import Base, get_db
from src.api.models import User, Conversation, Message
from src.api.auth import create_access_token, get_password_hash


class _OfflineTestEncoding:
    """Deterministic token counter for tests that never loads encoder data."""

    @staticmethod
    def encode(text: str) -> list[int]:
        return list(text.encode("utf-8"))


@pytest.fixture(autouse=True)
def offline_conversation_memory_tokenizer(monkeypatch):
    """Keep memory tests hermetic instead of downloading tiktoken assets."""
    from src.model import memory as memory_module

    encoding = _OfflineTestEncoding()

    def encoding_for_model(model: str):
        if model.startswith("unknown-"):
            raise KeyError(model)
        return encoding

    monkeypatch.setattr(memory_module.tiktoken, "encoding_for_model", encoding_for_model)
    monkeypatch.setattr(memory_module.tiktoken, "get_encoding", lambda _name: encoding)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def db_session(test_db: Session) -> Session:
    """Compatibility alias for unit tests that expect db_session."""
    return test_db


@pytest.fixture
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_user2(test_db: Session) -> User:
    """Create a second test user."""
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create an authentication token for test user."""
    return create_access_token(data={"sub": test_user.username})


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Create authorization headers with test token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_conversation(test_db: Session, test_user: User) -> Conversation:
    """Create a test conversation."""
    conversation = Conversation(
        title="Test Conversation",
        user_id=test_user.id,
    )
    test_db.add(conversation)
    test_db.commit()
    test_db.refresh(conversation)
    return conversation


@pytest.fixture
def test_messages(test_db: Session, test_conversation: Conversation) -> list[Message]:
    """Create test messages in a conversation."""
    messages = [
        Message(
            conversation_id=test_conversation.id,
            role="user",
            content="Hello, how are you?",
        ),
        Message(
            conversation_id=test_conversation.id,
            role="assistant",
            content="I'm doing well, thank you! How can I help you today?",
        ),
        Message(
            conversation_id=test_conversation.id,
            role="user",
            content="Can you explain quantum computing?",
        ),
    ]

    for msg in messages:
        test_db.add(msg)
    test_db.commit()

    for msg in messages:
        test_db.refresh(msg)

    return messages


@pytest.fixture
def test_message(test_messages: list[Message]) -> Message:
    """Return the first persisted test message."""
    return test_messages[0]


class MockModelProvider:
    """Mock model provider for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a mock response."""
        self.call_count += 1

        if self.should_fail:
            raise Exception(f"Mock failure from {self.name}")

        return f"Mock response from {self.name}: {prompt[:50]}..."

    async def generate_stream(self, prompt: str, **kwargs):
        """Generate a mock streaming response."""
        self.call_count += 1

        if self.should_fail:
            raise Exception(f"Mock failure from {self.name}")

        words = f"Mock streaming response from {self.name}".split()
        for word in words:
            yield word + " "

    def is_available(self) -> bool:
        """Check if provider is available."""
        return not self.should_fail


@pytest.fixture
def mock_openai_provider():
    """Create a mock OpenAI provider."""
    return MockModelProvider("OpenAI")


@pytest.fixture
def mock_anthropic_provider():
    """Create a mock Anthropic provider."""
    return MockModelProvider("Anthropic")


@pytest.fixture
def mock_ollama_provider():
    """Create a mock Ollama provider."""
    return MockModelProvider("Ollama")


@pytest.fixture
def failing_provider():
    """Create a mock provider that always fails."""
    return MockModelProvider("FailingProvider", should_fail=True)


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.execution_count = 0

    async def execute(self, **kwargs) -> dict:
        """Execute the mock tool."""
        self.execution_count += 1

        if self.should_fail:
            raise Exception(f"Mock tool {self.name} failed")

        return {
            "success": True,
            "result": f"Mock result from {self.name}",
            "execution_count": self.execution_count,
        }


@pytest.fixture
def mock_calculator_tool():
    """Create a mock calculator tool."""
    return MockTool("calculator")


@pytest.fixture
def mock_search_tool():
    """Create a mock search tool."""
    return MockTool("search")


@pytest.fixture
def failing_tool():
    """Create a mock tool that always fails."""
    return MockTool("failing_tool", should_fail=True)


# Test data factories
def create_test_user(
    db_or_username: Optional[Union[Session, str]] = None,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
    hashed_password: str = "hashed_password_123",
) -> User:
    """Factory for creating test users, optionally persisted to a database session."""
    db = db_or_username if isinstance(db_or_username, Session) else None
    if isinstance(db_or_username, str):
        username = db_or_username

    if email == "test@example.com" and username != "testuser":
        email = f"{username}@example.com"

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password) if db else hashed_password,
        is_active=True,
    )

    if db:
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def create_test_message(
    db_or_conversation_id: Union[Session, str],
    conversation_or_role: Union[Conversation, str],
    role_or_content: str,
    content: Optional[str] = None,
) -> Message:
    """Factory for creating test messages, optionally persisted to a database session."""
    db = db_or_conversation_id if isinstance(db_or_conversation_id, Session) else None

    if db:
        conversation = conversation_or_role
        if not isinstance(conversation, Conversation):
            raise TypeError("conversation is required when persisting a test message")
        message = Message(
            conversation_id=conversation.id,
            role=role_or_content,
            content=content or "",
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    return Message(
        conversation_id=db_or_conversation_id,
        role=str(conversation_or_role),
        content=role_or_content,
    )


def create_test_conversation(user_id: int, title: str = "Test") -> Conversation:
    """Factory for creating test conversations."""
    return Conversation(
        title=title,
        user_id=user_id,
    )
