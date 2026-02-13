```
# Tool Integration System Documentation

## Overview

The Zakera tool system provides a powerful, extensible framework for augmenting the AI agent with external capabilities. Tools can access APIs, perform computations, execute code, and more.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tool System                           │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐        ┌──────────────┐               │
│  │    Tool      │◄───────│   Tool       │               │
│  │   Registry   │        │   Manager    │               │
│  └──────────────┘        └──────────────┘               │
│         │                       │                        │
│         │ discovers             │ executes               │
│         ▼                       ▼                        │
│  ┌──────────────────────────────────────┐               │
│  │         Built-in Tools                │               │
│  ├──────────────────────────────────────┤               │
│  │ • Calculator    • Weather             │               │
│  │ • Web Search    • DateTime            │               │
│  │ • Code Executor                       │               │
│  └──────────────────────────────────────┘               │
│                                                           │
│  ┌──────────────────────────────────────┐               │
│  │        Custom Tools                   │               │
│  │  (User-defined plugins)               │               │
│  └──────────────────────────────────────┘               │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Tool Base Class (`src/tools/base.py`)

All tools inherit from the `Tool` abstract base class:

```python
from src.tools.base import Tool, ToolParameter, ToolParameterType, ToolResult

class MyCustomTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of what the tool does"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type=ToolParameterType.STRING,
                description="Input parameter",
                required=True
            )
        ]
    
    async def execute(self, input: str, **kwargs) -> ToolResult:
        # Tool logic here
        return ToolResult.success_result(data={"output": "result"})
```

### 2. Tool Registry (`src/tools/registry.py`)

Manages tool discovery and retrieval:

```python
from src.tools import get_registry

registry = get_registry()

# List all tools
tools = registry.list_tools()

# Get specific tool
tool = registry.get("calculator")

# Search tools
results = registry.search("math")

# Register custom tool
registry.register(MyCustomTool())
```

### 3. Tool Manager (`src/tools/manager.py`)

Handles tool execution with caching and rate limiting:

```python
from src.tools import get_tool_manager

manager = get_tool_manager()

# Execute a tool
result = await manager.execute_tool(
    "calculator",
    {"expression": "2 + 2"}
)

# Execute tools in parallel
results = await manager.execute_tools_parallel([
    ("calculator", {"expression": "10 * 5"}),
    ("weather", {"location": "London"}),
])

# Execute tool chain
chain = [
    {"tool_name": "calculator", "parameters": {"expression": "100 / 4"}},
    {"tool_name": "calculator", "parameters": {"expression": "result * 2"}}
]
results = await manager.execute_tool_chain(chain)
```

## Built-in Tools

### Calculator

Mathematical expression evaluator with safe execution.

**Parameters:**
- `expression` (string, required): Math expression to evaluate
- `precision` (integer, optional): Decimal places for result

**Examples:**
```python
# Basic arithmetic
result = await manager.execute_tool("calculator", {
    "expression": "2 + 2"
})  # Result: 4

# Trigonometry
result = await manager.execute_tool("calculator", {
    "expression": "sin(pi / 2)"
})  # Result: 1.0

# Complex expressions
result = await manager.execute_tool("calculator", {
    "expression": "sqrt(16) + log(100, 10)",
    "precision": 2
})  # Result: 6.0
```

**Supported Functions:**
- Arithmetic: `+, -, *, /, **, %, //`
- Functions: `sqrt, pow, exp, log, log10, log2`
- Trigonometry: `sin, cos, tan, asin, acos, atan`
- Constants: `pi, e, tau`
- Utilities: `abs, round, min, max, ceil, floor`

### Web Search

Search the internet for information.

**Parameters:**
- `query` (string, required): Search query
- `num_results` (integer, optional): Number of results (1-10, default: 5)
- `engine` (string, optional): Search engine (google, bing, duckduckgo)

**Examples:**
```python
# Search with DuckDuckGo (no API key needed)
result = await manager.execute_tool("web_search", {
    "query": "latest AI developments",
    "num_results": 5
})

# Search with Google (requires API key)
result = await manager.execute_tool("web_search", {
    "query": "Python async programming",
    "num_results": 3,
    "engine": "google"
})
```

**Configuration:**
```bash
# Google Custom Search
export GOOGLE_SEARCH_API_KEY=your_api_key
export GOOGLE_SEARCH_ENGINE_ID=your_engine_id

# Bing Search
export BING_SEARCH_API_KEY=your_api_key
```

### Code Executor

Execute code in a sandboxed environment.

**Parameters:**
- `code` (string, required): Code to execute
- `language` (string, optional): Programming language (currently: python)

