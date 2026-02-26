"""Comprehensive integration tests for conversation memory system.

Tests cover:
- Memory persistence and retrieval
- Concurrent access patterns
- Performance under load
- Edge cases and error handling
- Memory cleanup and garbage collection
"""

import pytest
import asyncio
import time
import uuid
from typing import List
from datetime import datetime, timedelta

from src.model.memory import ConversationMemory, Message
from src.model.memory_enhanced import EnhancedConversationMemory


class TestMemoryPersistence:
    """Tests for memory persistence operations."""
    
    @pytest.fixture
    async def memory(self, tmp_path):
        """Create memory instance with temporary database."""
        db_path = tmp_path / "test_memory.db"
        mem = ConversationMemory(database_url=f"sqlite:///{db_path}")
        await mem.initialize()
        yield mem
        await mem.cleanup()
    
    @pytest.mark.asyncio
    async def test_basic_persistence(self, memory):
        """Test basic message persistence."""
        conversation_id = str(uuid.uuid4())
        
        # Add messages
        await memory.add_message(
            conversation_id,
            Message(role="user", content="Hello")
        )
        await memory.add_message(
            conversation_id,
            Message(role="assistant", content="Hi there!")
        )
        
        # Retrieve messages
        messages = await memory.get_messages(conversation_id)
        
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"
    
    @pytest.mark.asyncio
    async def test_message_ordering(self, memory):
        """Test messages are retrieved in correct order."""
        conversation_id = str(uuid.uuid4())
        
        # Add messages with delays
        for i in range(10):
            await memory.add_message(
                conversation_id,
                Message(role="user", content=f"Message {i}")
            )
            await asyncio.sleep(0.01)  # Ensure different timestamps
        
        messages = await memory.get_messages(conversation_id)
        
        assert len(messages) == 10
        for i, msg in enumerate(messages):
            assert msg.content == f"Message {i}"
    
    @pytest.mark.asyncio
    async def test_multiple_conversations(self, memory):
        """Test handling multiple separate conversations."""
        conv_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        # Add messages to each conversation
        for i, conv_id in enumerate(conv_ids):
            await memory.add_message(
                conv_id,
                Message(role="user", content=f"Conversation {i}")
            )
        
        # Verify isolation
        for i, conv_id in enumerate(conv_ids):
            messages = await memory.get_messages(conv_id)
            assert len(messages) == 1
            assert messages[0].content == f"Conversation {i}"
    
    @pytest.mark.asyncio
    async def test_message_metadata(self, memory):
        """Test message metadata persistence."""
        conversation_id = str(uuid.uuid4())
        
        message = Message(
            role="user",
            content="Test message",
            metadata={
                "tokens": 10,
                "model": "gpt-4",
                "cost": 0.001
            }
        )
        
        await memory.add_message(conversation_id, message)
        messages = await memory.get_messages(conversation_id)
        
        assert messages[0].metadata["tokens"] == 10
        assert messages[0].metadata["model"] == "gpt-4"
        assert messages[0].metadata["cost"] == 0.001
    
    @pytest.mark.asyncio
    async def test_conversation_deletion(self, memory):
        """Test conversation deletion."""
        conversation_id = str(uuid.uuid4())
        
        # Add messages
        await memory.add_message(
            conversation_id,
            Message(role="user", content="Test")
        )
        
        # Verify exists
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == 1
        
        # Delete conversation
        await memory.delete_conversation(conversation_id)
        
        # Verify deleted
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == 0


class TestMemoryConcurrency:
    """Tests for concurrent memory access."""
    
    @pytest.fixture
    async def memory(self, tmp_path):
        """Create memory instance."""
        db_path = tmp_path / "test_concurrent.db"
        mem = ConversationMemory(database_url=f"sqlite:///{db_path}")
        await mem.initialize()
        yield mem
        await mem.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self, memory):
        """Test concurrent message additions."""
        conversation_id = str(uuid.uuid4())
        num_messages = 100
        
        async def add_messages(start_idx: int, count: int):
            for i in range(start_idx, start_idx + count):
                await memory.add_message(
                    conversation_id,
                    Message(role="user", content=f"Message {i}")
                )
        
        # Run concurrent writes
        tasks = [
            add_messages(i * 25, 25)
            for i in range(4)
        ]
        await asyncio.gather(*tasks)
        
        # Verify all messages saved
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == num_messages
    
    @pytest.mark.asyncio
    async def test_concurrent_read_write(self, memory):
        """Test concurrent reads and writes."""
        conversation_id = str(uuid.uuid4())
        
        async def writer():
            for i in range(50):
                await memory.add_message(
                    conversation_id,
                    Message(role="user", content=f"Msg {i}")
                )
                await asyncio.sleep(0.001)
        
        async def reader():
            for _ in range(50):
                messages = await memory.get_messages(conversation_id)
                await asyncio.sleep(0.001)
        
        # Run concurrent read/write
        await asyncio.gather(
            writer(),
            reader(),
            reader()
        )
        
        # Verify final state
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == 50
    
    @pytest.mark.asyncio
    async def test_multiple_conversation_concurrent_access(self, memory):
        """Test concurrent access to different conversations."""
        num_conversations = 10
        messages_per_conv = 20
        
        async def populate_conversation(conv_id: str):
            for i in range(messages_per_conv):
                await memory.add_message(
                    conv_id,
                    Message(role="user", content=f"Message {i}")
                )
        
        # Create conversations concurrently
        conv_ids = [str(uuid.uuid4()) for _ in range(num_conversations)]
        tasks = [populate_conversation(cid) for cid in conv_ids]
        await asyncio.gather(*tasks)
        
        # Verify all conversations
        for conv_id in conv_ids:
            messages = await memory.get_messages(conv_id)
            assert len(messages) == messages_per_conv


