"""Pytest configuration and shared fixtures."""
import asyncio
import pytest
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
import tempfile
import os

from src.api.main import app
from src.api.database import Base, get_db
from src.api.models import User, Conversation, Message
from src.api.auth import create_access_token, get_password_hash


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_zakera.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a test database session."""
    # Create test database
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
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
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)
        # Remove test database file
        if os.path.exists("./test_zakera.db"):
            os.remove("./test_zakera.db")


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
def create_test_message(conversation_id: int, role: str, content: str) -> Message:
    """Factory for creating test messages."""
    return Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )


def create_test_conversation(user_id: int, title: str = "Test") -> Conversation:
    """Factory for creating test conversations."""
    return Conversation(
        title=title,
        user_id=user_id,
    )
