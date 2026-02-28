# Perplexity AI Provider

## Overview

Perplexity AI is a powerful search-enhanced AI provider that combines large language models with real-time web search capabilities. The Sonar models can access current information from the web and provide responses with proper citations.

## Features

- **Real-Time Web Search**: Access current information from the internet
- **Citation Support**: Responses include source citations for verification
- **Multiple Models**: Choose from different Sonar models based on your needs
- **Search Filtering**: Control search domains, recency, and more
- **Streaming Support**: Get responses in real-time
- **Cost-Effective**: Competitive pricing compared to other providers

## Setup

### 1. Get API Key

1. Visit [Perplexity AI](https://www.perplexity.ai/)
2. Sign up for an account
3. Navigate to API settings
4. Generate an API key

### 2. Configure Environment

Add your API key to `.env`:

```bash
PERPLEXITY_API_KEY=your-api-key-here
```

### 3. Enable in Configuration

Update `config/providers.yaml` or your configuration:

```yaml
providers:
  perplexity:
    enabled: true
    api_key: ${PERPLEXITY_API_KEY}
    default_model: sonar
    timeout: 60
```

## Available Models

### Sonar (Base)

- **Context Length**: 12,000 tokens
- **Cost**: $0.001 per 1K tokens (both input/output)
- **Best For**: Fast searches, quick answers, cost-sensitive applications
- **Features**: Real-time web search, citations

### Sonar Medium

- **Context Length**: 16,000 tokens
- **Cost**: $0.0015 per 1K tokens
- **Best For**: Balanced performance, moderate complexity
- **Features**: Enhanced accuracy, longer context

### Sonar Large

- **Context Length**: 32,000 tokens  
- **Cost**: $0.002 per 1K tokens
- **Best For**: Complex queries, research, long-form content
- **Features**: Best accuracy, maximum context window

## Usage Examples

### Basic Query

```python
from zakera import ZakeraClient

client = ZakeraClient()

response = await client.chat.send(
    message="What are the latest developments in quantum computing?",
    model="sonar",
    provider="perplexity"
)

print(response.content)
print(f"Citations: {response.metadata['citations']}")
```

### Search with Domain Filter

```python
response = await client.chat.send(
    message="Latest machine learning papers",
    model="sonar",
    provider="perplexity",
    search_domain_filter=["arxiv.org", "github.com"],
    return_citations=True
)
```

### Recent News Only

```python
response = await client.chat.send(
    message="What happened in AI this week?",
    model="sonar",
    provider="perplexity",
    search_recency_filter="week",  # Options: hour, day, week, month, year
    return_citations=True
)
```

### Streaming Response

```python
response = await client.chat.stream(
    message="Explain recent AI breakthroughs",
    model="sonar",
    provider="perplexity"
)

async for chunk in response.stream:
    print(chunk, end="", flush=True)
```

### With Related Questions

```python
response = await client.chat.send(
    message="Climate change impact on agriculture",
    model="sonar-large",
    provider="perplexity",
    return_related_questions=True,
    return_citations=True
)

print(response.content)
print(f"Related: {response.metadata.get('related_questions', [])}")
```

## Advanced Configuration

### Search Parameters

```python
config = {
    # Filter by domains (whitelist)
    "search_domain_filter": ["arxiv.org", "github.com", "nature.com"],
    
    # Time-based filtering
    "search_recency_filter": "day",  # hour, day, week, month, year
    
    # Return citations
    "return_citations": True,
    
    # Return related questions for exploration
    "return_related_questions": True,
    
    # Standard parameters
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9,
    "top_k": 50,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
}

response = await client.chat.send(
    message="Your query",
    model="sonar",
    provider="perplexity",
    **config
)
```

## Cost Optimization

### Choose the Right Model

- **Quick Lookups**: Use `sonar` (cheapest)
- **General Use**: Use `sonar-medium` (balanced)
- **Complex Research**: Use `sonar-large` (most capable)

### Optimize Token Usage

```python
# Limit response length
response = await client.chat.send(
    message="Summarize quantum computing in 100 words",
    model="sonar",
    max_tokens=150  # ~100 words + buffer
)
```

### Filter Search Domains

```python
# Reduce search scope for faster, cheaper responses
response = await client.chat.send(
    message="Latest Python packages",
    model="sonar",
    search_domain_filter=["pypi.org", "github.com"]  # Focused search
)
```

## Monitoring

### Track Citations

```python
response = await client.chat.send(
    message="AI safety research",
    model="sonar",
    return_citations=True
)

# Log citations for audit trail
for i, citation in enumerate(response.metadata['citations'], 1):
    print(f"{i}. {citation}")
```

### Monitor Costs

```python
total_cost = 0

for query in queries:
    response = await client.chat.send(query, model="sonar")
    total_cost += response.cost
    
print(f"Total cost: ${total_cost:.6f}")
```

## Best Practices

1. **Always Request Citations**: Enable citations for verifiable information
2. **Use Domain Filters**: Narrow search scope for better results
3. **Set Recency Filters**: Use when current information is critical
4. **Monitor Usage**: Track costs and tokens per request
5. **Handle Rate Limits**: Implement exponential backoff
6. **Cache Responses**: Store results to avoid redundant searches
7. **Validate Citations**: Programmatically check citation accessibility

## Troubleshooting

### Invalid API Key

```bash
Error: Invalid API key
```

**Solution**: Verify your API key in `.env` and Perplexity dashboard

### Rate Limit Exceeded

```bash
Error: 429 Too Many Requests
```

**Solution**: Implement rate limiting or upgrade your plan

### No Citations Returned

```python
if not response.metadata.get('citations'):
    print("No citations available for this query")
```

**Solution**: Ensure `return_citations=True` and query is search-eligible

### Search Results Empty

**Possible Causes**:
- Domain filter too restrictive
- Recency filter too narrow
- Query doesn't require web search

**Solution**: Broaden filters or rephrase query

## Comparison with Other Providers

| Feature | Perplexity | OpenAI | Anthropic | Google Gemini |
|---------|------------|--------|-----------|---------------|
| Web Search | ✅ Built-in | ❌ Requires plugins | ❌ No | ⚠️ Limited |
| Citations | ✅ Yes | ❌ No | ❌ No | ⚠️ Sometimes |
| Real-time Info | ✅ Yes | ❌ No | ❌ No | ⚠️ Yes |
| Context Window | 32K | 128K | 200K | 2M |
| Cost/1K tokens | $0.001 | $0.01 | $0.003 | $0.00125 |
| Best For | Current info | General chat | Analysis | Large context |

## API Reference

### PerplexityProvider Methods

```python
class PerplexityProvider(BaseProvider):
    async def generate(
        prompt: str,
        model: str = "sonar",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        search_domain_filter: Optional[List[str]] = None,
        search_recency_filter: Optional[str] = None,
        return_citations: bool = True,
        return_related_questions: bool = False,
        **kwargs
    ) -> ModelResponse
```

### ModelResponse Schema

```python
{
    "content": str,
    "model": str,
    "provider": "perplexity",
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int,
    "cost": float,
    "metadata": {
        "citations": List[str],
        "related_questions": Optional[List[str]],
        "finish_reason": str,
        "model_used": str
    }
}
```

## Support

- **Documentation**: [Perplexity API Docs](https://docs.perplexity.ai/)
- **Community**: [Perplexity Discord](https://discord.gg/perplexity)
- **Issues**: [GitHub Issues](https://github.com/itsmepraks/zakera/issues)
- **Email**: support@perplexity.ai

## License

Perplexity AI is a commercial service. Review their [Terms of Service](https://www.perplexity.ai/terms) before use.