**Examples:**
```python
# Execute Python code
result = await manager.execute_tool("code_executor", {
    "code": """
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
print(f"Sum: {total}")
total
"""
})
# Returns: stdout, stderr, and result value

# Expression evaluation
result = await manager.execute_tool("code_executor", {
    "code": "[x**2 for x in range(5)]"
})
# Result: [0, 1, 4, 9, 16]
```

**Security Features:**
- Restricted builtins (no file I/O, imports)
- Execution timeout (5 seconds)
- Output size limits
- No network access

**Warning:** For production use, consider Docker-based sandboxing for enhanced security.

### Weather

Get current weather information for locations.

**Parameters:**
- `location` (string, required): City name or "city,country"
- `units` (string, optional): metric, imperial, or standard

**Examples:**
```python
# Get weather in Celsius
result = await manager.execute_tool("weather", {
    "location": "London",
    "units": "metric"
})

# Get weather in Fahrenheit
result = await manager.execute_tool("weather", {
    "location": "New York,US",
    "units": "imperial"
})
```

**Configuration:**
```bash
export OPENWEATHER_API_KEY=your_api_key
```

Get a free API key at: https://openweathermap.org/api

### DateTime

Get current date and time information.

**Parameters:**
- `operation` (string, optional): current, format, convert, calculate
- `timezone` (string, optional): Timezone name (e.g., "America/New_York")
- `format` (string, optional): strftime format string

**Examples:**
```python
# Get current time in UTC
result = await manager.execute_tool("datetime", {
    "timezone": "UTC"
})

# Get time in specific timezone
result = await manager.execute_tool("datetime", {
    "timezone": "America/New_York"
})

# Custom format
result = await manager.execute_tool("datetime", {
    "operation": "format",
    "timezone": "Europe/London",
    "format": "%B %d, %Y at %I:%M %p"
})
```

## API Endpoints

### List All Tools

```http
GET /api/tools?category=computation&enabled_only=true
```

**Response:**
```json
[
  {
    "name": "calculator",
    "description": "Evaluates mathematical expressions...",
    "version": "1.0.0",
    "category": "computation",
    "tags": ["math", "calculator"],
    "parameters": [...],
    "enabled": true
  }
]
```

### Get Tool Information

```http
GET /api/tools/{tool_name}
```

**Response:**
```json
{
  "name": "calculator",
  "description": "Evaluates mathematical expressions safely...",
  "parameters": [
    {
      "name": "expression",
      "type": "string",
      "description": "Mathematical expression to evaluate",
      "required": true
    }
  ]
}
```

### Execute Tool

```http
POST /api/tools/execute
Content-Type: application/json

{
  "tool_name": "calculator",
  "parameters": {
    "expression": "2 + 2"
  },
  "use_cache": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "result": 4,
    "expression": "2 + 2"
  },
  "execution_time": 0.002,
  "metadata": {}
}
```

### Execute Tool Chain

```http
POST /api/tools/execute-chain
Content-Type: application/json

{
  "steps": [
    {
      "tool_name": "weather",
      "parameters": {"location": "London"}
    },
    {
      "tool_name": "calculator",
      "parameters": {"expression": "temperature * 9/5 + 32"},
      "output_mapping": {"temperature": "temperature"}
    }
  ]
}
```

### Get Tool Statistics

```http
GET /api/tools/statistics?tool_name=calculator
```

**Response:**
```json
{
  "total_executions": 150,
  "successful_executions": 148,
  "failed_executions": 2,
  "success_rate": 98.67,
  "average_execution_time": 0.015
}
```

## Creating Custom Tools

### Step 1: Create Tool Class

```python
# src/tools/custom/my_tool.py

from typing import List
from src.tools.base import Tool, ToolParameter, ToolParameterType, ToolResult

class MyCustomTool(Tool):
    @property
    def name(self) -> str:
        return "my_custom_tool"
    
    @property
    def description(self) -> str:
        return "Description of what my tool does"
    
    @property
    def category(self) -> str:
        return "custom"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input_text",
                type=ToolParameterType.STRING,
                description="Text to process",
                required=True
            ),
            ToolParameter(
                name="option",
                type=ToolParameterType.STRING,
                description="Processing option",
                required=False,
                default="standard",
                enum=["standard", "advanced"]
            )
        ]
    
    async def execute(self, input_text: str, option: str = "standard", **kwargs) -> ToolResult:
        try:
            # Your tool logic here
            result = f"Processed: {input_text} with {option} option"
            
            return ToolResult.success_result(
                data={"output": result},
                metadata={"option_used": option}
            )
        except Exception as e:
            return ToolResult.error_result(f"Processing failed: {str(e)}")
```

### Step 2: Register Tool

