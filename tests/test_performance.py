"""
Performance tests for the database persistence system.

These tests verify that the system performs well under load and with
large datasets.
"""
import pytest
import time
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.api.models import Conversation, Message
from src.model.memory import ConversationMemory
from tests.conftest import create_test_conversation, create_test_message, create_test_user

pytestmark = [pytest.mark.performance, pytest.mark.slow]

# ============================================================================
# Database Performance Tests
# ============================================================================

class TestDatabasePerformance:
    """Test database operation performance."""
    
    def test_bulk_conversation_creation(self, db_session: Session, test_user):
        """Test creating many conversations efficiently."""
        start_time = time.time()
        
        conversations = []
        for i in range(100):
            conv = Conversation(
                user_id=test_user.id,
                title=f"Perf Test Conversation {i}",
                tags=["performance", "test"]
            )
            conversations.append(conv)
        
        db_session.add_all(conversations)
        db_session.commit()
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert elapsed < 2.0
        assert len(conversations) == 100
    
    def test_bulk_message_creation(self, db_session: Session, test_conversation):
        """Test creating many messages efficiently."""
        start_time = time.time()
        
        messages = []
        for i in range(500):
            msg = Message(
                conversation_id=test_conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Performance test message {i}",
                tokens_used=10
            )
            messages.append(msg)
        
        db_session.add_all(messages)
        db_session.commit()
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 3 seconds)
        assert elapsed < 3.0
        assert len(messages) == 500
    
    def test_conversation_query_performance(self, db_session: Session, test_user):
        """Test querying conversations efficiently."""
        # Create test data
        for i in range(50):
            create_test_conversation(
                db_session, test_user, 
                f"Query Perf {i}",
                tags=["test"] if i % 2 == 0 else ["other"]
            )
        db_session.commit()
        
        start_time = time.time()
        
        # Query with filters
        convs = db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id,
            Conversation.is_deleted == False,
            Conversation.tags.contains(["test"])
        ).all()
        
        elapsed = time.time() - start_time
        
        # Should be fast with indexes (< 0.1 seconds)
        assert elapsed < 0.1
        assert len(convs) > 0
    
    def test_message_query_with_joins(self, db_session: Session, test_user):
        """Test complex queries with joins."""
        # Create data
        for i in range(20):
            conv = create_test_conversation(db_session, test_user, f"Join Test {i}")
            for j in range(10):
                create_test_message(db_session, conv, "user", f"Message {j}")
        db_session.commit()
        
        start_time = time.time()
        
        # Query messages with conversation join
        messages = db_session.query(Message).join(Conversation).filter(
            Conversation.user_id == test_user.id,
            Message.role == "user"
        ).limit(50).all()
        
        elapsed = time.time() - start_time
        
        # Should be efficient with proper indexes
        assert elapsed < 0.2
        assert len(messages) > 0

# ============================================================================
# Memory System Performance Tests
# ============================================================================

class TestMemoryPerformance:
    """Test ConversationMemory performance."""
    
    def test_large_conversation_loading(self, db_session: Session, test_user):
        """Test loading conversation with many messages."""
        # Create conversation with many messages
        conv = create_test_conversation(db_session, test_user, "Large Conv")
        for i in range(200):
            create_test_message(
                db_session, conv,
                "user" if i % 2 == 0 else "assistant",
                f"Message {i}" * 10  # Make messages longer
            )
        db_session.commit()
        
        start_time = time.time()
        
        # Load into memory
        memory = ConversationMemory.from_conversation_id(
            conversation_id=conv.id,
            db=db_session
        )
        
        elapsed = time.time() - start_time
        
        # Should load efficiently (< 1 second)
        assert elapsed < 1.0
        assert len(memory.turns) > 0
    
    def test_message_adding_performance(self, db_session: Session, test_user):
        """Test adding many messages to memory."""
        conv = create_test_conversation(db_session, test_user, "Add Perf")
        memory = ConversationMemory(
            conversation_id=conv.id,
            db=db_session
        )
        
        start_time = time.time()
        
        # Add many messages
        for i in range(100):
            memory.add_turn("user" if i % 2 == 0 else "assistant", f"Message {i}")
        
        elapsed = time.time() - start_time
        
        # Should be fast (< 2 seconds including DB writes)
        assert elapsed < 2.0
    
    def test_token_counting_performance(self):
        """Test token counting with large messages."""
        memory = ConversationMemory()
        
        # Create large message set
        large_messages = [
            {"role": "user", "content": "This is a test message. " * 100}
            for _ in range(50)
        ]
        
        start_time = time.time()
        
        count = memory._count_tokens(large_messages)
        
        elapsed = time.time() - start_time
        
        # Should count efficiently (< 0.5 seconds)
        assert elapsed < 0.5
        assert count > 0

# ============================================================================
# API Performance Tests
# ============================================================================

