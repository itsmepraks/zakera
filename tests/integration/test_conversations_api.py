"""
Integration tests for conversation API endpoints.

Tests the full API workflow including authentication, CRUD operations,
and error handling.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import Conversation, Message

pytestmark = pytest.mark.integration

# ============================================================================
# Conversation Creation Tests
# ============================================================================

class TestConversationCreation:
    """Test conversation creation endpoint."""
    
    def test_create_conversation_success(self, client: TestClient, auth_headers: dict):
        """Test successful conversation creation."""
        response = client.post(
            "/api/v1/conversations",
            json={
                "title": "New Conversation",
                "system_prompt": "You are helpful.",
                "model_name": "gpt-4-turbo-preview",
                "temperature": 0.7,
                "tags": ["test", "api"]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Conversation"
        assert data["model_name"] == "gpt-4-turbo-preview"
        assert "test" in data["tags"]
        assert data["message_count"] == 0
        assert data["total_tokens"] == 0
    
    def test_create_conversation_minimal(self, client: TestClient, auth_headers: dict):
        """Test creating conversation with minimal data."""
        response = client.post(
            "/api/v1/conversations",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Conversation"  # Default
    
    def test_create_conversation_unauthorized(self, client: TestClient):
        """Test conversation creation without authentication."""
        response = client.post(
            "/api/v1/conversations",
            json={"title": "Test"}
        )
        
        assert response.status_code == 401

# ============================================================================
# Conversation Listing Tests
# ============================================================================

class TestConversationListing:
    """Test conversation listing endpoint."""
    
    def test_list_conversations(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test listing conversations."""
        response = client.get(
            "/api/v1/conversations",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5  # We have 5 test conversations
        assert all("id" in conv for conv in data)
    
    def test_list_conversations_pagination(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test conversation pagination."""
        response = client.get(
            "/api/v1/conversations?skip=2&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
    
    def test_list_conversations_filter_archived(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test filtering by archived status."""
        response = client.get(
            "/api/v1/conversations?archived=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(conv["is_archived"] for conv in data)
    
    def test_list_conversations_filter_pinned(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test filtering by pinned status."""
        response = client.get(
            "/api/v1/conversations?pinned=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(conv["is_pinned"] for conv in data)
    
    def test_list_conversations_search(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test searching conversations."""
        response = client.get(
            "/api/v1/conversations?search=Conversation+1",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("1" in conv["title"] for conv in data)
    
    def test_list_conversations_tags(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test filtering by tags."""
        response = client.get(
            "/api/v1/conversations?tags=test",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all("test" in conv.get("tags", []) for conv in data if conv.get("tags"))
    
    def test_list_conversations_sorting(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test sorting conversations."""
        # Sort by title ascending
        response = client.get(
            "/api/v1/conversations?sort_by=title&order=asc",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

# ============================================================================
# Conversation Retrieval Tests
# ============================================================================

class TestConversationRetrieval:
    """Test conversation retrieval endpoint."""
    
    def test_get_conversation(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test getting a specific conversation."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_conversation.id
        assert data["title"] == test_conversation.title
        assert "messages" in data
    
    def test_get_conversation_with_messages(self, client: TestClient, auth_headers: dict, test_conversation_with_messages: Conversation):
        """Test getting conversation with messages."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation_with_messages.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 4
    
    def test_get_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent conversation."""
        response = client.get(
            "/api/v1/conversations/invalid-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_get_conversation_unauthorized_user(self, client: TestClient, test_conversation: Conversation, test_user2):
        """Test accessing another user's conversation."""
        from src.api.auth import create_access_token
        
        # Create token for different user
        other_user_token = create_access_token(data={"sub": test_user2.username})
        headers = {"Authorization": f"Bearer {other_user_token}"}
        
        response = client.get(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=headers
        )
        
        assert response.status_code == 404  # Not found (hidden for security)

# ============================================================================
# Conversation Update Tests
# ============================================================================

class TestConversationUpdate:
    """Test conversation update endpoint."""
    
    def test_update_conversation_title(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test updating conversation title."""
        response = client.patch(
            f"/api/v1/conversations/{test_conversation.id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
    
    def test_update_conversation_archive(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test archiving conversation."""
        response = client.patch(
            f"/api/v1/conversations/{test_conversation.id}",
            json={"is_archived": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True
    
    def test_update_conversation_pin(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test pinning conversation."""
        response = client.patch(
            f"/api/v1/conversations/{test_conversation.id}",
            json={"is_pinned": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_pinned"] is True
    
    def test_update_conversation_tags(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test updating conversation tags."""
        response = client.patch(
            f"/api/v1/conversations/{test_conversation.id}",
            json={"tags": ["new", "tags"]},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "new" in data["tags"]
        assert "tags" in data["tags"]
    
    def test_update_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """Test updating non-existent conversation."""
        response = client.patch(
            "/api/v1/conversations/invalid-id",
            json={"title": "New Title"},
            headers=auth_headers
        )
        
        assert response.status_code == 404

# ============================================================================
# Conversation Deletion Tests
# ============================================================================

class TestConversationDeletion:
    """Test conversation deletion endpoint."""
    
    def test_delete_conversation_soft(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, db_session: Session):
        """Test soft delete conversation."""
        response = client.delete(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hard_delete"] is False
        
        # Check database - should be soft deleted
        db_session.refresh(test_conversation)
        assert test_conversation.is_deleted is True
    
    def test_delete_conversation_hard(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, db_session: Session):
        """Test hard delete conversation."""
        conv_id = test_conversation.id
        
        response = client.delete(
            f"/api/v1/conversations/{conv_id}?hard_delete=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hard_delete"] is True
        
        # Check database - should be gone
        conv = db_session.query(Conversation).filter(Conversation.id == conv_id).first()
        assert conv is None
    
    def test_delete_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting non-existent conversation."""
        response = client.delete(
            "/api/v1/conversations/invalid-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404

# ============================================================================
# Message Operations Tests
# ============================================================================

class TestMessageOperations:
    """Test message-related endpoints."""
    
    def test_add_message(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test adding a message to conversation."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            json={
                "role": "user",
                "content": "Hello, AI!",
                "metadata": {"source": "api_test"}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, AI!"
        assert data["metadata"]["source"] == "api_test"
    
    def test_get_messages(self, client: TestClient, auth_headers: dict, test_conversation_with_messages: Conversation):
        """Test getting messages from conversation."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation_with_messages.id}/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert all("role" in msg and "content" in msg for msg in data)
    
    def test_get_messages_filter_by_role(self, client: TestClient, auth_headers: dict, test_conversation_with_messages: Conversation):
        """Test filtering messages by role."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation_with_messages.id}/messages?role=user",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(msg["role"] == "user" for msg in data)
    
    def test_get_messages_pagination(self, client: TestClient, auth_headers: dict, test_conversation_with_messages: Conversation):
        """Test message pagination."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation_with_messages.id}/messages?skip=1&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

# ============================================================================
# Statistics Tests
# ============================================================================

class TestConversationStatistics:
    """Test conversation statistics endpoint."""
    
    def test_get_statistics(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test getting user conversation statistics."""
        response = client.get(
            "/api/v1/conversations/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_conversations" in data
        assert "active_conversations" in data
        assert "archived_conversations" in data
        assert "total_messages" in data
        assert "total_tokens" in data
        assert "total_cost" in data
        assert data["total_conversations"] >= 5

# ============================================================================
# Sharing Tests
# ============================================================================

class TestConversationSharing:
    """Test conversation sharing endpoints."""
    
    def test_create_share(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test creating a conversation share."""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/share",
            json={
                "is_public": True,
                "expires_in_days": 7,
                "can_edit": False
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "share_token" in data
        assert "share_url" in data
        assert data["is_public"] is True
        assert data["can_edit"] is False
    
    def test_list_shares(self, client: TestClient, auth_headers: dict, test_conversation: Conversation, test_share):
        """Test listing conversation shares."""
        response = client.get(
            f"/api/v1/conversations/{test_conversation.id}/shares",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(share["id"] == test_share.id for share in data)

# ============================================================================
# Bulk Operations Tests
# ============================================================================

class TestBulkOperations:
    """Test bulk operation endpoints."""
    
    def test_bulk_archive(self, client: TestClient, auth_headers: dict, test_conversations: list, db_session: Session):
        """Test bulk archive conversations."""
        conv_ids = [conv.id for conv in test_conversations[:3]]
        
        response = client.post(
            "/api/v1/conversations/bulk/archive",
            json=conv_ids,
            params={"archive": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        
        # Check database
        for conv_id in conv_ids:
            conv = db_session.query(Conversation).filter(Conversation.id == conv_id).first()
            assert conv.is_archived is True
    
    def test_bulk_delete(self, client: TestClient, auth_headers: dict, test_conversations: list, db_session: Session):
        """Test bulk delete conversations."""
        conv_ids = [conv.id for conv in test_conversations[:2]]
        
        response = client.post(
            "/api/v1/conversations/bulk/delete",
            json=conv_ids,
            params={"hard_delete": False},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["hard_delete"] is False
        
        # Check soft deleted
        for conv_id in conv_ids:
            conv = db_session.query(Conversation).filter(Conversation.id == conv_id).first()
            assert conv.is_deleted is True

# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test API error handling."""
    
    def test_invalid_json(self, client: TestClient, auth_headers: dict):
        """Test handling invalid JSON."""
        response = client.post(
            "/api/v1/conversations",
            data="invalid json",
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_invalid_field_type(self, client: TestClient, auth_headers: dict):
        """Test handling invalid field types."""
        response = client.post(
            "/api/v1/conversations",
            json={"temperature": "not_a_number"},
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_missing_required_auth(self, client: TestClient):
        """Test endpoints require authentication."""
        response = client.get("/api/v1/conversations")
        assert response.status_code == 401
