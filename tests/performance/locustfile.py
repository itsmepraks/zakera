"""
Locust performance testing suite for Zakera AI Chat Agent.

This module provides comprehensive load testing for:
- REST API endpoints
- WebSocket connections
- Model provider interactions
- Authentication flows
- Tool execution

Run with: locust -f tests/performance/locustfile.py
"""

import json
import random
import time
from typing import Dict, List, Optional

from locust import HttpUser, TaskSet, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import websocket


class APIEndpointTasks(TaskSet):
    """Task set for testing REST API endpoints."""
    
    def on_start(self):
        """Initialize user session with authentication."""
        # Login and get token
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"testuser_{random.randint(1000, 9999)}",
            "password": "testpassword123"
        })
        
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Register new user if login fails
            self.client.post("/api/v1/auth/register", json={
                "username": f"testuser_{random.randint(1000, 9999)}",
                "email": f"test{random.randint(1000, 9999)}@example.com",
                "password": "testpassword123"
            })
            response = self.client.post("/api/v1/auth/login", json={
                "username": f"testuser_{random.randint(1000, 9999)}",
                "password": "testpassword123"
            })
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        
        self.conversation_id = None
        self.messages = [
            "What is artificial intelligence?",
            "Explain machine learning in simple terms",
            "How does natural language processing work?",
            "What are neural networks?",
            "Tell me about deep learning"
        ]
    
    @task(5)
    def send_chat_message(self):
        """Test sending chat messages (highest weight)."""
        message = random.choice(self.messages)
        
        with self.client.post(
            "/api/v1/chat/send",
            json={
                "message": message,
                "conversation_id": self.conversation_id,
                "model": random.choice(["gpt-3.5-turbo", "gemini-1.5-flash", "claude-3-haiku"]),
                "stream": False
            },
            headers=self.headers,
            catch_response=True,
            name="/api/v1/chat/send"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.conversation_id = data.get("conversation_id")
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(3)
    def get_conversations(self):
        """Test retrieving conversation list."""
        with self.client.get(
            "/api/v1/conversations",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/conversations"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(2)
    def get_conversation_history(self):
        """Test retrieving conversation history."""
        if not self.conversation_id:
            return
        
        with self.client.get(
            f"/api/v1/conversations/{self.conversation_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/conversations/{id}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(2)
    def search_conversations(self):
        """Test conversation search functionality."""
        with self.client.get(
            f"/api/v1/conversations/search?q={random.choice(['AI', 'machine', 'learning'])}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/conversations/search"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(1)
    def execute_tool(self):
        """Test tool execution."""
        with self.client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "web_search",
                "parameters": {"query": "latest AI news"}
            },
            headers=self.headers,
            catch_response=True,
            name="/api/v1/tools/execute"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(1)
    def export_conversation(self):
        """Test conversation export."""
        if not self.conversation_id:
            return
        
        with self.client.get(
            f"/api/v1/conversations/{self.conversation_id}/export?format=json",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/conversations/{id}/export"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        with self.client.get(
            "/api/v1/monitoring/health",
            catch_response=True,
            name="/api/v1/monitoring/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")


class StreamingChatTasks(TaskSet):
    """Task set for testing streaming chat responses."""
    
    def on_start(self):
        """Initialize user session."""
        # Reuse authentication logic
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"streamuser_{random.randint(1000, 9999)}",
            "password": "testpassword123"
        })
        
        if response.status_code != 200:
            self.client.post("/api/v1/auth/register", json={
                "username": f"streamuser_{random.randint(1000, 9999)}",
                "email": f"stream{random.randint(1000, 9999)}@example.com",
                "password": "testpassword123"
            })
            response = self.client.post("/api/v1/auth/login", json={
                "username": f"streamuser_{random.randint(1000, 9999)}",
                "password": "testpassword123"
            })
        
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task
    def streaming_chat(self):
        """Test streaming chat endpoint."""
        start_time = time.time()
        
        with self.client.post(
            "/api/v1/chat/stream",
            json={
                "message": "Write a detailed explanation of quantum computing",
                "model": "gpt-3.5-turbo",
                "stream": True
            },
            headers=self.headers,
            stream=True,
            catch_response=True,
            name="/api/v1/chat/stream"
        ) as response:
            if response.status_code == 200:
                chunks = 0
                for line in response.iter_lines():
                    if line:
                        chunks += 1
                
                total_time = int((time.time() - start_time) * 1000)
                events.request.fire(
                    request_type="STREAM",
                    name="/api/v1/chat/stream",
                    response_time=total_time,
                    response_length=chunks,
                    exception=None,
                    context={}
                )
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")


class WebSocketTasks(TaskSet):
    """Task set for testing WebSocket connections."""
    
    def on_start(self):
        """Establish WebSocket connection."""
        # Get auth token first
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"wsuser_{random.randint(1000, 9999)}",
            "password": "testpassword123"
        })
        
        if response.status_code != 200:
            self.client.post("/api/v1/auth/register", json={
                "username": f"wsuser_{random.randint(1000, 9999)}",
                "email": f"ws{random.randint(1000, 9999)}@example.com",
                "password": "testpassword123"
            })
            response = self.client.post("/api/v1/auth/login", json={
                "username": f"wsuser_{random.randint(1000, 9999)}",
                "password": "testpassword123"
            })
        
        self.token = response.json().get("access_token")
        self.ws = None
    
    @task
    def websocket_chat(self):
        """Test WebSocket chat interaction."""
        start_time = time.time()
        
        try:
            # Connect to WebSocket
            ws_url = f"ws://localhost:8000/api/v1/ws/chat?token={self.token}"
            self.ws = websocket.create_connection(ws_url, timeout=10)
            
            # Send message
            self.ws.send(json.dumps({
                "type": "message",
                "content": "Hello, how are you?",
                "model": "gpt-3.5-turbo"
            }))
            
            # Receive response
            response = self.ws.recv()
            data = json.loads(response)
            
            total_time = int((time.time() - start_time) * 1000)
            
            events.request.fire(
                request_type="WS",
                name="/api/v1/ws/chat",
                response_time=total_time,
                response_length=len(response),
                exception=None,
                context={}
            )
            
            self.ws.close()
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="WS",
                name="/api/v1/ws/chat",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={}
            )
    
    def on_stop(self):
        """Clean up WebSocket connection."""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


