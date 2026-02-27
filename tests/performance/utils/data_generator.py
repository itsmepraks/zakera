"""Data Generator for Performance Tests

Generates realistic test data:
- Chat messages (simple, complex, long)
- Conversation titles
- Tool requests
- User profiles
- Random model selection
"""

import random
import os
from typing import List, Dict, Optional
from faker import Faker
import logging

logger = logging.getLogger(__name__)


class DataGenerator:
    """Generates realistic test data for performance testing"""
    
    def __init__(self, locale: str = 'en_US', seed: Optional[int] = None):
        """Initialize data generator
        
        Args:
            locale: Faker locale
            seed: Random seed for reproducibility
        """
        self.fake = Faker(locale)
        if seed:
            Faker.seed(seed)
            random.seed(seed)
        
        # Model options
        self.models = [
            'gpt-4-turbo',
            'gpt-4',
            'gpt-3.5-turbo',
            'claude-3-opus',
            'claude-3-sonnet',
            'claude-3-haiku',
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'llama-3-8b',
            'llama-3-70b',
            'mistral-7b',
            'mixtral-8x7b-32768'
        ]
        
        # Message templates
        self.simple_questions = [
            "What is {topic}?",
            "Tell me about {topic}",
            "Explain {topic} simply",
            "How does {topic} work?",
            "What are the benefits of {topic}?"
        ]
        
        self.complex_questions = [
            "Can you provide a detailed analysis of {topic} including its historical context, current applications, and future implications?",
            "Compare and contrast {topic1} and {topic2}, highlighting their key differences and similarities.",
            "Explain the technical architecture of {topic}, including all major components and their interactions.",
            "What are the best practices for implementing {topic} in a production environment?"
        ]
        
        self.topics = [
            'artificial intelligence',
            'machine learning',
            'quantum computing',
            'blockchain',
            'cloud computing',
            'cybersecurity',
            'data science',
            'web development',
            'mobile app development',
            'DevOps',
            'microservices',
            'containerization',
            'API design',
            'database optimization',
            'distributed systems'
        ]
        
        self.tool_requests = [
            "What's the weather in {city}?",
            "Calculate {math_expr}",
            "Search the web for {query}",
            "What's the current time in {city}?",
            "Convert {amount} USD to EUR",
            "Execute this Python code: {code}"
        ]
    
    def generate_message(self, length: str = 'medium') -> str:
        """Generate a chat message
        
        Args:
            length: 'short', 'medium', or 'long'
        
        Returns:
            Generated message string
        """
        if length == 'short':
            return self.generate_short_message()
        elif length == 'long':
            return self.generate_long_message()
        else:
            return self.generate_medium_message()
    
    def generate_short_message(self) -> str:
        """Generate a short message (1-2 sentences)"""
        templates = [
            self.fake.sentence(),
            f"Hi, {self.fake.sentence()}",
            f"{self.fake.sentence()} {self.fake.sentence()}",
            random.choice(self.simple_questions).format(topic=random.choice(self.topics))
        ]
        return random.choice(templates)
    
    def generate_medium_message(self) -> str:
        """Generate a medium message (3-5 sentences)"""
        num_sentences = random.randint(3, 5)
        return ' '.join([self.fake.sentence() for _ in range(num_sentences)])
    
    def generate_long_message(self) -> str:
        """Generate a long message (multiple paragraphs)"""
        num_paragraphs = random.randint(2, 4)
        paragraphs = [self.fake.paragraph(nb_sentences=5) for _ in range(num_paragraphs)]
        return '\n\n'.join(paragraphs)
    
    def generate_simple_question(self) -> str:
        """Generate a simple question"""
        template = random.choice(self.simple_questions)
        topic = random.choice(self.topics)
        return template.format(topic=topic)
    
    def generate_complex_question(self) -> str:
        """Generate a complex, detailed question"""
        template = random.choice(self.complex_questions)
        topic1 = random.choice(self.topics)
        topic2 = random.choice([t for t in self.topics if t != topic1])
        
        return template.format(
            topic=topic1,
            topic1=topic1,
            topic2=topic2
        )
    
    def generate_tool_request_message(self) -> str:
        """Generate a message that requires tool usage"""
        template = random.choice(self.tool_requests)
        
        city = self.fake.city()
        math_expr = f"{random.randint(10, 100)} * {random.randint(2, 20)}"
        query = random.choice(self.topics)
        amount = random.randint(100, 10000)
        code = "print('Hello, World!')"
        
        return template.format(
            city=city,
            math_expr=math_expr,
            query=query,
            amount=amount,
            code=code
        )
    
    def generate_conversation_title(self) -> str:
        """Generate a conversation title"""
        templates = [
            f"Discussion about {random.choice(self.topics)}",
            f"{self.fake.catch_phrase()}",
            f"{self.fake.bs()}",
            f"Chat on {self.fake.date()}",
            f"{random.choice(self.topics).title()} Questions"
        ]
        return random.choice(templates)
    
    def select_random_model(self, distribution: Optional[Dict[str, int]] = None) -> str:
        """Select a random model, optionally with weighted distribution
        
        Args:
            distribution: Dict mapping model names to weights
        
        Returns:
            Selected model name
        """
        if distribution:
            models = list(distribution.keys())
            weights = list(distribution.values())
            return random.choices(models, weights=weights, k=1)[0]
        else:
            # Default distribution favoring cheaper/faster models
            weights = [
                5,  # gpt-4-turbo
                3,  # gpt-4
                15, # gpt-3.5-turbo
                3,  # claude-3-opus
                7,  # claude-3-sonnet
                10, # claude-3-haiku
                8,  # gemini-1.5-pro
                20, # gemini-1.5-flash (most popular)
                12, # llama-3-8b
                5,  # llama-3-70b
                7,  # mistral-7b
                5   # mixtral
            ]
            return random.choices(self.models, weights=weights, k=1)[0]
    
    def generate_messages(self, count: int, topics: Optional[List[str]] = None,
                         lengths: Optional[List[str]] = None) -> List[str]:
        """Generate multiple messages
        
        Args:
            count: Number of messages to generate
            topics: List of topics to use
            lengths: List of message lengths ('short', 'medium', 'long')
        
        Returns:
            List of generated messages
        """
        if topics:
            self.topics = topics
        
        if not lengths:
            lengths = ['short', 'medium', 'long']
        
        messages = []
        for _ in range(count):
            length = random.choice(lengths)
            messages.append(self.generate_message(length))
        
        return messages
    
    def generate_user(self, user_type: str = 'casual') -> Dict:
        """Generate a user profile
        
        Args:
            user_type: 'casual', 'power', or 'api'
        
        Returns:
            User profile dict
        """
        base_user = {
            'email': self.fake.email(),
            'name': self.fake.name(),
            'company': self.fake.company(),
            'type': user_type
        }
        
        if user_type == 'casual':
            base_user['usage_frequency'] = 'low'
            base_user['preferred_models'] = ['gemini-1.5-flash', 'gpt-3.5-turbo']
        elif user_type == 'power':
            base_user['usage_frequency'] = 'high'
            base_user['preferred_models'] = ['gpt-4-turbo', 'claude-3-opus']
            base_user['uses_tools'] = True
        elif user_type == 'api':
            base_user['usage_frequency'] = 'very_high'
            base_user['preferred_models'] = ['gemini-1.5-flash']  # Cheap & fast
            base_user['automated'] = True
        
        return base_user
    
    def generate_users(self, count: int, types: Optional[List[str]] = None) -> List[Dict]:
        """Generate multiple users
        
        Args:
            count: Number of users to generate
            types: List of user types to include
        
        Returns:
            List of user profile dicts
        """
        if not types:
            types = ['casual', 'power', 'api']
        
        users = []
        for _ in range(count):
            user_type = random.choice(types)
            users.append(self.generate_user(user_type))
        
        return users
    
    def generate_code_snippet(self, language: str = 'python') -> str:
        """Generate a code snippet for testing
        
        Args:
            language: Programming language
        
        Returns:
            Code snippet string
        """
        if language == 'python':
            snippets = [
                "def hello():\n    print('Hello, World!')",
                "for i in range(10):\n    print(i)",
                "import math\nprint(math.sqrt(16))",
                "x = [1, 2, 3, 4, 5]\nprint(sum(x))"
            ]
        elif language == 'javascript':
            snippets = [
                "console.log('Hello, World!');",
                "const x = [1, 2, 3];\nconsole.log(x.map(n => n * 2));",
                "function add(a, b) { return a + b; }"
            ]
        else:
            snippets = ["// Code example"]
        
        return random.choice(snippets)
