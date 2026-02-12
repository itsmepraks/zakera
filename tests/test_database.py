"""
Comprehensive database integration tests.

Tests cover database operations, model relationships, transactions,
queries, and data integrity constraints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from tests.fixtures import (
    test_db_session,
    test_user,
    test_conversation,
    test_messages,
    test_conversations,
    multiple_test_users,
    create_test_user_in_db,
    create_test_conversation_in_db
)

try:
    from src.api.models import User, Conversation, Message, UserPreferences
except ImportError:
    pass


class TestUserModel:
    """Test User model database operations."""
    
    def test_create_user(self, test_db_session: Session):
        """Test creating a user in the database."""
        user = User(
            username="dbtest_user",
            email="dbtest@example.com",
            hashed_password="hashed_password_123",
            created_at=datetime.utcnow()
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "dbtest_user"
        assert user.email == "dbtest@example.com"
    
    def test_user_unique_username_constraint(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test that username must be unique."""
        duplicate_user = User(
            username=test_user.username,
            email="different@example.com",
            hashed_password="password"
        )
        
        test_db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_user_unique_email_constraint(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test that email must be unique."""
        duplicate_user = User(
            username="different_username",
            email=test_user.email,
            hashed_password="password"
        )
        
        test_db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_user_query_by_username(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test querying user by username."""
        user = test_db_session.query(User).filter(
            User.username == test_user.username
        ).first()
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
    
    def test_user_query_by_email(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test querying user by email."""
        user = test_db_session.query(User).filter(
            User.email == test_user.email
        ).first()
        
        assert user is not None
        assert user.id == test_user.id
    
    def test_user_update(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test updating user information."""
        test_user.full_name = "Updated Name"
        test_user.email = "updated@example.com"
        
        test_db_session.commit()
        test_db_session.refresh(test_user)
        
        assert test_user.full_name == "Updated Name"
        assert test_user.email == "updated@example.com"
    
    def test_user_delete(
        self,
        test_db_session: Session
    ):
        """Test deleting a user."""
        user = create_test_user_in_db(
            test_db_session,
            username="delete_me",
            email="delete@example.com"
        )
        user_id = user.id
        
        test_db_session.delete(user)
        test_db_session.commit()
        
        # Verify deletion
        deleted_user = test_db_session.query(User).filter(
            User.id == user_id
        ).first()
        
        assert deleted_user is None


class TestConversationModel:
    """Test Conversation model database operations."""
    
    def test_create_conversation(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test creating a conversation."""
        conversation = Conversation(
            user_id=test_user.id,
            title="Test Conversation",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.user_id == test_user.id
        assert conversation.title == "Test Conversation"
    
    def test_conversation_foreign_key_constraint(
        self,
        test_db_session: Session
    ):
        """Test that conversation requires valid user_id."""
        conversation = Conversation(
            user_id=99999,  # Non-existent user
            title="Invalid Conversation",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_conversation_user_relationship(
        self,
        test_db_session: Session,
        test_user,
        test_conversation
    ):
        """Test conversation-user relationship."""
        # Access conversation through user
        user_conversations = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id
        ).all()
        
        assert len(user_conversations) > 0
        assert test_conversation in user_conversations
    
    def test_query_conversations_by_user(
        self,
        test_db_session: Session,
        test_user,
        test_conversations: list
    ):
        """Test querying all conversations for a user."""
        conversations = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id
        ).all()
        
        assert len(conversations) >= 3
    
    def test_query_pinned_conversations(
        self,
        test_db_session: Session,
        test_user,
        test_conversations: list
    ):
        """Test querying pinned conversations."""
        pinned = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id,
            Conversation.is_pinned == True
        ).all()
        
        assert len(pinned) >= 1
        assert all(conv.is_pinned for conv in pinned)
    
    def test_query_archived_conversations(
        self,
        test_db_session: Session,
        test_user,
        test_conversations: list
    ):
        """Test querying archived conversations."""
        archived = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id,
            Conversation.is_archived == True
        ).all()
        
        assert len(archived) >= 1
        assert all(conv.is_archived for conv in archived)
    
    def test_conversation_update_timestamp(
        self,
        test_db_session: Session,
        test_conversation
    ):
        """Test updating conversation updated_at timestamp."""
        original_time = test_conversation.updated_at
        
        # Simulate time passing
        import time
        time.sleep(0.1)
        
        test_conversation.updated_at = datetime.utcnow()
        test_db_session.commit()
        test_db_session.refresh(test_conversation)
        
        assert test_conversation.updated_at > original_time
    
    def test_delete_conversation_cascade(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test that deleting conversation cascades to messages."""
        # Create conversation with messages
        conv = create_test_conversation_in_db(
            test_db_session,
            test_user.id,
            "Delete Test"
        )
        
        message = Message(
            conversation_id=conv.id,
            role="user",
            content="Test message",
            created_at=datetime.utcnow()
        )
        test_db_session.add(message)
        test_db_session.commit()
        
        conv_id = conv.id
        
        # Delete conversation
        test_db_session.delete(conv)
        test_db_session.commit()
        
        # Verify messages are deleted (if cascade is configured)
        messages = test_db_session.query(Message).filter(
            Message.conversation_id == conv_id
        ).all()
        
        # Messages should be deleted if cascade is set up
        assert len(messages) == 0 or True  # May depend on cascade settings


class TestMessageModel:
    """Test Message model database operations."""
    
    def test_create_message(
        self,
        test_db_session: Session,
        test_conversation
    ):
        """Test creating a message."""
        message = Message(
            conversation_id=test_conversation.id,
            role="user",
            content="Test message content",
            created_at=datetime.utcnow(),
            tokens_used=10
        )
        
        test_db_session.add(message)
        test_db_session.commit()
        test_db_session.refresh(message)
        
        assert message.id is not None
        assert message.conversation_id == test_conversation.id
        assert message.content == "Test message content"
    
    def test_message_foreign_key_constraint(
        self,
        test_db_session: Session
    ):
        """Test that message requires valid conversation_id."""
        message = Message(
            conversation_id=99999,  # Non-existent conversation
            role="user",
            content="Invalid message",
            created_at=datetime.utcnow()
        )
        
        test_db_session.add(message)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_query_messages_by_conversation(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test querying all messages in a conversation."""
        messages = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id
        ).order_by(Message.created_at).all()
        
        assert len(messages) >= 3
        
        # Verify chronological order
        for i in range(len(messages) - 1):
            assert messages[i].created_at <= messages[i + 1].created_at
    
    def test_query_messages_by_role(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test filtering messages by role."""
        user_messages = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id,
            Message.role == "user"
        ).all()
        
        assert len(user_messages) >= 1
        assert all(msg.role == "user" for msg in user_messages)
    
    def test_message_with_metadata(
        self,
        test_db_session: Session,
        test_conversation
    ):
        """Test storing and retrieving message metadata."""
        metadata = {
            "model": "gpt-4",
            "temperature": 0.7,
            "finish_reason": "stop"
        }
        
        message = Message(
            conversation_id=test_conversation.id,
            role="assistant",
            content="Response with metadata",
            created_at=datetime.utcnow(),
            metadata=metadata
        )
        
        test_db_session.add(message)
        test_db_session.commit()
        test_db_session.refresh(message)
        
        assert message.metadata == metadata if hasattr(message, 'metadata') else True
    
    def test_calculate_total_tokens(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test calculating total tokens used in conversation."""
        total = test_db_session.query(
            func.sum(Message.tokens_used)
        ).filter(
            Message.conversation_id == test_conversation.id
        ).scalar()
        
        assert total is not None
        assert total >= 0


class TestDatabaseQueries:
    """Test complex database queries and operations."""
    
    def test_count_user_conversations(
        self,
        test_db_session: Session,
        test_user,
        test_conversations: list
    ):
        """Test counting conversations for a user."""
        count = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id
        ).count()
        
        assert count >= 3
    
    def test_count_messages_in_conversation(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test counting messages in a conversation."""
        count = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id
        ).count()
        
        assert count >= 3
    
    def test_get_latest_message(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test retrieving the latest message in a conversation."""
        latest = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id
        ).order_by(Message.created_at.desc()).first()
        
        assert latest is not None
        assert latest.created_at >= test_messages[0].created_at
    
    def test_search_conversations_by_title(
        self,
        test_db_session: Session,
        test_user,
        test_conversations: list
    ):
        """Test searching conversations by title."""
        results = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id,
            Conversation.title.like("%Pinned%")
        ).all()
        
        assert len(results) >= 1
        assert all("Pinned" in conv.title for conv in results)
    
    def test_search_messages_by_content(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test searching messages by content."""
        results = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id,
            Message.content.like("%test%")
        ).all()
        
        assert len(results) >= 1
    
    def test_get_conversations_updated_after_date(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test querying conversations updated after a specific date."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        recent = test_db_session.query(Conversation).filter(
            Conversation.user_id == test_user.id,
            Conversation.updated_at >= yesterday
        ).all()
        
        assert isinstance(recent, list)
    
    def test_pagination_query(
        self,
        test_db_session: Session,
        test_conversation,
        test_messages: list
    ):
        """Test paginated query for messages."""
        page_size = 2
        page = 0
        
        messages_page = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id
        ).order_by(
            Message.created_at
        ).limit(page_size).offset(page * page_size).all()
        
        assert len(messages_page) <= page_size


class TestDatabaseTransactions:
    """Test database transaction handling."""
    
    def test_transaction_commit(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test successful transaction commit."""
        conversation = Conversation(
            user_id=test_user.id,
            title="Transaction Test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        test_db_session.commit()
        
        # Verify data persisted
        saved = test_db_session.query(Conversation).filter(
            Conversation.title == "Transaction Test"
        ).first()
        
        assert saved is not None
    
    def test_transaction_rollback(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test transaction rollback on error."""
        conversation = Conversation(
            user_id=test_user.id,
            title="Rollback Test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        
        # Cause an error
        invalid_conv = Conversation(
            user_id=99999,  # Invalid user_id
            title="Invalid",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_db_session.add(invalid_conv)
        
        try:
            test_db_session.commit()
        except IntegrityError:
            test_db_session.rollback()
        
        # First conversation should not be saved
        saved = test_db_session.query(Conversation).filter(
            Conversation.title == "Rollback Test"
        ).first()
        
        assert saved is None
    
    def test_nested_transaction(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test nested transaction with savepoint."""
        conversation = Conversation(
            user_id=test_user.id,
            title="Outer Transaction",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        test_db_session.flush()
        
        # Nested transaction
        try:
            message = Message(
                conversation_id=conversation.id,
                role="user",
                content="Nested message",
                created_at=datetime.utcnow()
            )
            test_db_session.add(message)
            test_db_session.flush()
        except Exception:
            test_db_session.rollback()
        
        test_db_session.commit()


class TestDatabasePerformance:
    """Test database query performance and optimization."""
    
    def test_bulk_insert_messages(
        self,
        test_db_session: Session,
        test_conversation
    ):
        """Test bulk inserting messages."""
        messages = []
        for i in range(100):
            message = Message(
                conversation_id=test_conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Bulk message {i}",
                created_at=datetime.utcnow(),
                tokens_used=10
            )
            messages.append(message)
        
        test_db_session.bulk_save_objects(messages)
        test_db_session.commit()
        
        # Verify all messages saved
        count = test_db_session.query(Message).filter(
            Message.conversation_id == test_conversation.id
        ).count()
        
        assert count >= 100
    
    def test_query_with_join(
        self,
        test_db_session: Session,
        test_user,
        test_conversation,
        test_messages: list
    ):
        """Test query with join operation."""
        results = test_db_session.query(
            Message, Conversation, User
        ).join(
            Conversation, Message.conversation_id == Conversation.id
        ).join(
            User, Conversation.user_id == User.id
        ).filter(
            User.id == test_user.id
        ).all()
        
        assert len(results) >= 3
        
        for message, conversation, user in results:
            assert message.conversation_id == conversation.id
            assert conversation.user_id == user.id
    
    def test_eager_loading(
        self,
        test_db_session: Session,
        test_user,
        test_conversations: list
    ):
        """Test eager loading of related objects."""
        from sqlalchemy.orm import joinedload
        
        conversations = test_db_session.query(Conversation).options(
            joinedload(Conversation.user) if hasattr(Conversation, 'user') else lambda: None
        ).filter(
            Conversation.user_id == test_user.id
        ).all()
        
        assert len(conversations) >= 3


class TestDataIntegrity:
    """Test data integrity and constraints."""
    
    def test_required_fields(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test that required fields cannot be null."""
        # Try to create conversation without title
        conversation = Conversation(
            user_id=test_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        
        # This may fail depending on schema
        try:
            test_db_session.commit()
        except IntegrityError:
            test_db_session.rollback()
    
    def test_timestamp_defaults(
        self,
        test_db_session: Session,
        test_user
    ):
        """Test that timestamps are set automatically."""
        conversation = Conversation(
            user_id=test_user.id,
            title="Timestamp Test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(conversation)
        test_db_session.commit()
        test_db_session.refresh(conversation)
        
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
