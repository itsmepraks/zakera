"""Comprehensive tests for vector-based memory management.

Tests cover:
- Basic memory operations (add, retrieve, clear)
- Semantic similarity search
- Message clustering
- Embedding caching
- Performance benchmarks
- Edge cases and error handling
"""

import asyncio
import time
from datetime import datetime, timedelta

import numpy as np
import pytest

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from src.model.memory_vector import (
    Message,
    VectorMemoryConfig,
    VectorMemoryStore,
)


pytestmark = pytest.mark.skipif(
    not SENTENCE_TRANSFORMERS_AVAILABLE,
    reason="sentence-transformers not available"
)


@pytest.fixture
def memory_config():
    """Create test memory configuration."""
    return VectorMemoryConfig(
        model_name="all-MiniLM-L6-v2",
        max_messages=50,
        similarity_threshold=0.7,
        top_k=5,
        enable_caching=True,
        cache_size=100,
    )


@pytest.fixture
def memory_store(memory_config):
    """Create test memory store."""
    store = VectorMemoryStore(memory_config)
    yield store
    store.clear()


class TestVectorMemoryBasics:
    """Test basic memory operations."""

    def test_initialization(self, memory_config):
        """Test memory store initialization."""
        store = VectorMemoryStore(memory_config)
        
        assert store.config == memory_config
        assert len(store.messages) == 0
        assert store.embedding_dim > 0
        assert store.encoder is not None

    def test_add_single_message(self, memory_store):
        """Test adding a single message."""
        memory_store.add_message(
            role="user",
            content="Hello, how are you?",
        )
        
        assert len(memory_store.messages) == 1
        message = memory_store.messages[0]
        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.embedding is not None
        assert message.embedding.shape[0] == memory_store.embedding_dim

    def test_add_multiple_messages(self, memory_store):
        """Test adding multiple messages."""
        messages = [
            ("user", "What is machine learning?"),
            ("assistant", "Machine learning is a branch of AI..."),
            ("user", "Can you explain neural networks?"),
            ("assistant", "Neural networks are computing systems..."),
        ]
        
        for role, content in messages:
            memory_store.add_message(role, content)
        
        assert len(memory_store.messages) == 4
        
        # Check roles
        roles = [m.role for m in memory_store.messages]
        assert roles == ["user", "assistant", "user", "assistant"]

    def test_add_message_with_metadata(self, memory_store):
        """Test adding message with metadata."""
        metadata = {
            "model": "gpt-4",
            "temperature": 0.7,
            "tokens": 150,
        }
        
        memory_store.add_message(
            role="assistant",
            content="This is a response",
            metadata=metadata,
        )
        
        message = memory_store.messages[0]
        assert message.metadata == metadata

    def test_max_messages_limit(self, memory_config):
        """Test that max_messages limit is enforced."""
        memory_config.max_messages = 5
        store = VectorMemoryStore(memory_config)
        
        # Add more messages than the limit
        for i in range(10):
            store.add_message("user", f"Message {i}")
        
        # Should only keep last 5 messages
        assert len(store.messages) == 5
        assert store.messages[0].content == "Message 5"
        assert store.messages[-1].content == "Message 9"

    def test_clear_memory(self, memory_store):
        """Test clearing memory."""
        # Add some messages
        for i in range(5):
            memory_store.add_message("user", f"Message {i}")
        
        assert len(memory_store.messages) == 5
        
        # Clear memory
        memory_store.clear()
        
        assert len(memory_store.messages) == 0
        assert len(memory_store.embedding_cache) == 0


class TestRetrievalOperations:
    """Test message retrieval operations."""

    def test_get_recent_messages(self, memory_store):
        """Test retrieving recent messages."""
        # Add messages
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            memory_store.add_message(role, f"Message {i}")
        
        # Get last 5 messages
        recent = memory_store.get_recent_messages(n=5)
        
        assert len(recent) == 5
        assert recent[0]["content"] == "Message 5"
        assert recent[-1]["content"] == "Message 9"

    def test_get_recent_messages_by_role(self, memory_store):
        """Test retrieving recent messages filtered by role."""
        # Add mixed messages
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            memory_store.add_message(role, f"Message {i}")
        
        # Get only user messages
        user_messages = memory_store.get_recent_messages(n=10, role="user")
        
        assert len(user_messages) == 5
        assert all(m["role"] == "user" for m in user_messages)

    def test_get_recent_messages_empty(self, memory_store):
        """Test retrieving messages from empty memory."""
        recent = memory_store.get_recent_messages(n=5)
        assert len(recent) == 0


