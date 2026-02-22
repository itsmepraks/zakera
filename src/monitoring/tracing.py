"""
Distributed Tracing Module with OpenTelemetry

Provides comprehensive distributed tracing capabilities for the Zakera AI chat agent
using OpenTelemetry. Enables request-to-response tracing, performance monitoring,
and debugging across all system components.

Features:
- Automatic FastAPI request tracing
- Custom spans for model providers, conversations, and tools
- Trace context propagation across async operations
- Jaeger backend integration for visualization
- Performance metrics embedded in traces
- Error tracking with exception details

Usage:
    # Initialize tracing (call once at startup)
    from src.monitoring.tracing import setup_tracing
    setup_tracing(service_name="zakera-api", environment="production")

    # Use decorator for automatic function tracing
    from src.monitoring.tracing import trace_function
    
    @trace_function("custom.operation")
    async def my_function(arg1, arg2):
        # Your code here
        pass

    # Use context manager for manual span control
    from src.monitoring.tracing import tracer
    
    with tracer.start_as_current_span("custom-operation") as span:
        span.set_attribute("user.id", user_id)
        # Your code here

Access traces at: http://localhost:16686 (Jaeger UI)
"""

import functools
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

# Global tracer instance
tracer: Optional[trace.Tracer] = None

# Configuration
TRACING_ENABLED = os.getenv("TRACING_ENABLED", "true").lower() == "true"
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4318")
SAMPLING_RATE = float(os.getenv("TRACING_SAMPLING_RATE", "1.0"))  # 1.0 = 100%
CONSOLE_EXPORT = os.getenv("TRACING_CONSOLE_EXPORT", "false").lower() == "true"


