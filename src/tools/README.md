# Zakera Tool Integration System

> [!WARNING]
> **Legacy module documentation.** The vNext tool boundary is allowlisted and capability-based. Unsafe legacy code-execution and unrestricted file-reading tools are disabled by default and are not sandboxes.

The tool system extends Zakera's AI capabilities with external tools and services.

## 📁 Directory Structure

```
src/tools/
├── __init__.py           # Package exports
├── base.py              # Base Tool class and interfaces
├── registry.py          # Tool registry and discovery
├── manager.py           # Tool execution manager
├── builtin/             # Built-in tools
│   ├── __init__.py
│   ├── calculator.py    # Mathematical evaluation
│   ├── web_search.py    # Web search integration
│   ├── code_executor.py # Code execution sandbox
│   ├── weather.py       # Weather information
│   └── datetime_tool.py # Date/time operations
└── custom/              # Custom user tools (create this directory)
```

## 🚀 Quick Start

### Using Tools in Python

```python
from src.tools import get_tool_manager

# Get manager instance
manager = get_tool_manager()

# Execute a tool
result = await manager.execute_tool("calculator", {
    "expression": "2 + 2"
})

if result.success:
    print(result.data["result"])  # 4
else:
    print(f"Error: {result.error}")
```

### Using Tools via API

```bash
# List available tools
GET /api/tools

# Execute a tool
POST /api/tools/execute
{
  "tool_name": "calculator",
  "parameters": {"expression": "10 * 5"}
}
```

## 🔌 Built-in Tools

| Tool | Description | Category |
|------|-------------|----------|
| `calculator` | Math expression evaluator | computation |
| `web_search` | Search engines (Google, Bing, DDG) | information |
| `code_executor` | Sandboxed code execution | computation |
| `weather` | Weather information | information |
| `datetime` | Date/time operations | utility |

## 🛠️ Creating Custom Tools

### Step 1: Create Tool Class

Create a new file in `src/tools/custom/my_tool.py`:

```python
from typing import List
from src.tools.base import Tool, ToolParameter, ToolParameterType, ToolResult

class MyCustomTool(Tool):
    @property
    def name(self) -> str:
        return "my_custom_tool"
    
    @property
    def description(self) -> str:
        return "What my tool does"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type=ToolParameterType.STRING,
                description="Input description",
                required=True
            )
        ]
    
    async def execute(self, input: str, **kwargs) -> ToolResult:
        try:
            # Your tool logic here
            result = process_input(input)
            return ToolResult.success_result(data={"output": result})
        except Exception as e:
            return ToolResult.error_result(f"Failed: {str(e)}")
```

### Step 2: Register Tool

```python
from src.tools import get_registry
from src.tools.custom.my_tool import MyCustomTool

registry = get_registry()
registry.register(MyCustomTool())
```

### Step 3: Use Tool

```python
from src.tools import get_tool_manager

manager = get_tool_manager()
result = await manager.execute_tool("my_custom_tool", {"input": "test"})
```

## 🎯 Key Features

### Result Caching
```python
# First call - executes tool
result1 = await manager.execute_tool("weather", {"location": "London"})

# Second call - returns cached result (within TTL)
result2 = await manager.execute_tool("weather", {"location": "London"})
assert result2.metadata["from_cache"] == True
```

### Rate Limiting
```python
class MyTool(Tool):
    @property
    def rate_limit(self) -> int:
        return 10  # Maximum 10 calls per minute
```

### Timeout Protection
```python
class MyTool(Tool):
    @property
    def timeout(self) -> int:
        return 30  # Maximum 30 seconds execution time
```

### Parallel Execution
```python
results = await manager.execute_tools_parallel([
    ("tool1", params1),
    ("tool2", params2),
    ("tool3", params3),
])
```

### Tool Chaining
```python
chain = [
    {"tool_name": "tool1", "parameters": {...}},
    {"tool_name": "tool2", "parameters": {...}},
]
results = await manager.execute_tool_chain(chain)
```

## 📊 Monitoring

### Get Statistics

```python
# Overall statistics
stats = manager.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")

# Per-tool statistics
calc_stats = manager.get_statistics("calculator")
print(f"Calculator called {calc_stats['total_executions']} times")
```

### Execution History

```python
# Get recent executions
history = manager.get_execution_history(limit=50)

for entry in history:
    print(f"{entry['timestamp']}: {entry['tool_name']} - {entry['success']}")
```

### Cache Management

```python
# Clear all cache
manager.clear_cache()

# Clear specific tool cache
manager.clear_cache("weather")
```

## 🔐 Security

### Input Validation

All parameters are validated before execution:

```python
# Type validation
# Range validation (min/max)
# Enum validation (allowed values)
# Pattern validation (regex)
```

### Sandboxed Execution

Code executor runs in restricted environment:

- ✅ No file system access
- ✅ No network access
- ✅ No imports allowed
- ✅ Limited builtins only
- ✅ Timeout protection

### API Key Management

Store API keys in environment variables:

```bash
export OPENWEATHER_API_KEY=your_key
export GOOGLE_SEARCH_API_KEY=your_key
```

Never hardcode API keys in code!

## 🧪 Testing

### Run Tool Tests

```bash
# All tool tests
pytest tests/test_tools.py -v

# Specific test
pytest tests/test_tools.py::TestCalculatorTool -v

# With coverage
pytest tests/test_tools.py --cov=src/tools
```

### Test Your Custom Tool

```python
import pytest
from my_tool import MyCustomTool

@pytest.mark.asyncio
async def test_my_tool():
    tool = MyCustomTool()
    result = await tool.execute(input="test")
    
    assert result.success
    assert "output" in result.data
```

## 📚 Documentation

- **[Complete Guide](../../docs/tools.md)** - Full documentation
- **[Examples](../../docs/tools-examples.md)** - Practical examples
- **[API Reference](../../docs/api-reference.md)** - API endpoints

## 🤝 Contributing

To add a new built-in tool:

1. Create file in `src/tools/builtin/`
2. Inherit from `Tool` base class
3. Implement required methods
4. Add to `builtin/__init__.py`
5. Write tests
6. Update documentation
7. Submit PR

See [Creating Custom Tools](#creating-custom-tools) above.

## ⚡ Performance Tips

1. **Enable Caching** for repeated queries
2. **Use Parallel Execution** for independent tools
3. **Set Appropriate Timeouts** to prevent hanging
4. **Monitor Statistics** to identify bottlenecks
5. **Clear Cache** periodically if memory is concern

## 🐛 Troubleshooting

### Tool Not Found

```python
# Error: ToolNotFoundError: Tool 'my_tool' not found

# Solution: Check if tool is registered
registry = get_registry()
print(registry.get_tool_names())
```

### Tool Timeout

```python
# Error: Tool execution timed out

# Solution: Increase timeout
class MyTool(Tool):
    @property
    def timeout(self) -> int:
        return 60  # Increase from default 30s
```

### Rate Limit Exceeded

```python
# Error: Rate limit exceeded for tool 'web_search'

# Solution: Wait before retrying, or disable rate limiting
manager.enable_rate_limiting = False  # For development only!
```

## 📞 Support

- Check [docs/tools.md](../../docs/tools.md) for detailed documentation
- Review [docs/tools-examples.md](../../docs/tools-examples.md) for examples
- Open an issue on GitHub
- Review test files for usage patterns

---

**The tool system is production-ready and extensively documented!** Start building with tools today. 🎉
