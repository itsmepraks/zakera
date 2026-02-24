"""Pytest configuration for integration tests."""

import pytest
import asyncio
import os
from typing import Generator

from src.api.database import init_db, close_db
from src.api.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Setup test database before all tests."""
    # Set test environment
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    
    # Initialize database
    await init_db()
    
    yield
    
    # Cleanup
    await close_db()
    
    # Remove test database file
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture(scope="function")
async def clean_db():
    """Clean database before each test."""
    # Truncate all tables
    from src.api.database import get_db
    
    db = await get_db()
    try:
        # Add cleanup logic here
        pass
    finally:
        await db.close()
    
    yield


@pytest.fixture
def test_user():
    """Create test user."""
    return {
        "user_id": "test_user_123",
        "username": "test_user",
        "email": "test@example.com"
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "This is a test response from the assistant."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        },
        "model": "gpt-3.5-turbo"
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "content": [{
            "type": "text",
            "text": "This is a test response from Claude."
        }],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 15,
            "output_tokens": 25
        },
        "model": "claude-2"
    }