class TestSemanticSearch:
    """Test semantic similarity search."""

    def test_search_similar_messages(self, memory_store):
        """Test semantic search for similar messages."""
        # Add diverse messages
        messages = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "I love pizza and pasta",
            "Neural networks are fascinating",
            "What's the weather today?",
        ]
        
        for msg in messages:
            memory_store.add_message("user", msg)
        
        # Search for AI-related content
        results = memory_store.search_similar(
            query="Tell me about AI and ML",
            top_k=3,
        )
        
        # Should return AI/ML related messages with high similarity
        assert len(results) > 0
        
        # Check that top results are AI-related
        top_content = [msg.content for msg, score in results[:2]]
        assert any("intelligence" in c.lower() or "learning" in c.lower() 
                   for c in top_content)

    def test_search_with_threshold(self, memory_store):
        """Test search with similarity threshold."""
        # Add messages
        memory_store.add_message("user", "Python programming")
        memory_store.add_message("user", "Cooking recipes")
        
        # Search with high threshold
        results = memory_store.search_similar(
            query="Python coding",
            threshold=0.9,  # Very high threshold
        )
        
        # Should only return very similar messages
        for msg, score in results:
            assert score >= 0.9

    def test_search_by_role(self, memory_store):
        """Test searching within specific role."""
        # Add mixed messages
        memory_store.add_message("user", "What is Python?")
        memory_store.add_message("assistant", "Python is a programming language")
        memory_store.add_message("user", "How to learn Python?")
        
        # Search only assistant messages
        results = memory_store.search_similar(
            query="programming language",
            role="assistant",
        )
        
        assert all(msg.role == "assistant" for msg, score in results)

    def test_search_empty_memory(self, memory_store):
        """Test search on empty memory."""
        results = memory_store.search_similar(query="test query")
        assert len(results) == 0

    def test_similarity_scores_normalized(self, memory_store):
        """Test that similarity scores are normalized."""
        memory_store.add_message("user", "Hello world")
        memory_store.add_message("user", "Goodbye world")
        
        results = memory_store.search_similar(
            query="Hello universe",
            threshold=0.0,  # Get all results
        )
        
        for msg, score in results:
            assert 0.0 <= score <= 1.0


class TestContextRetrieval:
    """Test context-aware message retrieval."""

    def test_get_context_messages(self, memory_store):
        """Test retrieving context-aware messages."""
        # Add conversation history
        messages = [
            "What is Python?",
            "Python is a programming language",
            "Can you recommend a good book?",
            "Sure, I recommend 'Clean Code'",
            "Tell me more about Python features",
        ]
        
        for msg in messages:
            role = "user" if messages.index(msg) % 2 == 0 else "assistant"
            memory_store.add_message(role, msg)
        
        # Get context for Python-related query
        context = memory_store.get_context_messages(
            query="Python programming",
            max_messages=5,
            include_recent=2,
        )
        
        assert len(context) <= 5
        assert len(context) >= 2  # At least recent messages

    def test_context_deduplication(self, memory_store):
        """Test that context messages are deduplicated."""
        # Add messages
        memory_store.add_message("user", "Tell me about AI")
        memory_store.add_message("assistant", "AI is amazing")
        
        context = memory_store.get_context_messages(
            query="AI",
            max_messages=10,
            include_recent=2,
        )
        
        # Check no duplicates
        contents = [m["content"] for m in context]
        assert len(contents) == len(set(contents))


class TestClustering:
    """Test message clustering functionality."""

    def test_cluster_messages(self, memory_store):
        """Test clustering similar messages."""
        # Add messages in two distinct topics
        ai_messages = [
            "What is AI?",
            "Explain machine learning",
            "How do neural networks work?",
        ]
        
        food_messages = [
            "I love pizza",
            "Best pasta recipes",
            "Italian food is delicious",
        ]
        
        for msg in ai_messages + food_messages:
            memory_store.add_message("user", msg)
        
        # Cluster with moderate threshold
        clusters = memory_store.cluster_messages(threshold=0.6)
        
        # Should create at least 2 clusters
        assert len(clusters) >= 2
        
        # Each cluster should have at least one message
        for cluster in clusters:
            assert len(cluster) >= 1

    def test_cluster_empty_memory(self, memory_store):
        """Test clustering on empty memory."""
        clusters = memory_store.cluster_messages()
        assert len(clusters) == 0

    def test_cluster_single_message(self, memory_store):
        """Test clustering with single message."""
        memory_store.add_message("user", "Single message")
        
        clusters = memory_store.cluster_messages()
        
        assert len(clusters) == 1
        assert len(clusters[0]) == 1

    def test_summarize_cluster(self, memory_store):
        """Test cluster summarization."""
        # Create a cluster
        messages = [
            Message(role="user", content="Message 1", embedding=np.random.rand(384)),
            Message(role="assistant", content="Message 2", embedding=np.random.rand(384)),
        ]
        
        summary = memory_store.summarize_cluster(messages)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "2 messages" in summary


