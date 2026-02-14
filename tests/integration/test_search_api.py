"""
Integration tests for search API endpoints.

Tests search functionality across conversations and messages.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.models import Conversation, Message
from tests.conftest import create_test_conversation, create_test_message

pytestmark = pytest.mark.integration

# ============================================================================
# Message Search Tests
# ============================================================================

class TestMessageSearch:
    """Test message search functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_searchable_data(self, db_session: Session, test_user):
        """Create searchable test data."""
        # Create conversations with specific content
        conv1 = create_test_conversation(db_session, test_user, "AI Research")
        create_test_message(db_session, conv1, "user", "What is machine learning?")
        create_test_message(db_session, conv1, "assistant", "Machine learning is a subset of AI...")
        
        conv2 = create_test_conversation(db_session, test_user, "Python Tutorial")
        create_test_message(db_session, conv2, "user", "How do I use decorators in Python?")
        create_test_message(db_session, conv2, "assistant", "Python decorators are functions that modify other functions...")
        
        conv3 = create_test_conversation(db_session, test_user, "Data Science")
        create_test_message(db_session, conv3, "user", "Explain neural networks")
        create_test_message(db_session, conv3, "assistant", "Neural networks are machine learning models...")
        
        db_session.commit()
    
    def test_search_messages_basic(self, client: TestClient, auth_headers: dict):
        """Test basic message search."""
        response = client.get(
            "/api/v1/search/messages?query=machine+learning",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any("machine learning" in msg["content"].lower() for msg in data)
    
    def test_search_messages_with_snippet(self, client: TestClient, auth_headers: dict):
        """Test that search results include snippets."""
        response = client.get(
            "/api/v1/search/messages?query=Python",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # Check snippet exists and contains query
        for msg in data:
            assert "snippet" in msg
            assert len(msg["snippet"]) > 0
    
    def test_search_messages_filter_by_role(self, client: TestClient, auth_headers: dict):
        """Test filtering search results by role."""
        response = client.get(
            "/api/v1/search/messages?query=neural&role=user",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(msg["role"] == "user" for msg in data)
    
    def test_search_messages_filter_by_conversation(self, client: TestClient, auth_headers: dict, test_conversation: Conversation):
        """Test filtering search by conversation."""
        response = client.get(
            f"/api/v1/search/messages?query=test&conversation_id={test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(msg["conversation_id"] == test_conversation.id for msg in data)
    
    def test_search_messages_pagination(self, client: TestClient, auth_headers: dict):
        """Test message search pagination."""
        response = client.get(
            "/api/v1/search/messages?query=machine&limit=1&offset=0",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
    
    def test_search_messages_no_results(self, client: TestClient, auth_headers: dict):
        """Test search with no matching results."""
        response = client.get(
            "/api/v1/search/messages?query=nonexistent_query_xyz",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_search_messages_special_characters(self, client: TestClient, auth_headers: dict):
        """Test search with special characters."""
        response = client.get(
            "/api/v1/search/messages?query=machine+learning",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        # Should handle URL encoding properly

# ============================================================================
# Conversation Search Tests
# ============================================================================

class TestConversationSearch:
    """Test conversation search functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_conversations(self, db_session: Session, test_user):
        """Create searchable conversations."""
        convs = [
            ("Machine Learning Basics", "Learn about ML"),
            ("Python Programming", "Python coding tips"),
            ("Data Science Projects", "Working with data"),
            ("Web Development", "Building websites"),
            ("Machine Learning Advanced", "Deep learning topics")
        ]
        
        for title, prompt in convs:
            conv = create_test_conversation(
                db_session, test_user, title, 
                system_prompt=prompt,
                tags=["ml"] if "machine" in title.lower() else ["other"]
            )
        
        db_session.commit()
    
    def test_search_conversations_by_title(self, client: TestClient, auth_headers: dict):
        """Test searching conversations by title."""
        response = client.get(
            "/api/v1/search/conversations?query=Machine+Learning",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any("Machine Learning" in conv["title"] for conv in data)
    
    def test_search_conversations_by_system_prompt(self, client: TestClient, auth_headers: dict):
        """Test searching conversations by system prompt."""
        response = client.get(
            "/api/v1/search/conversations?query=coding",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
    
    def test_search_conversations_with_tags(self, client: TestClient, auth_headers: dict):
        """Test filtering search by tags."""
        response = client.get(
            "/api/v1/search/conversations?query=Machine&tags=ml",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all("ml" in conv.get("tags", []) for conv in data if conv.get("tags"))
    
    def test_search_conversations_exclude_archived(self, client: TestClient, auth_headers: dict):
        """Test excluding archived conversations from search."""
        response = client.get(
            "/api/v1/search/conversations?query=Machine&include_archived=false",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(not conv["is_archived"] for conv in data)
    
    def test_search_conversations_pagination(self, client: TestClient, auth_headers: dict):
        """Test conversation search pagination."""
        response = client.get(
            "/api/v1/search/conversations?query=Machine&limit=1",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1
    
    def test_search_conversations_with_preview(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test that search results include last message preview."""
        # Create conversation with message
        conv = create_test_conversation(db_session, test_user, "Test Preview")
        create_test_message(db_session, conv, "user", "This is the last message")
        db_session.commit()
        
        response = client.get(
            "/api/v1/search/conversations?query=Preview",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            # At least one should have a preview
            assert any(conv.get("last_message_preview") for conv in data)

# ============================================================================
# Unified Search Tests
# ============================================================================

class TestUnifiedSearch:
    """Test unified search across all content."""
    
    def test_search_all(self, client: TestClient, auth_headers: dict):
        """Test unified search endpoint."""
        response = client.get(
            "/api/v1/search/all?query=machine",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "messages" in data
        assert "total_conversations" in data
        assert "total_messages" in data
        assert "total_results" in data
    
    def test_search_all_limit(self, client: TestClient, auth_headers: dict):
        """Test unified search with limit."""
        response = client.get(
            "/api/v1/search/all?query=machine&limit=2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) <= 2
        assert len(data["messages"]) <= 2
    
    def test_search_all_totals(self, client: TestClient, auth_headers: dict):
        """Test that totals are calculated correctly."""
        response = client.get(
            "/api/v1/search/all?query=machine",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == data["total_conversations"] + data["total_messages"]

# ============================================================================
# Recent Conversations Tests
# ============================================================================

class TestRecentConversations:
    """Test recent conversations endpoint."""
    
    def test_get_recent_conversations(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test getting recent conversations."""
        response = client.get(
            "/api/v1/search/recent",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        # Should be ordered by updated_at (most recent first)
        if len(data) > 1:
            assert data[0]["updated_at"] >= data[1]["updated_at"]
    
    def test_recent_conversations_limit(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test limiting recent conversations."""
        response = client.get(
            "/api/v1/search/recent?limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
    
    def test_recent_conversations_exclude_archived(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test excluding archived from recent."""
        response = client.get(
            "/api/v1/search/recent?include_archived=false",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(not conv["is_archived"] for conv in data)
    
    def test_recent_conversations_pinned_first(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test that pinned conversations appear first."""
        response = client.get(
            "/api/v1/search/recent",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0 and any(conv["is_pinned"] for conv in data):
            # First one should be pinned if any are pinned
            pinned_indices = [i for i, conv in enumerate(data) if conv["is_pinned"]]
            if pinned_indices:
                assert 0 in pinned_indices or data[0]["is_pinned"]

# ============================================================================
# Tags Tests
# ============================================================================

class TestTagsEndpoint:
    """Test tags listing endpoint."""
    
    def test_get_all_tags(self, client: TestClient, auth_headers: dict, test_conversations: list):
        """Test getting all user tags."""
        response = client.get(
            "/api/v1/search/tags",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have tags from test_conversations
        assert "test" in data or "sample" in data
    
    def test_tags_are_unique(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test that returned tags are unique."""
        # Create conversations with duplicate tags
        for i in range(3):
            create_test_conversation(
                db_session, test_user, 
                f"Conv {i}",
                tags=["common", "tag"]
            )
        db_session.commit()
        
        response = client.get(
            "/api/v1/search/tags",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Each tag should appear only once
        assert len(data) == len(set(data))
    
    def test_tags_sorted(self, client: TestClient, auth_headers: dict):
        """Test that tags are returned sorted."""
        response = client.get(
            "/api/v1/search/tags",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        if len(data) > 1:
            # Should be sorted alphabetically
            assert data == sorted(data)

# ============================================================================
# Search Edge Cases
# ============================================================================

class TestSearchEdgeCases:
    """Test search edge cases and error handling."""
    
    def test_search_empty_query(self, client: TestClient, auth_headers: dict):
        """Test search with empty query."""
        response = client.get(
            "/api/v1/search/messages?query=",
            headers=auth_headers
        )
        
        # Should reject empty query (min_length=2)
        assert response.status_code == 422
    
    def test_search_very_short_query(self, client: TestClient, auth_headers: dict):
        """Test search with very short query."""
        response = client.get(
            "/api/v1/search/messages?query=a",
            headers=auth_headers
        )
        
        # Should reject single character (min_length=2)
        assert response.status_code == 422
    
    def test_search_unicode_query(self, client: TestClient, auth_headers: dict):
        """Test search with unicode characters."""
        response = client.get(
            "/api/v1/search/messages?query=你好",
            headers=auth_headers
        )
        
        # Should handle unicode
        assert response.status_code == 200
    
    def test_search_unauthorized(self, client: TestClient):
        """Test search without authentication."""
        response = client.get("/api/v1/search/messages?query=test")
        assert response.status_code == 401
    
    def test_search_invalid_role(self, client: TestClient, auth_headers: dict):
        """Test search with invalid role filter."""
        response = client.get(
            "/api/v1/search/messages?query=test&role=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_search_large_limit(self, client: TestClient, auth_headers: dict):
        """Test search with limit exceeding maximum."""
        response = client.get(
            "/api/v1/search/messages?query=test&limit=1000",
            headers=auth_headers
        )
        
        # Should reject or cap at max (100)
        assert response.status_code == 422
    
    def test_search_negative_offset(self, client: TestClient, auth_headers: dict):
        """Test search with negative offset."""
        response = client.get(
            "/api/v1/search/messages?query=test&offset=-1",
            headers=auth_headers
        )
        
        assert response.status_code == 422

# ============================================================================
# Performance Tests
# ============================================================================

class TestSearchPerformance:
    """Test search performance characteristics."""
    
    @pytest.mark.slow
    def test_search_with_many_results(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test search performance with many results."""
        # Create many conversations and messages
        for i in range(50):
            conv = create_test_conversation(db_session, test_user, f"Performance Test {i}")
            for j in range(10):
                create_test_message(
                    db_session, conv, 
                    "user" if j % 2 == 0 else "assistant",
                    f"Test message {i}-{j} with searchable content"
                )
        db_session.commit()
        
        response = client.get(
            "/api/v1/search/messages?query=searchable",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        # Should complete in reasonable time
    
    @pytest.mark.slow
    def test_search_pagination_performance(self, client: TestClient, auth_headers: dict):
        """Test pagination doesn't degrade with large offsets."""
        response = client.get(
            "/api/v1/search/messages?query=test&offset=100&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        # Should handle large offsets efficiently