class TestMemoryPerformance:
    """Performance tests for memory operations."""
    
    @pytest.fixture
    async def memory(self, tmp_path):
        """Create memory instance."""
        db_path = tmp_path / "test_performance.db"
        mem = EnhancedConversationMemory(database_url=f"sqlite:///{db_path}")
        await mem.initialize()
        yield mem
        await mem.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_conversation_retrieval(self, memory):
        """Test retrieval performance with large conversations."""
        conversation_id = str(uuid.uuid4())
        num_messages = 1000
        
        # Add many messages
        for i in range(num_messages):
            await memory.add_message(
                conversation_id,
                Message(role="user", content=f"Message {i}" * 50)  # Long content
            )
        
        # Measure retrieval time
        start_time = time.time()
        messages = await memory.get_messages(conversation_id, limit=100)
        retrieval_time = time.time() - start_time
        
        assert len(messages) == 100
        assert retrieval_time < 0.5  # Should retrieve in < 500ms
    
    @pytest.mark.asyncio
    async def test_memory_window_performance(self, memory):
        """Test windowed message retrieval performance."""
        conversation_id = str(uuid.uuid4())
        
        # Add messages
        for i in range(500):
            await memory.add_message(
                conversation_id,
                Message(role="user", content=f"Message {i}")
            )
        
        # Test different window sizes
        window_sizes = [10, 50, 100, 200]
        
        for size in window_sizes:
            start_time = time.time()
            messages = await memory.get_messages(conversation_id, limit=size)
            retrieval_time = time.time() - start_time
            
            assert len(messages) == size
            assert retrieval_time < 0.2  # Should be fast
    
    @pytest.mark.asyncio
    async def test_search_performance(self, memory):
        """Test search performance across conversations."""
        # Create multiple conversations with searchable content
        num_conversations = 50
        
        for i in range(num_conversations):
            conv_id = str(uuid.uuid4())
            await memory.add_message(
                conv_id,
                Message(role="user", content=f"Unique identifier {i}")
            )
        
        # Search performance
        start_time = time.time()
        results = await memory.search_messages("identifier", limit=10)
        search_time = time.time() - start_time
        
        assert len(results) == 10
        assert search_time < 1.0  # Should search in < 1s


class TestMemoryEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @pytest.fixture
    async def memory(self, tmp_path):
        """Create memory instance."""
        db_path = tmp_path / "test_edge_cases.db"
        mem = ConversationMemory(database_url=f"sqlite:///{db_path}")
        await mem.initialize()
        yield mem
        await mem.cleanup()
    
    @pytest.mark.asyncio
    async def test_empty_conversation(self, memory):
        """Test handling of empty conversations."""
        conversation_id = str(uuid.uuid4())
        messages = await memory.get_messages(conversation_id)
        assert messages == []
    
    @pytest.mark.asyncio
    async def test_very_long_message(self, memory):
        """Test handling of very long messages."""
        conversation_id = str(uuid.uuid4())
        
        # Create a very long message (1MB)
        long_content = "A" * (1024 * 1024)
        
        await memory.add_message(
            conversation_id,
            Message(role="user", content=long_content)
        )
        
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == 1
        assert len(messages[0].content) == len(long_content)
    
    @pytest.mark.asyncio
    async def test_special_characters(self, memory):
        """Test handling of special characters in messages."""
        conversation_id = str(uuid.uuid4())
        
        special_content = "Test \n\t\r Unicode: 你好 🚀 Emoji: 👍 SQL: O'Reilly"
        
        await memory.add_message(
            conversation_id,
            Message(role="user", content=special_content)
        )
        
        messages = await memory.get_messages(conversation_id)
        assert messages[0].content == special_content
    
    @pytest.mark.asyncio
    async def test_null_and_empty_values(self, memory):
        """Test handling of null and empty values."""
        conversation_id = str(uuid.uuid4())
        
        # Empty content
        await memory.add_message(
            conversation_id,
            Message(role="user", content="")
        )
        
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == 1
        assert messages[0].content == ""
    
    @pytest.mark.asyncio
    async def test_conversation_limit_exceeded(self, memory):
        """Test behavior when conversation limit is exceeded."""
        conversation_id = str(uuid.uuid4())
        
        # Add many messages
        for i in range(1000):
            await memory.add_message(
                conversation_id,
                Message(role="user", content=f"Message {i}")
            )
        
        # Get with limit
        messages = await memory.get_messages(conversation_id, limit=10)
        assert len(messages) == 10
        
        # Get all should work but be limited by default max
        all_messages = await memory.get_messages(conversation_id)
        assert len(all_messages) <= 1000


