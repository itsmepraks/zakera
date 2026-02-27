"""Tool execution performance testing."""

import time
import random
from typing import Dict, Any

from locust import HttpUser, TaskSet, task, between, tag

from .config import config
from .utils.auth import AuthHelper
from .utils.data_generator import DataGenerator
from .utils.metrics import CustomMetrics


class ToolExecutionBehavior(TaskSet):
    """Task set for testing tool executions."""
    
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
    
    @task(30)
    @tag("tools", "calculator")
    def test_calculator_tool(self):
        """Test calculator tool execution."""
        expressions = [
            "2 + 2",
            "100 * 50",
            "(10 + 5) * 3",
            "sqrt(144)",
            "2 ** 10"
        ]
        
        self._execute_tool(
            "calculator",
            {"expression": random.choice(expressions)}
        )
    
    @task(25)
    @tag("tools", "search")
    def test_web_search_tool(self):
        """Test web search tool."""
        queries = [
            "Python programming tips",
            "machine learning basics",
            "latest tech news",
            "cloud computing trends",
            "API design best practices"
        ]
        
        self._execute_tool(
            "web_search",
            {"query": random.choice(queries), "limit": 5}
        )
    
    @task(20)
    @tag("tools", "code")
    def test_code_executor_tool(self):
        """Test code execution tool."""
        code_samples = [
            {"language": "python", "code": "print('Hello, World!')"},
            {"language": "python", "code": "result = sum([1, 2, 3, 4, 5])\nprint(result)"},
            {"language": "javascript", "code": "console.log('Test');"},
        ]
        
        sample = random.choice(code_samples)
        self._execute_tool("code_executor", sample)
    
    @task(15)
    @tag("tools", "weather")
    def test_weather_tool(self):
        """Test weather lookup tool."""
        cities = ["New York", "London", "Tokyo", "Paris", "Sydney"]
        
        self._execute_tool(
            "weather",
            {"location": random.choice(cities)}
        )
    
    @task(10)
    @tag("tools", "translation")
    def test_translation_tool(self):
        """Test translation tool."""
        self._execute_tool(
            "translator",
            {
                "text": "Hello, how are you?",
                "target_language": random.choice(["es", "fr", "de", "ja"])
            }
        )
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]):
        """Execute a tool and measure performance.
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
        """
        start_time = time.time()
        
        with self.client.post(
            f"{config.ENDPOINTS['tools']}/{tool_name}/execute",
            headers=self.headers,
            json=parameters,
            catch_response=True,
            name=f"/api/v1/tools/{tool_name}/execute"
        ) as response:
            duration = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if result is cached
                is_cached = data.get("cached", False)
                cache_status = "HIT" if is_cached else "MISS"
                
                print(f"Tool {tool_name}: {duration:.0f}ms [Cache: {cache_status}]")
                
                response.success()
            else:
                self.metrics.record_error(f"tool_{tool_name}_error")
                response.failure(f"Tool {tool_name} failed: {response.status_code}")
    
    @task(20)
    @tag("tools", "chat-with-tools")
    def test_chat_with_tools(self):
        """Test chat with automatic tool selection."""
        messages = [
            "What's 25 * 4?",
            "Search for Python tutorials",
            "What's the weather in Tokyo?",
            "Translate 'thank you' to Spanish",
            "Execute this Python code: print(2+2)"
        ]
        
        message = random.choice(messages)
        
        with self.client.post(
            config.ENDPOINTS["chat"],
            headers=self.headers,
            json={
                "message": message,
                "model": "gpt-3.5-turbo",
                "enable_tools": True,
                "stream": False
            },
            catch_response=True,
            name="/api/v1/chat [with-tools]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                tools_used = data.get("tools_used", [])
                
                if tools_used:
                    print(f"Tools used: {', '.join(tools_used)}")
                
                response.success()
            else:
                response.failure("Chat with tools failed")


class ToolCachingBehavior(TaskSet):
    """Test tool result caching performance."""
    
    def on_start(self):
        """Initialize test session."""
        self.auth_helper = AuthHelper(self.client)
        self.token = self.auth_helper.login()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @task
    @tag("tools", "caching")
    def test_cache_performance(self):
        """Test cache hit vs miss performance."""
        # Same calculation multiple times to test caching
        expression = "123 * 456"
        
        times = []
        
        for i in range(5):
            start_time = time.time()
            
            response = self.client.post(
                f"{config.ENDPOINTS['tools']}/calculator/execute",
                headers=self.headers,
                json={"expression": expression}
            )
            
            duration = (time.time() - start_time) * 1000
            times.append(duration)
            
            if response.status_code == 200:
                data = response.json()
                is_cached = data.get("cached", False)
                print(f"Request {i+1}: {duration:.0f}ms [Cached: {is_cached}]")
        
        # Log cache effectiveness
        if len(times) > 1:
            first_time = times[0]
            avg_cached = sum(times[1:]) / len(times[1:])
            speedup = first_time / avg_cached if avg_cached > 0 else 0
            print(f"Cache speedup: {speedup:.2f}x")


class ToolExecutionUser(HttpUser):
    """User for tool execution testing."""
    
    tasks = {ToolExecutionBehavior: 4, ToolCachingBehavior: 1}
    wait_time = between(1, 3)
