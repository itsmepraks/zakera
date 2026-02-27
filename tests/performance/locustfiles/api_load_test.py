"""API Load Test - Tests REST API endpoints

Tests:
- User authentication
- Chat message sending
- Conversation management
- User profile operations
- Health checks
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.auth_helper import AuthHelper
from utils.data_generator import DataGenerator
from utils.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class APIUser(HttpUser):
    """Simulates a user interacting with the Zakera API"""
    
    wait_time = between(
        float(os.getenv('MIN_WAIT_TIME', 1)),
        float(os.getenv('MAX_WAIT_TIME', 5))
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = AuthHelper()
        self.data_gen = DataGenerator()
        self.api_key = None
        self.conversation_id = None
        self.user_id = None
        self.metrics = MetricsCollector()
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Authenticate user
        self.authenticate()
        
        # Create initial conversation
        self.create_conversation()
    
    def authenticate(self):
        """Authenticate and get API key/token"""
        try:
            # Try to get API key from environment
            api_key = os.getenv('API_KEY')
            
            if api_key:
                self.api_key = api_key
                self.client.headers.update({
                    'Authorization': f'Bearer {api_key}'
                })
            else:
                # Perform login
                response = self.client.post(
                    '/api/v1/auth/login',
                    json={
                        'email': os.getenv('TEST_USER_EMAIL', 'test@example.com'),
                        'password': os.getenv('TEST_USER_PASSWORD', 'testpass')
                    },
                    name='Auth: Login'
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.api_key = data.get('access_token')
                    self.user_id = data.get('user_id')
                    self.client.headers.update({
                        'Authorization': f'Bearer {self.api_key}'
                    })
                else:
                    logger.error(f"Authentication failed: {response.status_code}")
                    raise RescheduleTask()
        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise RescheduleTask()
    
    def create_conversation(self):
        """Create a new conversation"""
        try:
            response = self.client.post(
                '/api/v1/conversations',
                json={
                    'title': self.data_gen.generate_conversation_title(),
                    'model': self.data_gen.select_random_model()
                },
                name='Conversation: Create'
            )
            
            if response.status_code == 201:
                self.conversation_id = response.json().get('id')
            else:
                logger.warning(f"Failed to create conversation: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
    
    @task(10)
    def send_chat_message(self):
        """Send a chat message (most common action)"""
        if not self.conversation_id:
            self.create_conversation()
            if not self.conversation_id:
                return
        
        message = self.data_gen.generate_message()
        model = self.data_gen.select_random_model()
        
        start_time = time.time()
        
        try:
            with self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'conversation_id': self.conversation_id,
                    'model': model,
                    'stream': False
                },
                catch_response=True,
                name='Chat: Send Message'
            ) as response:
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    response.success()
                    
                    # Collect custom metrics
                    self.metrics.record_chat_metrics(
                        model=model,
                        duration=duration,
                        tokens=data.get('usage', {}).get('total_tokens', 0),
                        cost=data.get('cost', 0)
                    )
                else:
                    response.failure(f"Failed with status {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    @task(3)
    def send_chat_with_tools(self):
        """Send a chat message that uses tools"""
        if not self.conversation_id:
            self.create_conversation()
            if not self.conversation_id:
                return
        
        message = self.data_gen.generate_tool_request_message()
        
        try:
            self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'conversation_id': self.conversation_id,
                    'model': 'gpt-4-turbo',  # Use capable model for tools
                    'tools': ['web_search', 'calculator', 'weather'],
                    'stream': False
                },
                name='Chat: Send with Tools'
            )
        except Exception as e:
            logger.error(f"Error sending message with tools: {e}")
    
    @task(5)
    def get_conversation_history(self):
        """Get conversation history"""
        if not self.conversation_id:
            return
        
        try:
            self.client.get(
                f'/api/v1/conversations/{self.conversation_id}/messages',
                name='Conversation: Get History'
            )
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
    
    @task(2)
    def list_conversations(self):
        """List user's conversations"""
        try:
            self.client.get(
                '/api/v1/conversations',
                params={'limit': 20, 'offset': 0},
                name='Conversation: List'
            )
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
    
    @task(2)
    def update_conversation(self):
        """Update conversation metadata"""
        if not self.conversation_id:
            return
        
        try:
            self.client.patch(
                f'/api/v1/conversations/{self.conversation_id}',
                json={
                    'title': self.data_gen.generate_conversation_title()
                },
                name='Conversation: Update'
            )
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")
    
    @task(1)
    def export_conversation(self):
        """Export conversation"""
        if not self.conversation_id:
            return
        
        format_choice = random.choice(['json', 'markdown', 'text'])
        
        try:
            self.client.get(
                f'/api/v1/conversations/{self.conversation_id}/export',
                params={'format': format_choice},
                name='Conversation: Export'
            )
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
    
    @task(2)
    def get_user_profile(self):
        """Get user profile"""
        try:
            self.client.get(
                '/api/v1/user/me',
                name='User: Get Profile'
            )
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
    
    @task(1)
    def health_check(self):
        """Check API health"""
        try:
            self.client.get(
                '/api/v1/health',
                name='Health: Check'
            )
        except Exception as e:
            logger.error(f"Error checking health: {e}")
    
    @task(1)
    def new_conversation(self):
        """Start a new conversation (simulate user starting fresh)"""
        self.create_conversation()


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("Starting API load test...")
    logger.info(f"Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("API load test completed")
    
    # Generate custom metrics report
    metrics = MetricsCollector()
    metrics.generate_report()
