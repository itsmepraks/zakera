# Distributed Tracing with OpenTelemetry

## Overview

Zakera uses OpenTelemetry for comprehensive distributed tracing, providing deep visibility into system performance, request flows, and debugging capabilities across all components.

## Features

### Automatic Instrumentation
- **FastAPI**: All HTTP requests, routes, and exceptions
- **SQLAlchemy**: Database queries with SQL comments
- **HTTPX/AioHTTP/Requests**: All HTTP client calls
- **Async Operations**: Full support for async/await patterns

### Custom Tracing
- Model provider calls with token usage and costs
- Conversation processing across multiple turns
- Tool executions with input/output capture
- Custom business logic spans
- Performance metrics embedded in traces

### Trace Visualization
- Jaeger UI for exploring traces
- Service dependency graphs
- Latency analysis and percentiles
- Error tracking and debugging
- Request flow visualization

## Quick Start

### 1. Start Jaeger Backend

```bash
# Using Docker Compose (recommended)
docker-compose up -d jaeger

# Access Jaeger UI
open http://localhost:16686
```

### 2. Configure Tracing

```bash
# .env file
TRACING_ENABLED=true
OTLP_ENDPOINT=http://localhost:4318
TRACING_SAMPLING_RATE=1.0  # 100% sampling (use 0.1 for 10% in production)
```

### 3. Initialize in Application

```python
from fastapi import FastAPI
from src.monitoring.tracing import setup_tracing, instrument_fastapi

# Initialize tracing
setup_tracing(
    service_name="zakera-api",
    service_version="0.6.0",
    environment="production"
)

# Create FastAPI app
app = FastAPI()

# Instrument app with automatic tracing
instrument_fastapi(app)
```

## Usage Examples

### Decorator Pattern (Recommended)

```python
from src.monitoring.tracing import trace_function

@trace_function("process_user_message")
async def process_message(user_id: str, message: str):
    # Automatically traced with:
    # - Function name
    # - Execution time
    # - Exceptions (if any)
    result = await model.generate(message)
    return result
```

### Context Manager Pattern

```python
from src.monitoring.tracing import trace_span

async def complex_operation():
    with trace_span("database.query", {"table": "conversations"}) as span:
        results = await db.query(...)
        span.set_attribute("results.count", len(results))
        span.add_event("query_complete")
        return results
```

### Model Call Tracing

```python
from src.monitoring.tracing import trace_model_call

async def call_openai(prompt: str):
    with trace_model_call(
        provider="openai",
        model="gpt-4",
        input_tokens=100,
        output_tokens=50,
        cost=0.003
    ) as span:
        response = await openai_client.chat.completions.create(...)
        span.add_event("response_received")
        return response
```

### Conversation Tracing

```python
from src.monitoring.tracing import trace_conversation

async def handle_conversation(conv_id: str, user_id: str):
    with trace_conversation(
        conversation_id=conv_id,
        user_id=user_id,
        message_count=10
    ) as span:
        history = await get_history(conv_id)
        span.set_attribute("history.tokens", calculate_tokens(history))
        return history
```

### Tool Execution Tracing

```python
from src.monitoring.tracing import trace_tool_execution

async def execute_web_search(query: str):
    with trace_tool_execution(
        tool_name="web_search",
        tool_input={"query": query}
    ) as span:
        results = await search_api.search(query)
        span.set_attribute("results.count", len(results))
        span.set_attribute("results.relevance", results[0].score)
        return results
```

### Adding Events to Current Span

```python
from src.monitoring.tracing import add_trace_event

async def process_with_cache(key: str):
    # Check cache
    if cached := await cache.get(key):
        add_trace_event("cache_hit", {"cache.key": key})
        return cached
    
    add_trace_event("cache_miss", {"cache.key": key})
    result = await expensive_operation()
    await cache.set(key, result)
    return result
```

### Trace ID for Log Correlation

```python
from src.monitoring.tracing import get_trace_id
import logging

logger = logging.getLogger(__name__)

async def handle_request(request_id: str):
    trace_id = get_trace_id()
    logger.info(
        f"Processing request",
        extra={
            "request_id": request_id,
            "trace_id": trace_id
        }
    )
```

## Architecture

### Components

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Zakera    │─────▶│ OpenTelemetry│─────▶│   Jaeger    │
│ Application │      │   Collector  │      │   Backend   │
└─────────────┘      └──────────────┘      └─────────────┘
       │                                           │
       │                                           ▼
       │                                    ┌─────────────┐
       │                                    │  Jaeger UI  │
       │                                    │(Port 16686) │
       │                                    └─────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              Automatic Instrumentation               │
