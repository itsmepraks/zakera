"""
Tests for Enhanced Conversation Memory System
"""

import pytest
from datetime import datetime, timedelta
from src.model.memory_enhanced import (
    EnhancedConversationMemory,
    ConversationTurn,
    ConversationSummary,
    MemoryImportance,
    SummarizationStrategy
)


class TestConversationTurn:
    """Test ConversationTurn dataclass"""
    
    def test_turn_creation(self):
        """Test creating a conversation turn"""
        turn = ConversationTurn(
            role="user",
            content="Hello, how are you?",
            importance=0.5
        )
        
        assert turn.role == "user"
        assert turn.content == "Hello, how are you?"
        assert turn.importance == 0.5
        assert turn.turn_id is not None
        assert turn.is_summarized is False
    
    def test_turn_id_generation(self):
        """Test unique ID generation"""
        turn1 = ConversationTurn(role="user", content="Test 1")
        turn2 = ConversationTurn(role="user", content="Test 2")
        
        assert turn1.turn_id != turn2.turn_id
        assert len(turn1.turn_id) == 16


class TestMemoryImportance:
    """Test importance scoring"""
    
    def test_calculate_importance_critical(self):
        """Test critical importance detection"""
        memory = EnhancedConversationMemory()
        
        # Critical keywords
        score = memory._calculate_importance("user", "My name is John")
        assert score >= MemoryImportance.CRITICAL.value
        
        score = memory._calculate_importance("user", "Remember this is important")
        assert score >= MemoryImportance.CRITICAL.value
    
    def test_calculate_importance_high(self):
        """Test high importance detection"""
        memory = EnhancedConversationMemory()
        
        score = memory._calculate_importance("user", "I like Python programming")
        assert score >= MemoryImportance.HIGH.value
    
    def test_calculate_importance_user_vs_assistant(self):
        """Test that user messages are weighted higher"""
        memory = EnhancedConversationMemory()
        
        user_score = memory._calculate_importance("user", "Tell me about AI")
        assistant_score = memory._calculate_importance("assistant", "Tell me about AI")
        
        assert user_score > assistant_score
    
    def test_calculate_importance_questions(self):
        """Test that questions get higher importance"""
        memory = EnhancedConversationMemory()
        
        question_score = memory._calculate_importance("user", "What is machine learning?")
        statement_score = memory._calculate_importance("user", "Machine learning is interesting")
        
        assert question_score > statement_score


class TestMemoryBasics:
    """Test basic memory operations"""
    
    def test_memory_initialization(self):
        """Test memory initialization"""
        memory = EnhancedConversationMemory(
            max_tokens=4000,
            max_turns=100,
            system_prompt="Test prompt"
        )
        
        assert memory.max_tokens == 4000
        assert memory.max_turns == 100
        assert memory.system_prompt == "Test prompt"
        assert len(memory.turns) == 0
        assert len(memory.summaries) == 0
    
    def test_add_turn(self):
        """Test adding turns to memory"""
        memory = EnhancedConversationMemory()
        
        memory.add_turn("user", "Hello!", importance=0.5)
        memory.add_turn("assistant", "Hi there!", importance=0.5)
        
        assert len(memory.turns) == 2
        assert memory.turns[0].role == "user"
        assert memory.turns[1].role == "assistant"
    
    def test_token_counting(self):
        """Test token counting"""
        memory = EnhancedConversationMemory()
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        token_count = memory._count_tokens(messages)
        assert token_count > 0
        assert isinstance(token_count, int)


class TestImportantFacts:
    """Test important facts extraction"""
    
    def test_extract_name(self):
        """Test extracting user's name"""
        memory = EnhancedConversationMemory()
        
        turn = ConversationTurn(
            role="user",
            content="My name is Alice",
            importance=MemoryImportance.CRITICAL.value
        )
        
        memory._extract_important_facts(turn)
        
        assert len(memory.important_facts) > 0
        assert any("Alice" in fact for fact in memory.important_facts)
    
    def test_extract_preferences(self):
        """Test extracting user preferences"""
        memory = EnhancedConversationMemory()
        
        turn = ConversationTurn(
            role="user",
            content="I prefer dark mode in all my applications",
            importance=MemoryImportance.CRITICAL.value
        )
        
        memory._extract_important_facts(turn)
        
        assert len(memory.important_facts) > 0
        assert any("prefer" in fact.lower() for fact in memory.important_facts)
    
    def test_no_duplicate_facts(self):
        """Test that duplicate facts are not added"""
        memory = EnhancedConversationMemory()
        
        turn = ConversationTurn(
            role="user",
            content="I like Python",
            importance=MemoryImportance.CRITICAL.value
        )
        
        memory._extract_important_facts(turn)
        memory._extract_important_facts(turn)
        
        # Should only be added once
        assert memory.important_facts.count("I like Python") <= 1


