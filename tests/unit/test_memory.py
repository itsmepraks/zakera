"""
Unit tests for the ConversationMemory system.

Tests memory management, database integration, and token handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from src.model.memory import ConversationMemory, ConversationTurn
from src.api.models import Conversation, Message
from tests.conftest import create_test_conversation, create_test_message

pytestmark = pytest.mark.unit

# ============================================================================
# ConversationMemory Basic Tests
# ============================================================================


class TestConversationMemoryBasics:
    """Test basic ConversationMemory functionality."""

    def test_create_memory(self):
        """Test basic memory creation."""
        memory = ConversationMemory(max_tokens=4000, max_turns=50, system_prompt="You are helpful.")

        assert memory.max_tokens == 4000
        assert memory.max_turns == 50
        assert memory.system_prompt == "You are helpful."
        assert len(memory.turns) == 0

    def test_add_turn(self):
        """Test adding conversation turns."""
        memory = ConversationMemory()

        memory.add_turn("user", "Hello!")
        memory.add_turn("assistant", "Hi there!")

        assert len(memory.turns) == 2
        assert memory.turns[0].role == "user"
        assert memory.turns[0].content == "Hello!"
        assert memory.turns[1].role == "assistant"
        assert memory.turns[1].content == "Hi there!"

    def test_add_turn_with_metadata(self):
        """Test adding turns with metadata."""
        memory = ConversationMemory()

        metadata = {"source": "web", "timestamp": "2026-01-01"}
        memory.add_turn("user", "Test message", metadata=metadata)

        assert memory.turns[0].metadata == metadata

    def test_max_turns_limit(self):
        """Test that max_turns limit is enforced."""
        memory = ConversationMemory(max_turns=5)

        # Add more than max_turns
        for i in range(10):
            memory.add_turn("user", f"Message {i}")

        # Should only keep last 5
        assert len(memory.turns) == 5
        assert memory.turns[0].content == "Message 5"
        assert memory.turns[-1].content == "Message 9"

    def test_clear_memory(self):
        """Test clearing conversation memory."""
        memory = ConversationMemory()
        memory.add_turn("user", "Test")
        memory.add_turn("assistant", "Response")

        memory.clear()

        assert len(memory.turns) == 0


# ============================================================================
# Message Formatting Tests
# ============================================================================


class TestMessageFormatting:
    """Test message formatting for API calls."""

    def test_get_messages_basic(self):
        """Test basic message retrieval."""
        memory = ConversationMemory(system_prompt="You are helpful.")
        memory.add_turn("user", "Hello")
        memory.add_turn("assistant", "Hi")

        messages = memory.get_messages()

        assert len(messages) == 3  # system + 2 turns
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful."
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_get_messages_without_system(self):
        """Test message retrieval without system prompt."""
        memory = ConversationMemory()
        memory.add_turn("user", "Hello")

        messages = memory.get_messages(include_system=False)

        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_get_messages_token_limit(self):
        """Test that messages respect token limit."""
        memory = ConversationMemory(max_tokens=100)

        # Add many messages
        for i in range(10):
            memory.add_turn("user", f"This is a test message number {i} " * 10)

        messages = memory.get_messages()

        # Should fit within token limit
        token_count = memory._count_tokens(messages)
        assert token_count <= memory.max_tokens


# ============================================================================
# Token Counting Tests
# ============================================================================


class TestTokenCounting:
    """Test token counting functionality."""

    def test_count_tokens_simple(self):
        """Test basic token counting."""
        memory = ConversationMemory()

        messages = [{"role": "user", "content": "Hello world"}]

        count = memory._count_tokens(messages)
        assert count > 0
        assert isinstance(count, int)

    def test_count_tokens_multiple_messages(self):
        """Test counting tokens across multiple messages."""
        memory = ConversationMemory()

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        count = memory._count_tokens(messages)

        # Should account for all messages plus overhead
        assert count > 10


# ============================================================================
# Summary Tests
# ============================================================================


class TestConversationSummary:
    """Test conversation summary generation."""

    def test_get_summary_empty(self):
        """Test summary of empty conversation."""
        memory = ConversationMemory()

        summary = memory.get_summary()

        assert summary["total_turns"] == 0
        assert summary["user_turns"] == 0
        assert summary["assistant_turns"] == 0
        assert summary["first_turn"] is None
        assert summary["last_turn"] is None

    def test_get_summary_with_messages(self):
        """Test summary with messages."""
        memory = ConversationMemory()
        memory.add_turn("user", "Hello")
        memory.add_turn("assistant", "Hi")
        memory.add_turn("user", "How are you?")

        summary = memory.get_summary()

        assert summary["total_turns"] == 3
        assert summary["user_turns"] == 2
        assert summary["assistant_turns"] == 1
        assert summary["first_turn"] is not None
        assert summary["last_turn"] is not None
        assert summary["estimated_tokens"] > 0


# ============================================================================
# Export/Import Tests
# ============================================================================


class TestExportImport:
    """Test conversation export and import."""

    def test_export_conversation(self):
        """Test exporting conversation data."""
        memory = ConversationMemory()
        memory.add_turn("user", "Hello", metadata={"source": "web"})
        memory.add_turn("assistant", "Hi there!")

        exported = memory.export()

        assert len(exported) == 2
        assert exported[0]["role"] == "user"
        assert exported[0]["content"] == "Hello"
        assert exported[0]["metadata"] == {"source": "web"}
        assert "timestamp" in exported[0]

    def test_import_conversation(self):
        """Test importing conversation from export."""
        export_data = [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2026-01-01T12:00:00",
                "metadata": {"test": "data"},
            },
            {
                "role": "assistant",
                "content": "Hi",
                "timestamp": "2026-01-01T12:00:01",
                "metadata": {},
            },
        ]

        memory = ConversationMemory.from_export(
            export_data, max_tokens=4000, system_prompt="Test prompt"
        )

        assert len(memory.turns) == 2
        assert memory.turns[0].content == "Hello"
        assert memory.turns[0].metadata["test"] == "data"
        assert memory.system_prompt == "Test prompt"


# ============================================================================
# Database Integration Tests (Mocked)
# ============================================================================


class TestDatabaseIntegration:
    """Test database integration with mocking."""

    def test_save_to_db_without_db(self):
        """Test that save without db session doesn't crash."""
        memory = ConversationMemory()

        # Should not raise error
        memory.add_turn("user", "Test")
        assert len(memory.turns) == 1

    def test_load_from_db(self, db_session: Session, test_conversation: Conversation):
        """Test loading conversation from database."""
        # Add messages to conversation
        for i in range(3):
            msg = Message(
                conversation_id=test_conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )
            db_session.add(msg)
        db_session.commit()

        # Load into memory
        memory = ConversationMemory(conversation_id=test_conversation.id, db=db_session)

        # Should load messages (excluding system messages)
        assert len(memory.turns) == 3
        assert memory.system_prompt == "You are a helpful AI assistant."

    def test_save_to_db(self, db_session: Session, test_conversation: Conversation):
        """Test saving messages to database."""
        memory = ConversationMemory(conversation_id=test_conversation.id, db=db_session)

        # Add turn - should save to database
        memory.add_turn("user", "Test message")

        # Check database
        messages = (
            db_session.query(Message).filter(Message.conversation_id == test_conversation.id).all()
        )

        assert len(messages) == 1
        assert messages[0].content == "Test message"
        assert messages[0].role == "user"

    def test_from_conversation_id(self, db_session: Session, test_conversation: Conversation):
        """Test factory method for loading from conversation_id."""
        # Add messages
        create_test_message(db_session, test_conversation, "user", "Hello")
        create_test_message(db_session, test_conversation, "assistant", "Hi")

        # Load using factory method
        memory = ConversationMemory.from_conversation_id(
            conversation_id=test_conversation.id, db=db_session
        )

        assert len(memory.turns) == 2
        assert memory.conversation_id == test_conversation.id

    def test_update_conversation_stats(self, db_session: Session, test_conversation: Conversation):
        """Test updating conversation statistics."""
        memory = ConversationMemory(conversation_id=test_conversation.id, db=db_session)

        # Update stats
        memory.update_conversation_stats(total_tokens=150, total_cost=0.003)

        # Check database
        db_session.refresh(test_conversation)
        assert test_conversation.total_tokens == 150
        assert test_conversation.total_cost == 0.003

    def test_conversation_metadata_update(
        self, db_session: Session, test_conversation: Conversation
    ):
        """Test that conversation metadata is updated on message add."""
        initial_count = test_conversation.message_count or 0

        memory = ConversationMemory(conversation_id=test_conversation.id, db=db_session)

        memory.add_turn("user", "New message")

        # Conversation should be updated
        db_session.refresh(test_conversation)
        assert test_conversation.message_count == initial_count + 1


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content(self):
        """Test adding message with empty content."""
        memory = ConversationMemory()
        memory.add_turn("user", "")

        assert len(memory.turns) == 0

    def test_very_long_message(self):
        """Test handling very long messages."""
        memory = ConversationMemory(max_tokens=100)

        long_message = "word " * 1000  # Very long message
        memory.add_turn("user", long_message)

        messages = memory.get_messages()
        # Should handle without crashing
        assert len(messages) > 0

    def test_special_characters(self):
        """Test handling special characters."""
        memory = ConversationMemory()

        special_content = "Hello! 你好 🌟 <script>alert('test')</script>"
        memory.add_turn("user", special_content)

        assert memory.turns[0].content == special_content

    def test_null_metadata(self):
        """Test handling null metadata."""
        memory = ConversationMemory()
        memory.add_turn("user", "Test", metadata=None)

        assert memory.turns[0].metadata == {}

    def test_invalid_conversation_id(self, db_session: Session):
        """Test loading from invalid conversation_id."""
        memory = ConversationMemory(conversation_id="invalid-id-123", db=db_session)

        # Should handle gracefully
        assert len(memory.turns) == 0

    def test_concurrent_updates(self, db_session: Session, test_conversation: Conversation):
        """Test concurrent memory updates."""
        memory1 = ConversationMemory(conversation_id=test_conversation.id, db=db_session)
        memory2 = ConversationMemory(conversation_id=test_conversation.id, db=db_session)

        # Both add messages
        memory1.add_turn("user", "From memory 1")
        memory2.add_turn("user", "From memory 2")

        # Both should save without errors
        messages = (
            db_session.query(Message).filter(Message.conversation_id == test_conversation.id).all()
        )

        assert len(messages) == 2


