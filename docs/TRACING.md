# Distributed Tracing with OpenTelemetry

This document describes the distributed tracing implementation in Zakera using OpenTelemetry.

## Overview

Distributed tracing allows you to track requests as they flow through the entire system, from the initial API call through model provider interactions, database queries, and tool executions. This is invaluable for:

- **Performance Optimization**: Identify bottlenecks and slow operations
- **Debugging**: Understand the complete request flow and find issues faster
- **Monitoring**: Track system health and performance over time
- **Cost Attribution**: See which operations consume the most resources

## Architecture

```
Client Request
    ↓
[FastAPI Endpoint] ──────────────────────┐
    ↓                                     |
[Authentication] ─────────────────────┐   |
    ↓                                 |   |
[Conversation Service] ────────────┐  |   |
    ↓                              |  |   |
[Model Provider Call] ──────────┐  |  |   |
    ├─ [OpenAI API]             |  |  |   |
    ├─ [Anthropic API]          |  |  |   |
    └─ [Gemini API]             ↓  ↓  ↓   ↓
                            [OpenTelemetry SDK]
                                    ↓
                            [Batch Processor]
                                    ↓
                              [Jaeger/OTLP]
                                    ↓
                            [Visualization UI]
```

## Quick Start

### 1. Enable Tracing

Edit your `.env` file:

```bash
# Enable tracing
TRACING_ENABLED=true

# Choose exporter (jaeger, otlp, console)
TRACE_EXPORTER=jaeger

# Jaeger configuration
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831

# Sample rate (0.0 to 1.0)
TRACE_SAMPLE_RATE=1.0
```

### 2. Start Jaeger

```bash
# Using Docker Compose
docker-compose up -d jaeger

# Access Jaeger UI
open http://localhost:16686
```

### 3. Initialize Tracing in Your App

```python
from fastapi import FastAPI
from monitoring.tracing import setup_tracing

app = FastAPI()

# Initialize tracing
setup_tracing(app)
```

## Usage Examples

### Automatic Tracing with Decorator

```python
from monitoring.tracing import trace

@trace("conversation.create")
async def create_conversation(user_id: str, message: str) -> Conversation:
    """Create a new conversation - automatically traced."""
    # Your logic here
    return conversation

@trace(
    name="model.generate",
    attributes={"provider": "openai"},
)
async def generate_response(prompt: str) -> str:
    """Generate response with custom attributes."""
    return response
```

### Manual Span Creation

```python
from monitoring.tracing import trace_context

async def process_message(message: str) -> str:
    with trace_context("message.processing") as span:
        # Add custom attributes
        span.set_attribute("message.length", len(message))
        span.set_attribute("language", detect_language(message))
        
        # Process message
        result = await process(message)
        
        # Add result attributes
        span.set_attribute("result.length", len(result))
        
        return result
```

### Model Provider Tracing

```python
from monitoring.tracing import trace_model_call
import time

async def call_openai(prompt: str) -> str:
    # Create span with model-specific attributes
    span = trace_model_call(
        provider="openai",
        model="gpt-4-turbo",
        input_tokens=count_tokens(prompt),
        temperature=0.7,
    )
    
    start = time.time()
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        
        # Add output attributes
        span.set_attribute("model.output_tokens", response.usage.completion_tokens)
        span.set_attribute("model.cost", calculate_cost(response.usage))
        span.set_attribute("model.latency", time.time() - start)
        span.set_status(Status(StatusCode.OK))
        
        return response.choices[0].message.content
    
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()
```

### Conversation Flow Tracing

```python
from monitoring.tracing import trace_conversation

async def handle_conversation(conversation_id: str, user_id: str, message: str):
    span = trace_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        message_count=get_message_count(conversation_id),
    )
    
    try:
        # Load conversation history
        span.add_event("loading_history")
        history = await load_history(conversation_id)
        span.set_attribute("history.loaded", len(history))
        
        # Generate response
        span.add_event("generating_response")
        response = await generate(message, history)
        
        # Save to database
        span.add_event("saving_message")
        await save_message(conversation_id, message, response)
        
        span.set_status(Status(StatusCode.OK))
        return response
    
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()
```

### Tool Execution Tracing

```python
from monitoring.tracing import trace_tool_execution
import time

async def execute_tool(tool_name: str, params: dict) -> dict:
    start = time.time()
    success = False
    
    try:
        result = await tool_registry.execute(tool_name, params)
        success = True
        return result
    
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        raise
    
    finally:
        execution_time = time.time() - start
        span = trace_tool_execution(
            tool_name=tool_name,
            success=success,
            execution_time=execution_time,
            params_count=len(params),
        )
        span.end()
```

### Adding Events to Current Span

```python
from monitoring.tracing import add_span_event, add_span_attribute

async def complex_operation():
    # Add milestone events
    add_span_event("validation_started")
    await validate_input()
    
    add_span_event("validation_complete")
    add_span_attribute("validation.passed", True)
    
    add_span_event("processing_started")
    result = await process()
    
    add_span_event("processing_complete", {
        "result.size": len(result),
        "result.type": type(result).__name__,
    })
    
    return result
```

## Configuration

### Environment Variables

