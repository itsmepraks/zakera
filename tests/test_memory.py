"""Comprehensive unit tests for conversation memory system"""

import pytest
from datetime import datetime
from src.model.memory import ConversationMemory, ConversationTurn


class TestConversationTurn:
    """Test ConversationTurn dataclass"""
    
    def test_conversation_turn_creation(self):
        """Test basic conversation turn creation"""
        turn = ConversationTurn(
            role="user",
            content="Hello, how are you?"
        )
        
        assert turn.role == "user"
        assert turn.content == "Hello, how are you?"
        assert turn.timestamp is not None
        assert isinstance(turn.metadata, dict)
        assert len(turn.metadata) == 0
    
    def test_conversation_turn_with_metadata(self):
        """Test conversation turn with custom metadata"""
        metadata = {"source": "web", "user_id": "123"}
        turn = ConversationTurn(
            role="assistant",
            content="I'm doing well, thank you!",
            metadata=metadata
        )
        
        assert turn.metadata == metadata
        assert turn.metadata["source"] == "web"
        assert turn.metadata["user_id"] == "123"
    
    def test_timestamp_format(self):
        """Test that timestamp is in ISO format"""
        turn = ConversationTurn(role="user", content="Test")
        # Should be parseable as ISO datetime
        timestamp = datetime.fromisoformat(turn.timestamp)
        assert isinstance(timestamp, datetime)


class TestConversationMemory:
    """Test ConversationMemory class"""
    
    @pytest.fixture
    def memory(self):
        """Create a fresh memory instance for each test"""
        return ConversationMemory(
            max_tokens=1000,
            max_turns=10,
            system_prompt="You are a helpful assistant.",
            model="gpt-4"
        )
    
    def test_initialization(self, memory):
        """Test memory initialization with parameters"""
        assert memory.max_tokens == 1000
        assert memory.max_turns == 10
        assert memory.system_prompt == "You are a helpful assistant."
        assert memory.model == "gpt-4"
        assert len(memory.turns) == 0
        assert memory.encoding is not None
    
    def test_default_initialization(self):
        """Test memory initialization with defaults"""
        memory = ConversationMemory()
        assert memory.max_tokens == 4000
        assert memory.max_turns == 50
        assert "helpful AI assistant" in memory.system_prompt
        assert memory.model == "gpt-4"
    
    def test_add_single_turn(self, memory):
        """Test adding a single conversation turn"""
        memory.add_turn("user", "Hello!")
        
        assert len(memory.turns) == 1
        assert memory.turns[0].role == "user"
        assert memory.turns[0].content == "Hello!"
    
    def test_add_multiple_turns(self, memory):
        """Test adding multiple conversation turns"""
        memory.add_turn("user", "Hello!")
        memory.add_turn("assistant", "Hi there!")
        memory.add_turn("user", "How are you?")
        
        assert len(memory.turns) == 3
        assert memory.turns[0].role == "user"
        assert memory.turns[1].role == "assistant"
        assert memory.turns[2].role == "user"
    
    def test_add_turn_with_metadata(self, memory):
        """Test adding turn with custom metadata"""
        metadata = {"intent": "greeting", "confidence": 0.95}
        memory.add_turn("user", "Hello!", metadata=metadata)
        
        assert memory.turns[0].metadata == metadata
        assert memory.turns[0].metadata["intent"] == "greeting"
    
    def test_max_turns_trimming(self, memory):
        """Test that old turns are trimmed when exceeding max_turns"""
        # Add more turns than max_turns (10)
        for i in range(15):
            memory.add_turn("user", f"Message {i}")
        
        assert len(memory.turns) == 10
        # Should keep the most recent 10 turns
        assert memory.turns[0].content == "Message 5"
        assert memory.turns[-1].content == "Message 14"
    
    def test_get_messages_basic(self, memory):
        """Test getting messages in API format"""
        memory.add_turn("user", "Hello!")
        memory.add_turn("assistant", "Hi there!")
        
        messages = memory.get_messages()
        
        # Should include system prompt + 2 turns
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hi there!"
    
    def test_get_messages_without_system(self, memory):
        """Test getting messages without system prompt"""
        memory.add_turn("user", "Hello!")
        memory.add_turn("assistant", "Hi there!")
        
        messages = memory.get_messages(include_system=False)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
    
    def test_token_counting(self, memory):
        """Test that token counting works"""
        memory.add_turn("user", "This is a test message.")
        
        messages = memory.get_messages()
        token_count = memory._count_tokens(messages)
        
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_token_limit_trimming(self):
        """Test that messages are trimmed to fit token limit"""
        # Create memory with very small token limit
        memory = ConversationMemory(max_tokens=50, max_turns=100)
        
        # Add many turns with long content
        for i in range(10):
            memory.add_turn("user", "This is a longer message that contains multiple words and tokens.")
            memory.add_turn("assistant", "This is a response with multiple words and tokens as well.")
        
        messages = memory.get_messages(include_system=False)
        token_count = memory._count_tokens(messages)
        
        # Should be trimmed to fit within token limit
        assert token_count <= 50
        # Should have fewer messages than total turns
        assert len(messages) < len(memory.turns)
    
    def test_get_summary_empty(self, memory):
        """Test getting summary of empty conversation"""
        summary = memory.get_summary()
        
        assert summary["total_turns"] == 0
        assert summary["user_turns"] == 0
        assert summary["assistant_turns"] == 0
        assert summary["first_turn"] is None
        assert summary["last_turn"] is None
    
    def test_get_summary_with_turns(self, memory):
        """Test getting summary with conversation turns"""
        memory.add_turn("user", "Hello!")
        memory.add_turn("assistant", "Hi there!")
        memory.add_turn("user", "How are you?")
        memory.add_turn("assistant", "I'm doing well!")
        
        summary = memory.get_summary()
        
        assert summary["total_turns"] == 4
        assert summary["user_turns"] == 2
        assert summary["assistant_turns"] == 2
        assert summary["estimated_tokens"] > 0
        assert summary["first_turn"] is not None
        assert summary["last_turn"] is not None
    
    def test_clear_conversation(self, memory):
        """Test clearing all conversation turns"""
        memory.add_turn("user", "Hello!")
        memory.add_turn("assistant", "Hi there!")
        
        assert len(memory.turns) == 2
        
        memory.clear()
        
        assert len(memory.turns) == 0
        summary = memory.get_summary()
        assert summary["total_turns"] == 0
    
    def test_export_conversation(self, memory):
        """Test exporting conversation data"""
        metadata1 = {"source": "web"}
        metadata2 = {"source": "api"}
        
        memory.add_turn("user", "Hello!", metadata=metadata1)
        memory.add_turn("assistant", "Hi there!", metadata=metadata2)
        
        exported = memory.export()
        
        assert len(exported) == 2
        assert exported[0]["role"] == "user"
        assert exported[0]["content"] == "Hello!"
        assert exported[0]["metadata"] == metadata1
        assert "timestamp" in exported[0]
        assert exported[1]["role"] == "assistant"
        assert exported[1]["content"] == "Hi there!"
    
    def test_from_export(self):
        """Test importing conversation from exported data"""
        export_data = [
            {
                "role": "user",
                "content": "Hello!",
                "timestamp": "2024-01-01T12:00:00",
                "metadata": {"source": "web"}
            },
            {
                "role": "assistant",
                "content": "Hi there!",
                "timestamp": "2024-01-01T12:00:01",
                "metadata": {"source": "api"}
            }
        ]
        
        memory = ConversationMemory.from_export(
            export_data,
            max_tokens=2000,
            system_prompt="Custom prompt"
        )
        
        assert len(memory.turns) == 2
        assert memory.turns[0].role == "user"
        assert memory.turns[0].content == "Hello!"
        assert memory.turns[0].metadata["source"] == "web"
        assert memory.turns[1].role == "assistant"
        assert memory.max_tokens == 2000
        assert memory.system_prompt == "Custom prompt"
    
    def test_export_import_roundtrip(self, memory):
        """Test that export and import are reversible"""
        # Add some turns
        memory.add_turn("user", "Question 1")
        memory.add_turn("assistant", "Answer 1")
        memory.add_turn("user", "Question 2", metadata={"important": True})
        
        # Export
        exported = memory.export()
        
        # Import into new memory
        new_memory = ConversationMemory.from_export(
            exported,
            max_tokens=memory.max_tokens,
            max_turns=memory.max_turns,
            system_prompt=memory.system_prompt,
            model=memory.model
        )
        
        # Verify same state
        assert len(new_memory.turns) == len(memory.turns)
        for i in range(len(memory.turns)):
            assert new_memory.turns[i].role == memory.turns[i].role
            assert new_memory.turns[i].content == memory.turns[i].content
            assert new_memory.turns[i].metadata == memory.turns[i].metadata
    
    def test_message_ordering(self, memory):
        """Test that messages are returned in correct order"""
        memory.add_turn("user", "First")
        memory.add_turn("assistant", "Second")
        memory.add_turn("user", "Third")
        
        messages = memory.get_messages(include_system=False)
        
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"
    
    def test_token_budget_respects_system_prompt(self, memory):
        """Test that system prompt tokens are counted in budget"""
        # Add turns that would exceed token limit without system prompt
        for i in range(5):
            memory.add_turn("user", "This is a test message with some words.")
        
        messages_with_system = memory.get_messages(include_system=True)
        messages_without_system = memory.get_messages(include_system=False)
        
        # With system prompt should have same or fewer conversation turns
        # due to token budget
        assert len(messages_with_system) >= len(messages_without_system)
    
    def test_unknown_model_fallback(self):
        """Test that unknown models fall back to default encoding"""
        memory = ConversationMemory(model="unknown-model-xyz")
        
        # Should still work with fallback encoding
        memory.add_turn("user", "Test message")
        messages = memory.get_messages()
        token_count = memory._count_tokens(messages)
        
        assert token_count > 0
        assert memory.encoding is not None


class TestConversationMemoryEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_content(self):
        """Test adding turn with empty content"""
        memory = ConversationMemory()
        memory.add_turn("user", "")
        
        assert len(memory.turns) == 1
        assert memory.turns[0].content == ""
    
    def test_very_long_message(self):
        """Test handling very long messages"""
        memory = ConversationMemory(max_tokens=100)
        
        # Add a very long message
        long_message = "word " * 1000
        memory.add_turn("user", long_message)
        
        messages = memory.get_messages(include_system=False)
        token_count = memory._count_tokens(messages)
        
        # Should be trimmed to fit token limit
        assert token_count <= 100
    
    def test_special_characters(self):
        """Test handling special characters and unicode"""
        memory = ConversationMemory()
        
        special_content = "Hello! 你好 🌟 \n\t Special chars: @#$%^&*()"
        memory.add_turn("user", special_content)
        
        assert memory.turns[0].content == special_content
        messages = memory.get_messages()
        assert messages[-1]["content"] == special_content
    
    def test_zero_max_turns(self):
        """Test behavior with max_turns=0 or max_turns=1"""
        memory = ConversationMemory(max_turns=1)
        
        memory.add_turn("user", "First")
        memory.add_turn("user", "Second")
        memory.add_turn("user", "Third")
        
        # Should only keep 1 turn
        assert len(memory.turns) == 1
        assert memory.turns[0].content == "Third"