├──────────────────────────────────────────────────────┤
│ • FastAPI (HTTP requests, routes, errors)            │
│ • SQLAlchemy (database queries)                      │
│ • HTTPX/AioHTTP (HTTP client calls)                  │
│ • Custom spans (models, conversations, tools)        │
└──────────────────────────────────────────────────────┘
```

### Trace Flow

```
HTTP Request
    │
    ├─ FastAPI Span (automatic)
    │   ├─ Authentication Span
    │   ├─ Conversation Span (custom)
    │   │   ├─ Database Query Span (automatic)
    │   │   └─ Memory Retrieval Span (custom)
    │   ├─ Model Provider Span (custom)
    │   │   ├─ Token Counting Span
    │   │   ├─ API Call Span (automatic via HTTPX)
    │   │   └─ Response Processing Span
    │   └─ Tool Execution Span (custom)
    │       └─ HTTP Request Span (automatic)
    └─ Response
```

## Configuration

### Environment Variables

```bash
# Enable/disable tracing
TRACING_ENABLED=true

# OTLP endpoint (Jaeger collector)
OTLP_ENDPOINT=http://localhost:4318

# Sampling rate (0.0 to 1.0)
# 1.0 = 100% (dev/staging)
# 0.1 = 10% (production with high traffic)
TRACING_SAMPLING_RATE=1.0

# Export traces to console (debugging)
TRACING_CONSOLE_EXPORT=false
```

### Jaeger Ports

```yaml
UI:              http://localhost:16686
OTLP HTTP:       http://localhost:4318
OTLP gRPC:       http://localhost:4317
Jaeger Thrift:   http://localhost:14268
Zipkin:          http://localhost:9411
```

## Best Practices

### 1. Use Appropriate Span Names

```python
# ❌ Bad: Too generic
with trace_span("process"):
    ...

# ✅ Good: Descriptive and hierarchical
with trace_span("conversation.process.summarize"):
    ...
```

### 2. Add Relevant Attributes

```python
# ❌ Bad: Missing context
with trace_span("model.call"):
    result = await model.generate(prompt)

# ✅ Good: Rich attributes for filtering/analysis
with trace_span("model.call", {
    "model.provider": "openai",
    "model.name": "gpt-4",
    "prompt.length": len(prompt),
    "user.id": user_id
}) as span:
    result = await model.generate(prompt)
    span.set_attribute("tokens.input", result.input_tokens)
    span.set_attribute("tokens.output", result.output_tokens)
```

### 3. Use Events for Milestones

```python
with trace_span("data.processing") as span:
    span.add_event("validation_started")
    validate_data(data)
    
    span.add_event("transformation_started")
    transformed = transform_data(data)
    
    span.add_event("storage_started")
    await store_data(transformed)
    
    span.add_event("processing_complete")
```

### 4. Handle Errors Properly

```python
try:
    with trace_span("critical.operation") as span:
        result = await risky_operation()
        span.set_attribute("result.status", "success")
except Exception as e:
    # Exception is automatically recorded in span
    logger.error(f"Operation failed: {e}")
    raise
```

### 5. Adjust Sampling in Production

```python
# Development: Trace everything
TRACING_SAMPLING_RATE=1.0

# Production (high traffic): Sample 10%
TRACING_SAMPLING_RATE=0.1

# Production (critical paths): Always trace specific operations
# Use custom sampling logic in code
```

## Analyzing Traces

### Finding Slow Requests

1. Open Jaeger UI: http://localhost:16686
2. Select service: `zakera-api`
3. Set minimum duration: `1000ms` (1 second)
4. Click "Find Traces"
5. Examine spans to identify bottlenecks

### Debugging Errors

1. Select service and set tag: `error=true`
2. Click on failed trace
3. Examine exception details in span
4. Follow trace through all services
5. Check span attributes for context

### Analyzing Dependencies

1. Click "System Architecture" tab
2. View service dependency graph
3. Identify external service calls
4. Check latency between services

### Performance Optimization

1. Group traces by operation
2. Compare P50, P95, P99 latencies
3. Identify outliers
4. Drill into slow traces
5. Optimize identified bottlenecks

## Integration with Other Tools

### Log Correlation

```python
from src.monitoring.tracing import get_trace_id
import structlog