```python
from src.tools import get_registry
from my_tool import MyCustomTool

# Register the tool
registry = get_registry()
registry.register(MyCustomTool())
```

### Step 3: Use Tool

```python
from src.tools import get_tool_manager

manager = get_tool_manager()
result = await manager.execute_tool(
    "my_custom_tool",
    {"input_text": "Hello, world!", "option": "advanced"}
)
```

## Advanced Features

### Result Caching

Tools automatically cache successful results for 5 minutes:

```python
manager = get_tool_manager()

# First call - executes tool
result1 = await manager.execute_tool("weather", {"location": "London"})

# Second call within 5 minutes - returns cached result
result2 = await manager.execute_tool("weather", {"location": "London"})
assert result2.metadata["from_cache"] == True

# Disable caching for specific call
result3 = await manager.execute_tool(
    "weather",
    {"location": "London"},
    use_cache=False
)

# Clear cache
manager.clear_cache("weather")  # Clear specific tool
manager.clear_cache()  # Clear all
```

### Rate Limiting

Tools can specify rate limits:

```python
class MyTool(Tool):
    @property
    def rate_limit(self) -> Optional[int]:
        return 10  # 10 calls per minute
```

The manager automatically enforces rate limits and returns errors when exceeded.

### Retries

Automatic retries with exponential backoff:

```python
# Enable retries (default: 3 attempts)
result = await manager.execute_tool(
    "web_search",
    {"query": "test"},
    retry_on_failure=True  # Default
)

# Disable retries
result = await manager.execute_tool(
    "web_search",
    {"query": "test"},
    retry_on_failure=False
)
```

### Parallel Execution

Execute multiple tools simultaneously:

```python
results = await manager.execute_tools_parallel([
    ("calculator", {"expression": "2 + 2"}),
    ("weather", {"location": "London"}),
    ("datetime", {"timezone": "UTC"}),
])

for result in results:
    if result.success:
        print(result.data)
```

### Tool Chains

Chain tools where each output feeds the next:

```python
chain = [
    {
        "tool_name": "web_search",
        "parameters": {"query": "current temperature Paris", "num_results": 1}
    },
    {
        "tool_name": "weather",
        "parameters": {"location": "Paris"},
    }
]

results = await manager.execute_tool_chain(chain)
```

## Integration with Chat System

### Function Calling

Tools can be exposed to AI models as functions:

```python
from src.tools import get_registry

registry = get_registry()
schemas = registry.export_schema()

# Use with OpenAI
import openai

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's 25 * 4?"}],
    functions=list(schemas.values())
)

# If model calls a function
if response.choices[0].finish_reason == "function_call":
    function_call = response.choices[0].message.function_call
    tool_name = function_call.name
    parameters = json.loads(function_call.arguments)
    
    # Execute the tool
    result = await manager.execute_tool(tool_name, parameters)
```

### Automatic Tool Selection

The AI can automatically select and use appropriate tools:

```python
# In your chat endpoint
from src.tools import get_tool_manager, get_registry

async def process_message(user_message: str):
    # Get available tools
    registry = get_registry()
    tool_schemas = registry.export_schema()
    
    # Send to AI with tool schemas
    response = await ai_provider.generate(
        messages=[{"role": "user", "content": user_message}],
        tools=tool_schemas
    )
    
    # Execute tool if AI requests it
    if response.tool_calls:
        manager = get_tool_manager()
        
        for tool_call in response.tool_calls:
            result = await manager.execute_tool(
                tool_call.name,
                tool_call.parameters
            )
            
            # Send result back to AI
            # ...
```

## Configuration

### Environment Variables

```bash
# Search APIs
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_engine_id
BING_SEARCH_API_KEY=your_bing_api_key

# Weather API
OPENWEATHER_API_KEY=your_openweather_api_key

# Tool System
TOOL_CACHE_TTL=300  # Cache TTL in seconds
TOOL_MAX_RETRIES=3   # Max retry attempts
ENABLE_TOOL_CACHE=true
ENABLE_TOOL_RATE_LIMITING=true
```

### Tool Configuration

Tools can be configured programmatically:

```python
manager = get_tool_manager()
manager.cache_ttl = 600  # 10 minutes
manager.max_retries = 5
manager.enable_cache = True
manager.enable_rate_limiting = True
```

## Monitoring and Debugging

### Execution History

```python
# Get execution history
history = manager.get_execution_history(tool_name="calculator", limit=50)

for entry in history:
    print(f"{entry['timestamp']}: {entry['tool_name']} - {entry['success']}")
```

### Statistics

