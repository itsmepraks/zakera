# Google Gemini Provider Guide

## Overview

The Gemini provider integrates Google's latest Gemini models into the Zakera AI chat agent system. This includes support for Gemini 1.5 Pro and Flash models with massive context windows and advanced capabilities.

## Features

- **Multiple Models**: Support for Gemini 1.5 Pro, 1.5 Flash, and 1.0 Pro
- **Streaming Responses**: Real-time token streaming for better UX
- **Large Context**: Up to 2M tokens context window (Gemini 1.5 Pro)
- **Cost Tracking**: Automatic token counting and cost calculation
- **Safety Controls**: Configurable content filtering
- **Tool Support**: Function calling and tool integration
- **Multimodal**: Support for text and image inputs

## Setup

### 1. Get API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create or select a project
3. Generate an API key

### 2. Configure Environment

Add to your `.env` file:

```env
# Google Gemini Configuration
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-1.5-pro

# Optional: Advanced Configuration
GEMINI_TEMPERATURE=0.7
GEMINI_TOP_P=0.9
GEMINI_TOP_K=40
GEMINI_MAX_TOKENS=8192
```

### 3. Install Dependencies

```bash
pip install google-generativeai
```

## Available Models

### Gemini 1.5 Pro
- **Context Window**: 2,048,000 tokens
- **Best For**: Complex tasks, long documents, detailed analysis
- **Pricing**: $0.00125/1K input, $0.005/1K output
- **Features**: Multimodal, function calling, advanced reasoning

### Gemini 1.5 Flash
- **Context Window**: 1,048,000 tokens
- **Best For**: Fast responses, high throughput, cost optimization
- **Pricing**: $0.000125/1K input, $0.0005/1K output
- **Features**: 10x cheaper, 2x faster, still highly capable

### Gemini 1.0 Pro (Legacy)
- **Context Window**: 32,000 tokens
- **Best For**: Basic tasks, compatibility
- **Pricing**: $0.00025/1K input, $0.0005/1K output

## Usage Examples

### Basic Usage

```python
from src.model.providers_gemini import GeminiProvider
import os

# Initialize provider
provider = GeminiProvider(
    api_key=os.getenv("GOOGLE_API_KEY"),
    model="gemini-1.5-pro"
)

# Generate response
response = await provider.generate(
    prompt="Explain quantum computing in simple terms",
    system_prompt="You are a helpful science educator."
)

print(response.content)
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.total_tokens}")
```

### Streaming Responses

```python
# Stream response for better UX
async for chunk in provider.generate_stream(
    prompt="Write a short story about a robot"
):
    print(chunk.content, end="", flush=True)
```

### With Conversation History

```python
history = [
    {"role": "user", "content": "What's the capital of France?"},
    {"role": "assistant", "content": "The capital of France is Paris."},
]

response = await provider.generate(
    prompt="What's the population?",
    conversation_history=history
)
```

### Via API Endpoint

```bash
curl -X POST "http://localhost:8000/api/v1/chat/send" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "Hello!",
    "model": "gemini-1.5-pro",
    "stream": true
  }'
```

## Configuration Options

### Temperature (0.0 - 1.0)
Controls randomness in responses:
- **0.0**: Deterministic, focused
- **0.7**: Balanced (default)
- **1.0**: Creative, diverse

```python
provider = GeminiProvider(
    api_key=api_key,
    temperature=0.9  # More creative
)
```

### Top-P (0.0 - 1.0)
Nucleus sampling parameter:
- Lower values: More focused
- Higher values: More diverse

### Top-K (1 - 100)
Considers top K tokens:
- Lower values: More predictable
- Higher values: More variety

### Max Output Tokens
Limit response length:
```python
provider = GeminiProvider(
    api_key=api_key,
    max_output_tokens=2048
)
```

## Safety Settings

Gemini includes built-in safety filters:

```python
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configure safety (in provider code)
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}
```

## Performance Optimization

### Use Flash for High Throughput

```env
GEMINI_MODEL=gemini-1.5-flash
```

Best for:
- Chat applications with high volume
- Cost-sensitive deployments
- Quick responses needed

### Use Pro for Complex Tasks

```env
GEMINI_MODEL=gemini-1.5-pro
```

Best for:
- Long document analysis
- Complex reasoning tasks
- Multi-step problem solving

### Context Caching

Gemini automatically caches repeated contexts:
- Reduces latency for follow-up questions
- Lowers costs for repeated content
- Transparent to the application

## Error Handling

```python
try:
    response = await provider.generate(prompt="Hello")
except Exception as e:
    logger.error(f"Gemini error: {str(e)}")
    # Fallback to another provider
```

## Monitoring

The provider integrates with Prometheus metrics:

```python
# Metrics automatically tracked:
- gemini_requests_total
- gemini_request_duration_seconds
- gemini_tokens_total
- gemini_cost_total
- gemini_errors_total
```

View in Grafana dashboard at http://localhost:3001

## Cost Optimization Tips

1. **Use Flash for Most Queries**: 10x cheaper than Pro
2. **Implement Caching**: Reduce repeated context
3. **Limit Output Tokens**: Set max_output_tokens appropriately
4. **Monitor Usage**: Track costs in Grafana
5. **Batch Requests**: Process multiple queries efficiently

## Comparison with Other Providers

| Feature | Gemini 1.5 Pro | GPT-4 Turbo | Claude 3 Sonnet |
|---------|----------------|-------------|------------------|
| Context Window | 2M tokens | 128K tokens | 200K tokens |
| Input Cost/1K | $0.00125 | $0.01 | $0.003 |
| Output Cost/1K | $0.005 | $0.03 | $0.015 |
| Streaming | ✅ | ✅ | ✅ |
| Function Calling | ✅ | ✅ | ✅ |
| Multimodal | ✅ | ✅ | ✅ |

## Troubleshooting

### API Key Issues
```
Error: API key not valid
```
Solution: Verify API key in Google AI Studio

### Rate Limits
```
Error: Resource exhausted
```
Solution: Implement exponential backoff or upgrade quota

### Safety Blocks
```
Response blocked by safety filters
```
Solution: Adjust safety settings or rephrase prompt

### Token Limits
```
Error: Request exceeds token limit
```
Solution: Reduce context or split into multiple requests

## Next Steps

- [Model Provider Guide](model-providers.md)
- [API Reference](api-reference.md)
- [Cost Optimization Guide](cost-optimization.md)
- [Multi-Provider Setup](multi-provider.md)

## Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Google AI Studio](https://makersuite.google.com/)
- [Gemini Pricing](https://ai.google.dev/pricing)
- [Safety Guidance](https://ai.google.dev/docs/safety_guidance)
