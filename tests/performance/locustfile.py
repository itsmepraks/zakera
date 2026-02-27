"""Main Locust test file for Zakera AI Chat Agent performance testing.

Usage:
    # Normal load test
    locust -f tests/performance/locustfile.py --host http://localhost:8000 --tags normal
    
    # Stress test
    locust -f tests/performance/locustfile.py --host http://localhost:8000 --tags stress
    
    # With web UI
    locust -f tests/performance/locustfile.py --host http://localhost:8000
    
    # Headless with HTML report
    locust -f tests/performance/locustfile.py \
        --host http://localhost:8000 \
        --users 50 \
        --spawn-rate 5 \
        --run-time 5m \
        --headless \
        --html reports/performance.html
"""

import json
import random
import time
from typing import Any, Dict

from locust import HttpUser, TaskSet, between, tag, task
from locust.contrib.fasthttp import FastHttpUser

from .config import config, get_scenario_config
from .utils.auth import AuthHelper
from .utils.data_generator import DataGenerator
from .utils.metrics import CustomMetrics


class ChatBehavior(TaskSet):
    """Task set for chat-related operations."""
    
    def on_start(self):
        """Initialize user session."""
        self.auth_helper = AuthHelper(self.client)
        self.data_gen = DataGenerator()
        self.metrics = CustomMetrics()
        
        # Login and get token
        self.token = self.auth_helper.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Create initial conversation
        self.conversation_id = None
        self._create_conversation()
    
    def _create_conversation(self):
        """Create a new conversation."""
        with self.client.post(
            config.ENDPOINTS["conversations"],
            headers=self.headers,
            json={"title": "Performance Test Conversation"},
            catch_response=True
        ) as response:
            if response.status_code == 201:
                self.conversation_id = response.json()["id"]
                response.success()
            else:
                response.failure(f"Failed to create conversation: {response.status_code}")
    
    @task(70)
    @tag("normal", "stress", "spike")
    def send_message(self):
        """Send a chat message."""
        if not self.conversation_id:
            self._create_conversation()
        
        message = random.choice(config.TEST_MESSAGES)
        start_time = time.time()
        
        with self.client.post(
            config.ENDPOINTS["chat"],
            headers=self.headers,
            json={
                "message": message,
                "conversation_id": self.conversation_id,
                "model": config.DEFAULT_MODEL,
                "stream": False
            },
            catch_response=True,
            name="/api/v1/chat"
        ) as response:
            duration = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                self.metrics.record_model_latency(
                    config.PROVIDER,
                    duration
                )
                if "usage" in data:
                    self.metrics.record_token_usage(
                        data["usage"].get("total_tokens", 0)
                    )
                response.success()
            else:
                response.failure(f"Send message failed: {response.status_code}")
    
    @task(10)
    @tag("normal", "stress")
    def list_conversations(self):
        """List user conversations."""
        with self.client.get(
            config.ENDPOINTS["conversations"],
            headers=self.headers,
            catch_response=True,
            name="/api/v1/conversations"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List conversations failed: {response.status_code}")
    
    @task(5)
    @tag("normal")
    def get_conversation(self):
        """Get conversation details."""
        if not self.conversation_id:
            return
        
        with self.client.get(
            f"{config.ENDPOINTS['conversations']}/{self.conversation_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/conversations/{id}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get conversation failed: {response.status_code}")
    
    @task(3)
    @tag("normal")
    def export_conversation(self):
        """Export conversation."""
        if not self.conversation_id:
            return
        
        export_format = random.choice(["json", "markdown", "text"])
        
        with self.client.get(
            config.ENDPOINTS["export"].format(conversation_id=self.conversation_id),
            headers=self.headers,
            params={"format": export_format},
            catch_response=True,
            name="/api/v1/conversations/{id}/export"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Export failed: {response.status_code}")
    
    @task(2)
    @tag("normal", "stress")
    def list_providers(self):
        """List available model providers."""
        with self.client.get(
            config.ENDPOINTS["providers"],
            headers=self.headers,
            catch_response=True,
            name="/api/v1/models/providers"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List providers failed: {response.status_code}")
    
    @task(10)
    @tag("normal", "stress", "spike", "endurance")
    def health_check(self):
        """Check API health."""
        with self.client.get(
            config.ENDPOINTS["health"],
            catch_response=True,
            name="/api/v1/monitoring/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class ConversationFlowBehavior(TaskSet):
    """Task set for complete conversation flow."""
    
    def on_start(self):
        """Initialize user session."""
        self.auth_helper = AuthHelper(self.client)
        self.token = self.auth_helper.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task
    @tag("endurance")
    def complete_conversation_flow(self):
        """Execute a complete conversation workflow."""
        # 1. Create conversation
        with self.client.post(
            config.ENDPOINTS["conversations"],
            headers=self.headers,
            json={"title": "Flow Test"},
            catch_response=True
        ) as response:
            if response.status_code != 201:
                response.failure("Failed to create conversation")
                return
            conversation_id = response.json()["id"]
            response.success()
        
        # 2. Send multiple messages
        for i in range(5):
            message = random.choice(config.TEST_MESSAGES)
            with self.client.post(
                config.ENDPOINTS["chat"],
                headers=self.headers,
                json={
                    "message": message,
                    "conversation_id": conversation_id,
                    "model": config.DEFAULT_MODEL
                },
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Message {i} failed")
            
            time.sleep(random.uniform(1, 3))
        
        # 3. Export conversation
        with self.client.get(
            config.ENDPOINTS["export"].format(conversation_id=conversation_id),
            headers=self.headers,
            params={"format": "json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Export failed")
        
        # 4. Delete conversation
        with self.client.delete(
            f"{config.ENDPOINTS['conversations']}/{conversation_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 204]:
                response.success()
            else:
                response.failure("Delete failed")


class ZakeraUser(FastHttpUser):
    """Main user class for load testing."""
    
    # Use FastHttpUser for better performance
    tasks = {ChatBehavior: 3, ConversationFlowBehavior: 1}
    
    # Wait time between tasks
    scenario_config = get_scenario_config()
    wait_time = between(
        scenario_config.get("min_wait", config.MIN_WAIT),
        scenario_config.get("max_wait", config.MAX_WAIT)
    )
    
    # Connection settings
    connection_timeout = 30.0
    network_timeout = 30.0
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.start_time = time.time()
        print(f"User {self.environment.runner.user_count} started")
    
    def on_stop(self):
        """Called when a simulated user stops."""
        duration = time.time() - self.start_time
        print(f"User stopped after {duration:.2f} seconds")


class WebSocketUser(HttpUser):
    """User class for WebSocket testing."""
    
    wait_time = between(1, 3)
    
    @task
    @tag("websocket")
    def websocket_chat(self):
        """Test WebSocket chat functionality."""
        # WebSocket testing requires separate implementation
        # See test_websocket.py for details
        pass


# Event hooks for custom reporting
from locust import events


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print(f"\n{'='*80}")
    print(f"Starting Performance Test")
    print(f"Scenario: {config.SCENARIO}")
    print(f"Host: {environment.host}")
    print(f"Users: {config.USERS}")
    print(f"Spawn Rate: {config.SPAWN_RATE}")
    print(f"Run Time: {config.RUN_TIME}")
    print(f"{'='*80}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print(f"\n{'='*80}")
    print(f"Performance Test Completed")
    print(f"Total Requests: {environment.stats.total.num_requests}")
    print(f"Total Failures: {environment.stats.total.num_failures}")
    print(f"Failure Rate: {environment.stats.total.fail_ratio:.2%}")
    print(f"Average Response Time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Median Response Time: {environment.stats.total.median_response_time:.2f}ms")
    print(f"95th Percentile: {environment.stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th Percentile: {environment.stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Max Response Time: {environment.stats.total.max_response_time:.2f}ms")
    print(f"Requests per Second: {environment.stats.total.total_rps:.2f}")
    print(f"{'='*80}\n")
    
    # Check thresholds
    p95 = environment.stats.total.get_response_time_percentile(0.95)
    error_rate = environment.stats.total.fail_ratio * 100
    
    failures = []
    if p95 > config.THRESHOLDS["p95_latency_ms"]:
        failures.append(f"P95 latency ({p95:.2f}ms) exceeds threshold ({config.THRESHOLDS['p95_latency_ms']}ms)")
    
    if error_rate > config.THRESHOLDS["error_rate_percent"]:
        failures.append(f"Error rate ({error_rate:.2f}%) exceeds threshold ({config.THRESHOLDS['error_rate_percent']}%)")
    
    if failures:
        print("\n⚠️  PERFORMANCE THRESHOLD FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        print()
    else:
        print("\n✅ All performance thresholds met!\n")