```bash
# Enable/disable tracing
TRACING_ENABLED=true

# Service identification
SERVICE_NAME=zakera-ai-chat
SERVICE_VERSION=0.6.0
ENVIRONMENT=production

# Exporter configuration
TRACE_EXPORTER=jaeger  # jaeger, otlp, or console
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
OTLP_ENDPOINT=http://localhost:4317

# Sampling (0.0 = none, 1.0 = all)
TRACE_SAMPLE_RATE=1.0
```

### Sampling Strategies

```python
# Production: Sample 10% of traces
TRACE_SAMPLE_RATE=0.1

# Staging: Sample 50%
TRACE_SAMPLE_RATE=0.5

# Development: Sample everything
TRACE_SAMPLE_RATE=1.0
```

## Jaeger UI

### Accessing Jaeger

1. Start Jaeger: `docker-compose up -d jaeger`
2. Open browser: `http://localhost:16686`
3. Select service: "zakera-ai-chat"
4. View traces and analyze performance

### Key Features

- **Service Map**: Visualize service dependencies
- **Trace Search**: Find specific traces by operation, tags, or duration
- **Trace Timeline**: See detailed request flow and timing
- **Comparison**: Compare multiple traces side-by-side
- **Dependencies**: Understand service interactions

### Useful Queries

```
# Find slow model calls (> 5 seconds)
operation:model.* duration>5s

# Find errors
tags:error=true

# Find specific conversation
tags:conversation.id=conv_123

# Find expensive operations (> $0.01)
tags:model.cost>0.01

# Find operations by user
tags:conversation.user_id=user_456
```

## Best Practices

### 1. Use Descriptive Span Names

```python
# Good
@trace("conversation.create")
@trace("model.openai.gpt4.generate")
@trace("tool.calculator.execute")

# Bad
@trace("function1")
@trace("process")
```

### 2. Add Meaningful Attributes

```python
# Good - helps with debugging and analysis
span.set_attribute("user_id", user_id)
span.set_attribute("model", "gpt-4-turbo")
span.set_attribute("tokens", 1500)
span.set_attribute("cost", 0.045)

# Avoid sensitive data
# Bad - contains PII
span.set_attribute("user_email", email)  # DON'T DO THIS
span.set_attribute("api_key", key)       # DON'T DO THIS
```

### 3. Record Exceptions

```python
try:
    result = await risky_operation()
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
    raise
```

### 4. Use Events for Milestones

```python
span.add_event("cache_miss")
span.add_event("database_query_started")
span.add_event("model_response_received")
```

### 5. Clean Up Resources

```python
span = tracer.start_span("operation")
try:
    # Your code
    pass
finally:
    span.end()  # Always end spans
```

## Performance Impact

- **Overhead**: < 5ms per request with batch processing
- **Memory**: ~1-2MB per 1000 spans
- **Network**: Minimal (batched exports every 5 seconds)
- **CPU**: < 1% additional CPU usage

### Optimization Tips

1. **Use sampling in production**: `TRACE_SAMPLE_RATE=0.1`
2. **Batch exports**: Default configuration uses efficient batching
3. **Limit span attributes**: Only add essential attributes
4. **Async exports**: Non-blocking span export

## Troubleshooting

### Traces Not Appearing in Jaeger

1. Check if tracing is enabled: `TRACING_ENABLED=true`
2. Verify Jaeger is running: `docker-compose ps jaeger`
3. Check logs for export errors
4. Verify network connectivity to Jaeger

### High Memory Usage

1. Reduce sample rate: `TRACE_SAMPLE_RATE=0.1`
2. Check for span leaks (not calling `span.end()`)
3. Reduce batch size in span processor

### Missing Spans

1. Ensure decorator is used: `@trace()`
2. Check if function is async/sync compatible
3. Verify context propagation in async code

## Integration with Other Tools

### Prometheus Metrics

Correlate traces with metrics using trace IDs:

```python
span = get_current_span()
trace_id = span.get_span_context().trace_id
metric.labels(trace_id=trace_id).inc()
```

### Logging

Add trace context to logs:

```python
from opentelemetry import trace

span = trace.get_current_span()
trace_id = span.get_span_context().trace_id
logger.info("Processing request", extra={"trace_id": trace_id})
```

## Advanced Usage

### Custom Span Processors

```python
from opentelemetry.sdk.trace.export import SpanProcessor

class CustomProcessor(SpanProcessor):
    def on_start(self, span, parent_context):
        # Add custom logic on span start
        pass
    
    def on_end(self, span):
        # Add custom logic on span end
        pass

provider.add_span_processor(CustomProcessor())
```

### Multiple Exporters

```python
# Export to both Jaeger and console
jaeger_exporter = JaegerExporter(...)
console_exporter = ConsoleSpanExporter()

provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
provider.add_span_processor(BatchSpanProcessor(console_exporter))
```

## Security Considerations

1. **Never trace sensitive data**: API keys, passwords, PII
2. **Sanitize inputs**: Remove sensitive information before adding to spans
3. **Secure Jaeger**: Use authentication and HTTPS in production
4. **Limit retention**: Configure appropriate trace retention periods
5. **Access control**: Restrict who can view traces

## Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Python SDK Reference](https://opentelemetry-python.readthedocs.io/)
- [Best Practices](https://opentelemetry.io/docs/instrumentation/python/manual/)

## Support

For issues or questions:
- GitHub Issues: https://github.com/itsmepraks/zakera/issues
- Documentation: https://docs.zakera.app/tracing