class ModelProviderTasks(TaskSet):
    """Task set for testing different model providers."""
    
    def on_start(self):
        """Initialize user session."""
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"modeluser_{random.randint(1000, 9999)}",
            "password": "testpassword123"
        })
        
        if response.status_code != 200:
            self.client.post("/api/v1/auth/register", json={
                "username": f"modeluser_{random.randint(1000, 9999)}",
                "email": f"model{random.randint(1000, 9999)}@example.com",
                "password": "testpassword123"
            })
            response = self.client.post("/api/v1/auth/login", json={
                "username": f"modeluser_{random.randint(1000, 9999)}",
                "password": "testpassword123"
            })
        
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        self.models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "claude-3-haiku",
            "claude-3-sonnet",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
    
    @task
    def test_model_provider(self):
        """Test different model providers."""
        model = random.choice(self.models)
        
        with self.client.post(
            "/api/v1/chat/send",
            json={
                "message": "What is the capital of France?",
                "model": model,
                "stream": False
            },
            headers=self.headers,
            catch_response=True,
            name=f"/api/v1/chat/send [model={model}]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")


class ZakeraUser(FastHttpUser):
    """
    Main user class for load testing.
    
    Uses FastHttpUser for better performance in high-load scenarios.
    """
    
    # Wait time between tasks (simulates real user behavior)
    wait_time = between(1, 3)
    
    # Task distribution
    tasks = {
        APIEndpointTasks: 10,      # 50% of users
        StreamingChatTasks: 3,     # 15% of users
        WebSocketTasks: 3,         # 15% of users
        ModelProviderTasks: 4,     # 20% of users
    }
    
    # Connection settings
    connection_timeout = 10.0
    network_timeout = 10.0


class NormalLoadUser(ZakeraUser):
    """User class for normal load testing."""
    wait_time = between(2, 5)


class StressTestUser(ZakeraUser):
    """User class for stress testing."""
    wait_time = between(0.5, 1)


class SpikeTestUser(ZakeraUser):
    """User class for spike testing."""
    wait_time = between(0.1, 0.5)


# Event listeners for custom metrics
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize custom metrics collection."""
    print("🚀 Starting Zakera Performance Test Suite")
    print(f"📊 Target: {environment.host}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    print("✅ Test started")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and statistics."""
    print("🏁 Test completed")
    print("\n📊 Final Statistics:")
    
    stats = environment.stats
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min Response Time: {stats.total.min_response_time}ms")
    print(f"Max Response Time: {stats.total.max_response_time}ms")
    print(f"Requests/s: {stats.total.total_rps:.2f}")
    
    if stats.total.num_requests > 0:
        failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        print(f"Failure Rate: {failure_rate:.2f}%")
