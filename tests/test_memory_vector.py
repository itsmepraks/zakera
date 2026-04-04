import pytest
import numpy as np
from datetime import datetime
from src.model.memory_vector import VectorMemoryStore, VectorMemoryConfig, Message

@pytest.fixture
def memory_config():
    return VectorMemoryConfig(
        model_name="all-MiniLM-L6-v2",
        max_messages=5,
        top_k=2
    )

@pytest.fixture
def memory_store(memory_config):
    return VectorMemoryStore(config=memory_config)

def test_add_message(memory_store):
    """Test adding a message to the store."""
    memory_store.add_message(role="user", content="Hello, how are you?")
    
    assert len(memory_store.messages) == 1
    assert memory_store.messages[0].role == "user"
    assert memory_store.messages[0].content == "Hello, how are you?"
    assert memory_store.messages[0].embedding is not None

def test_max_messages_limit(memory_store):
    """Test that the store respects the max_messages limit."""
    for i in range(10):
        memory_store.add_message(role="user", content=f"Message {i}")
    
    assert len(memory_store.messages) == 5
    assert memory_store.messages[-1].content == "Message 9"
    assert memory_store.messages[0].content == "Message 5"

def test_search_similar(memory_store):
    """Test searching for similar messages."""
    memory_store.add_message(role="user", content="I love programming in Python")
    memory_store.add_message(role="user", content="The weather is nice today")
    memory_store.add_message(role="user", content="Software engineering is fun")
    
    results = memory_store.search_similar("coding", top_k=2)
    
    assert len(results) > 0
    # The most similar should be about programming or software engineering
    assert "programming" in results[0][0].content.lower() or "software" in results[0][0].content.lower()

def test_get_recent_messages(memory_store):
    """Test retrieving recent messages."""
    memory_store.add_message(role="user", content="Msg 1")
    memory_store.add_message(role="assistant", content="Response 1")
    memory_store.add_message(role="user", content="Msg 2")
    
    recent = memory_store.get_recent_messages(n=2)
    assert len(recent) == 2
    assert recent[0]["content"] == "Response 1"
    assert recent[1]["content"] == "Msg 2"

def test_clear_memory(memory_store):
    """Test clearing the memory store."""
    memory_store.add_message(role="user", content="Some content")
    assert len(memory_store.messages) == 1
    
    memory_store.clear()
    assert len(memory_store.messages) == 0
    assert len(memory_store.embedding_cache) == 0

def test_get_stats(memory_store):
    """Test getting memory statistics."""
    memory_store.add_message(role="user", content="Hello")
    memory_store.add_message(role="assistant", content="Hi there")
    
    stats = memory_store.get_stats()
    assert stats["total_messages"] == 2
    assert stats["role_distribution"]["user"] == 1
    assert stats["role_distribution"]["assistant"] == 1
    assert "embedding_dim" in stats
