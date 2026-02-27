"""Test data generator for performance tests."""

import random
import string
from typing import List, Dict, Any
from datetime import datetime, timedelta


class DataGenerator:
    """Generate realistic test data for load testing."""
    
    # Sample conversation topics
    TOPICS = [
        "technology", "science", "programming", "ai", "machine learning",
        "web development", "data science", "cloud computing", "cybersecurity",
        "productivity", "health", "fitness", "cooking", "travel", "education"
    ]
    
    # Sample message templates
    MESSAGE_TEMPLATES = [
        "How do I {action} {topic}?",
        "Explain {topic} in simple terms",
        "What are the benefits of {topic}?",
        "Can you help me with {topic}?",
        "Tell me more about {topic}",
        "What's the best way to learn {topic}?",
        "Compare {topic} with {other_topic}",
        "What are the latest trends in {topic}?",
    ]
    
    ACTIONS = [
        "learn", "understand", "implement", "optimize", "improve",
        "master", "get started with", "practice", "teach"
    ]
    
    def generate_message(self) -> str:
        """Generate a realistic chat message.
        
        Returns:
            Generated message string
        """
        template = random.choice(self.MESSAGE_TEMPLATES)
        return template.format(
            action=random.choice(self.ACTIONS),
            topic=random.choice(self.TOPICS),
            other_topic=random.choice(self.TOPICS)
        )
    
    def generate_conversation_title(self) -> str:
        """Generate a conversation title.
        
        Returns:
            Generated title
        """
        topic = random.choice(self.TOPICS).title()
        suffixes = ["Discussion", "Chat", "Questions", "Learning", "Guide"]
        return f"{topic} {random.choice(suffixes)}"
    
    def generate_username(self) -> str:
        """Generate a random username.
        
        Returns:
            Generated username
        """
        adjectives = ["happy", "clever", "brave", "quick", "smart", "cool"]
        nouns = ["user", "tester", "dev", "coder", "engineer", "builder"]
        number = random.randint(1000, 9999)
        return f"{random.choice(adjectives)}_{random.choice(nouns)}_{number}"
    
    def generate_user_profile(self) -> Dict[str, Any]:
        """Generate a user profile.
        
        Returns:
            User profile dict
        """
        return {
            "username": self.generate_username(),
            "email": f"{self.generate_username()}@test.com",
            "preferences": {
                "model": random.choice(["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"]),
                "theme": random.choice(["light", "dark"]),
                "language": "en"
            }
        }
    
    def generate_tool_request(self) -> Dict[str, Any]:
        """Generate a tool execution request.
        
        Returns:
            Tool request dict
        """
        tools = [
            {
                "name": "calculator",
                "input": {"expression": f"{random.randint(1, 100)} + {random.randint(1, 100)}"}
            },
            {
                "name": "web_search",
                "input": {"query": f"latest {random.choice(self.TOPICS)} news"}
            },
            {
                "name": "code_executor",
                "input": {
                    "language": "python",
                    "code": "print('Hello, World!')"
                }
            }
        ]
        return random.choice(tools)
    
    def generate_message_batch(self, count: int = 10) -> List[str]:
        """Generate a batch of messages.
        
        Args:
            count: Number of messages to generate
            
        Returns:
            List of generated messages
        """
        return [self.generate_message() for _ in range(count)]
    
    @staticmethod
    def generate_random_string(length: int = 10) -> str:
        """Generate a random string.
        
        Args:
            length: Length of string
            
        Returns:
            Random string
        """
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_timestamp(days_ago: int = 0) -> str:
        """Generate a timestamp.
        
        Args:
            days_ago: Days before now
            
        Returns:
            ISO format timestamp
        """
        dt = datetime.now() - timedelta(days=days_ago)
        return dt.isoformat()