class TestMemoryCleanup:
    """Tests for memory cleanup and garbage collection."""
    
    @pytest.fixture
    async def memory(self, tmp_path):
        """Create memory instance."""
        db_path = tmp_path / "test_cleanup.db"
        mem = EnhancedConversationMemory(database_url=f"sqlite:///{db_path}")
        await mem.initialize()
        yield mem
        await mem.cleanup()
    
    @pytest.mark.asyncio
    async def test_old_conversation_cleanup(self, memory):
        """Test cleanup of old conversations."""
        # Create old conversation
        old_conv_id = str(uuid.uuid4())
        await memory.add_message(
            old_conv_id,
            Message(role="user", content="Old message")
        )
        
        # Mark as old (mock timestamp modification would go here)
        # In production, this would use database timestamp manipulation
        
        # Create recent conversation
        new_conv_id = str(uuid.uuid4())
        await memory.add_message(
            new_conv_id,
            Message(role="user", content="New message")
        )
        
        # Cleanup old conversations (> 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        await memory.cleanup_old_conversations(cutoff_date)
        
        # Recent conversation should still exist
        messages = await memory.get_messages(new_conv_id)
        assert len(messages) >= 1
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, memory):
        """Test cache cleanup."""
        conversation_id = str(uuid.uuid4())
        
        # Add messages and populate cache
        for i in range(10):
            await memory.add_message(
                conversation_id,
                Message(role="user", content=f"Message {i}")
            )
        
        # Get messages (populates cache)
        await memory.get_messages(conversation_id)
        
        # Clear cache
        await memory.clear_cache()
        
        # Should still work after cache clear
        messages = await memory.get_messages(conversation_id)
        assert len(messages) == 10
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, memory):
        """Test for memory leaks in long-running operations."""
        import gc
        import sys
        
        # Get initial memory usage
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform many operations
        for i in range(100):
            conv_id = str(uuid.uuid4())
            await memory.add_message(
                conv_id,
                Message(role="user", content=f"Message {i}")
            )
            await memory.get_messages(conv_id)
            await memory.delete_conversation(conv_id)
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Object growth should be minimal
        growth = final_objects - initial_objects
        assert growth < 1000  # Reasonable threshold


class TestMemoryIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_workflow(self, tmp_path):
        """Test complete conversation lifecycle."""
        db_path = tmp_path / "test_integration.db"
        memory = EnhancedConversationMemory(database_url=f"sqlite:///{db_path}")
        await memory.initialize()
        
        try:
            conversation_id = str(uuid.uuid4())
            
            # Simulate multi-turn conversation
            turns = [
                ("user", "What is AI?"),
                ("assistant", "AI is artificial intelligence."),
                ("user", "Can you explain more?"),
                ("assistant", "AI involves machine learning and deep learning."),
                ("user", "What are the applications?"),
                ("assistant", "AI is used in various fields like healthcare, finance, etc.")
            ]
            
            # Add messages
            for role, content in turns:
                await memory.add_message(
                    conversation_id,
                    Message(role=role, content=content)
                )
            
            # Retrieve full conversation
            messages = await memory.get_messages(conversation_id)
            assert len(messages) == 6
            
            # Get conversation summary
            summary = await memory.get_conversation_summary(conversation_id)
            assert summary is not None
            assert "messages" in summary
            assert summary["messages"] == 6
            
            # Search within conversation
            results = await memory.search_messages("AI", conversation_id=conversation_id)
            assert len(results) > 0
            
            # Get recent context (last 2 turns)
            context = await memory.get_messages(conversation_id, limit=4)
            assert len(context) == 4
            
            # Archive conversation
            await memory.archive_conversation(conversation_id)
            
            # Should still be retrievable
            archived_messages = await memory.get_messages(conversation_id)
            assert len(archived_messages) == 6
            
        finally:
            await memory.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
