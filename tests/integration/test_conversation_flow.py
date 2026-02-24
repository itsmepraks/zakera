"""Integration tests for conversation flow."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json

from src.api.main import app
from src.model.memory import ConversationMemory
from src.model.model_manager import ModelManager
from src.api.database import get_db, init_db
from src.api.models import Conversation, Message
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def test_client():
    """Create test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
async def clean_db():
    """Clean database before each test."""
    await init_db()
    yield
    # Cleanup after test


@pytest.fixture
def test_user_id() -> str:
    """Test user ID."""
    return "test_user_123"


@pytest.fixture
def test_conversation_id() -> str:
    """Test conversation ID."""
    return "test_conv_456"


class TestBasicConversationFlow:
    """Test basic conversation operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, test_client, test_user_id):
        """Test creating a new conversation."""
        response = test_client.post(
            "/api/v1/conversations",
            json={
                "user_id": test_user_id,
                "title": "Test Conversation",
                "model": "gpt-3.5-turbo",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["user_id"] == test_user_id
        assert data["title"] == "Test Conversation"
        assert data["model"] == "gpt-3.5-turbo"

    @pytest.mark.asyncio
    async def test_send_message(self, test_client, test_user_id, test_conversation_id):
        """Test sending a message."""
        # Create conversation first
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Send message
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "Hello, how are you?",
                "role": "user",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["role"] == "assistant"
        assert "content" in data
        assert len(data["content"]) > 0

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, test_client, test_user_id):
        """Test retrieving conversation history."""
        # Create conversation and send messages
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Send multiple messages
        messages = [
            "What is Python?",
            "Tell me about list comprehensions",
            "Show me an example"
        ]
        
        for msg in messages:
            test_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": msg, "role": "user"}
            )
        
        # Get history
        response = test_client.get(
            f"/api/v1/conversations/{conv_id}/messages"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        # Should have user messages + assistant responses
        assert len(data["messages"]) >= len(messages) * 2


class TestMultiTurnConversations:
    """Test multi-turn conversations with context."""

    @pytest.mark.asyncio
    async def test_context_retention(self, test_client, test_user_id):
        """Test that context is retained across multiple turns."""
        # Create conversation
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id, "model": "gpt-3.5-turbo"}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # First message: Introduce a topic
        response1 = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "My name is Alice and I love Python programming.",
                "role": "user"
            }
        )
        assert response1.status_code == 200
        
        # Second message: Reference the topic (tests context)
        response2 = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "What is my name?",
                "role": "user"
            }
        )
        assert response2.status_code == 200
        response2_data = response2.json()
        
        # Assistant should remember the name
        assert "alice" in response2_data["content"].lower()
        
        # Third message: Reference another part of context
        response3 = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "What programming language did I mention?",
                "role": "user"
            }
        )
        assert response3.status_code == 200
        response3_data = response3.json()
        
        # Assistant should remember Python
        assert "python" in response3_data["content"].lower()

    @pytest.mark.asyncio
    async def test_long_conversation_memory_management(self, test_client, test_user_id):
        """Test memory management in long conversations."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id, "max_context_length": 1000}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Send many messages to exceed context window
        for i in range(20):
            response = test_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={
                    "content": f"This is message number {i}. " + "word " * 50,
                    "role": "user"
                }
            )
            assert response.status_code == 200
        
        # Get conversation metadata
        response = test_client.get(f"/api/v1/conversations/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Should have token tracking
        assert "total_tokens" in data
        assert "messages_count" in data
        assert data["messages_count"] > 0


class TestConversationBranching:
    """Test conversation branching and version management."""

    @pytest.mark.asyncio
    async def test_create_branch(self, test_client, test_user_id):
        """Test creating a conversation branch."""
        # Create base conversation
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Send some messages
        test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Original message", "role": "user"}
        )
        
        # Create branch from this point
        branch_response = test_client.post(
            f"/api/v1/conversations/{conv_id}/branch",
            json={"branch_name": "Alternative path"}
        )
        
        assert branch_response.status_code == 200
        branch_data = branch_response.json()
        assert "branch_id" in branch_data
        assert branch_data["parent_id"] == conv_id

    @pytest.mark.asyncio
    async def test_branch_independence(self, test_client, test_user_id):
        """Test that branches are independent."""
        # Create conversation and branch
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        branch_response = test_client.post(
            f"/api/v1/conversations/{conv_id}/branch"
        )
        branch_id = branch_response.json()["branch_id"]
        
        # Send different messages to each
        test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Main branch message", "role": "user"}
        )
        
        test_client.post(
            f"/api/v1/conversations/{branch_id}/messages",
            json={"content": "Branch message", "role": "user"}
        )
        
        # Verify independence
        main_msgs = test_client.get(
            f"/api/v1/conversations/{conv_id}/messages"
        ).json()["messages"]
        
        branch_msgs = test_client.get(
            f"/api/v1/conversations/{branch_id}/messages"
        ).json()["messages"]
        
        # Should have different last messages
        assert main_msgs[-1]["content"] != branch_msgs[-1]["content"]


