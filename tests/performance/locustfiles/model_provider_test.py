"""Model Provider Load Test - Tests all 8 LLM providers

Tests:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude 3)
- Google Gemini (1.5 Pro, Flash)
- Ollama (Local models)
- HuggingFace
- Cohere
- Groq
- Mistral

Metrics:
- Provider-specific latency
- Token usage and costs
- Error rates by provider
- Failover behavior
"""

import json
import time
import os
import sys
import random
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.auth_helper import AuthHelper
from utils.data_generator import DataGenerator
from utils.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class ModelProviderTester(HttpUser):
    """Tests all model providers systematically"""
    
    wait_time = between(1, 3)
    
    # Model configurations for testing
    MODELS = {
        'openai': ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'],
        'anthropic': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
        'gemini': ['gemini-1.5-pro', 'gemini-1.5-flash'],
        'ollama': ['llama-3-8b', 'llama-3-70b', 'mistral-7b', 'codellama'],
        'huggingface': ['meta-llama/Llama-2-7b-chat-hf'],
        'cohere': ['command', 'command-light'],
        'groq': ['llama-3-70b-8192', 'mixtral-8x7b-32768'],
        'mistral': ['mistral-small', 'mistral-medium', 'mistral-large']
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth = AuthHelper()
        self.data_gen = DataGenerator()
        self.api_key = os.getenv('API_KEY')
        self.conversation_id = None
        self.metrics = MetricsCollector()
        self.provider_stats = {}
    
    def on_start(self):
        """Initialize user"""
        if self.api_key:
            self.client.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })
        
        # Create test conversation
        self.create_conversation()
    
    def create_conversation(self):
        """Create a test conversation"""
        try:
            response = self.client.post(
                '/api/v1/conversations',
                json={'title': 'Model Provider Test'},
                name='Setup: Create Conversation'
            )
            if response.status_code == 201:
                self.conversation_id = response.json().get('id')
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
    
    def test_model(self, provider, model, message=None):
        """Test a specific model"""
        if not self.conversation_id:
            self.create_conversation()
        
        if message is None:
            message = self.data_gen.generate_message()
        
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
                name=f'Provider: {provider} ({model})'
            ) as response:
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    response.success()
                    
                    # Record provider-specific metrics
                    self.metrics.record_provider_metrics(
                        provider=provider,
                        model=model,
                        duration=duration,
                        tokens=data.get('usage', {}).get('total_tokens', 0),
                        cost=data.get('cost', 0),
                        success=True
                    )
                    
                    return True
                else:
                    response.failure(f"Status {response.status_code}")
                    self.metrics.record_provider_metrics(
                        provider=provider,
                        model=model,
                        duration=duration,
                        tokens=0,
                        cost=0,
                        success=False
                    )
                    return False
        
        except Exception as e:
            logger.error(f"Error testing {provider}/{model}: {e}")
            return False
    
    # OpenAI Tasks
    @task(10)
    def test_openai_gpt35(self):
        """Test OpenAI GPT-3.5 (most popular)"""
        self.test_model('openai', 'gpt-3.5-turbo')
    
    @task(5)
    def test_openai_gpt4(self):
        """Test OpenAI GPT-4"""
        self.test_model('openai', 'gpt-4-turbo')
    
    # Anthropic Tasks
    @task(7)
    def test_anthropic_haiku(self):
        """Test Claude 3 Haiku (fast)"""
        self.test_model('anthropic', 'claude-3-haiku')
    
    @task(3)
    def test_anthropic_sonnet(self):
        """Test Claude 3 Sonnet"""
        self.test_model('anthropic', 'claude-3-sonnet')
    
    # Google Gemini Tasks
    @task(12)
    def test_gemini_flash(self):
        """Test Gemini 1.5 Flash (fastest, cheapest)"""
        self.test_model('gemini', 'gemini-1.5-flash')
    
    @task(5)
    def test_gemini_pro(self):
        """Test Gemini 1.5 Pro"""
        self.test_model('gemini', 'gemini-1.5-pro')
    
    # Ollama Tasks (Local)
    @task(8)
    def test_ollama_llama(self):
        """Test Ollama Llama 3 (local, free)"""
        self.test_model('ollama', 'llama-3-8b')
    
    @task(3)
    def test_ollama_mistral(self):
        """Test Ollama Mistral (local, free)"""
        self.test_model('ollama', 'mistral-7b')
    
    # HuggingFace Tasks
    @task(4)
    def test_huggingface(self):
        """Test HuggingFace models"""
        self.test_model('huggingface', 'meta-llama/Llama-2-7b-chat-hf')
    
    # Cohere Tasks
    @task(5)
    def test_cohere(self):
        """Test Cohere Command"""
        self.test_model('cohere', 'command')
    
    # Groq Tasks
    @task(6)
    def test_groq(self):
        """Test Groq (ultra-fast)"""
        model = random.choice(['llama-3-70b-8192', 'mixtral-8x7b-32768'])
        self.test_model('groq', model)
    
    # Mistral Tasks
    @task(4)
    def test_mistral(self):
        """Test Mistral AI"""
        model = random.choice(['mistral-small', 'mistral-medium'])
        self.test_model('mistral', model)
    
    @task(2)
    def test_long_context(self):
        """Test models with long context (Gemini Pro, Claude)"""
        long_message = self.data_gen.generate_long_message()
        
        # Test Gemini Pro (2M context)
        self.test_model('gemini', 'gemini-1.5-pro', long_message)
    
    @task(1)
    def test_all_providers_failover(self):
        """Test failover between providers"""
        message = self.data_gen.generate_message()
        
        # Try multiple providers in order
        providers = [
            ('gemini', 'gemini-1.5-flash'),
            ('openai', 'gpt-3.5-turbo'),
            ('anthropic', 'claude-3-haiku')
        ]
        
        for provider, model in providers:
            if self.test_model(provider, model, message):
                break  # Stop on first success
    
    @task(2)
    def cost_comparison_test(self):
        """Compare costs across providers for same task"""
        message = "Explain quantum computing in simple terms."
        
        # Test same message on different providers
        test_models = [
            ('gemini', 'gemini-1.5-flash'),  # Cheapest
            ('openai', 'gpt-3.5-turbo'),
            ('anthropic', 'claude-3-haiku'),
        ]
        
        for provider, model in test_models:
            self.test_model(provider, model, message)
    
    @task(1)
    def speed_comparison_test(self):
        """Compare response speeds"""
        message = "Hi, how are you?"
        
        # Test fast models
        fast_models = [
            ('gemini', 'gemini-1.5-flash'),
            ('groq', 'llama-3-70b-8192'),
            ('openai', 'gpt-3.5-turbo'),
        ]
        
        for provider, model in fast_models:
            self.test_model(provider, model, message)