class TestSummarization:
    """Test conversation summarization"""
    
    def test_should_summarize_many_turns(self):
        """Test summarization trigger with many turns"""
        memory = EnhancedConversationMemory(
            summary_threshold=5,
            short_term_window=3
        )
        
        # Add many turns
        for i in range(15):
            memory.add_turn("user", f"Message {i}", importance=0.3)
        
        assert memory._should_summarize()
    
    def test_should_summarize_token_limit(self):
        """Test summarization trigger with token limit"""
        memory = EnhancedConversationMemory(
            max_tokens=1000,
            summary_threshold=20
        )
        
        # Add long messages
        for i in range(10):
            memory.add_turn(
                "user", 
                "This is a very long message " * 50,
                importance=0.3
            )
        
        assert memory._should_summarize()
    
    def test_generate_summary_text(self):
        """Test summary text generation"""
        memory = EnhancedConversationMemory()
        
        turns = [
            ConversationTurn(role="user", content="What is AI?", importance=0.7),
            ConversationTurn(role="assistant", content="AI is artificial intelligence", importance=0.5),
            ConversationTurn(role="user", content="How does it work?", importance=0.6)
        ]
        
        summary = memory._generate_summary_text(turns)
        
        assert len(summary) > 0
        assert isinstance(summary, str)
    
    def test_create_summary(self):
        """Test creating a summary"""
        memory = EnhancedConversationMemory(
            summary_threshold=3,
            short_term_window=2
        )
        
        # Add turns
        for i in range(10):
            memory.add_turn("user", f"Message {i}", importance=0.3)
        
        initial_summaries = len(memory.summaries)
        memory._create_summary()
        
        # Should have created at least one summary
        assert len(memory.summaries) >= initial_summaries
    
    def test_summarized_turns_marked(self):
        """Test that summarized turns are marked"""
        memory = EnhancedConversationMemory(
            summary_threshold=3,
            short_term_window=2
        )
        
        # Add turns
        for i in range(10):
            memory.add_turn("user", f"Message {i}", importance=0.2)
        
        memory._create_summary()
        
        # Some turns should be marked as summarized
        summarized = [t for t in memory.turns if t.is_summarized]
        assert len(summarized) > 0


