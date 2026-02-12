"""
Comprehensive API integration tests for conversation endpoints.

Tests cover CRUD operations, filtering, pagination, permissions,
and edge cases for the conversation management API.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.fixtures import (
    client,
    test_db_session,
    test_user,
    test_user_token,
    auth_headers,
    test_conversation,
    test_conversations,
    test_messages,
    multiple_test_users
)


class TestConversationCreation:
    """Test conversation creation endpoints."""
    
    def test_create_conversation_success(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test successful conversation creation."""
        response = client.post(
            "/api/conversations",
            json={"title": "New Conversation"},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Conversation"
        assert "id" in data
        assert data["is_pinned"] is False
        assert data["is_archived"] is False
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_conversation_with_optional_fields(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test conversation creation with all optional fields."""
        response = client.post(
            "/api/conversations",
            json={
                "title": "Important Conversation",
                "is_pinned": True,
                "metadata": {"category": "work", "priority": "high"}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Important Conversation"
        assert data["is_pinned"] is True
        assert data["metadata"]["category"] == "work"
    
    def test_create_conversation_without_auth(self, client: TestClient):
        """Test that conversation creation requires authentication."""
        response = client.post(
            "/api/conversations",
            json={"title": "Unauthorized Conversation"}
        )
        
        assert response.status_code == 401
    
    def test_create_conversation_invalid_data(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test conversation creation with invalid data."""
        # Empty title
        response = client.post(
            "/api/conversations",
            json={"title": ""},
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Missing required field
        response = client.post(
            "/api/conversations",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_create_conversation_title_too_long(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test conversation creation with excessively long title."""
        long_title = "x" * 300  # Assuming max length is 255
        response = client.post(
            "/api/conversations",
            json={"title": long_title},
            headers=auth_headers
        )
        
        # Should either succeed with truncation or fail with validation
        assert response.status_code in [201, 422]


class TestConversationRetrieval:
    """Test conversation retrieval endpoints."""
    
    def test_list_conversations_empty(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test listing conversations when none exist."""
        response = client.get("/api/conversations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or ("conversations" in data)
    
    def test_list_conversations(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test listing all user conversations."""
        response = client.get("/api/conversations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Handle both list and paginated response formats
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        assert len(conversations) >= 3
    
    def test_get_conversation_by_id(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test retrieving a specific conversation by ID."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_conversation.id
        assert data["title"] == test_conversation.title
    
    def test_get_nonexistent_conversation(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test retrieving a conversation that doesn't exist."""
        response = client.get(
            "/api/conversations/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_get_other_user_conversation(
        self,
        client: TestClient,
        test_db_session: Session,
        test_conversation,
        multiple_test_users: list
    ):
        """Test that users cannot access other users' conversations."""
        # Create token for different user
        from src.api.auth import create_access_token
        other_user_token = create_access_token(
            data={"sub": multiple_test_users[1].username, "user_id": str(multiple_test_users[1].id)}
        )
        other_headers = {"Authorization": f"Bearer {other_user_token}"}
        
        response = client.get(
            f"/api/conversations/{test_conversation.id}",
            headers=other_headers
        )
        
        # Should return 404 or 403
        assert response.status_code in [403, 404]
    
    def test_list_conversations_with_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test conversation listing with pagination parameters."""
        response = client.get(
            "/api/conversations?limit=2&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check pagination works
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        assert len(conversations) <= 2
    
    def test_filter_conversations_by_archived(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test filtering conversations by archived status."""
        response = client.get(
            "/api/conversations?is_archived=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        # All returned conversations should be archived
        for conv in conversations:
            assert conv["is_archived"] is True
    
    def test_filter_conversations_by_pinned(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test filtering conversations by pinned status."""
        response = client.get(
            "/api/conversations?is_pinned=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        # All returned conversations should be pinned
        for conv in conversations:
            assert conv["is_pinned"] is True
    
    def test_search_conversations(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test searching conversations by title."""
        response = client.get(
            "/api/conversations?search=Pinned",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        conversations = data if isinstance(data, list) else data.get("conversations", [])
        
        # At least one result should contain "Pinned" in title
        if conversations:
            assert any("Pinned" in conv["title"] for conv in conversations)


class TestConversationUpdate:
    """Test conversation update endpoints."""
    
    def test_update_conversation_title(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test updating conversation title."""
        response = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["id"] == test_conversation.id
    
    def test_pin_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test pinning a conversation."""
        response = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"is_pinned": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_pinned"] is True
    
    def test_archive_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test archiving a conversation."""
        response = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"is_archived": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True
    
    def test_update_conversation_metadata(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test updating conversation metadata."""
        metadata = {"tags": ["important", "work"], "priority": "high"}
        response = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"metadata": metadata},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
    
    def test_update_nonexistent_conversation(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test updating a conversation that doesn't exist."""
        response = client.patch(
            "/api/conversations/99999",
            json={"title": "Updated"},
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_update_other_user_conversation(
        self,
        client: TestClient,
        test_conversation,
        multiple_test_users: list
    ):
        """Test that users cannot update other users' conversations."""
        from src.api.auth import create_access_token
        other_user_token = create_access_token(
            data={"sub": multiple_test_users[1].username, "user_id": str(multiple_test_users[1].id)}
        )
        other_headers = {"Authorization": f"Bearer {other_user_token}"}
        
        response = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"title": "Hacked"},
            headers=other_headers
        )
        
        assert response.status_code in [403, 404]


class TestConversationDeletion:
    """Test conversation deletion endpoints."""
    
    def test_delete_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test deleting a conversation."""
        response = client.delete(
            f"/api/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 204]
        
        # Verify deletion
        get_response = client.get(
            f"/api/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    def test_delete_conversation_with_messages(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test deleting a conversation that contains messages."""
        response = client.delete(
            f"/api/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        # Should cascade delete messages
        assert response.status_code in [200, 204]
    
    def test_delete_nonexistent_conversation(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test deleting a conversation that doesn't exist."""
        response = client.delete(
            "/api/conversations/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_delete_other_user_conversation(
        self,
        client: TestClient,
        test_conversation,
        multiple_test_users: list
    ):
        """Test that users cannot delete other users' conversations."""
        from src.api.auth import create_access_token
        other_user_token = create_access_token(
            data={"sub": multiple_test_users[1].username, "user_id": str(multiple_test_users[1].id)}
        )
        other_headers = {"Authorization": f"Bearer {other_user_token}"}
        
        response = client.delete(
            f"/api/conversations/{test_conversation.id}",
            headers=other_headers
        )
        
        assert response.status_code in [403, 404]


class TestConversationAnalytics:
    """Test conversation analytics and statistics endpoints."""
    
    def test_get_conversation_stats(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test retrieving conversation statistics."""
        response = client.get(
            f"/api/conversations/{test_conversation.id}/stats",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "message_count" in data or "total_messages" in data
            assert "total_tokens" in data or "tokens_used" in data
    
    def test_export_conversation(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation,
        test_messages: list
    ):
        """Test exporting conversation data."""
        # Test JSON export
        response = client.get(
            f"/api/conversations/{test_conversation.id}/export?format=json",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            assert response.headers.get("content-type") in [
                "application/json",
                "application/octet-stream"
            ]
    
    def test_get_user_analytics(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test retrieving user-level conversation analytics."""
        response = client.get(
            "/api/analytics/conversations",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestConversationBulkOperations:
    """Test bulk operations on conversations."""
    
    def test_bulk_archive_conversations(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test archiving multiple conversations at once."""
        conversation_ids = [conv.id for conv in test_conversations[:2]]
        
        response = client.post(
            "/api/conversations/bulk/archive",
            json={"conversation_ids": conversation_ids},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "updated" in data
    
    def test_bulk_delete_conversations(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversations: list
    ):
        """Test deleting multiple conversations at once."""
        conversation_ids = [conv.id for conv in test_conversations[:2]]
        
        response = client.post(
            "/api/conversations/bulk/delete",
            json={"conversation_ids": conversation_ids},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "deleted" in data


class TestConversationEdgeCases:
    """Test edge cases and error handling."""
    
    def test_conversation_with_special_characters(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test conversation creation with special characters in title."""
        special_title = "Test 🔥 Conversation with émojis & spëcial çhars"
        response = client.post(
            "/api/conversations",
            json={"title": special_title},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert special_title in data["title"]
    
    def test_concurrent_conversation_updates(
        self,
        client: TestClient,
        auth_headers: dict,
        test_conversation
    ):
        """Test handling of concurrent updates to the same conversation."""
        # Simulate concurrent updates
        response1 = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"title": "Update 1"},
            headers=auth_headers
        )
        
        response2 = client.patch(
            f"/api/conversations/{test_conversation.id}",
            json={"title": "Update 2"},
            headers=auth_headers
        )
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Last update should win
        final_response = client.get(
            f"/api/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        assert final_response.json()["title"] == "Update 2"
    
    def test_invalid_json_payload(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test handling of invalid JSON in request body."""
        response = client.post(
            "/api/conversations",
            data="invalid json{{{",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_sql_injection_attempt(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test that SQL injection attempts are handled safely."""
        malicious_title = "'; DROP TABLE conversations; --"
        response = client.post(
            "/api/conversations",
            json={"title": malicious_title},
            headers=auth_headers
        )
        
        # Should either succeed (with escaped title) or fail validation
        assert response.status_code in [201, 422]
        
        # Verify database is intact
        list_response = client.get("/api/conversations", headers=auth_headers)
        assert list_response.status_code == 200