class TestConversationExport:
    """Test conversation export functionality."""

    @pytest.mark.asyncio
    async def test_export_json(self, test_client, test_user_id):
        """Test exporting conversation as JSON."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Add messages
        test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Test message", "role": "user"}
        )
        
        # Export as JSON
        response = test_client.get(
            f"/api/v1/conversations/{conv_id}/export",
            params={"format": "json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "messages" in data
        assert len(data["messages"]) > 0

    @pytest.mark.asyncio
    async def test_export_markdown(self, test_client, test_user_id):
        """Test exporting conversation as Markdown."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Test message", "role": "user"}
        )
        
        # Export as Markdown
        response = test_client.get(
            f"/api/v1/conversations/{conv_id}/export",
            params={"format": "markdown"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert "# Conversation" in content
        assert "Test message" in content


class TestProviderFailover:
    """Test model provider failover."""

    @pytest.mark.asyncio
    async def test_automatic_failover(self, test_client, test_user_id):
        """Test automatic failover to backup provider."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={
                "user_id": test_user_id,
                "model": "gpt-4",
                "fallback_models": ["gpt-3.5-turbo", "claude-2"]
            }
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Send message (should work even if primary fails)
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Test failover", "role": "user"}
        )
        
        # Should succeed with fallback
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        
        # Check which model was used
        assert "model_used" in data


class TestConcurrentConversations:
    """Test handling multiple concurrent conversations."""

    @pytest.mark.asyncio
    async def test_concurrent_messages(self, test_client, test_user_id):
        """Test sending messages to multiple conversations concurrently."""
        # Create multiple conversations
        conv_ids = []
        for i in range(5):
            response = test_client.post(
                "/api/v1/conversations",
                json={"user_id": test_user_id}
            )
            conv_ids.append(response.json()["conversation_id"])
        
        # Send messages concurrently
        async def send_message(conv_id: str, message: str):
            return test_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": message, "role": "user"}
            )
        
        # Use asyncio.gather for concurrent requests
        tasks = [
            send_message(conv_id, f"Message to conversation {i}")
            for i, conv_id in enumerate(conv_ids)
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        for response in responses:
            if isinstance(response, Exception):
                pytest.fail(f"Request failed: {response}")
            assert response.status_code == 200


class TestPerformance:
    """Performance benchmarks for conversation operations."""

    @pytest.mark.asyncio
    async def test_message_send_latency(self, test_client, test_user_id):
        """Test message send latency."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        start_time = datetime.now()
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Quick test", "role": "user"}
        )
        end_time = datetime.now()
        
        latency = (end_time - start_time).total_seconds()
        
        assert response.status_code == 200
        # Should respond within 5 seconds
        assert latency < 5.0

    @pytest.mark.asyncio
    async def test_conversation_list_performance(self, test_client, test_user_id):
        """Test performance of listing conversations."""
        # Create many conversations
        for i in range(50):
            test_client.post(
                "/api/v1/conversations",
                json={"user_id": test_user_id}
            )
        
        start_time = datetime.now()
        response = test_client.get(
            f"/api/v1/users/{test_user_id}/conversations",
            params={"limit": 50}
        )
        end_time = datetime.now()
        
        latency = (end_time - start_time).total_seconds()
        
        assert response.status_code == 200
        # Should retrieve within 1 second
        assert latency < 1.0
        assert len(response.json()["conversations"]) <= 50


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_conversation_id(self, test_client):
        """Test handling of invalid conversation ID."""
        response = test_client.get(
            "/api/v1/conversations/invalid-id/messages"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_message(self, test_client, test_user_id):
        """Test sending empty message."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "", "role": "user"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_message_too_long(self, test_client, test_user_id):
        """Test handling of excessively long messages."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Create a very long message
        long_message = "word " * 100000
        
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": long_message, "role": "user"}
        )
        
        # Should reject or truncate
        assert response.status_code in [400, 413]


class TestCostTracking:
    """Test cost tracking and token usage."""

    @pytest.mark.asyncio
    async def test_token_counting(self, test_client, test_user_id):
        """Test accurate token counting."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Count these tokens please", "role": "user"}
        )
        
        data = response.json()
        assert "tokens" in data
        assert "input" in data["tokens"]
        assert "output" in data["tokens"]
        assert "total" in data["tokens"]
        assert data["tokens"]["total"] > 0

    @pytest.mark.asyncio
    async def test_cost_calculation(self, test_client, test_user_id):
        """Test cost calculation."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id, "model": "gpt-4"}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        response = test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Calculate cost", "role": "user"}
        )
        
        data = response.json()
        assert "cost" in data
        assert isinstance(data["cost"], (int, float))
        assert data["cost"] >= 0


class TestRateLimiting:
    """Test rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, test_client, test_user_id):
        """Test that rate limits are enforced."""
        conv_response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        conv_id = conv_response.json()["conversation_id"]
        
        # Send many requests rapidly
        responses = []
        for i in range(100):
            response = test_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": f"Message {i}", "role": "user"}
            )
            responses.append(response.status_code)
        
        # Some requests should be rate limited
        assert 429 in responses  # Too Many Requests


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