class ProviderStressTest(HttpUser):
    """Stress test specific providers"""
    
    wait_time = between(0.5, 2)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.getenv('API_KEY')
        self.data_gen = DataGenerator()
        self.metrics = MetricsCollector()
    
    def on_start(self):
        if self.api_key:
            self.client.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })
    
    @task
    def rapid_fire_requests(self):
        """Send rapid requests to test rate limiting and queueing"""
        provider = random.choice(['gemini', 'openai', 'anthropic'])
        
        models = {
            'gemini': 'gemini-1.5-flash',
            'openai': 'gpt-3.5-turbo',
            'anthropic': 'claude-3-haiku'
        }
        
        model = models[provider]
        message = self.data_gen.generate_short_message()
        
        try:
            self.client.post(
                '/api/v1/chat/send',
                json={
                    'message': message,
                    'model': model,
                    'stream': False
                },
                name=f'Stress: {provider}'
            )
        except Exception as e:
            logger.error(f"Stress test error: {e}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("Starting model provider load test...")
    logger.info("Testing 8 providers: OpenAI, Anthropic, Gemini, Ollama, HuggingFace, Cohere, Groq, Mistral")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("Model provider load test completed")
    
    # Generate provider comparison report
    metrics = MetricsCollector()
    metrics.generate_provider_report()
