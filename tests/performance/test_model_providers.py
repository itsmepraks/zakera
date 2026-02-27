"""Model provider performance testing."""

import time
import random
from typing import List, Dict

from locust import HttpUser, TaskSet, task, between, tag

from .config import config
from .utils.auth import AuthHelper
from .utils.data_generator import DataGenerator
from .utils.metrics import CustomMetrics


class ModelProviderBehavior(TaskSet):
    """Task set for testing model providers."""
    
    # List of providers to test
    PROVIDERS = [
        {"provider": "openai", "model": "gpt-3.5-turbo"},
        {"provider": "openai", "model": "gpt-4"},
        {"provider": "anthropic", "model": "claude-3-sonnet-20240229"},
        {"provider": "google", "model": "gemini-1.5-flash"},
        {"provider": "google", "model": "gemini-1.5-pro"},
    ]
    
    def on_start(self):
        """Initialize test session."""
        self.auth_helper = AuthHelper(self.client)
        self.data_gen = DataGenerator()
        self.metrics = CustomMetrics()
        
        self.token = self.auth_helper.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task(40)
    @tag("provider", "openai")
    def test_openai_gpt35(self):
        """Test OpenAI GPT-3.5-Turbo."""
        self._test_provider("openai", "gpt-3.5-turbo")
    
    @task(20)
    @tag("provider", "openai")
    def test_openai_gpt4(self):
        """Test OpenAI GPT-4."""
        self._test_provider("openai", "gpt-4")
    
    @task(20)
    @tag("provider", "anthropic")
    def test_anthropic_claude(self):
        """Test Anthropic Claude."""
        self._test_provider("anthropic", "claude-3-sonnet-20240229")
    
    @task(15)
    @tag("provider", "google")
    def test_google_gemini_flash(self):
        """Test Google Gemini Flash."""
        self._test_provider("google", "gemini-1.5-flash")
    
    @task(5)
    @tag("provider", "google")
    def test_google_gemini_pro(self):
        """Test Google Gemini Pro."""
        self._test_provider("google", "gemini-1.5-pro")
    
    def _test_provider(self, provider: str, model: str):
        """Test a specific provider.
        
        Args:
            provider: Provider name
            model: Model name
        """
        message = self.data_gen.generate_message()
        start_time = time.time()
        
        with self.client.post(
            config.ENDPOINTS["chat"],
            headers=self.headers,
            json={
                "message": message,
                "model": model,
                "provider": provider,
                "stream": False
            },
            catch_response=True,
            name=f"/api/v1/chat [{provider}/{model}]"
        ) as response:
            duration = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Record custom metrics
                self.metrics.record_model_latency(provider, duration)
                
                if "usage" in data:
                    self.metrics.record_token_usage(data["usage"].get("total_tokens", 0))
                
                response.success()
            else:
                self.metrics.record_error(f"{provider}_{response.status_code}")
                response.failure(f"{provider} failed: {response.status_code}")
    
    @task(10)
    @tag("provider", "fallback")
    def test_provider_fallback(self):
        """Test provider fallback mechanism."""
        # Send request with primary and fallback providers
        message = self.data_gen.generate_message()
        
        with self.client.post(
            config.ENDPOINTS["chat"],
            headers=self.headers,
            json={
                "message": message,
                "model": "gpt-3.5-turbo",
                "provider": "openai",
                "fallback_providers": ["google", "anthropic"],
                "stream": False
            },
            catch_response=True,
            name="/api/v1/chat [with-fallback]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                actual_provider = data.get("provider_used", "unknown")
                print(f"Provider used: {actual_provider}")
                response.success()
            else:
                response.failure("Fallback test failed")
    
    @task(5)
    @tag("provider", "streaming")
    def test_streaming_response(self):
        """Test streaming responses."""
        message = self.data_gen.generate_message()
        provider = random.choice(self.PROVIDERS)
        
        start_time = time.time()
        
        with self.client.post(
            config.ENDPOINTS["chat"],
            headers=self.headers,
            json={
                "message": message,
                "model": provider["model"],
                "provider": provider["provider"],
                "stream": True
            },
            stream=True,
            catch_response=True,
            name=f"/api/v1/chat [streaming]"
        ) as response:
            if response.status_code == 200:
                # Read streaming response
                chunks = 0
                for chunk in response.iter_lines():
                    if chunk:
                        chunks += 1
                
                duration = (time.time() - start_time) * 1000
                print(f"Received {chunks} chunks in {duration:.2f}ms")
                response.success()
            else:
                response.failure("Streaming failed")


class ProviderComparisonBehavior(TaskSet):
    """Compare performance across providers."""
    
    def on_start(self):
        """Initialize test session."""
        self.auth_helper = AuthHelper(self.client)
        self.data_gen = DataGenerator()
        self.token = self.auth_helper.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task
    @tag("provider-comparison")
    def compare_all_providers(self):
        """Send same message to all providers and compare."""
        message = self.data_gen.generate_message()
        
        providers = [
            ("openai", "gpt-3.5-turbo"),
            ("google", "gemini-1.5-flash"),
            ("anthropic", "claude-3-sonnet-20240229"),
        ]
        
        results = []
        
        for provider, model in providers:
            start_time = time.time()
            
            try:
                response = self.client.post(
                    config.ENDPOINTS["chat"],
                    headers=self.headers,
                    json={
                        "message": message,
                        "model": model,
                        "provider": provider,
                        "stream": False
                    }
                )
                
                duration = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    results.append({
                        "provider": provider,
                        "model": model,
                        "duration_ms": duration,
                        "tokens": data.get("usage", {}).get("total_tokens", 0)
                    })
            except Exception as e:
                print(f"Provider {provider} error: {e}")
        
        # Log comparison
        if results:
            fastest = min(results, key=lambda x: x["duration_ms"])
            print(f"\nProvider Comparison for: '{message[:50]}...'")
            for r in results:
                print(f"  {r['provider']:12} - {r['duration_ms']:6.0f}ms - {r['tokens']} tokens")
            print(f"  Fastest: {fastest['provider']} ({fastest['duration_ms']:.0f}ms)\n")


class ModelProviderUser(HttpUser):
    """User for model provider testing."""
    
    tasks = {ModelProviderBehavior: 3, ProviderComparisonBehavior: 1}
    wait_time = between(1, 3)