```python
# Overall statistics
stats = manager.get_statistics()
print(f"Success rate: {stats['success_rate']}%")
print(f"Average time: {stats['average_execution_time']}s")

# Per-tool statistics
calc_stats = manager.get_statistics("calculator")
```

### Logging

Enable debug logging for tools:

```python
import logging

logging.getLogger("src.tools").setLevel(logging.DEBUG)
```

## Error Handling

Tools return `ToolResult` objects with success/error information:

```python
result = await manager.execute_tool("calculator", {"expression": "invalid"})

if result.success:
    print(f"Result: {result.data}")
else:
    print(f"Error: {result.error}")
    print(f"Execution time: {result.execution_time}s")
```

## Testing Tools

### Unit Testing

```python
import pytest
from src.tools.builtin.calculator import CalculatorTool

@pytest.mark.asyncio
async def test_calculator():
    tool = CalculatorTool()
    result = await tool.execute(expression="2 + 2")
    
    assert result.success
    assert result.data["result"] == 4
```

### Integration Testing

```python
from src.tools import get_tool_manager

@pytest.mark.asyncio
async def test_tool_execution():
    manager = get_tool_manager()
    result = await manager.execute_tool("calculator", {"expression": "10 / 2"})
    
    assert result.success
    assert result.data["result"] == 5.0
```

## Best Practices

### 1. Error Handling

Always return `ToolResult` objects, never raise exceptions from `execute()`:

```python
async def execute(self, **parameters) -> ToolResult:
    try:
        # Tool logic
        return ToolResult.success_result(data=result)
    except Exception as e:
        return ToolResult.error_result(f"Failed: {str(e)}")
```

### 2. Resource Management

Use `initialize()` and `cleanup()` for resources:

```python
class MyTool(Tool):
    async def initialize(self):
        await super().initialize()
        self.client = httpx.AsyncClient()
    
    async def cleanup(self):
        await self.client.aclose()
        await super().cleanup()
```

### 3. Validation

Leverage parameter validation:

```python
ToolParameter(
    name="count",
    type=ToolParameterType.INTEGER,
    min_value=1,
    max_value=100,
    required=True
)
```

### 4. Timeouts

Set appropriate timeouts for tools:

```python
@property
def timeout(self) -> int:
    return 30  # seconds
```

### 5. Rate Limiting

Protect external APIs with rate limits:

```python
@property
def rate_limit(self) -> Optional[int]:
    return 20  # calls per minute
```

## Troubleshooting

### Tool Not Found

```
ToolNotFoundError: Tool 'my_tool' not found in registry
```

**Solution:** Ensure tool is registered. Check that tool class is in `builtin/` directory or manually registered.

### Rate Limit Exceeded

```
Rate limit exceeded for tool 'web_search'
```

**Solution:** Wait before making more calls, or increase rate limit in tool configuration.

### Timeout Errors

```
Tool execution timed out after 30 seconds
```

**Solution:** Optimize tool logic, increase timeout, or break into smaller operations.

### API Key Errors

```
Weather API not configured
```

**Solution:** Set required environment variables for the tool.

## Performance Optimization

### 1. Use Caching

Enable caching for expensive operations:

```python
manager.enable_cache = True
manager.cache_ttl = 600  # 10 minutes
```

### 2. Parallel Execution

Execute independent tools in parallel:

```python
results = await manager.execute_tools_parallel([
    ("tool1", params1),
    ("tool2", params2),
])
```

### 3. Async All The Way

Always use `async def` for tool execution:

```python
async def execute(self, **params) -> ToolResult:
    result = await some_async_operation()
    return ToolResult.success_result(data=result)
```

## Security Considerations

1. **Input Validation**: Always validate tool parameters
2. **Sandboxing**: Use restricted environments for code execution
3. **API Key Security**: Store API keys in environment variables
4. **Rate Limiting**: Prevent abuse with rate limits
5. **Timeout Protection**: Prevent long-running operations
6. **Output Sanitization**: Sanitize tool outputs before displaying to users

## Future Enhancements

- [ ] Docker-based code execution for enhanced security
- [ ] More language support for code executor
- [ ] Vector database integration for semantic search
- [ ] File operations with secure sandboxing
- [ ] Database query tools
- [ ] Browser automation tools
- [ ] Image generation and analysis
- [ ] Audio/video processing
- [ ] Custom tool marketplace

## Contributing

To contribute a new tool:

1. Create tool class in `src/tools/builtin/` or `src/tools/custom/`
2. Inherit from `Tool` base class
3. Implement required methods
4. Add comprehensive docstrings
5. Write tests in `tests/test_tools.py`
6. Update this documentation
7. Submit pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

---

**Need Help?** Check the examples in `src/tools/builtin/` or open an issue on GitHub.