# ============================================================================
# ConversationTurn Tests
# ============================================================================


class TestConversationTurn:
    """Test ConversationTurn dataclass."""

    def test_create_turn(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(role="user", content="Hello", metadata={"source": "test"})

        assert turn.role == "user"
        assert turn.content == "Hello"
        assert turn.metadata["source"] == "test"
        assert turn.timestamp is not None

    def test_turn_timestamp_auto(self):
        """Test automatic timestamp generation."""
        turn = ConversationTurn(role="user", content="Test")

        # Should have ISO format timestamp
        assert "T" in turn.timestamp
        assert "Z" in turn.timestamp or "+" in turn.timestamp or "-" in turn.timestamp

    def test_turn_default_metadata(self):
        """Test default empty metadata."""
        turn = ConversationTurn(role="user", content="Test")

        assert turn.metadata == {}


# ============================================================================
# Performance Tests
# ============================================================================


class TestMemoryPerformance:
    """Test memory system performance characteristics."""

    @pytest.mark.slow
    def test_large_conversation(self):
        """Test handling large conversations."""
        memory = ConversationMemory(max_tokens=4000, max_turns=1000)

        # Add many messages
        for i in range(500):
            memory.add_turn("user", f"Message {i}")
            memory.add_turn("assistant", f"Response {i}")

        # Should handle efficiently
        messages = memory.get_messages()
        assert len(messages) > 0

        summary = memory.get_summary()
        assert summary["total_turns"] <= 1000

    @pytest.mark.slow
    def test_token_counting_performance(self):
        """Test token counting performance."""
        memory = ConversationMemory()

        # Create large message set
        large_messages = [
            {"role": "user", "content": "This is a test message " * 50} for _ in range(100)
        ]

        # Should count efficiently
        count = memory._count_tokens(large_messages)
        assert count > 0