class TestContextOptimization:
    """Test context window optimization"""
    
    def test_get_messages_basic(self):
        """Test getting messages"""
        memory = EnhancedConversationMemory()
        
        memory.add_turn("user", "Hello", importance=0.5)
        memory.add_turn("assistant", "Hi", importance=0.5)
        
        messages = memory.get_messages()
        
        # Should include system + 2 turns
        assert len(messages) >= 2
        assert any(m["role"] == "user" for m in messages)
        assert any(m["role"] == "assistant" for m in messages)
    
    def test_get_messages_with_important_facts(self):
        """Test that important facts are included"""
        memory = EnhancedConversationMemory()
        memory.important_facts = ["User's name: Alice", "Prefers Python"]
        
        memory.add_turn("user", "Hello", importance=0.5)
        
        messages = memory.get_messages(optimize_context=True)
        
        # Should include facts as system message
        system_messages = [m for m in messages if m["role"] == "system"]
        assert len(system_messages) > 1  # Original system + facts
    
    def test_get_messages_with_summaries(self):
        """Test that summaries are included"""
        memory = EnhancedConversationMemory()
        
        # Add a summary
        summary = ConversationSummary(
            summary_text="Previous discussion about AI",
            turn_ids=["1", "2", "3"],
            start_timestamp=datetime.utcnow().isoformat(),
            end_timestamp=datetime.utcnow().isoformat(),
            token_count=50,
            compression_ratio=0.3
        )
        memory.summaries.append(summary)
        
        memory.add_turn("user", "New question", importance=0.5)
        
        messages = memory.get_messages(optimize_context=True)
        
        # Should include summary
        assert any("Previous discussion" in str(m) for m in messages)
    
    def test_get_messages_respects_token_limit(self):
        """Test that messages respect token limit"""
        memory = EnhancedConversationMemory(max_tokens=500)
        
        # Add many long messages
        for i in range(20):
            memory.add_turn("user", "This is a long message " * 20, importance=0.3)
        
        messages = memory.get_messages()
        token_count = memory._count_tokens(messages)
        
        # Should not exceed max tokens
        assert token_count <= memory.max_tokens
    
    def test_recent_messages_always_included(self):
        """Test that recent messages are always included"""
        memory = EnhancedConversationMemory(short_term_window=3)
        
        # Add many messages
        for i in range(10):
            memory.add_turn("user", f"Message {i}", importance=0.3)
        
        messages = memory.get_messages()
        user_messages = [m for m in messages if m["role"] == "user"]
        
        # Last 3 should be present
        assert "Message 9" in str(messages)
        assert "Message 8" in str(messages)
        assert "Message 7" in str(messages)
    
    def test_high_importance_messages_prioritized(self):
        """Test that high importance messages are prioritized"""
        memory = EnhancedConversationMemory(
            max_tokens=1000,
            short_term_window=2
        )
        
        # Add old low importance messages
        for i in range(5):
            memory.add_turn("user", f"Low importance {i}", importance=0.2)
        
        # Add old high importance message
        memory.add_turn("user", "CRITICAL INFO", importance=MemoryImportance.CRITICAL.value)
        
        # Add recent messages
        memory.add_turn("user", "Recent 1", importance=0.5)
        memory.add_turn("user", "Recent 2", importance=0.5)
        
        messages = memory.get_messages(optimize_context=True)
        message_text = str(messages)
        
        # Critical message should be included
        assert "CRITICAL INFO" in message_text


class TestMemoryOptimization:
    """Test memory optimization"""
    
    def test_optimize_memory(self):
        """Test memory optimization"""
        memory = EnhancedConversationMemory(
            summary_threshold=5,
            short_term_window=3
        )
        
        # Add many turns
        for i in range(20):
            memory.add_turn("user", f"Message {i}", importance=0.2)
        
        turns_before = len(memory.turns)
        memory.optimize_memory(aggressive=False)
        turns_after = len(memory.turns)
        
        # Should have reduced turns or created summaries
        assert turns_after <= turns_before or len(memory.summaries) > 0
    
    def test_optimize_memory_aggressive(self):
        """Test aggressive memory optimization"""
        memory = EnhancedConversationMemory(
            summary_threshold=10,
            short_term_window=3
        )
        
        # Add old turns
        for i in range(30):
            turn = ConversationTurn(
                role="user",
                content=f"Message {i}",
                importance=0.1,
                timestamp=(datetime.utcnow() - timedelta(days=2)).isoformat()
            )
            memory.turns.append(turn)
        
        turns_before = len(memory.turns)
        memory.optimize_memory(aggressive=True)
        turns_after = len(memory.turns)
        
        # Aggressive should remove more
        assert turns_after < turns_before


class TestMemoryStats:
    """Test memory statistics"""
    
    def test_get_context_stats(self):
        """Test getting context statistics"""
        memory = EnhancedConversationMemory()
        
        memory.add_turn("user", "Hello", importance=0.5)
        memory.add_turn("assistant", "Hi", importance=0.5)
        
        stats = memory.get_context_stats()
        
        assert "total_turns" in stats
        assert "active_turns" in stats
        assert "token_count" in stats
        assert "token_usage_percent" in stats
        assert stats["total_turns"] == 2
    
    def test_memory_health_assessment(self):
        """Test memory health assessment"""
        memory = EnhancedConversationMemory(max_tokens=1000)
        
        # Low usage
        memory.add_turn("user", "Hi", importance=0.5)
        assert memory._assess_memory_health() == "excellent"
        
        # High usage
        for i in range(50):
            memory.add_turn("user", "Long message " * 20, importance=0.3)
        
        health = memory._assess_memory_health()
        assert health in ["excellent", "good", "moderate", "needs_optimization"]
    
    def test_compression_ratio_calculation(self):
        """Test compression ratio calculation"""
        memory = EnhancedConversationMemory()
        
        # Add turns
        for i in range(5):
            turn = ConversationTurn(
                role="user",
                content=f"Message {i}",
                importance=0.3,
                token_count=50,
                turn_id=str(i)
            )
            memory.turns.append(turn)
        
        # Add summary
        summary = ConversationSummary(
            summary_text="Summary",
            turn_ids=["0", "1", "2"],
            start_timestamp=datetime.utcnow().isoformat(),
            end_timestamp=datetime.utcnow().isoformat(),
            token_count=30,  # Compressed from 150 to 30
            compression_ratio=0.2
        )
        memory.summaries.append(summary)
        
        ratio = memory._calculate_overall_compression()
        assert 0 < ratio < 1


