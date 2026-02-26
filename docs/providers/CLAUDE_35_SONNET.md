# Claude-3.5 Sonnet Provider

Comprehensive guide for using Anthropic's Claude-3.5 Sonnet with Zakera.

## Overview

Claude-3.5 Sonnet is Anthropic's most intelligent and capable model, offering:

- **200K context window** for processing long documents
- **Advanced reasoning** and analysis capabilities
- **Streaming responses** for real-time output
- **Built-in rate limiting** for production reliability
- **Cost-effective pricing** at $3/$15 per 1M tokens

## Setup

### 1. Get API Key

Sign up at [Anthropic Console](https://console.anthropic.com/) and generate an API key.

### 2. Configure Environment

```bash
# Add to .env
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### 3. Verify Configuration

```python
from src.model.providers_claude import Claude35SonnetProvider

async def check_setup():
    provider = Claude35SonnetProvider()
    metrics = provider.get_metrics()
    print(f"Provider initialized: {provider.model_name}")
```

## Basic Usage

### Simple Generation

```python
from src.model.providers_claude import Claude35SonnetProvider
from src.model.providers import Message

async def generate_response():
    provider = Claude35SonnetProvider()
    
    messages = [
        Message(role="user", content="Explain quantum computing in simple terms")
    ]
    
    response = await provider.generate(messages)
    print(response.content)
    print(f"Tokens: {response.usage['total_tokens']}")
    print(f"Cost: ${response.usage['cost_usd']:.6f}")
```

### Streaming Responses

```python
async def stream_response():
    provider = Claude35SonnetProvider()
    
    messages = [
        Message(role="user", content="Write a short story about AI")
    ]
    
    async for chunk in provider.stream_generate(messages):
        print(chunk, end='', flush=True)
```

### With System Message

```python
messages = [
    Message(role="system", content="You are a helpful coding assistant"),
    Message(role="user", content="Write a Python function to sort a list")
]

response = await provider.generate(messages)
```

## Advanced Features

### Rate Limiting Configuration

```python
from src.model.providers_claude import RateLimitConfig

config = RateLimitConfig(
    requests_per_minute=50,  # Max requests per minute
    requests_per_day=1000,   # Max requests per day
    tokens_per_minute=100000,  # Token limit per minute
    max_retries=3,            # Retry attempts
    retry_base_delay=1.0,     # Initial retry delay
    max_retry_delay=60.0      # Max retry delay
)

provider = Claude35SonnetProvider(rate_limit_config=config)
```

### Generation Parameters

```python
response = await provider.generate(
    messages,
    temperature=0.7,     # Randomness (0.0-1.0)
    max_tokens=4096,     # Max output length
    top_p=0.9,          # Nucleus sampling
    top_k=40            # Top-k sampling
)
```

### Context Manager Usage

```python
async with Claude35SonnetProvider() as provider:
    response = await provider.generate(messages)
    # Client automatically closed on exit
```

## Monitoring & Metrics

### Get Provider Metrics

```python
metrics = provider.get_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Total cost: ${metrics['total_cost_usd']:.2f}")
print(f"Avg latency: {metrics['average_latency_seconds']:.2f}s")
print(f"Rate limit hits: {metrics['rate_limit_hits']}")
```

### Distributed Tracing

All requests are automatically traced with OpenTelemetry:

```python
# View traces in Jaeger: http://localhost:16686
# Spans include:
# - Request duration
# - Token usage
# - Cost calculation
# - Error details
```

### Prometheus Metrics

The provider exports metrics for monitoring:

- `zakera_model_requests_total` - Total requests by provider
- `zakera_model_tokens_total` - Token usage
- `zakera_model_cost_usd_total` - Total cost
- `zakera_model_latency_seconds` - Request latency

## Production Best Practices

### 1. Error Handling

```python
try:
    response = await provider.generate(messages)
except Exception as e:
    logger.error(f"Generation failed: {e}")
    # Implement fallback logic
    response = await fallback_provider.generate(messages)
```

### 2. Rate Limit Management

```python
# Check rate limits before critical operations
metrics = provider.get_metrics()
if metrics['daily_requests'] >= metrics['daily_limit'] * 0.9:
    logger.warning("Approaching daily rate limit")
    # Switch to alternative provider
```

### 3. Cost Optimization

```python
# Use streaming for long responses
async for chunk in provider.stream_generate(messages, max_tokens=1000):
    # Process incrementally
    pass

# Monitor costs
if provider.metrics.total_cost > budget_threshold:
    # Switch to cheaper model
    pass
```

### 4. Context Window Management

```python
# Claude-3.5 Sonnet supports 200K tokens
def estimate_tokens(text: str) -> int:
    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4

# Check before sending
total_tokens = sum(estimate_tokens(msg.content) for msg in messages)
if total_tokens > 180000:  # Leave buffer
    # Truncate or summarize messages
    messages = truncate_messages(messages, max_tokens=180000)
```

## Pricing

Claude-3.5 Sonnet pricing (as of 2024):

- **Input**: $3.00 per 1M tokens
- **Output**: $15.00 per 1M tokens

### Cost Examples

```python
# Short conversation (100 input, 200 output tokens)
cost = (100 / 1_000_000 * 3.0) + (200 / 1_000_000 * 15.0)
print(f"${cost:.6f}")  # $0.003300

# Long document analysis (50K input, 2K output tokens)
cost = (50000 / 1_000_000 * 3.0) + (2000 / 1_000_000 * 15.0)
print(f"${cost:.6f}")  # $0.180000
```

## Comparison with Other Models

| Feature | Claude-3.5 Sonnet | GPT-4 Turbo | Gemini 1.5 Pro |
|---------|-------------------|-------------|----------------|
| Context | 200K tokens | 128K tokens | 1M tokens |
| Input Cost | $3/1M | $10/1M | $3.5/1M |
| Output Cost | $15/1M | $30/1M | $10.5/1M |
| Streaming | ✅ Yes | ✅ Yes | ✅ Yes |
| Best For | Analysis, Writing | General Purpose | Long Context |

## Troubleshooting

### Rate Limit Errors

```python
# Error: "Rate limit exceeded"
# Solution: Adjust rate limit configuration
config = RateLimitConfig(requests_per_minute=30)  # Lower limit
provider = Claude35SonnetProvider(rate_limit_config=config)
```

### Timeout Errors

```python
# Error: "Request timeout"
# Solution: Increase timeout or reduce max_tokens
response = await provider.generate(messages, max_tokens=2048)
```

### Context Length Errors

```python
# Error: "Context length exceeded"
# Solution: Truncate messages or use summarization
from src.model.memory import truncate_conversation
messages = truncate_conversation(messages, max_tokens=180000)
```

## API Reference

### Claude35SonnetProvider

```python
class Claude35SonnetProvider(ModelProvider):
    def __init__(
        api_key: Optional[str] = None,
        model_name: str = "claude-3-5-sonnet-20241022",
        rate_limit_config: Optional[RateLimitConfig] = None
    )
    
    async def generate(
        messages: List[Message],
        **kwargs
    ) -> ModelResponse
    
    async def stream_generate(
        messages: List[Message],
        **kwargs
    ) -> AsyncIterator[str]
    
    def get_metrics() -> Dict[str, Any]
```

### RateLimitConfig

```python
@dataclass
class RateLimitConfig:
    requests_per_minute: int = 50
    requests_per_day: int = 1000
    tokens_per_minute: int = 100000
    max_retries: int = 3
    retry_base_delay: float = 1.0
    max_retry_delay: float = 60.0
```

## Resources

- [Anthropic Documentation](https://docs.anthropic.com/)
- [Claude API Reference](https://docs.anthropic.com/claude/reference/)
- [Pricing Information](https://www.anthropic.com/pricing)
- [Rate Limits](https://docs.anthropic.com/claude/reference/rate-limits)

## Support

For issues or questions:
- GitHub Issues: [zakera/issues](https://github.com/itsmepraks/zakera/issues)
- Documentation: [docs/README.md](../README.md)
