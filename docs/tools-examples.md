# Tool System Examples

Practical examples demonstrating how to use the Zakera tool integration system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Using Built-in Tools](#using-built-in-tools)
3. [Creating Custom Tools](#creating-custom-tools)
4. [Advanced Usage](#advanced-usage)
5. [Integration with Chat](#integration-with-chat)
6. [Production Patterns](#production-patterns)

## Quick Start

### Basic Tool Execution

```python
from src.tools import get_tool_manager

# Get the tool manager
manager = get_tool_manager()

# Execute a simple calculation
result = await manager.execute_tool(
    "calculator",
    {"expression": "2 + 2"}
)

print(result.data["result"])  # Output: 4
```

### List Available Tools

```python
from src.tools import get_registry

registry = get_registry()

# List all tools
for tool in registry.list_tools():
    print(f"{tool.name}: {tool.description}")

# Output:
# calculator: Evaluates mathematical expressions...
# web_search: Search the web for information...
# code_executor: Execute code in a sandboxed environment...
# weather: Get current weather information...
# datetime: Get current date and time information...
```

## Using Built-in Tools

### Calculator Examples

```python
from src.tools import get_tool_manager

manager = get_tool_manager()

# Basic arithmetic
result = await manager.execute_tool("calculator", {
    "expression": "15 * 8 + 23"
})
print(result.data["result"])  # 143

# Trigonometry
result = await manager.execute_tool("calculator", {
    "expression": "sin(pi/4) + cos(pi/4)"
})
print(result.data["result"])  # ~1.414

# Square roots and logarithms
result = await manager.execute_tool("calculator", {
    "expression": "sqrt(144) + log(1000, 10)"
})
print(result.data["result"])  # 15.0

# With precision control
result = await manager.execute_tool("calculator", {
    "expression": "22 / 7",
    "precision": 4
})
print(result.data["result"])  # 3.1429
```

### Web Search Examples

```python
# Search with DuckDuckGo (no API key needed)
result = await manager.execute_tool("web_search", {
    "query": "latest Python features",
    "num_results": 3,
    "engine": "duckduckgo"
})

for item in result.data["results"]:
    print(f"{item['title']}: {item['url']}")
    print(f"  {item['snippet']}\n")

# Search with Google (requires API key)
result = await manager.execute_tool("web_search", {
    "query": "machine learning tutorials",
    "num_results": 5,
    "engine": "google"
})
```

### Code Executor Examples

```python
# Execute simple Python code
result = await manager.execute_tool("code_executor", {
    "code": """
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
average = total / len(numbers)
print(f"Average: {average}")
average
"""
})

print(result.data["stdout"])  # "Average: 3.0"
print(result.data["result"])  # 3.0

# Data processing example
result = await manager.execute_tool("code_executor", {
    "code": """
data = [10, 20, 30, 40, 50]
squared = [x**2 for x in data]
print(f"Squared: {squared}")
squared
"""
})

# FizzBuzz example
result = await manager.execute_tool("code_executor", {
    "code": """
for i in range(1, 16):
    if i % 15 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)
"""
})
print(result.data["stdout"])
```

### Weather Examples

```python
# Get weather in metric units (Celsius)
result = await manager.execute_tool("weather", {
    "location": "London",
    "units": "metric"
})

weather = result.data["weather"]
print(f"Temperature: {weather['temperature']}°C")
print(f"Conditions: {weather['description']}")
print(f"Humidity: {weather['humidity']}%")

# Get weather in imperial units (Fahrenheit)
result = await manager.execute_tool("weather", {
    "location": "New York,US",
    "units": "imperial"
})

# Use the summary
print(result.data["summary"])
# "New York: 72°F, partly cloudy. Humidity: 65%, Wind: 5.2 m/s"
```

### DateTime Examples

```python
# Get current UTC time
result = await manager.execute_tool("datetime", {
    "timezone": "UTC"
})
print(result.data["datetime"])
print(result.data["weekday"])

# Get time in different timezone
result = await manager.execute_tool("datetime", {
    "timezone": "America/New_York"
})

# Custom format
result = await manager.execute_tool("datetime", {
    "operation": "format",
    "timezone": "Europe/Paris",
    "format": "%A, %B %d, %Y at %I:%M %p"
})
print(result.data["formatted"])
# "Monday, February 12, 2026 at 11:30 PM"
```

## Creating Custom Tools

### Example 1: Text Counter Tool

```python
from typing import List
from src.tools.base import Tool, ToolParameter, ToolParameterType, ToolResult

class TextCounterTool(Tool):
    """Count words, characters, and lines in text."""
    
    @property
    def name(self) -> str:
        return "text_counter"
    
    @property
    def description(self) -> str:
        return "Count words, characters, and lines in text"
    
    @property
    def category(self) -> str:
        return "text"
    
    @property
    def tags(self) -> List[str]:
        return ["text", "analysis", "counter"]
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="Text to analyze",
                required=True
            )
        ]
    
    async def execute(self, text: str, **kwargs) -> ToolResult:
        try:
            word_count = len(text.split())
            char_count = len(text)
            line_count = len(text.splitlines())
            
            return ToolResult.success_result(
                data={
                    "words": word_count,
                    "characters": char_count,
                    "lines": line_count,
                    "average_word_length": char_count / word_count if word_count > 0 else 0
                }
            )
        except Exception as e:
            return ToolResult.error_result(f"Counting failed: {str(e)}")

# Register and use
from src.tools import get_registry

registry = get_registry()
registry.register(TextCounterTool())

result = await manager.execute_tool("text_counter", {
    "text": "Hello world! This is a test."
})
print(result.data)  # {"words": 6, "characters": 28, "lines": 1, ...}
```

### Example 2: API Integration Tool

```python
import httpx
from src.tools.base import Tool, ToolParameter, ToolParameterType, ToolResult

class GitHubUserTool(Tool):
    """Fetch GitHub user information."""
    
    def __init__(self):
        super().__init__()
        self._client = None
    
    @property
    def name(self) -> str:
        return "github_user"
    
    @property
    def description(self) -> str:
        return "Get information about a GitHub user"
    
    @property
    def category(self) -> str:
        return "api"
    
    @property
    def rate_limit(self) -> int:
        return 30  # GitHub's rate limit
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="username",
                type=ToolParameterType.STRING,
                description="GitHub username",
                required=True
            )
        ]
    
    async def initialize(self):
        await super().initialize()
        self._client = httpx.AsyncClient()
    
    async def cleanup(self):
        if self._client:
            await self._client.aclose()
        await super().cleanup()
    
    async def execute(self, username: str, **kwargs) -> ToolResult:
        try:
            response = await self._client.get(
                f"https://api.github.com/users/{username}"
            )
            response.raise_for_status()
            data = response.json()
            
            return ToolResult.success_result(
                data={
                    "username": data["login"],
                    "name": data.get("name"),
                    "bio": data.get("bio"),
                    "public_repos": data["public_repos"],
                    "followers": data["followers"],
                    "following": data["following"],
                    "url": data["html_url"],
                }
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ToolResult.error_result(f"User '{username}' not found")
            return ToolResult.error_result(f"GitHub API error: {e.response.status_code}")
        except Exception as e:
            return ToolResult.error_result(f"Failed to fetch user: {str(e)}")
```

## Advanced Usage

### Parallel Tool Execution

```python
from src.tools import get_tool_manager

manager = get_tool_manager()

# Execute multiple tools at once
results = await manager.execute_tools_parallel([
    ("calculator", {"expression": "100 * 0.15"}),
    ("weather", {"location": "Tokyo", "units": "metric"}),
    ("datetime", {"timezone": "Asia/Tokyo"}),
])

for i, result in enumerate(results):
    if result.success:
        print(f"Result {i}: {result.data}")
    else:
        print(f"Error {i}: {result.error}")
```

### Tool Chaining

```python
# Example: Search for something, then analyze results

chain = [
    {
        "tool_name": "web_search",
        "parameters": {
            "query": "Python asyncio tutorial",
            "num_results": 3
        }
    },
    # Could chain to text analyzer, summarizer, etc.
]

results = await manager.execute_tool_chain(chain)

for i, result in enumerate(results):
    print(f"Step {i + 1}: {'Success' if result.success else 'Failed'}")
    if result.success:
        print(f"  Execution time: {result.execution_time:.3f}s")
```

### Conditional Tool Execution

```python
async def smart_calculation(expression: str):
    """Try calculation, fall back to code execution if needed."""
    
    # Try calculator first
    result = await manager.execute_tool("calculator", {
        "expression": expression
    })
    
    if result.success:
        return result.data["result"]
    
    # If calculator fails, try code executor
    print("Calculator failed, trying code executor...")
    result = await manager.execute_tool("code_executor", {
        "code": expression
    })
    
    if result.success:
        return result.data["result"]
    
    return None

# Use it
value = await smart_calculation("2 + 2")  # Uses calculator
value = await smart_calculation("[x**2 for x in range(5)]")  # Uses code executor
```

## Integration with Chat

### Example 1: Weather-Aware Chatbot

```python
async def handle_user_message(message: str):
    """Process user message with tool support."""
    
    # Simple keyword detection (in production, use AI for intent recognition)
    if "weather" in message.lower():
        # Extract location (simplified)
        words = message.split()
        location_idx = words.index("in") + 1 if "in" in words else -1
        
        if location_idx > 0 and location_idx < len(words):
            location = words[location_idx]
            
            result = await manager.execute_tool("weather", {
                "location": location,
                "units": "metric"
            })
            
            if result.success:
                return result.data["summary"]
    
    # Handle calculation requests
    if any(op in message for op in ["+", "-", "*", "/", "calculate"]):
        # Try to extract expression
        # In production, use more sophisticated parsing
        result = await manager.execute_tool("calculator", {
            "expression": message
        })
        
        if result.success:
            return f"The result is {result.data['result']}"
    
    return "I couldn't process that request with my tools."
```

### Example 2: AI Function Calling

```python
from src.tools import get_registry
import json

async def ai_with_tools(user_message: str, conversation_history: list):
    """AI agent with automatic tool selection."""
    
    # Get available tools
    registry = get_registry()
    tool_schemas = registry.export_schema()
    
    # Call AI with tool schemas
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=conversation_history + [
            {"role": "user", "content": user_message}
        ],
        functions=list(tool_schemas.values()),
        function_call="auto"
    )
    
    message = response.choices[0].message
    
    # Check if AI wants to use a tool
    if message.function_call:
        tool_name = message.function_call.name
        parameters = json.loads(message.function_call.arguments)
        
        # Execute the tool
        result = await manager.execute_tool(tool_name, parameters)
        
        # Send result back to AI
        function_result = {
            "role": "function",
            "name": tool_name,
            "content": json.dumps(result.data if result.success else {"error": result.error})
        }
        
        # Get AI's final response with tool result
        final_response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=conversation_history + [
                {"role": "user", "content": user_message},
                message,
                function_result
            ]
        )
        
        return final_response.choices[0].message.content
    
    return message.content
```

## Production Patterns

### Pattern 1: Robust Tool Execution with Fallbacks

```python
async def execute_with_fallback(
    primary_tool: str,
    fallback_tool: str,
    parameters: dict
):
    """Execute tool with automatic fallback."""
    
    # Try primary tool
    result = await manager.execute_tool(primary_tool, parameters)
    
    if result.success:
        return result
    
    # Log failure and try fallback
    logger.warning(f"{primary_tool} failed: {result.error}")
    logger.info(f"Trying fallback: {fallback_tool}")
    
    result = await manager.execute_tool(fallback_tool, parameters)
    result.metadata["fallback_used"] = True
    result.metadata["primary_tool"] = primary_tool
    
    return result

# Use it
result = await execute_with_fallback(
    primary_tool="google_search",
    fallback_tool="web_search",
    parameters={"query": "Python async", "num_results": 5}
)
```

### Pattern 2: Tool Result Aggregation

```python
async def aggregate_tool_results(tool_calls: list):
    """Execute multiple tools and aggregate results."""
    
    results = await manager.execute_tools_parallel(tool_calls)
    
    aggregated = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_tools": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "total_time": sum(r.execution_time for r in results if r.execution_time),
        "results": {}
    }
    
    for (tool_name, _), result in zip(tool_calls, results):
        aggregated["results"][tool_name] = {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "time": result.execution_time
        }
    
    return aggregated

# Use it
summary = await aggregate_tool_results([
    ("calculator", {"expression": "2 + 2"}),
    ("datetime", {"timezone": "UTC"}),
    ("weather", {"location": "Paris"}),
])

print(f"Executed {summary['total_tools']} tools in {summary['total_time']:.2f}s")
```

### Pattern 3: Cached Expensive Operations

```python
from functools import wraps

def cached_tool_call(cache_ttl: int = 300):
    """Decorator for caching tool calls with custom TTL."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get manager with custom cache settings
            manager = get_tool_manager()
            original_ttl = manager.cache_ttl
            
            try:
                manager.cache_ttl = cache_ttl
                return await func(*args, **kwargs)
            finally:
                manager.cache_ttl = original_ttl
        
        return wrapper
    return decorator

@cached_tool_call(cache_ttl=3600)  # Cache for 1 hour
async def get_weather_cached(location: str):
    result = await manager.execute_tool("weather", {"location": location})
    return result.data
```

### Pattern 4: Rate-Limited API Wrapper

```python
import asyncio
from collections import deque

class RateLimitedToolExecutor:
    """Execute tools with global rate limiting."""
    
    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.calls = deque()
    
    async def execute(self, tool_name: str, parameters: dict):
        """Execute tool with rate limiting."""
        
        # Remove old calls
        now = datetime.utcnow()
        while self.calls and (now - self.calls[0]).seconds >= 60:
            self.calls.popleft()
        
        # Check rate limit
        if len(self.calls) >= self.max_calls:
            wait_time = 60 - (now - self.calls[0]).seconds
            logger.info(f"Rate limit reached, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
        
        # Execute tool
        result = await manager.execute_tool(tool_name, parameters)
        self.calls.append(now)
        
        return result

# Use it
executor = RateLimitedToolExecutor(max_calls_per_minute=30)

for query in search_queries:
    result = await executor.execute("web_search", {"query": query})
```

### Pattern 5: Tool Result Validation

```python
from typing import Callable

async def execute_with_validation(
    tool_name: str,
    parameters: dict,
    validator: Callable[[ToolResult], bool]
):
    """Execute tool and validate result."""
    
    result = await manager.execute_tool(tool_name, parameters)
    
    if not result.success:
        return result
    
    # Validate result
    if not validator(result):
        result.success = False
        result.error = "Result validation failed"
        result.data = None
    
    return result

# Example validator
def validate_positive_number(result: ToolResult) -> bool:
    """Validate that result is a positive number."""
    if not result.success:
        return False
    return result.data.get("result", 0) > 0

# Use it
result = await execute_with_validation(
    "calculator",
    {"expression": "10 - 5"},
    validate_positive_number
)
```

## Error Handling Patterns

### Pattern 1: Graceful Degradation

```python
async def get_info_with_degradation(query: str):
    """Get information with graceful degradation."""
    
    # Try web search first
    result = await manager.execute_tool("web_search", {
        "query": query,
        "num_results": 3
    })
    
    if result.success and result.data["results"]:
        return {"source": "web", "data": result.data["results"]}
    
    # Fall back to providing search URL
    return {
        "source": "manual",
        "data": {
            "message": "Couldn't fetch results automatically",
            "search_url": f"https://www.google.com/search?q={query}"
        }
    }
```

### Pattern 2: Retry with Different Parameters

```python
async def smart_retry(tool_name: str, param_variations: list):
    """Try tool with different parameter variations until success."""
    
    for params in param_variations:
        result = await manager.execute_tool(tool_name, params)
        
        if result.success:
            result.metadata["params_used"] = params
            return result
    
    return ToolResult.error_result(
        "All parameter variations failed"
    )

# Use it
result = await smart_retry("weather", [
    {"location": "NYC"},
    {"location": "New York"},
    {"location": "New York,US"},
])
```

## Testing Tools

### Unit Test Example

```python
import pytest
from src.tools.builtin.calculator import CalculatorTool

@pytest.mark.asyncio
async def test_calculator_addition():
    tool = CalculatorTool()
    result = await tool.execute(expression="5 + 7")
    
    assert result.success
    assert result.data["result"] == 12
    assert result.execution_time is not None

@pytest.mark.asyncio
async def test_calculator_error_handling():
    tool = CalculatorTool()
    result = await tool.execute(expression="invalid expression")
    
    assert not result.success
    assert result.error is not None
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_tool_manager_execution():
    from src.tools import get_tool_manager, get_registry
    
    # Setup
    registry = get_registry()
    manager = get_tool_manager()
    
    # Execute tool
    result = await manager.execute_tool(
        "calculator",
        {"expression": "2 ** 8"}
    )
    
    assert result.success
    assert result.data["result"] == 256
    
    # Check statistics
    stats = manager.get_statistics("calculator")
    assert stats["total_executions"] > 0
```

### Mock External APIs

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_weather_tool_mocked(mock_get):
    """Test weather tool with mocked API."""
    
    # Mock API response
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "name": "London",
        "main": {"temp": 15.5, "humidity": 72},
        "weather": [{"description": "cloudy"}],
        "wind": {"speed": 5.2},
        "dt": 1234567890
    }
    mock_response.raise_for_status = AsyncMock()
    mock_get.return_value = mock_response
    
    # Execute tool
    from src.tools.builtin.weather import WeatherTool
    tool = WeatherTool()
    await tool.initialize()
    
    result = await tool.execute(location="London")
    
    assert result.success
    assert result.data["weather"]["temperature"] == 15.5
```

## Performance Optimization

### Cache Warming

```python
async def warm_cache(tool_configs: list):
    """Pre-populate cache with common queries."""
    
    for tool_name, params in tool_configs:
        await manager.execute_tool(tool_name, params)
    
    print(f"Cache warmed with {len(tool_configs)} entries")

# Warm cache at startup
await warm_cache([
    ("weather", {"location": "London"}),
    ("weather", {"location": "New York"}),
    ("datetime", {"timezone": "UTC"}),
])
```

### Batch Processing

```python
async def batch_process_calculations(expressions: list):
    """Process multiple calculations efficiently."""
    
    # Execute in parallel
    tool_calls = [
        ("calculator", {"expression": expr})
        for expr in expressions
    ]
    
    results = await manager.execute_tools_parallel(tool_calls)
    
    return [
        r.data["result"] if r.success else None
        for r in results
    ]

# Use it
expressions = ["2 + 2", "10 * 5", "sqrt(144)", "log(100, 10)"]
results = await batch_process_calculations(expressions)
print(results)  # [4, 50, 12.0, 2.0]
```

## Monitoring and Debugging

### Log Tool Executions

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("src.tools")
logger.setLevel(logging.DEBUG)

# Execute with detailed logging
result = await manager.execute_tool("calculator", {"expression": "2 + 2"})
```

### Track Performance

```python
async def monitor_tool_performance():
    """Monitor and report tool performance."""
    
    stats = manager.get_statistics()
    
    print(f"Total executions: {stats['total_executions']}")
    print(f"Success rate: {stats['success_rate']:.2f}%")
    print(f"Average time: {stats['average_execution_time']:.3f}s")
    print(f"Cache size: {stats['cache_size']} entries")
    
    # Per-tool statistics
    for tool in registry.list_tools():
        tool_stats = manager.get_statistics(tool.name)
        if tool_stats["total_executions"] > 0:
            print(f"\n{tool.name}:")
            print(f"  Calls: {tool_stats['total_executions']}")
            print(f"  Success rate: {tool_stats['success_rate']:.2f}%")
```

---

For more information, see the [Tool System Documentation](tools.md).
