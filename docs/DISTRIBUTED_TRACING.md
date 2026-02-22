# Distributed Tracing with OpenTelemetry

Comprehensive guide to distributed tracing in Zakera AI chat agent using OpenTelemetry and Jaeger.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Trace Visualization](#trace-visualization)
- [Custom Tracing](#custom-tracing)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Production Deployment](#production-deployment)

## Overview

### What is Distributed Tracing?

Distributed tracing provides end-to-end visibility into requests as they flow through your application. Each request creates a "trace" consisting of multiple "spans" representing individual operations.

### Benefits

- 🔍 **End-to-end visibility**: See entire request flow from API call to model response
- 🐛 **Faster debugging**: Identify bottlenecks and errors quickly
- 📊 **Performance optimization**: Find slow operations and optimize them
- 💰 **Cost analysis**: Track model usage and costs by user/conversation
- 🎯 **SLA monitoring**: Ensure response times meet requirements
- 🔗 **Dependency mapping**: Understand service interactions

### What Gets Traced?

Zakera automatically traces:

✅ **API Requests** - All HTTP endpoints with request/response details  
✅ **Model Provider Calls** - OpenAI, Anthropic, Gemini, Ollama, etc.  
✅ **Conversations** - Message creation, retrieval, updates  
✅ **Tool Executions** - Built-in and custom tool calls  
✅ **Database Operations** - Queries, transactions, connections  
✅ **Cache Operations** - Redis and in-memory cache access  
✅ **Authentication** - Login, token validation, MFA  
✅ **WebSocket** - Real-time messaging connections  

## Quick Start

### 1. Enable Tracing

```bash
# In your .env file
ENABLE_TRACING=true
TRACE_SAMPLING_RATE=1.0  # 100% for development
OTLP_ENDPOINT=http://localhost:4317
```

### 2. Start Jaeger

```bash
# Start all services including Jaeger
docker-compose up -d

# Or start Jaeger standalone
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:1.52
```

### 3. Access Jaeger UI

Open http://localhost:16686 in your browser.

### 4. Generate Traces

```bash
# Make API requests
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "Hello, AI!", "model": "gpt-3.5-turbo"}'
```

### 5. View Traces

1. Go to Jaeger UI (http://localhost:16686)
2. Select service: `zakera-api`
3. Click "Find Traces"
4. Click on a trace to see details

## Architecture

### OpenTelemetry Components

```
┌─────────────────────────────────────────────────────────┐
│                    Zakera Application                   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         OpenTelemetry SDK & API                  │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Automatic Instrumentation                   │  │
│  │  • FastAPI (HTTP requests)                       │  │
│  │  • SQLAlchemy (DB queries)                       │  │
│  │  • HTTPX/AioHTTP (HTTP clients)                  │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Custom Instrumentation                      │  │
│  │  • Model provider calls                          │  │
│  │  • Conversation flows                            │  │
│  │  • Tool executions                               │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Batch Span Processor                     │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
└──────────────────────────┼──────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ OTLP Exporter   │
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Jaeger Collector│
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Jaeger Storage │
                  │  (Elasticsearch)│
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Jaeger UI     │
                  │ (Visualization) │
                  └─────────────────┘
```

### Trace Structure

A typical chat request trace:

```
POST /api/v1/chat/send                    [150ms total]
├── auth.validate_token                   [5ms]
├── conversation.get_or_create            [20ms]
│   └── db.query.select_conversation      [15ms]
├── conversation.add_message              [10ms]
│   └── db.query.insert_message           [8ms]
├── model.openai.chat_completion          [100ms]
│   ├── cache.check                       [2ms]
│   ├── http.post.openai_api              [95ms]
│   └── cache.set                         [3ms]
├── conversation.update_metadata          [8ms]
│   └── db.query.update_conversation      [6ms]
└── response.serialize                    [7ms]
```

## Configuration

### Environment Variables

```bash
# Basic Configuration
ENABLE_TRACING=true                    # Enable/disable tracing
TRACE_SAMPLING_RATE=0.1                # Sample 10% of requests
OTEL_SERVICE_NAME=zakera-api           # Service name in traces
OTEL_SERVICE_VERSION=0.6.0             # Service version
OTEL_DEPLOYMENT_ENVIRONMENT=production # Environment tag

# Exporter Configuration
TRACE_EXPORTER=otlp                    # Exporter type
OTLP_ENDPOINT=http://localhost:4317    # OTLP gRPC endpoint
OTLP_HTTP_ENDPOINT=http://localhost:4318/v1/traces

# Jaeger Configuration (alternative)
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# Feature Flags
TRACE_DB_QUERIES=true                  # Trace database queries
TRACE_HTTP_REQUESTS=true               # Trace HTTP clients
TRACE_MODEL_CALLS=true                 # Trace model providers
TRACE_TOOL_EXECUTIONS=true             # Trace tool calls
TRACE_CONVERSATIONS=true               # Trace conversations

# Performance Tuning
OTEL_BSP_MAX_QUEUE_SIZE=2048           # Batch processor queue
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512     # Export batch size
OTEL_BSP_SCHEDULE_DELAY=5000           # Export delay (ms)
```

### Sampling Strategies

**Development**: 100% sampling
```bash
TRACE_SAMPLING_RATE=1.0
```

**Staging**: 50% sampling
```bash
TRACE_SAMPLING_RATE=0.5
```

**Production**: 10% sampling (recommended)
```bash
TRACE_SAMPLING_RATE=0.1
```

**Always trace errors**: Errors are always traced regardless of sampling rate.

## Usage Examples

### Automatic Tracing (Zero Code)

FastAPI routes are automatically traced:

```python
from fastapi import FastAPI
from monitoring.instrumentation import instrument_app

app = FastAPI()

@app.on_event("startup")
async def startup():
    # This enables automatic tracing for all routes
    instrument_app(app)

@app.post("/api/v1/chat/send")
async def send_message(message: str):
    # Automatically traced - no code changes needed!
    response = await process_message(message)
    return response
```

### Custom Function Tracing

**Async Functions**:

```python
from monitoring.tracing import trace_async_function

@trace_async_function("process_user_input")
async def process_input(user_input: str):
    # Function execution is traced
    cleaned = await clean_input(user_input)
    validated = await validate_input(cleaned)
    return validated
```

**Sync Functions**:

```python
from monitoring.tracing import trace_function

@trace_function("calculate_tokens")
def count_tokens(text: str) -> int:
    # Function execution is traced
    return len(text.split())
```

### Model Provider Tracing

```python
from monitoring.trace_decorators import trace_model_call

@trace_model_call(provider="openai", model="gpt-4")
async def call_openai(prompt: str):
    response = await openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response

# Trace will include:
# - Provider: openai
# - Model: gpt-4
# - Temperature: 0.7
# - Token usage: input, output, total
# - Response time
# - Cost information
```

### Conversation Flow Tracing

```python
from monitoring.trace_decorators import trace_conversation

@trace_conversation()
async def process_conversation(conversation_id: str, message: str, user_id: str):
    # Automatically captures:
    # - conversation_id
    # - user_id
    # - message length
    # - processing time
    
    conversation = await get_conversation(conversation_id)
    response = await generate_response(conversation, message)
    await save_message(conversation_id, message, response)
    
    return response
```

### Tool Execution Tracing

```python
from monitoring.trace_decorators import trace_tool_execution

@trace_tool_execution(tool_name="web_search")
async def search_web(query: str, max_results: int = 10):
    # Trace includes:
    # - Tool name
    # - Input parameters (excluding sensitive data)
    # - Execution time
    # - Success/failure status
    # - Cache hits
    
    results = await search_engine.search(query, limit=max_results)
    return results
```

### Context Manager Usage

```python
from monitoring.tracing import AsyncTraceContext

async def complex_operation():
    async with AsyncTraceContext("complex_operation") as span:
        # Add custom attributes
        span.set_attribute("user.id", user_id)
        span.set_attribute("operation.type", "batch_processing")
        
        # Nested operations are automatically child spans
        result = await process_data()
        
        # Add result metadata
        span.set_attribute("result.count", len(result))
        span.set_attribute("result.success", True)
        
        return result
```

### Manual Span Creation

```python
from monitoring.tracing import get_tracer
from opentelemetry.trace import Status, StatusCode

async def manual_tracing_example():
    tracer = get_tracer()
    
    with tracer.start_as_current_span("manual_operation") as span:
        span.set_attribute("custom.attribute", "value")
        
        try:
            result = await do_work()
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

### Adding Span Attributes

```python
from monitoring.tracing import set_span_attribute, add_span_event

async def process_with_metadata(data: dict):
    # Add attributes to current span
    set_span_attribute("data.size", len(data))
    set_span_attribute("data.type", data.get("type"))
    
    # Add events
    add_span_event("processing_started", {
        "timestamp": datetime.now().isoformat(),
        "items": len(data)
    })
    
    result = await process(data)
    
    add_span_event("processing_completed", {
        "duration_ms": 150,
        "success": True
    })
    
    return result
```

## Trace Visualization

### Jaeger UI Features

#### 1. Search Traces

- **Service**: Select `zakera-api`
- **Operation**: Filter by endpoint (e.g., `POST /api/v1/chat/send`)
- **Tags**: Filter by attributes (e.g., `user.id=123`, `model=gpt-4`)
- **Duration**: Find slow requests (e.g., `>5s`)
- **Time Range**: Select time period

#### 2. Trace Details

Click on a trace to see:

- **Timeline view**: Visual representation of spans
- **Span details**: Attributes, events, logs
- **Service graph**: Dependencies between services
- **Critical path**: Slowest operations highlighted

#### 3. Useful Queries

**Find slow API requests**:
```
service=zakera-api operation=POST /api/v1/chat/send minDuration=5s
```

**Find errors**:
```
service=zakera-api error=true
```

**Find specific user's traces**:
```
service=zakera-api user.id=user_123
```

**Find expensive model calls**:
```
service=zakera-api ai.model.provider=openai ai.cost.total>0.1
```

**Find conversations with many messages**:
```
service=zakera-api conversation.message_count>50
```

## Custom Tracing

### Database Instrumentation

```python
from sqlalchemy import create_engine
from monitoring.instrumentation import instrument_database

engine = create_engine(DATABASE_URL)
instrument_database(engine)  # Traces all SQL queries
```

### HTTP Client Tracing

Automatic for httpx, aiohttp, and requests:

```python
import httpx

# Automatically traced!
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/data")
```

### Custom Metrics in Spans

```python
async def track_model_cost():
    async with AsyncTraceContext("model_call") as span:
        response = await model.generate(prompt)
        
        # Add cost tracking
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 0.01 / 1000) + (output_tokens * 0.03 / 1000)
        
        span.set_attribute("ai.usage.input_tokens", input_tokens)
        span.set_attribute("ai.usage.output_tokens", output_tokens)
        span.set_attribute("ai.cost.total", cost)
        span.set_attribute("ai.cost.currency", "USD")
```

## Best Practices

### 1. Meaningful Span Names

❌ **Bad**:
```python
with AsyncTraceContext("process"):
    ...
```

✅ **Good**:
```python
with AsyncTraceContext("conversation.process_message"):
    ...
```

### 2. Add Relevant Attributes

```python
span.set_attribute("user.id", user_id)
span.set_attribute("conversation.id", conv_id)
span.set_attribute("model.provider", "openai")
span.set_attribute("model.name", "gpt-4")
```

### 3. Handle Errors Properly

```python
try:
    result = await risky_operation()
    span.set_status(Status(StatusCode.OK))
except Exception as e:
    span.set_status(Status(StatusCode.ERROR, str(e)))
    span.record_exception(e)
    raise
```

### 4. Don't Trace Everything

- Exclude health checks: `/health`, `/metrics`
- Use sampling in production
- Don't trace static files
- Skip tracing for high-frequency low-value operations

### 5. Secure Sensitive Data

❌ **Bad**:
```python
span.set_attribute("user.password", password)  # Never!
span.set_attribute("api_key", api_key)        # Never!
```

✅ **Good**:
```python
span.set_attribute("user.id", user_id)
span.set_attribute("auth.method", "jwt")
```

### 6. Use Semantic Conventions

Follow OpenTelemetry [semantic conventions](https://opentelemetry.io/docs/specs/semconv/):

```python
# HTTP attributes
span.set_attribute("http.method", "POST")
span.set_attribute("http.url", url)
span.set_attribute("http.status_code", 200)

# Database attributes
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.operation", "SELECT")
span.set_attribute("db.statement", query)
```

## Troubleshooting

### Traces Not Appearing

1. **Check if tracing is enabled**:
   ```bash
   echo $ENABLE_TRACING  # Should be 'true'
   ```

2. **Verify Jaeger is running**:
   ```bash
   docker ps | grep jaeger
   curl http://localhost:16686
   ```

3. **Check connectivity**:
   ```bash
   curl http://localhost:4318/v1/traces  # Should return 405
   ```

4. **Review logs**:
   ```bash
   docker logs zakera-backend | grep -i trace
   docker logs zakera-jaeger
   ```

### High Memory Usage

1. **Reduce sampling rate**:
   ```bash
   TRACE_SAMPLING_RATE=0.1  # 10% instead of 100%
   ```

2. **Tune batch processor**:
   ```bash
   OTEL_BSP_MAX_QUEUE_SIZE=1024        # Reduce queue
   OTEL_BSP_SCHEDULE_DELAY=10000       # Export more frequently
   ```

3. **Limit trace retention** in Jaeger

### Slow Performance

1. **Use batch processor** (default, but verify)
2. **Increase export delay**:
   ```bash
   OTEL_BSP_SCHEDULE_DELAY=10000  # 10 seconds
   ```
3. **Reduce sampling** in production

### Missing Spans

1. **Check parent context propagation**:
   ```python
   # Ensure context is propagated in async code
   from opentelemetry import context
   token = context.attach(current_context)
   try:
       await async_operation()
   finally:
       context.detach(token)
   ```

2. **Verify instrumentations are loaded**:
   ```python
   # Check logs for "instrumentation enabled" messages
   ```

## Performance Tuning

### Sampling Configuration

**Environment-based sampling**:
```python
sampling_rates = {
    "development": 1.0,   # 100%
    "staging": 0.5,       # 50%
    "production": 0.1,    # 10%
}

TRACE_SAMPLING_RATE = sampling_rates[environment]
```

**Always sample errors**:
```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

# Custom sampler that always samples errors
class ErrorSampler:
    def should_sample(self, context, trace_id, name, kind, attributes, links):
        # Always sample if there's an error
        if attributes and attributes.get("error") == True:
            return Decision.RECORD_AND_SAMPLE
        
        # Otherwise use ratio sampling
        return ratio_sampler.should_sample(...)
```

### Batch Processor Tuning

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,          # Default: 2048
    max_export_batch_size=512,    # Default: 512
    schedule_delay_millis=5000,   # Default: 5000 (5s)
    export_timeout_millis=30000,  # Default: 30000 (30s)
)
```

### Resource Detection

Automatic resource detection:
```python
from opentelemetry.sdk.resources import Resource, ResourceDetector

resource = Resource.create({
    "service.name": "zakera-api",
    "service.version": "0.6.0",
    "deployment.environment": "production",
    "cloud.provider": "aws",
    "cloud.region": "us-east-1",
})
```

## Production Deployment

### High Availability Setup

```yaml
# docker-compose.production.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.52
    environment:
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Elasticsearch Backend

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - es_data:/usr/share/elasticsearch/data
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:1.52
        env:
        - name: COLLECTOR_OTLP_ENABLED
          value: "true"
        - name: SPAN_STORAGE_TYPE
          value: elasticsearch
        ports:
        - containerPort: 16686
        - containerPort: 4317
        - containerPort: 4318
```

### Monitoring Jaeger

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'jaeger'
    static_configs:
      - targets: ['jaeger:14269']
```

### Data Retention

Configure trace retention:
```bash
# Keep traces for 7 days
docker run -e SPAN_STORAGE_TYPE=elasticsearch \
  -e ES_INDEX_CLEANER_ENABLED=true \
  -e ES_INDEX_CLEANER_DAYS=7 \
  jaegertracing/all-in-one:1.52
```

### Security

1. **Secure Jaeger UI** with authentication
2. **Encrypt trace data** in transit and at rest
3. **Redact sensitive data** from spans
4. **Use RBAC** to control access to traces

---

## Summary

Distributed tracing with OpenTelemetry provides:

✅ **Complete visibility** into request flows  
✅ **Fast debugging** of issues  
✅ **Performance optimization** opportunities  
✅ **Cost tracking** per model/user  
✅ **Production-ready** with minimal overhead  
✅ **Standard-based** (OpenTelemetry)  
✅ **Vendor-neutral** (works with any backend)  

**Next Steps**:
1. Enable tracing in development
2. Explore traces in Jaeger UI
3. Add custom tracing to your code
4. Configure sampling for production
5. Set up alerts on trace metrics

For more information:
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Zakera Monitoring Guide](MONITORING.md)
