# Claude-3.5 Sonnet Integration Guide

Comprehensive guide for integrating and using Anthropic's Claude-3.5 Sonnet models in Zakera.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Setup](#setup)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Advanced Features](#advanced-features)
- [Performance Optimization](#performance-optimization)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

Claude-3.5 Sonnet is Anthropic's latest and most advanced model in the Claude 3.5 family. It offers:

- **200,000 token context window** - Process entire books and large documents
- **8,192 max output tokens** - Generate longer responses
- **Advanced reasoning** - Superior performance on complex tasks
- **Tool use** - Native function calling support
- **Streaming responses** - Real-time text generation
- **Cost efficiency** - Balanced performance and price

### Model Variants

| Model | Release Date | Context | Max Output | Cost (Input) | Cost (Output) |
|-------|-------------|---------|------------|--------------|---------------|
| `claude-3-5-sonnet-20241022` | Oct 2024 | 200K | 8K | $3.00/M | $15.00/M |
| `claude-3-5-sonnet-20240620` | Jun 2024 | 200K | 8K | $3.00/M | $15.00/M |

**Recommendation**: Use `claude-3-5-sonnet-20241022` (latest) for best performance.

## Features

### Core Capabilities

✅ **Full Streaming Support**
- Server-Sent Events (SSE) for real-time responses
- Token-by-token generation
- Low latency streaming

✅ **Advanced Rate Limiting**
- Token bucket algorithm
- Request and token-based limiting
- Automatic throttling and queuing

✅ **Automatic Retries**
- Exponential backoff on failures
- Configurable retry attempts
- Smart error handling

✅ **Cost Tracking**
- Real-time cost calculation
- Token usage monitoring
- Budget management

✅ **Context Caching**
- Cache repeated context (90% cost savings)
- Smart cache invalidation
- Automatic cache management

✅ **OpenTelemetry Integration**
- Distributed tracing
- Performance monitoring
- Error tracking

## Setup

### 1. Get API Key

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Navigate to API Keys section
3. Create a new API key
4. Copy the key (starts with `sk-ant-`)

### 2. Install Dependencies

The provider uses `httpx` for async HTTP requests:

```bash
pip install httpx opentelemetry-api opentelemetry-sdk
```

### 3. Configure Environment

Add to your `.env` file:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here
ENABLE_ANTHROPIC=true

# Optional - Claude-3.5 specific
CLAUDE35_DEFAULT_MODEL=claude-3-5-sonnet-20241022
CLAUDE35_REQUESTS_PER_MINUTE=50
CLAUDE35_TOKENS_PER_MINUTE=100000
CLAUDE35_ENABLE_CACHING=true
CLAUDE35_MAX_RETRIES=3
CLAUDE35_TIMEOUT=120
```

## Configuration

### Rate Limits

Claude API has the following default limits:

| Tier | Requests/Min | Tokens/Min | Tokens/Day |
|------|-------------|------------|------------|
| Free | 5 | 25,000 | 300,000 |
| Build (Tier 1) | 50 | 50,000 | 2,500,000 |
| Build (Tier 2) | 50 | 100,000 | 5,000,000 |
| Scale | 2,000 | 2,000,000 | 10,000,000 |

Adjust your configuration based on your tier:

```bash
# For Build Tier 2
CLAUDE35_REQUESTS_PER_MINUTE=50
CLAUDE35_TOKENS_PER_MINUTE=100000

# For Scale Tier
CLAUDE35_REQUESTS_PER_MINUTE=2000
CLAUDE35_TOKENS_PER_MINUTE=2000000
```

### Timeouts

For long-running requests:

```bash
CLAUDE35_TIMEOUT=180  # 3 minutes for complex tasks
```

## Usage Examples

### Basic Usage

```python
from src.model.providers_claude35 import Claude35Provider, Message

# Initialize provider
provider = Claude35Provider(
    api_key="sk-ant-...",
    model_name="claude-3-5-sonnet-20241022"
)

# Create messages
messages = [
    Message(role="user", content="Explain quantum computing in simple terms")
]

# Generate response
response = await provider.generate(
    messages=messages,
    temperature=0.7,
    max_tokens=2048
)

print(response.content)
print(f"Cost: ${response.usage['cost']:.6f}")
print(f"Tokens: {response.usage['total_tokens']}")
```

### Streaming Responses

```python
# Stream response token by token
async for chunk in provider.stream_generate(
    messages=messages,
    temperature=0.7,
    max_tokens=2048
):
    print(chunk, end="", flush=True)
```

### With System Prompt

```python
messages = [
    Message(
        role="system",
        content="You are a helpful AI assistant specialized in physics."
    ),
    Message(
        role="user",
        content="Explain the double-slit experiment"
    )
]

response = await provider.generate(messages)
```

### Multi-Turn Conversation

```python
messages = [
    Message(role="user", content="What is Python?"),
    Message(role="assistant", content="Python is a programming language..."),
    Message(role="user", content="Show me a hello world example")
]

response = await provider.generate(messages)
```

### Advanced Parameters

```python
response = await provider.generate(
    messages=messages,
    temperature=0.8,      # Creativity (0.0-1.0)
    max_tokens=4096,      # Max response length
    top_p=0.95,          # Nucleus sampling
    top_k=50             # Top-k sampling
)
```

## Advanced Features

### Context Caching

Cache frequently used context to save costs:

```python
# Enable caching in provider initialization
provider = Claude35Provider(
    api_key="sk-ant-...",
    enable_caching=True
)

# Large context that will be cached
large_document = """... 50,000 token document ..."""

messages = [
    Message(role="user", content=f"Context: {large_document}\n\nQuestion: What is...?")
]

# First call: Full cost
response1 = await provider.generate(messages)

# Subsequent calls with same context: 90% cheaper!
response2 = await provider.generate(messages)
```

### Error Handling

```python
try:
    response = await provider.generate(messages)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded")
    elif e.response.status_code == 500:
        print("Server error")
    else:
        print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Custom Rate Limiting

```python
from src.model.providers_claude35 import RateLimiter

# Create custom rate limiter
rate_limiter = RateLimiter(
    requests_per_minute=100,
    tokens_per_minute=200000
)

# Use with provider
await rate_limiter.acquire(token_count=5000)
response = await provider.generate(messages)
```

## Performance Optimization

### 1. Streaming for Better UX

Use streaming for long responses to improve perceived latency:

```python
async for chunk in provider.stream_generate(messages):
    # Display chunk immediately
    display(chunk)
```

### 2. Optimize Token Usage

```python
# Use concise prompts
messages = [
    Message(
        role="user",
        content="Summarize: [document]"  # Clear and direct
    )
]

# Set appropriate max_tokens
response = await provider.generate(
    messages=messages,
    max_tokens=1024  # Limit response length
)
```

### 3. Batch Requests

```python
# Process multiple requests
tasks = [
    provider.generate([Message(role="user", content=q)])
    for q in questions
]

responses = await asyncio.gather(*tasks)
```

### 4. Use Context Caching

For repeated context:
- Cache documents, knowledge bases, instructions
- Save 90% on cached tokens
- Automatic cache management

## Monitoring and Debugging

### Enable Tracing

```python
# Tracing is automatic with OpenTelemetry
import os
os.environ["ENABLE_TRACING"] = "true"

# View traces in Jaeger
# http://localhost:16686
```

### Cost Tracking

```python
total_cost = 0

for message in messages:
    response = await provider.generate([message])
    cost = response.usage['cost']
    total_cost += cost
    print(f"Request cost: ${cost:.6f}")

print(f"Total cost: ${total_cost:.6f}")
```

### Log Analysis

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("src.model.providers_claude35")

# Detailed logs of API calls
response = await provider.generate(messages)
```

## Troubleshooting

### Rate Limit Errors

**Error**: `429 Too Many Requests`

**Solution**:
```bash
# Reduce rate limits
CLAUDE35_REQUESTS_PER_MINUTE=10
CLAUDE35_TOKENS_PER_MINUTE=25000
```

### Timeout Errors

**Error**: `Request timeout after 120s`

**Solution**:
```bash
# Increase timeout
CLAUDE35_TIMEOUT=300
```

Or reduce response length:
```python
response = await provider.generate(
    messages=messages,
    max_tokens=2048  # Smaller response
)
```

### Invalid API Key

**Error**: `401 Unauthorized`

**Solution**:
1. Verify key starts with `sk-ant-`
2. Check key is active in [Anthropic Console](https://console.anthropic.com/)
3. Ensure key has proper permissions

### Context Length Errors

**Error**: `Context length exceeded`

**Solution**:
```python
# Truncate messages to fit context window
from src.model.providers_claude35 import Claude35Provider

max_tokens = 200000  # Claude-3.5 context window
current_tokens = sum(provider._estimate_tokens(m.content) for m in messages)

if current_tokens > max_tokens:
    # Remove older messages
    messages = messages[-10:]  # Keep last 10 messages
```

## Best Practices

### 1. API Key Security

✅ **Do**:
- Store in environment variables
- Use secret management systems
- Rotate keys regularly

❌ **Don't**:
- Hardcode in source code
- Commit to version control
- Share publicly

### 2. Error Handling

```python
try:
    response = await provider.generate(messages)
except Exception as e:
    logger.error(f"Claude API error: {e}")
    # Fallback to alternative model
    response = await fallback_provider.generate(messages)
```

### 3. Cost Management

```python
# Set budget limits
MAX_DAILY_COST = 10.00  # $10/day
current_cost = 0

if current_cost + estimated_cost > MAX_DAILY_COST:
    raise Exception("Daily budget exceeded")
```

### 4. Prompt Engineering

```python
# Clear, specific prompts
messages = [
    Message(
        role="system",
        content="You are an expert in [domain]. Provide [specific output format]."
    ),
    Message(
        role="user",
        content="[Clear question with context]"
    )
]
```

### 5. Response Validation

```python
response = await provider.generate(messages)

# Validate response
if response.finish_reason != "end_turn":
    logger.warning(f"Unexpected finish reason: {response.finish_reason}")

if response.usage['completion_tokens'] >= max_tokens:
    logger.warning("Response may be truncated")
```

## Additional Resources

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [Rate Limits Documentation](https://docs.anthropic.com/claude/reference/rate-limits)
- [Context Caching Guide](https://docs.anthropic.com/claude/docs/prompt-caching)

## Support

For issues or questions:
- Open an issue on [GitHub](https://github.com/itsmepraks/zakera/issues)
- Check [troubleshooting guide](../TROUBLESHOOTING.md)
- Contact: support@zakera.ai

---

**Last Updated**: February 2026  
**Version**: 1.0.0