logger = structlog.get_logger()

def log_with_trace():
    logger.info(
        "Processing request",
        trace_id=get_trace_id(),
        user_id="user_123"
    )
```

### Metrics Correlation

```python
from prometheus_client import Histogram
from src.monitoring.tracing import get_trace_id

latency_histogram = Histogram(
    'request_latency_seconds',
    'Request latency',
    ['endpoint', 'trace_id']
)

with latency_histogram.labels(
    endpoint="/chat",
    trace_id=get_trace_id() or "none"
).time():
    await process_request()
```

### Alert Integration

```python
# In alert handlers
async def send_alert(error_message: str):
    trace_id = get_trace_id()
    await slack.send_message(
        f"Error: {error_message}\n"
        f"Trace: http://localhost:16686/trace/{trace_id}"
    )
```

## Troubleshooting

### Traces Not Appearing

1. Check Jaeger is running:
   ```bash
   curl http://localhost:16686
   ```

2. Verify OTLP endpoint:
   ```bash
   curl http://localhost:4318/v1/traces
   ```

3. Check environment variables:
   ```bash
   echo $TRACING_ENABLED  # should be "true"
   echo $OTLP_ENDPOINT    # should point to Jaeger
   ```

4. Enable console export for debugging:
   ```bash
   export TRACING_CONSOLE_EXPORT=true
   ```

### High Memory Usage

1. Reduce sampling rate:
   ```bash
   export TRACING_SAMPLING_RATE=0.1  # 10%
   ```

2. Adjust batch processor settings in `tracing.py`:
   ```python
   BatchSpanProcessor(
       exporter,
       max_queue_size=512,      # Reduce from 2048
       max_export_batch_size=128,  # Reduce from 512
   )
   ```

### Performance Impact

- Typical overhead: 1-3% with batching
- Network overhead: Minimal with async export
- Storage: ~1KB per span average

Optimization tips:
- Use sampling for high-traffic endpoints
- Limit attribute sizes (max 500 chars)
- Avoid creating spans in tight loops
- Use batch processing (enabled by default)

## Production Deployment

### Scalable Jaeger Setup

```yaml
# Use Jaeger with Elasticsearch backend
services:
  jaeger-collector:
    image: jaegertracing/jaeger-collector
    environment:
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
  
  jaeger-query:
    image: jaegertracing/jaeger-query
    environment:
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
  
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
```

### Security Considerations

1. Use TLS for OTLP export:
   ```python
   OTLPSpanExporter(
       endpoint="https://jaeger.company.com:4318",
       insecure=False,  # Enable TLS
       credentials=ssl_credentials
   )
   ```

2. Sanitize sensitive data:
   ```python
   # Don't add passwords, tokens, PII to spans
   span.set_attribute("user.id", user_id)  # ✅ OK
   span.set_attribute("user.email", email)  # ❌ PII
   span.set_attribute("api.key", api_key)  # ❌ Sensitive
   ```

3. Set data retention policies:
   ```bash
   # Jaeger with retention
   docker run -e SPAN_STORAGE_TYPE=elasticsearch \
              -e ES_INDEX_RETENTION=7d \
              jaegertracing/jaeger-collector
   ```

## Advanced Features

### Custom Samplers

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased

# Sample 10% of traces, always sample if parent is sampled
sampler = ParentBased(root=TraceIdRatioBased(0.1))

provider = TracerProvider(
    resource=resource,
    sampler=sampler
)
```

### Span Links (Batch Processing)

```python
from opentelemetry.trace import Link

# Link multiple related operations
with tracer.start_as_current_span(
    "batch.process",
    links=[Link(span_context) for span_context in parent_spans]
) as span:
    await process_batch(items)
```

### Baggage (Cross-Cutting Context)

```python
from opentelemetry.baggage import set_baggage

# Propagate data across service boundaries
set_baggage("tenant.id", "tenant_123")
set_baggage("experiment.variant", "B")
```

## Resources

- OpenTelemetry Docs: https://opentelemetry.io/docs/
- Jaeger Docs: https://www.jaegertracing.io/docs/
- Best Practices: https://opentelemetry.io/docs/concepts/signals/traces/
- Python SDK: https://opentelemetry-python.readthedocs.io/

## Support

For issues or questions:
- GitHub Issues: https://github.com/itsmepraks/zakera/issues
- Documentation: https://docs.zakera.app/tracing
- Community: https://discord.gg/zakera
