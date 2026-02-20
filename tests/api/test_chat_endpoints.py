"""Tests for chat API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import User, Conversation, Message


class TestChatEndpoints:
    """Test suite for chat endpoints."""
    
    def test_send_message_success(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test successfully sending a chat message."""
        response = client.post(
            "/api/v1/chat/send",
            json={
                "conversation_id": test_conversation.id,
                "message": "Hello, AI!",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "message_id" in data
    
    def test_send_message_unauthorized(self, client: TestClient, test_conversation: Conversation):
        """Test sending message without authentication."""
        response = client.post(
            "/api/v1/chat/send",
            json={
                "conversation_id": test_conversation.id,
                "message": "Hello, AI!",
            },
        )
        
        assert response.status_code == 401
    
    def test_send_message_invalid_conversation(self, client: TestClient, auth_headers: dict):
        """Test sending message to non-existent conversation."""
        response = client.post(
            "/api/v1/chat/send",
            json={
                "conversation_id": 99999,
                "message": "Hello, AI!",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    def test_send_empty_message(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test sending empty message."""
        response = client.post(
            "/api/v1/chat/send",
            json={
                "conversation_id": test_conversation.id,
                "message": "",
            },
            headers=auth_headers,
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_conversation_history(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_messages: list):
        """Test retrieving conversation history."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == len(test_messages)
    
    def test_get_conversation_history_with_pagination(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_messages: list):
        """Test paginated conversation history."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            params={"limit": 2, "offset": 0},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
    
    def test_delete_message(self, client: TestClient, auth_headers: dict, test_messages: list):
        """Test deleting a message."""
        message_id = test_messages[0].id
        response = client.delete(
            f"/api/v1/messages/{message_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
    
    def test_delete_message_unauthorized(self, client: TestClient, test_messages: list):
        """Test deleting message without authentication."""
        message_id = test_messages[0].id
        response = client.delete(f"/api/v1/messages/{message_id}")
        
        assert response.status_code == 401
    
    def test_create_conversation(self, client: TestClient, auth_headers: dict):
        """Test creating a new conversation."""
        response = client.post(
            "/api/v1/conversations",
            json={"title": "New Test Conversation"},
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Test Conversation"
        assert "id" in data
    
    def test_list_conversations(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test listing user conversations."""
        response = client.get(
            "/api/v1/conversations",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert len(data["conversations"]) >= 1
    
    def test_update_conversation_title(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test updating conversation title."""
        response = client.patch(
            f"/api/v1/conversations/{test_conversation.id}",
            json={"title": "Updated Title"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
    
    def test_delete_conversation(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test deleting a conversation."""
        response = client.delete(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