def setup_tracing(
    service_name: str = "zakera",
    service_version: str = "0.6.0",
    environment: str = "development",
    otlp_endpoint: Optional[str] = None,
) -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry distributed tracing.

    Sets up the tracer provider, exporters, and automatic instrumentation for
    FastAPI, SQLAlchemy, and HTTP clients. Should be called once at application
    startup.

    Args:
        service_name: Name of the service (default: "zakera")
        service_version: Version of the service (default: "0.6.0")
        environment: Deployment environment (default: "development")
        otlp_endpoint: OTLP collector endpoint (default: from env or localhost:4318)

    Returns:
        Tracer instance if tracing is enabled, None otherwise

    Example:
        >>> from src.monitoring.tracing import setup_tracing
        >>> tracer = setup_tracing(
        ...     service_name="zakera-api",
        ...     environment="production"
        ... )
        >>> if tracer:
        ...     print("Tracing initialized successfully")
    """
    global tracer

    if not TRACING_ENABLED:
        logger.info("Distributed tracing is disabled (TRACING_ENABLED=false)")
        return None

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                "deployment.environment": environment,
                "telemetry.sdk.name": "opentelemetry",
                "telemetry.sdk.language": "python",
                "telemetry.sdk.version": "1.22.0",
                "host.name": os.getenv("HOSTNAME", "localhost"),
            }
        )

        # Create tracer provider with resource
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter (sends to Jaeger)
        endpoint = otlp_endpoint or OTLP_ENDPOINT
        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            insecure=True,  # Use TLS in production
        )

        # Add batch span processor for efficient export
        # Batching reduces overhead and network calls
        provider.add_span_processor(
            BatchSpanProcessor(
                otlp_exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,  # Export every 5 seconds
            )
        )

        # Add console exporter for development debugging (optional)
        if CONSOLE_EXPORT:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("Console trace export enabled for debugging")

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer instance
        tracer = trace.get_tracer(__name__, service_version)

        # Automatic instrumentation for common libraries
        _setup_automatic_instrumentation()

        logger.info(
            f"OpenTelemetry tracing initialized successfully "
            f"(service={service_name}, env={environment}, endpoint={endpoint})"
        )

        return tracer

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        # Graceful degradation - continue without tracing
        return None


def _setup_automatic_instrumentation() -> None:
    """
    Configure automatic instrumentation for supported libraries.

    Instruments:
    - FastAPI (HTTP requests, routes, exceptions)
    - SQLAlchemy (database queries)
    - HTTPX (async HTTP client)
    - AioHTTP (async HTTP client)
    - Requests (sync HTTP client)
    """
    try:
        # Note: FastAPI instrumentation is done separately in main.py
        # to ensure proper app instance binding

        # Instrument database queries
        SQLAlchemyInstrumentor().instrument(
            enable_commenter=True,  # Add SQL comments with trace context
            skip_dep_check=True,
        )
        logger.debug("SQLAlchemy instrumentation enabled")

        # Instrument HTTP clients
        HTTPXClientInstrumentor().instrument()
        AioHttpClientInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        logger.debug("HTTP client instrumentation enabled")

    except Exception as e:
        logger.warning(f"Some automatic instrumentation failed: {e}")


def instrument_fastapi(app: Any) -> None:
    """
    Instrument FastAPI application with automatic tracing.

    Should be called after app creation but before starting the server.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> from src.monitoring.tracing import instrument_fastapi
        >>> 
        >>> app = FastAPI()
        >>> instrument_fastapi(app)
    """
    if not TRACING_ENABLED or not tracer:
        return

    try:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace.get_tracer_provider(),
            excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json",
        )
        logger.info("FastAPI automatic instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


def trace_function(span_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically trace function execution.

    Creates a new span for the decorated function with timing, arguments,
    and exception information.

    Args:
        span_name: Custom span name (default: function name)
        attributes: Additional attributes to add to the span

    Returns:
        Decorated function with tracing

    Example:
        >>> @trace_function("process_user_request")
        ... async def process_request(user_id: str, message: str):
        ...     # Your code here
        ...     return result

        >>> @trace_function(attributes={"version": "v2"})
        ... def calculate_cost(tokens: int):
        ...     return tokens * 0.002
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not tracer:
                return await func(*args, **kwargs)

            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    # Record exception in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not tracer:
                return func(*args, **kwargs)

            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, str(value))

                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    # Record exception in span
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    """
    Context manager for creating custom trace spans.

    Provides fine-grained control over span creation and attributes.

    Args:
        name: Span name
        attributes: Span attributes (key-value pairs)
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)

    Yields:
        Span instance for adding events and attributes

    Example:
        >>> from src.monitoring.tracing import trace_span
        >>> 
        >>> with trace_span("model.inference", {"model": "gpt-4"}) as span:
        ...     result = await model.generate(prompt)
        ...     span.set_attribute("tokens.total", result.tokens)
        ...     span.add_event("inference_complete")
    """
    if not tracer:
        yield None
        return

    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, str(value))

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("error", True)
            span.set_attribute("error.type", type(e).__name__)
            raise


def trace_model_call(
    provider: str,
    model: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost: Optional[float] = None,
):
    """
    Create a span for model provider API calls.

    Specialized tracing for LLM inference with relevant attributes.

    Args:
        provider: Provider name (e.g., "openai", "anthropic", "gemini")
        model: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens  
        cost: Cost in USD

    Returns:
        Context manager for the span

    Example:
        >>> with trace_model_call("openai", "gpt-4", 100, 50, 0.003) as span:
        ...     response = await openai_client.chat.completions.create(...)
        ...     span.add_event("response_received")
    """
    attributes = {
        "llm.provider": provider,
        "llm.model": model,
    }

    if input_tokens is not None:
        attributes["llm.input_tokens"] = input_tokens
    if output_tokens is not None:
        attributes["llm.output_tokens"] = output_tokens
    if cost is not None:
        attributes["llm.cost_usd"] = cost

    return trace_span(f"llm.{provider}.{model}", attributes, trace.SpanKind.CLIENT)


def trace_conversation(
    conversation_id: str,
    user_id: Optional[str] = None,
    message_count: Optional[int] = None,
):
    """
    Create a span for conversation processing.

    Args:
        conversation_id: Unique conversation identifier
        user_id: User identifier (optional)
        message_count: Number of messages in conversation

    Returns:
        Context manager for the span

    Example:
        >>> with trace_conversation("conv_123", "user_456", 10) as span:
        ...     messages = await get_conversation_history(conversation_id)
        ...     span.set_attribute("messages.loaded", len(messages))
    """
    attributes = {
        "conversation.id": conversation_id,
    }

    if user_id:
        attributes["user.id"] = user_id
    if message_count is not None:
        attributes["conversation.message_count"] = message_count

    return trace_span("conversation.process", attributes)


def trace_tool_execution(
    tool_name: str,
    tool_input: Optional[Dict[str, Any]] = None,
):
    """
    Create a span for tool execution.

    Args:
        tool_name: Name of the tool being executed
        tool_input: Tool input parameters (optional, for debugging)

    Returns:
        Context manager for the span

    Example:
        >>> with trace_tool_execution("web_search", {"query": "python"}) as span:
        ...     results = await search_engine.search(query)
        ...     span.set_attribute("results.count", len(results))
    """
    attributes = {
        "tool.name": tool_name,
    }

    if tool_input:
        # Limit size to avoid huge spans
        input_str = str(tool_input)[:500]
        attributes["tool.input"] = input_str

    return trace_span(f"tool.{tool_name}", attributes)


def add_trace_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.

    Useful for marking significant points in execution without creating
    a new span.

    Args:
        name: Event name
        attributes: Event attributes (optional)

    Example:
        >>> add_trace_event("cache_hit", {"cache.key": "user_123"})
        >>> add_trace_event("model_fallback", {"from": "gpt-4", "to": "gpt-3.5"})
    """
    if not tracer:
        return

    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.add_event(name, attributes or {})


def get_trace_id() -> Optional[str]:
    """
    Get the current trace ID for correlation with logs.

    Returns:
        Trace ID as hex string, or None if no active trace

    Example:
        >>> trace_id = get_trace_id()
        >>> logger.info(f"Processing request", extra={"trace_id": trace_id})
    """
    if not tracer:
        return None

    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()
        if span_context:
            return format(span_context.trace_id, "032x")
    return None


# Example usage and testing
if __name__ == "__main__":
    # Example setup and usage
    import asyncio

    async def example_usage():
        # Initialize tracing
        setup_tracing(service_name="zakera-test", environment="development")

        # Example 1: Using decorator
        @trace_function("example.operation")
        async def example_operation(value: int):
            await asyncio.sleep(0.1)
            return value * 2

        result = await example_operation(42)
        print(f"Result: {result}")

        # Example 2: Using context manager
        with trace_span("custom.operation", {"user": "test"}) as span:
            span.add_event("processing_started")
            await asyncio.sleep(0.1)
            span.set_attribute("result", "success")
            span.add_event("processing_complete")

        # Example 3: Model call tracing
        with trace_model_call("openai", "gpt-4", 100, 50, 0.003) as span:
            # Simulate API call
            await asyncio.sleep(0.2)
            span.add_event("response_received")

        print(f"Trace ID: {get_trace_id()}")
        print("View traces at: http://localhost:16686")

    asyncio.run(example_usage())
