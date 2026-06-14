"""
Unit tests for database models.

Tests model creation, validation, relationships, and methods.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.models import (
    User,
    UserPreferences,
    UserSession,
    Conversation,
    Message,
    ConversationShare,
    ConversationExport,
)
from tests.conftest import create_test_user, create_test_conversation, create_test_message

pytestmark = pytest.mark.unit

# ============================================================================
# User Model Tests
# ============================================================================


class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, db_session: Session):
        """Test basic user creation."""
        user = User(
            username="newuser",
            email="newuser@example.com",
            hashed_password="hashed_password_123",
            full_name="New User",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_unique_username(self, db_session: Session, test_user: User):
        """Test that usernames must be unique."""
        duplicate_user = User(
            username=test_user.username, email="different@example.com", hashed_password="password"
        )
        db_session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_unique_email(self, db_session: Session, test_user: User):
        """Test that emails must be unique."""
        duplicate_user = User(
            username="differentuser", email=test_user.email, hashed_password="password"
        )
        db_session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_conversations_relationship(self, db_session: Session, test_user: User):
        """Test user-conversations relationship."""
        # Create conversations for user
        for i in range(3):
            conv = Conversation(user_id=test_user.id, title=f"Conversation {i}")
            db_session.add(conv)

        db_session.commit()
        db_session.refresh(test_user)

        assert len(test_user.conversations) == 3
        assert all(conv.user_id == test_user.id for conv in test_user.conversations)

    def test_user_preferences_relationship(self, db_session: Session, test_user: User):
        """Test user-preferences relationship."""
        prefs = UserPreferences(
            user_id=test_user.id, theme="dark", language="es", model_preference="gpt-4"
        )
        db_session.add(prefs)
        db_session.commit()
        db_session.refresh(test_user)

        assert test_user.preferences is not None
        assert test_user.preferences.theme == "dark"
        assert test_user.preferences.language == "es"

    def test_user_repr(self, test_user: User):
        """Test user string representation."""
        repr_str = repr(test_user)
        assert "User" in repr_str
        assert test_user.username in repr_str
        assert test_user.email in repr_str


# ============================================================================
# UserSession Model Tests
# ============================================================================


class TestUserSessionModel:
    """Test UserSession model functionality."""

    def test_create_session(self, db_session: Session, test_user: User):
        """Test session creation."""
        session = UserSession(
            user_id=test_user.id,
            session_token="test_token_123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            device_info={"platform": "web", "browser": "Chrome"},
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.session_token == "test_token_123"
        assert session.is_active is True
        assert session.device_info["platform"] == "web"

    def test_session_unique_token(self, db_session: Session, test_user: User):
        """Test session tokens must be unique."""
        token = "duplicate_token"

        session1 = UserSession(user_id=test_user.id, session_token=token)
        db_session.add(session1)
        db_session.commit()

        session2 = UserSession(user_id=test_user.id, session_token=token)
        db_session.add(session2)

        with pytest.raises(IntegrityError):
            db_session.commit()


# ============================================================================
# Conversation Model Tests
# ============================================================================


class TestConversationModel:
    """Test Conversation model functionality."""

    def test_create_conversation(self, db_session: Session, test_user: User):
        """Test basic conversation creation."""
        conv = Conversation(
            user_id=test_user.id,
            title="Test Conversation",
            system_prompt="You are helpful.",
            model_name="gpt-4-turbo-preview",
            temperature=0.7,
            max_tokens=4000,
            tags=["test", "sample"],
        )
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        assert conv.id is not None
        assert conv.user_id == test_user.id
        assert conv.title == "Test Conversation"
        assert conv.temperature == 0.7
        assert conv.is_archived is False
        assert conv.is_pinned is False
        assert conv.is_deleted is False
        assert conv.tags == ["test", "sample"]
        assert conv.message_count == 0
        assert conv.total_tokens == 0
        assert conv.total_cost == 0.0

    def test_conversation_soft_delete(self, db_session: Session, test_conversation: Conversation):
        """Test conversation soft delete."""
        test_conversation.is_deleted = True
        test_conversation.deleted_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(test_conversation)

        assert test_conversation.is_deleted is True
        assert test_conversation.deleted_at is not None

    def test_conversation_messages_relationship(
        self, db_session: Session, test_conversation: Conversation
    ):
        """Test conversation-messages relationship."""
        # Add messages
        for i in range(5):
            msg = Message(
                conversation_id=test_conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )
            db_session.add(msg)

        db_session.commit()
        db_session.refresh(test_conversation)

        assert len(test_conversation.messages) == 5
        # Messages should be ordered by created_at
        assert all(
            msg.conversation_id == test_conversation.id for msg in test_conversation.messages
        )

    def test_conversation_cascade_delete(
        self, db_session: Session, test_conversation: Conversation
    ):
        """Test that deleting conversation deletes messages."""
        # Add messages
        for i in range(3):
            msg = Message(conversation_id=test_conversation.id, role="user", content=f"Message {i}")
            db_session.add(msg)
        db_session.commit()

        # Delete conversation
        db_session.delete(test_conversation)
        db_session.commit()

        # Messages should be deleted
        messages = (
            db_session.query(Message).filter(Message.conversation_id == test_conversation.id).all()
        )
        assert len(messages) == 0

    def test_conversation_metadata(self, db_session: Session, test_conversation: Conversation):
        """Test conversation metadata storage."""
        test_conversation.metadata = {"custom_field": "value", "nested": {"data": [1, 2, 3]}}
        db_session.commit()
        db_session.refresh(test_conversation)

        assert test_conversation.metadata["custom_field"] == "value"
        assert test_conversation.metadata["nested"]["data"] == [1, 2, 3]

    def test_conversation_repr(self, test_conversation: Conversation):
        """Test conversation string representation."""
        repr_str = repr(test_conversation)
        assert "Conversation" in repr_str
        assert test_conversation.title in repr_str


# ============================================================================
# Message Model Tests
# ============================================================================


class TestMessageModel:
    """Test Message model functionality."""

    def test_create_message(self, db_session: Session, test_conversation: Conversation):
        """Test basic message creation."""
        msg = Message(
            conversation_id=test_conversation.id,
            role="user",
            content="Hello, world!",
            tokens_used=3,
            model_name="gpt-4-turbo-preview",
            finish_reason="stop",
            latency_ms=250,
            metadata={"source": "web"},
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.id is not None
        assert msg.conversation_id == test_conversation.id
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.tokens_used == 3
        assert msg.latency_ms == 250
        assert msg.metadata["source"] == "web"
        assert msg.version == 1

    def test_message_threading(self, db_session: Session, test_conversation: Conversation):
        """Test message parent-child relationship (threading)."""
        parent_msg = Message(
            conversation_id=test_conversation.id, role="assistant", content="Original response"
        )
        db_session.add(parent_msg)
        db_session.commit()
        db_session.refresh(parent_msg)

        # Create child message (alternative response)
        child_msg = Message(
            conversation_id=test_conversation.id,
            role="assistant",
            content="Alternative response",
            parent_message_id=parent_msg.id,
            version=2,
        )
        db_session.add(child_msg)
        db_session.commit()
        db_session.refresh(parent_msg)

        assert len(parent_msg.child_messages) == 1
        assert parent_msg.child_messages[0].content == "Alternative response"
        assert child_msg.parent_message_id == parent_msg.id

    def test_message_cost_tracking(self, db_session: Session, test_conversation: Conversation):
        """Test message cost tracking."""
        msg = Message(
            conversation_id=test_conversation.id,
            role="assistant",
            content="Response",
            tokens_used=100,
            cost=0.003,  # $0.003
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.cost == 0.003
        assert msg.tokens_used == 100

    def test_message_error_tracking(self, db_session: Session, test_conversation: Conversation):
        """Test message error tracking."""
        msg = Message(
            conversation_id=test_conversation.id,
            role="assistant",
            content="",
            error="API rate limit exceeded",
            finish_reason="error",
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.error == "API rate limit exceeded"
        assert msg.finish_reason == "error"

    def test_message_repr(self, test_message: Message):
        """Test message string representation."""
        repr_str = repr(test_message)
        assert "Message" in repr_str
        assert test_message.role in repr_str


# ============================================================================
# ConversationShare Model Tests
# ============================================================================


class TestConversationShareModel:
    """Test ConversationShare model functionality."""

    def test_create_share(
        self, db_session: Session, test_conversation: Conversation, test_user: User
    ):
        """Test share creation."""
        share = ConversationShare(
            conversation_id=test_conversation.id,
            share_token="unique_token_123",
            shared_by=test_user.id,
            is_public=True,
            can_edit=False,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(share)
        db_session.commit()
        db_session.refresh(share)

        assert share.id is not None
        assert share.share_token == "unique_token_123"
        assert share.is_public is True
        assert share.can_edit is False
        assert share.view_count == 0

    def test_share_unique_token(
        self, db_session: Session, test_conversation: Conversation, test_user: User
    ):
        """Test share tokens must be unique."""
        token = "duplicate_share_token"

        share1 = ConversationShare(
            conversation_id=test_conversation.id, share_token=token, shared_by=test_user.id
        )
        db_session.add(share1)
        db_session.commit()

        share2 = ConversationShare(
            conversation_id=test_conversation.id, share_token=token, shared_by=test_user.id
        )
        db_session.add(share2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_share_with_specific_user(
        self,
        db_session: Session,
        test_conversation: Conversation,
        test_user: User,
        test_user2: User,
    ):
        """Test sharing with specific user."""
        share = ConversationShare(
            conversation_id=test_conversation.id,
            share_token="private_share_token",
            shared_by=test_user.id,
            shared_with=test_user2.id,
            is_public=False,
            can_edit=True,
        )
        db_session.add(share)
        db_session.commit()
        db_session.refresh(share)

        assert share.shared_with == test_user2.id
        assert share.is_public is False
        assert share.can_edit is True

    def test_share_expiration(
        self, db_session: Session, test_conversation: Conversation, test_user: User
    ):
        """Test share expiration."""
        # Create expired share
        share = ConversationShare(
            conversation_id=test_conversation.id,
            share_token="expired_token",
            shared_by=test_user.id,
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
        )
        db_session.add(share)
        db_session.commit()
        db_session.refresh(share)

        assert share.expires_at < datetime.utcnow()


# ============================================================================
# ConversationExport Model Tests
# ============================================================================


class TestConversationExportModel:
    """Test ConversationExport model functionality."""

    def test_create_export(
        self, db_session: Session, test_conversation: Conversation, test_user: User
    ):
        """Test export creation."""
        export = ConversationExport(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            export_format="pdf",
            file_path="/exports/conv_123.pdf",
            file_size=1024000,  # 1MB
            status="completed",
        )
        db_session.add(export)
        db_session.commit()
        db_session.refresh(export)

        assert export.id is not None
        assert export.export_format == "pdf"
        assert export.status == "completed"
        assert export.file_size == 1024000

    def test_export_status_tracking(
        self, db_session: Session, test_conversation: Conversation, test_user: User
    ):
        """Test export status transitions."""
        export = ConversationExport(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            export_format="markdown",
            status="pending",
        )
        db_session.add(export)
        db_session.commit()

        # Update to processing
        export.status = "processing"
        db_session.commit()

        # Update to completed
        export.status = "completed"
        export.completed_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(export)

        assert export.status == "completed"
        assert export.completed_at is not None

    def test_export_error_handling(
        self, db_session: Session, test_conversation: Conversation, test_user: User
    ):
        """Test export error tracking."""
        export = ConversationExport(
            conversation_id=test_conversation.id,
            user_id=test_user.id,
            export_format="json",
            status="failed",
            error_message="Disk space full",
        )
        db_session.add(export)
        db_session.commit()
        db_session.refresh(export)

        assert export.status == "failed"
        assert export.error_message == "Disk space full"


# ============================================================================
# Model Validation Tests
# ============================================================================


class TestModelValidation:
    """Test model validation and constraints."""

    def test_required_fields(self, db_session: Session):
        """Test that required fields are enforced."""
        # Conversation without required fields should fail
        with pytest.raises(Exception):  # Will raise IntegrityError or similar
            conv = Conversation()
            db_session.add(conv)
            db_session.commit()

    def test_default_values(self, db_session: Session, test_user: User):
        """Test that default values are applied."""
        conv = Conversation(user_id=test_user.id, title="Test")
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        # Check defaults
        assert conv.is_archived is False
        assert conv.is_pinned is False
        assert conv.is_deleted is False
        assert conv.message_count == 0
        assert conv.total_tokens == 0
        assert conv.total_cost == 0.0
        assert conv.extra_metadata == {}
        assert conv.tags == []

    def test_json_field_defaults(self, db_session: Session, test_user: User):
        """Test JSON field default values."""
        conv = Conversation(user_id=test_user.id, title="Test")
        db_session.add(conv)
        db_session.commit()
        db_session.refresh(conv)

        # JSON fields should have dict/list defaults
        assert isinstance(conv.extra_metadata, dict)
        assert isinstance(conv.tags, list)
