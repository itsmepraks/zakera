# Google Gemini 2.0 Flash Provider

The Gemini 2.0 Flash provider enables access to Google's latest Gemini 2.0 models with enhanced multimodal capabilities and extended context windows.

## Overview

Gemini 2.0 Flash is Google's latest generation AI model featuring:
- **1M token context window** for processing large documents
- **Native multimodal support** for text, images, video, and audio
- **Enhanced reasoning capabilities** with thinking mode
- **Grounding with Google Search** for up-to-date information
- **Free tier availability** during preview period
- **Streaming support** for real-time responses

## Supported Models

### gemini-2.0-flash-exp
- **Context Window**: 1,048,576 tokens (1M)
- **Max Output**: 8,192 tokens
- **Modalities**: Text, Images, Video, Audio
- **Cost**: Free during preview
- **Best For**: General purpose, long documents, multimodal tasks

### gemini-2.0-flash-thinking-exp
- **Context Window**: 32,768 tokens
- **Max Output**: 8,192 tokens
- **Modalities**: Text, Images
- **Cost**: Free during preview
- **Best For**: Complex reasoning, step-by-step problem solving

## Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_google_api_key_here

# Optional
DEFAULT_MODEL=gemini-2.0-flash-exp
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=8192
```

### Obtaining API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

## Usage Examples

### Basic Text Generation

```python
from src.model.providers_gemini2 import Gemini2Provider
from src.model.config import ModelConfig

# Initialize provider
config = ModelConfig(
    model="gemini-2.0-flash-exp",
    temperature=0.7,
    max_tokens=2048
)
provider = Gemini2Provider(api_key="your_api_key", config=config)

# Generate response
messages = [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": "Explain quantum computing in simple terms."}
]

response = await provider.generate(messages)
print(response.content)
print(f"Tokens used: {response.tokens_used}")
```

### Streaming Responses

```python
# Stream responses for real-time output
async for chunk in provider.stream(messages):
    if chunk.content:
        print(chunk.content, end="", flush=True)
    if chunk.finish_reason:
        print(f"\nFinished: {chunk.finish_reason}")
        print(f"Total tokens: {chunk.tokens_used}")
```

### Using Grounding with Google Search

```python
# Enable search grounding for factual queries
messages = [
    {"role": "user", "content": "What are the latest developments in AI this week?"}
]

response = await provider.generate(
    messages,
    use_search_grounding=True  # Enable Google Search integration
)
print(response.content)
```

### JSON Mode

```python
# Request structured JSON output
messages = [
    {
        "role": "user",
        "content": "List 3 programming languages and their use cases in JSON format."
    }
]

response = await provider.generate(
    messages,
    response_mime_type="application/json"
)
print(response.content)  # Returns valid JSON
```

### Advanced Configuration

```python
# Custom generation parameters
response = await provider.generate(
    messages,
    model="gemini-2.0-flash-thinking-exp",  # Use thinking mode
    temperature=0.9,
    max_tokens=4096,
    top_p=0.95,
    top_k=40
)
```

## Features

### Safety Settings

The provider includes built-in content safety filters:

```python
SAFETY_SETTINGS = {
    "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
}
```

Thresholds:
- `BLOCK_NONE`: No blocking
- `BLOCK_LOW_AND_ABOVE`: Block low probability and above
- `BLOCK_MEDIUM_AND_ABOVE`: Block medium probability and above (default)
- `BLOCK_ONLY_HIGH`: Block only high probability

### Error Handling

The provider implements robust error handling:

```python
try:
    response = await provider.generate(messages)
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded, retrying...")
    elif e.response.status_code == 400:
        print("Invalid request parameters")
    else:
        print(f"API error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Retry Logic

Automatic retry with exponential backoff:
- **Max retries**: 3
- **Initial delay**: 1 second
- **Backoff multiplier**: 2x
- **Handles**: Rate limits, transient errors

## API Endpoints

The provider uses the following Google AI API endpoints:

### Non-Streaming
```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
```

### Streaming
```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent
```

## Performance Considerations

### Context Window Optimization

With 1M token context:
- Can process entire books or codebases
- Maintain long conversation histories
- Analyze large datasets in single request

### Latency

- **First token**: ~500-1000ms
- **Streaming**: ~50-100ms per chunk
- **Batch processing**: Use non-streaming for better throughput

### Cost Optimization

During preview period:
- Free tier with rate limits
- Monitor token usage for production planning
- Use streaming for better UX without cost penalty

## Monitoring

### OpenTelemetry Integration

The provider includes automatic tracing:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Automatic spans created for:
# - gemini2_generate
# - gemini2_stream
```

### Metrics to Track

- **Token usage**: Input/output tokens per request
- **Latency**: Response time distribution
- **Error rate**: Failed requests by type
- **Cost**: Track for production planning

## Limitations

### Rate Limits (Preview)

- **Requests per minute**: 60
- **Tokens per minute**: Varies by usage
- **Concurrent requests**: 10

### Content Restrictions

- Subject to safety filters
- Cannot generate harmful content
- May refuse certain topics

### Model Availability

- Preview models may change
- Pricing will be introduced after preview
- Monitor Google AI announcements

## Best Practices

### 1. Use System Instructions

Provide clear system context:

```python
messages = [
    {
        "role": "system",
        "content": "You are an expert Python developer. Provide code examples."
    },
    {"role": "user", "content": "How do I read a CSV file?"}
]
```

### 2. Enable Streaming for UX

Use streaming for better user experience:

```python
async def stream_response(messages):
    async for chunk in provider.stream(messages):
        if chunk.content:
            yield chunk.content
```

### 3. Implement Proper Error Handling

Handle different error scenarios:

```python
try:
    response = await provider.generate(messages)
except ValueError as e:
    # Invalid configuration
    logger.error(f"Configuration error: {e}")
except httpx.HTTPStatusError as e:
    # API errors
    logger.error(f"API error: {e.response.status_code}")
except Exception as e:
    # Unexpected errors
    logger.error(f"Unexpected error: {e}")
```

### 4. Monitor Usage

Track token usage and costs:

```python
response = await provider.generate(messages)
logger.info(f"Request used {response.tokens_used} tokens")
logger.info(f"Cost: ${response.cost:.6f}")
```

## Troubleshooting

### Invalid API Key

```
Error: 401 Unauthorized
```

**Solution**: Verify API key in Google AI Studio

### Rate Limit Exceeded

```
Error: 429 Too Many Requests
```

**Solution**: Implement exponential backoff (built-in) or request quota increase

### Content Blocked

```
Error: Content filtered by safety settings
```

**Solution**: Adjust safety settings or rephrase request

### Model Not Found

```
Error: Model not supported
```

**Solution**: Check model name spelling and availability

## Migration from Gemini 1.5

If migrating from Gemini 1.5:

1. **Update model name**: `gemini-1.5-flash` → `gemini-2.0-flash-exp`
2. **Adjust context window**: 1M tokens now available
3. **Update import**: Use `Gemini2Provider` instead of `GeminiProvider`
4. **Test thoroughly**: Preview models may behave differently

## Additional Resources

- [Google AI Documentation](https://ai.google.dev/docs)
- [Gemini API Reference](https://ai.google.dev/api/rest)
- [Safety Settings Guide](https://ai.google.dev/docs/safety_setting_gemini)
- [Best Practices](https://ai.google.dev/docs/best_practices)

## Support

For issues or questions:
1. Check troubleshooting section
2. Review Google AI documentation
3. Open an issue in the repository
4. Contact the development team
