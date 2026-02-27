"""Mixed Scenario Load Test - Realistic user behavior patterns

Simulates:
- Casual users (occasional chatting)
- Power users (heavy usage, tools, exports)
- API users (programmatic access)
- Mobile users (slower connections)
- Different conversation patterns
"""

import json
import time
import os
import sys
import random
from locust import HttpUser, TaskSet, task, between, events
from locust.exception import RescheduleTask
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.auth_helper import AuthHelper
from utils.data_generator import DataGenerator
from utils.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class CasualUserBehavior(TaskSet):
    """Casual user: occasional usage, simple queries"""
    
    wait_time = between(5, 15)  # Long think time
    
    def on_start(self):
        """Setup casual user"""
        self.conversation_id = None
        self.data_gen = DataGenerator()
        self.create_conversation()
    
    def create_conversation(self):
        try:
            response = self.client.post(
                '/api/v1/conversations',
                json={'title': self.data_gen.generate_conversation_title()}
            )
            if response.status_code == 201:
                self.conversation_id = response.json().get('id')
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
    
    @task(10)
    def simple_question(self):
        """Ask simple questions"""
        if not self.conversation_id:
            self.create_conversation()
        
        message = self.data_gen.generate_simple_question()
        
        try:
            self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'conversation_id': self.conversation_id,
                    'model': 'gemini-1.5-flash'  # Prefer cheap models
                },
                name='Casual: Simple Question'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(3)
    def check_history(self):
        """Check conversation history"""
        if self.conversation_id:
            try:
                self.client.get(
                    f'/api/v1/conversations/{self.conversation_id}/messages',
                    name='Casual: Check History'
                )
            except Exception as e:
                logger.error(f"Error: {e}")
    
    @task(1)
    def browse_conversations(self):
        """Browse past conversations"""
        try:
            self.client.get(
                '/api/v1/conversations',
                name='Casual: Browse'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(1)
    def new_topic(self):
        """Start new conversation on new topic"""
        self.create_conversation()


class PowerUserBehavior(TaskSet):
    """Power user: heavy usage, advanced features"""
    
    wait_time = between(1, 3)  # Short think time
    
    def on_start(self):
        self.conversation_ids = []
        self.data_gen = DataGenerator()
        self.metrics = MetricsCollector()
        # Create multiple conversations
        for _ in range(3):
            self.create_conversation()
    
    def create_conversation(self):
        try:
            response = self.client.post(
                '/api/v1/conversations',
                json={
                    'title': self.data_gen.generate_conversation_title(),
                    'model': random.choice(['gpt-4-turbo', 'claude-3-opus', 'gemini-1.5-pro'])
                }
            )
            if response.status_code == 201:
                self.conversation_ids.append(response.json().get('id'))
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(10)
    def complex_query(self):
        """Ask complex, detailed questions"""
        if not self.conversation_ids:
            self.create_conversation()
        
        conv_id = random.choice(self.conversation_ids)
        message = self.data_gen.generate_complex_question()
        
        try:
            self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'conversation_id': conv_id,
                    'model': 'gpt-4-turbo'  # Use powerful models
                },
                name='Power: Complex Query'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(5)
    def use_tools(self):
        """Use tools frequently"""
        if not self.conversation_ids:
            return
        
        conv_id = random.choice(self.conversation_ids)
        message = self.data_gen.generate_tool_request_message()
        
        try:
            self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'conversation_id': conv_id,
                    'model': 'gpt-4-turbo',
                    'tools': ['web_search', 'calculator', 'weather', 'code_executor']
                },
                name='Power: Use Tools'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(3)
    def export_conversation(self):
        """Export conversations regularly"""
        if not self.conversation_ids:
            return
        
        conv_id = random.choice(self.conversation_ids)
        format_choice = random.choice(['json', 'markdown', 'pdf'])
        
        try:
            self.client.get(
                f'/api/v1/conversations/{conv_id}/export',
                params={'format': format_choice},
                name='Power: Export'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(2)
    def manage_conversations(self):
        """Update conversation metadata"""
        if not self.conversation_ids:
            return
        
        conv_id = random.choice(self.conversation_ids)
        
        try:
            self.client.patch(
                f'/api/v1/conversations/{conv_id}',
                json={
                    'title': self.data_gen.generate_conversation_title(),
                    'tags': ['important', 'work']
                },
                name='Power: Manage'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(1)
    def analytics_check(self):
        """Check usage analytics"""
        try:
            self.client.get(
                '/api/v1/user/analytics',
                name='Power: Analytics'
            )
        except Exception as e:
            logger.error(f"Error: {e}")


class APIUserBehavior(TaskSet):
    """API user: programmatic access, automation"""
    
    wait_time = between(0.5, 2)  # Rapid automated requests
    
    def on_start(self):
        self.data_gen = DataGenerator()
        self.batch_size = 5
    
    @task(10)
    def batch_requests(self):
        """Send batch of automated requests"""
        messages = [self.data_gen.generate_message() for _ in range(self.batch_size)]
        
        for message in messages:
            try:
                self.client.post(
                    '/api/v1/chat/send',
                    json={
                        'message': message,
                        'model': 'gemini-1.5-flash',  # Fast and cheap for automation
                        'stream': False
                    },
                    name='API: Batch Request'
                )
            except Exception as e:
                logger.error(f"Error: {e}")
    
    @task(5)
    def parallel_model_test(self):
        """Test multiple models in parallel"""
        message = self.data_gen.generate_message()
        models = ['gpt-3.5-turbo', 'gemini-1.5-flash', 'claude-3-haiku']
        
        for model in models:
            try:
                self.client.post(
                    '/api/v1/chat/send',
                    json={
                        'message': message,
                        'model': model,
                        'stream': False
                    },
                    name=f'API: Parallel {model}'
                )
            except Exception as e:
                logger.error(f"Error: {e}")
    
    @task(2)
    def health_monitoring(self):
        """Monitor API health"""
        try:
            self.client.get('/api/v1/health', name='API: Health')
            self.client.get('/api/v1/metrics', name='API: Metrics')
        except Exception as e:
            logger.error(f"Error: {e}")


class MobileUserBehavior(TaskSet):
    """Mobile user: slower connections, streaming preferred"""
    
    wait_time = between(3, 8)
    
    def on_start(self):
        self.conversation_id = None
        self.data_gen = DataGenerator()
    
    @task(10)
    def streaming_chat(self):
        """Use streaming for better mobile experience"""
        message = self.data_gen.generate_short_message()
        
        try:
            self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'model': 'gemini-1.5-flash',  # Fast models for mobile
                    'stream': True
                },
                name='Mobile: Streaming'
            )
        except Exception as e:
            logger.error(f"Error: {e}")
    
    @task(2)
    def quick_check(self):
        """Quick checks with minimal data"""
        try:
            self.client.get(
                '/api/v1/conversations?limit=5',
                name='Mobile: Quick Check'
            )
        except Exception as e:
            logger.error(f"Error: {e}")


class MixedScenarioUser(HttpUser):
    """User that randomly exhibits different behavior patterns"""
    
    tasks = {
        CasualUserBehavior: 60,  # 60% casual users
        PowerUserBehavior: 20,   # 20% power users
        APIUserBehavior: 10,     # 10% API users
        MobileUserBehavior: 10   # 10% mobile users
    }
    
    wait_time = between(1, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv('API_KEY')
    
    def on_start(self):
        if self.api_key:
            self.client.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("Starting mixed scenario load test...")
    logger.info("User distribution: 60% Casual, 20% Power, 10% API, 10% Mobile")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("Mixed scenario load test completed")
