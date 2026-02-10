"""Pytest configuration and shared fixtures"""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing"""
    return [
        {
            "role": "user",
            "content": "What is artificial intelligence?",
            "timestamp": "2024-01-01T10:00:00",
            "metadata": {"intent": "question"}
        },
        {
            "role": "assistant",
            "content": "Artificial intelligence (AI) is a branch of computer science...",
            "timestamp": "2024-01-01T10:00:05",
            "metadata": {"model": "gpt-4"}
        },
        {
            "role": "user",
            "content": "Can you give me an example?",
            "timestamp": "2024-01-01T10:00:30",
            "metadata": {"intent": "follow-up"}
        },
        {
            "role": "assistant",
            "content": "Sure! A common example is virtual assistants like Siri or Alexa...",
            "timestamp": "2024-01-01T10:00:35",
            "metadata": {"model": "gpt-4"}
        }
    ]