class TestConsolidation:
    """Test memory consolidation."""

    def test_consolidate_memory(self, memory_store):
        """Test memory consolidation."""
        # Add diverse messages
        for i in range(10):
            memory_store.add_message("user", f"Message about topic {i % 3}")
        
        stats = memory_store.consolidate_memory()
        
        assert stats["status"] == "completed"
        assert stats["total_messages"] == 10
        assert stats["clusters"] > 0
        assert len(stats["summaries"]) == stats["clusters"]

    def test_consolidate_empty_memory(self, memory_store):
        """Test consolidating empty memory."""
        stats = memory_store.consolidate_memory()
        
        assert stats["status"] == "empty"
        assert stats["clusters"] == 0


class TestCaching:
    """Test embedding caching mechanism."""

    def test_embedding_caching_enabled(self, memory_store):
        """Test that embeddings are cached."""
        content = "Test message for caching"
        
        # Add message twice
        memory_store.add_message("user", content)
        
        # Cache should contain the embedding
        assert len(memory_store.embedding_cache) > 0

    def test_cache_size_limit(self, memory_config):
        """Test cache size limit enforcement."""
        memory_config.cache_size = 5
        store = VectorMemoryStore(memory_config)
        
        # Add more unique messages than cache size
        for i in range(10):
            store.add_message("user", f"Unique message {i}")
        
        # Cache should not exceed limit
        assert len(store.embedding_cache) <= 5

    def test_caching_disabled(self, memory_config):
        """Test with caching disabled."""
        memory_config.enable_caching = False
        store = VectorMemoryStore(memory_config)
        
        store.add_message("user", "Test message")
        
        # Cache should be empty
        assert len(store.embedding_cache) == 0


class TestExportImport:
    """Test memory export and statistics."""

    def test_export_memory(self, memory_store):
        """Test exporting memory to dictionary."""
        # Add some messages
        memory_store.add_message("user", "Message 1")
        memory_store.add_message("assistant", "Message 2")
        
        exported = memory_store.export()
        
        assert "config" in exported
        assert "messages" in exported
        assert "total_messages" in exported
        assert exported["total_messages"] == 2
        assert len(exported["messages"]) == 2

    def test_export_preserves_metadata(self, memory_store):
        """Test that export preserves metadata."""
        metadata = {"key": "value"}
        memory_store.add_message("user", "Test", metadata=metadata)
        
        exported = memory_store.export()
        
        assert exported["messages"][0]["metadata"] == metadata

    def test_get_stats(self, memory_store):
        """Test getting memory statistics."""
        # Add mixed messages
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            memory_store.add_message(role, f"Message {i}")
        
        stats = memory_store.get_stats()
        
        assert stats["total_messages"] == 10
        assert "role_distribution" in stats
        assert stats["role_distribution"]["user"] == 5
        assert stats["role_distribution"]["assistant"] == 5
        assert "embedding_dim" in stats


class TestPerformance:
    """Test performance characteristics."""

    def test_large_scale_addition(self, memory_store):
        """Test adding large number of messages."""
        start_time = time.time()
        
        # Add 100 messages
        for i in range(100):
            memory_store.add_message("user", f"Message number {i}")
        
        duration = time.time() - start_time
        
        # Should complete in reasonable time (adjust based on hardware)
        assert duration < 30  # 30 seconds for 100 messages

    def test_search_performance(self, memory_store):
        """Test search performance."""
        # Add messages
        for i in range(50):
            memory_store.add_message("user", f"Message about topic {i}")
        
        start_time = time.time()
        
        # Perform 10 searches
        for _ in range(10):
            memory_store.search_similar("test query", top_k=5)
        
        duration = time.time() - start_time
        
        # Should complete quickly
        assert duration < 5  # 5 seconds for 10 searches


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_message_content(self, memory_store):
        """Test adding message with empty content."""
        memory_store.add_message("user", "")
        
        assert len(memory_store.messages) == 1
        assert memory_store.messages[0].content == ""

    def test_very_long_message(self, memory_store):
        """Test handling very long messages."""
        long_message = "word " * 10000  # Very long message
        
        memory_store.add_message("user", long_message)
        
        assert len(memory_store.messages) == 1
        assert memory_store.messages[0].embedding is not None

    def test_special_characters(self, memory_store):
        """Test handling special characters."""
        special_message = "Test 🎉 with émojis and spëcial çharacters!"
        
        memory_store.add_message("user", special_message)
        
        assert len(memory_store.messages) == 1
        assert memory_store.messages[0].content == special_message

    def test_search_with_empty_query(self, memory_store):
        """Test search with empty query."""
        memory_store.add_message("user", "Test message")
        
        results = memory_store.search_similar(query="")
        
        # Should return results (empty string has an embedding)
        assert isinstance(results, list)


@pytest.mark.parametrize("model_name", [
    "all-MiniLM-L6-v2",
    "all-mpnet-base-v2",
])
def test_different_embedding_models(model_name):
    """Test with different embedding models."""
    config = VectorMemoryConfig(model_name=model_name)
    store = VectorMemoryStore(config)
    
    store.add_message("user", "Test message")
    
    assert len(store.messages) == 1
    assert store.messages[0].embedding is not None