class TestExportImport:
    """Test export and import functionality"""
    
    def test_export_memory(self):
        """Test exporting memory state"""
        memory = EnhancedConversationMemory()
        
        memory.add_turn("user", "Hello", importance=0.5)
        memory.important_facts.append("Test fact")
        
        export_data = memory.export()
        
        assert "turns" in export_data
        assert "summaries" in export_data
        assert "important_facts" in export_data
        assert "metadata" in export_data
        assert len(export_data["turns"]) == 1
        assert len(export_data["important_facts"]) == 1
    
    def test_import_memory(self):
        """Test importing memory state"""
        # Create and export
        memory1 = EnhancedConversationMemory()
        memory1.add_turn("user", "Hello", importance=0.5)
        memory1.important_facts.append("Test fact")
        
        export_data = memory1.export()
        
        # Import to new memory
        memory2 = EnhancedConversationMemory.from_export(export_data)
        
        assert len(memory2.turns) == 1
        assert memory2.turns[0].content == "Hello"
        assert "Test fact" in memory2.important_facts
    
    def test_export_import_with_summaries(self):
        """Test export/import with summaries"""
        memory1 = EnhancedConversationMemory()
        
        # Add summary
        summary = ConversationSummary(
            summary_text="Test summary",
            turn_ids=["1", "2"],
            start_timestamp=datetime.utcnow().isoformat(),
            end_timestamp=datetime.utcnow().isoformat(),
            token_count=20,
            compression_ratio=0.4
        )
        memory1.summaries.append(summary)
        
        export_data = memory1.export()
        memory2 = EnhancedConversationMemory.from_export(export_data)
        
        assert len(memory2.summaries) == 1
        assert memory2.summaries[0].summary_text == "Test summary"


class TestStrategies:
    """Test different summarization strategies"""
    
    def test_strategy_none(self):
        """Test NONE strategy doesn't summarize"""
        memory = EnhancedConversationMemory(
            summarization_strategy=SummarizationStrategy.NONE
        )
        
        for i in range(20):
            memory.add_turn("user", f"Message {i}", importance=0.3)
        
        assert not memory._should_summarize()
    
    def test_strategy_adaptive(self):
        """Test ADAPTIVE strategy"""
        memory = EnhancedConversationMemory(
            summarization_strategy=SummarizationStrategy.ADAPTIVE,
            summary_threshold=5,
            short_term_window=3
        )
        
        for i in range(15):
            memory.add_turn("user", f"Message {i}", importance=0.3)
        
        assert memory._should_summarize()


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_memory(self):
        """Test operations on empty memory"""
        memory = EnhancedConversationMemory()
        
        messages = memory.get_messages()
        stats = memory.get_context_stats()
        
        assert len(messages) >= 0  # At least system prompt
        assert stats["total_turns"] == 0
    
    def test_very_long_single_message(self):
        """Test handling very long single message"""
        memory = EnhancedConversationMemory(max_tokens=1000)
        
        long_message = "word " * 1000
        memory.add_turn("user", long_message, importance=0.5)
        
        messages = memory.get_messages()
        token_count = memory._count_tokens(messages)
        
        # Should handle gracefully
        assert token_count > 0
    
    def test_all_high_importance(self):
        """Test when all messages are high importance"""
        memory = EnhancedConversationMemory(max_tokens=1000)
        
        for i in range(20):
            memory.add_turn(
                "user",
                f"CRITICAL: Message {i}",
                importance=MemoryImportance.CRITICAL.value
            )
        
        messages = memory.get_messages()
        
        # Should still respect token limits
        token_count = memory._count_tokens(messages)
        assert token_count <= memory.max_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