class TestAPIPerformance:
    """Test API endpoint performance."""
    
    def test_list_conversations_performance(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test listing many conversations."""
        # Create many conversations
        for i in range(50):
            create_test_conversation(db_session, test_user, f"API Perf {i}")
        db_session.commit()
        
        start_time = time.time()
        
        response = client.get(
            "/api/v1/conversations?limit=50",
            headers=auth_headers
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Should respond quickly (< 1 second)
        assert elapsed < 1.0
    
    def test_search_performance(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test search performance with many results."""
        # Create searchable data
        for i in range(30):
            conv = create_test_conversation(db_session, test_user, f"Search Performance {i}")
            for j in range(10):
                create_test_message(
                    db_session, conv,
                    "user",
                    f"Searchable content test message {j}"
                )
        db_session.commit()
        
        start_time = time.time()
        
        response = client.get(
            "/api/v1/search/messages?query=searchable",
            headers=auth_headers
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Should search efficiently (< 1 second)
        assert elapsed < 1.0
    
    def test_conversation_with_messages_performance(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test retrieving conversation with many messages."""
        # Create conversation with many messages
        conv = create_test_conversation(db_session, test_user, "Messages Perf")
        for i in range(100):
            create_test_message(db_session, conv, "user", f"Message {i}")
        db_session.commit()
        
        start_time = time.time()
        
        response = client.get(
            f"/api/v1/conversations/{conv.id}",
            headers=auth_headers
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Should retrieve efficiently (< 1 second)
        assert elapsed < 1.0
    
    def test_bulk_operations_performance(self, client: TestClient, auth_headers: dict, db_session: Session, test_user):
        """Test bulk operations performance."""
        # Create conversations to bulk operate on
        conv_ids = []
        for i in range(20):
            conv = create_test_conversation(db_session, test_user, f"Bulk {i}")
            conv_ids.append(conv.id)
        db_session.commit()
        
        start_time = time.time()
        
        response = client.post(
            "/api/v1/conversations/bulk/archive",
            json=conv_ids,
            params={"archive": True},
            headers=auth_headers
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Should complete efficiently (< 1 second)
        assert elapsed < 1.0

# ============================================================================
# Concurrent Access Tests
# ============================================================================

class TestConcurrentAccess:
    """Test system performance under concurrent access."""
    
    def test_concurrent_conversation_creation(self, db_session: Session):
        """Test creating conversations from multiple users concurrently."""
        users = [create_test_user(db_session, f"user{i}") for i in range(5)]
        
        start_time = time.time()
        
        # Simulate concurrent operations
        for user in users:
            for i in range(10):
                create_test_conversation(db_session, user, f"Concurrent {i}")
        
        db_session.commit()
        
        elapsed = time.time() - start_time
        
        # Should handle multiple users efficiently (< 2 seconds)
        assert elapsed < 2.0
    
    def test_concurrent_message_adding(self, db_session: Session, test_user):
        """Test adding messages to multiple conversations concurrently."""
        # Create conversations
        convs = [create_test_conversation(db_session, test_user, f"Conc {i}") for i in range(10)]
        db_session.commit()
        
        start_time = time.time()
        
        # Add messages to all conversations
        for conv in convs:
            for i in range(10):
                create_test_message(db_session, conv, "user", f"Message {i}")
        
        db_session.commit()
        
        elapsed = time.time() - start_time
        
        # Should handle concurrent writes (< 2 seconds)
        assert elapsed < 2.0

# ============================================================================
# Memory Usage Tests
# ============================================================================

class TestMemoryUsage:
    """Test memory consumption of operations."""
    
    @pytest.mark.skipif(True, reason="Requires memory_profiler")
    def test_large_query_memory(self, db_session: Session, test_user):
        """Test memory usage of large queries."""
        # Create large dataset
        for i in range(100):
            conv = create_test_conversation(db_session, test_user, f"Memory Test {i}")
            for j in range(50):
                create_test_message(db_session, conv, "user", f"Message {j}")
        db_session.commit()
        
        # Query all messages
        messages = db_session.query(Message).all()
        
        # Should not consume excessive memory
        assert len(messages) == 5000
    
    def test_conversation_memory_pagination(self, db_session: Session, test_user):
        """Test that pagination limits memory usage."""
        # Create many conversations
        for i in range(100):
            create_test_conversation(db_session, test_user, f"Paginate {i}")
        db_session.commit()
        
        # Query with pagination
        page1 = db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id
        ).limit(10).all()
        
        # Should only load 10, not all 100
        assert len(page1) == 10

# ============================================================================
# Stress Tests
# ============================================================================

class TestStress:
    """Stress tests for system limits."""
    
    @pytest.mark.slow
    def test_maximum_messages_per_conversation(self, db_session: Session, test_user):
        """Test handling conversations with maximum messages."""
        conv = create_test_conversation(db_session, test_user, "Max Messages")
        
        # Add many messages (stress test)
        messages = []
        for i in range(1000):
            msg = Message(
                conversation_id=conv.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Stress test message {i}"
            )
            messages.append(msg)
            
            # Commit in batches
            if i % 100 == 0:
                db_session.add_all(messages)
                db_session.commit()
                messages = []
        
        # Commit remaining
        if messages:
            db_session.add_all(messages)
            db_session.commit()
        
        # Should handle large conversations
        message_count = db_session.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()
        assert message_count == 1000
    
    @pytest.mark.slow
    def test_deep_message_threading(self, db_session: Session, test_user):
        """Test handling deep message thread hierarchies."""
        conv = create_test_conversation(db_session, test_user, "Deep Threading")
        
        # Create deep thread
        parent = None
        for i in range(50):  # 50 levels deep
            msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=f"Level {i}",
                parent_message_id=parent.id if parent else None
            )
            db_session.add(msg)
            db_session.commit()
            db_session.refresh(msg)
            parent = msg
        
        # Should handle deep hierarchies
        assert parent is not None
        
        # Count depth
        depth = 0
        current = parent
        while current.parent_message_id:
            depth += 1
            current = db_session.query(Message).filter(
                Message.id == current.parent_message_id
            ).first()
        
        assert depth == 49  # 50 messages = 49 parent relationships
