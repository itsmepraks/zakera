# OpenAI Integration Guide

This guide explains how to use the OpenAI integration in Zakera, including setup, configuration, and advanced features.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Zakera provides a complete OpenAI integration with the following features:

- ✅ Full Chat Completions API support
- ✅ Streaming responses with Server-Sent Events (SSE)
- ✅ Function calling support
- ✅ JSON mode for structured outputs
- ✅ Automatic retry with exponential backoff
- ✅ Comprehensive error handling
- ✅ Token usage tracking
- ✅ Configurable timeouts and rate limiting

## Setup

### 1. Install Dependencies

The OpenAI integration requires the following Python packages (already in requirements.txt):

```bash
pip install openai httpx
```

### 2. Configure API Key

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

Or add it to your `.env` file:

```env
OPENAI_API_KEY=sk-...
```

### 3. Optional Configuration

You can customize the OpenAI provider with additional environment variables:

```env
# Custom base URL (for proxies or Azure OpenAI)
OPENAI_BASE_URL=https://api.openai.com/v1

# Organization ID (for team accounts)
OPENAI_ORGANIZATION=org-...

# Retry configuration
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT=60.0
```

## Basic Usage

### Simple Chat Completion

```python
from src.model.providers import OpenAIProvider, Message

# Initialize provider
provider = OpenAIProvider(model_name="gpt-4")

# Create messages
messages = [
    Message(role="system", content="You are a helpful assistant."),
    Message(role="user", content="What is the capital of France?")
]

# Generate response
response = await provider.generate(messages)

print(response.content)  # "The capital of France is Paris."
print(response.usage)    # {'prompt_tokens': 20, 'completion_tokens': 8, ...}
```

### Streaming Response

```python
# Stream response chunks as they're generated
async for chunk in provider.stream_generate(messages):
    print(chunk, end="", flush=True)
```

### With Parameters

```python
response = await provider.generate(
    messages,
    temperature=0.7,      # Creativity (0-2)
    max_tokens=500,       # Maximum response length
    top_p=0.9,           # Nucleus sampling
    presence_penalty=0.5, # Discourage repetition
    frequency_penalty=0.5 # Discourage common words
)
```

## Advanced Features

### Function Calling

Use function calling to extend the model's capabilities:

```python
functions = [
    {
        "name": "get_weather",
        "description": "Get the current weather in a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location"]
        }
    }
]

messages = [
    Message(role="user", content="What's the weather like in Boston?")
]

response = await provider.generate(
    messages,
    functions=functions
)

# Response will contain function call information
if "get_weather" in response.content:
    # Parse and execute function
    function_data = json.loads(response.content)
    print(function_data)  # {'name': 'get_weather', 'arguments': '{"location": "Boston"}'}
```

### JSON Mode

Force the model to return valid JSON:

```python
messages = [
    Message(
        role="system",
        content="You are a helpful assistant that returns JSON."
    ),
    Message(
        role="user",
        content="Extract the person's name, age, and city from: 'John Smith is 30 years old and lives in New York.'"
    )
]

response = await provider.generate(
    messages,
    response_format={"type": "json_object"}
)

data = json.loads(response.content)
print(data)  # {'name': 'John Smith', 'age': 30, 'city': 'New York'}
```

### Deterministic Outputs

Use seeds for reproducible results:

```python
response = await provider.generate(
    messages,
    seed=42,
    temperature=0.0  # Use with seed for maximum determinism
)
```

### Multi-Turn Conversations

```python
conversation = [
    Message(role="system", content="You are a helpful assistant."),
    Message(role="user", content="Tell me a joke."),
]

# First response
response1 = await provider.generate(conversation)
conversation.append(
    Message(role="assistant", content=response1.content)
)

# Follow-up
conversation.append(
    Message(role="user", content="Explain why that's funny.")
)

response2 = await provider.generate(conversation)
```

## Error Handling

The OpenAI provider includes comprehensive error handling:

```python
from src.model.providers import OpenAIError

try:
    response = await provider.generate(messages)
except OpenAIError as e:
    if e.status_code == 401:
        print("Invalid API key")
    elif e.status_code == 429:
        print("Rate limit exceeded")
    elif e.status_code >= 500:
        print("OpenAI server error")
    else:
        print(f"Error: {e.message}")
```

### Automatic Retries

The provider automatically retries failed requests with exponential backoff:

- Retryable errors: 429 (rate limit), 500+ (server errors), timeouts
- Non-retryable errors: 400-499 (except 429)
- Default max retries: 3
- Backoff: 2^attempt seconds (1s, 2s, 4s, ...)

## Best Practices

### 1. Use Appropriate Models

```python
# For simple tasks
provider = OpenAIProvider(model_name="gpt-3.5-turbo")

# For complex reasoning
provider = OpenAIProvider(model_name="gpt-4-turbo-preview")

# For balanced performance
provider = OpenAIProvider(model_name="gpt-4")
```

### 2. Optimize Token Usage

```python
# Monitor token usage
response = await provider.generate(messages, max_tokens=200)
print(f"Tokens used: {response.usage['total_tokens']}")

# Use shorter system messages
messages = [
    Message(role="system", content="Be concise."),
    Message(role="user", content=user_input)
]
```

### 3. Handle Rate Limits

```python
import asyncio

async def generate_with_rate_limit(provider, messages, delay=1.0):
    """Add delay between requests to avoid rate limits"""
    response = await provider.generate(messages)
    await asyncio.sleep(delay)
    return response
```

### 4. Use Streaming for Better UX

```python
# Stream responses for better perceived performance
async def stream_to_user(provider, messages):
    buffer = ""
    async for chunk in provider.stream_generate(messages):
        buffer += chunk
        # Update UI in real-time
        yield chunk
    return buffer
```

### 5. Implement Caching

```python
import hashlib
from functools import lru_cache

def cache_key(messages):
    """Generate cache key from messages"""
    content = "".join(m.content for m in messages)
    return hashlib.md5(content.encode()).hexdigest()

# Simple in-memory cache
response_cache = {}

async def cached_generate(provider, messages):
    key = cache_key(messages)
    if key in response_cache:
        return response_cache[key]
    
    response = await provider.generate(messages)
    response_cache[key] = response
    return response
```

## Troubleshooting

### API Key Issues

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Timeout Errors

```python
# Increase timeout for long responses
provider = OpenAIProvider()
provider.timeout = 120.0  # 2 minutes
```

### Rate Limit Errors

- Check your usage: https://platform.openai.com/account/usage
- Upgrade your plan for higher limits
- Implement request batching and delays

### Model Not Found

```python
# List available models
import httpx

async def list_models(api_key):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return response.json()
```

### Connection Issues

```python
# Use custom base URL for proxies
import os
os.environ["OPENAI_BASE_URL"] = "https://your-proxy.com/v1"

provider = OpenAIProvider()
```

## Examples

See `examples/openai_examples.py` for complete working examples including:

- Basic chat completion
- Streaming responses
- Function calling
- JSON mode
- Multi-turn conversations
- Error handling
- Rate limiting
- Caching strategies

## API Reference

For complete API documentation, see the docstrings in `src/model/providers.py` or visit:
https://platform.openai.com/docs/api-reference/chat

## Support

For issues specific to the OpenAI integration:
- Check OpenAI status: https://status.openai.com
- OpenAI documentation: https://platform.openai.com/docs
- File an issue: https://github.com/itsmepraks/zakera/issues
