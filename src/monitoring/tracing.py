"""Distributed tracing with OpenTelemetry.

This module provides comprehensive distributed tracing capabilities for the
Zakera AI chat agent using OpenTelemetry. It includes automatic instrumentation
for FastAPI, SQLAlchemy, and HTTP clients, as well as custom tracing for
model provider calls, conversation flows, and tool executions.

Usage:
    # Initialize tracing (usually in main.py)
    from monitoring.tracing import setup_tracing
    setup_tracing()

    # Use decorator for automatic tracing
    from monitoring.tracing import trace

    @trace("conversation.process")
    async def process_conversation(message: str) -> str:
        # Function logic here
        pass

    # Manual span creation
    from monitoring.tracing import tracer

    with tracer.start_as_current_span("custom.operation") as span:
        span.set_attribute("custom.attribute", "value")
        # Operation logic here
"""

import functools
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
)
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

# Type variable for generic decorators
F = TypeVar("F", bound=Callable[..., Any])

# Global tracer instance
tracer: trace.Tracer = trace.get_tracer(__name__)

# Configuration
SERVICE_NAME_VALUE = os.getenv("SERVICE_NAME", "zakera-ai-chat")
SERVICE_VERSION_VALUE = os.getenv("SERVICE_VERSION", "0.6.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
TRACING_ENABLED = os.getenv("TRACING_ENABLED", "true").lower() == "true"
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
TRACE_SAMPLE_RATE = float(os.getenv("TRACE_SAMPLE_RATE", "1.0"))  # 1.0 = 100%
EXPORTER_TYPE = os.getenv("TRACE_EXPORTER", "jaeger")  # jaeger, otlp, console


def setup_tracing(
    app: Optional[Any] = None,
    service_name: str = SERVICE_NAME_VALUE,
    service_version: str = SERVICE_VERSION_VALUE,
    environment: str = ENVIRONMENT,
) -> TracerProvider:
    """Set up OpenTelemetry tracing with automatic instrumentation.

    This function initializes the OpenTelemetry SDK with the specified
    configuration and sets up automatic instrumentation for FastAPI,
    SQLAlchemy, and HTTP clients.

    Args:
        app: FastAPI application instance for automatic instrumentation
        service_name: Name of the service for trace identification
        service_version: Version of the service
        environment: Deployment environment (dev, staging, prod)

    Returns:
        TracerProvider instance for additional configuration if needed

    Example:
        from fastapi import FastAPI
        from monitoring.tracing import setup_tracing

        app = FastAPI()
        setup_tracing(app)
    """
    if not TRACING_ENABLED:
        logger.info("Tracing is disabled via TRACING_ENABLED=false")
        return None

    logger.info(
        f"Setting up OpenTelemetry tracing for {service_name} v{service_version} "
        f"in {environment} environment"
    )

    # Create resource with service information
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": environment,
            "telemetry.sdk.language": "python",
            "telemetry.sdk.name": "opentelemetry",
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporter based on type
    exporter = _create_exporter(EXPORTER_TYPE)
    if exporter:
        # Use BatchSpanProcessor for better performance
        processor = BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,  # 5 seconds
        )
        provider.add_span_processor(processor)
        logger.info(f"Added {EXPORTER_TYPE} exporter to tracing pipeline")

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Set up propagators for context propagation
    from opentelemetry.propagate import set_global_textmap
    set_global_textmap(TraceContextTextMapPropagator())

    # Automatic instrumentation
    _setup_auto_instrumentation(app)

    # Update global tracer
    global tracer
    tracer = trace.get_tracer(__name__)

    logger.info("OpenTelemetry tracing setup complete")
    return provider


def _create_exporter(exporter_type: str) -> Optional[SpanExporter]:
    """Create span exporter based on configuration.

    Args:
        exporter_type: Type of exporter (jaeger, otlp, console)

    Returns:
        SpanExporter instance or None if invalid type
    """
    try:
        if exporter_type == "jaeger":
            return JaegerExporter(
                agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
                agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
            )
        elif exporter_type == "otlp":
            return OTLPSpanExporter(endpoint=OTLP_ENDPOINT)
        elif exporter_type == "console":
            return ConsoleSpanExporter()
        else:
            logger.warning(f"Unknown exporter type: {exporter_type}")
            return None
    except Exception as e:
        logger.error(f"Failed to create {exporter_type} exporter: {e}")
        return None


def _setup_auto_instrumentation(app: Optional[Any] = None) -> None:
    """Set up automatic instrumentation for common libraries.

    Args:
        app: FastAPI application instance
    """
    try:
        # FastAPI instrumentation
        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI automatic instrumentation enabled")

        # HTTP client instrumentation
        HTTPXClientInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        AioHttpClientInstrumentor().instrument()
        logger.info("HTTP client instrumentation enabled")

        # SQLAlchemy instrumentation will be done when engine is created
        logger.info("Automatic instrumentation setup complete")

    except Exception as e:
        logger.error(f"Error setting up automatic instrumentation: {e}")


def trace(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
) -> Callable[[F], F]:
    """Decorator to automatically trace a function.

    Args:
        name: Span name (defaults to function name)
        attributes: Additional attributes to add to the span
        record_exception: Whether to record exceptions in the span

    Returns:
        Decorated function with tracing

    Example:
        @trace("conversation.create", attributes={"user_type": "premium"})
        async def create_conversation(user_id: str) -> Conversation:
            # Function logic
            pass
    """
    def decorator(func: F) -> F:
        span_name = name or f"{func.__module__}.{func.__qualname__}"

        if not TRACING_ENABLED:
            return func

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Add function arguments as attributes
                    _add_function_attributes(span, func, args, kwargs)

                    # Execute function
                    result = await func(*args, **kwargs)

                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Add function arguments as attributes
                    _add_function_attributes(span, func, args, kwargs)

                    # Execute function
                    result = func(*args, **kwargs)

                    # Mark span as successful
                    span.set_status(Status(StatusCode.OK))
                    return result

                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                    raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _add_function_attributes(
    span: Span,
    func: Callable,
    args: tuple,
    kwargs: dict,
) -> None:
    """Add function signature attributes to span.

    Args:
        span: Current span
        func: Function being traced
        args: Positional arguments
        kwargs: Keyword arguments
    """
    try:
        import inspect
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()

        # Add safe attributes (avoid sensitive data)
        safe_params = ["user_id", "conversation_id", "model", "provider", "tool_name"]
        for param_name, param_value in bound_args.arguments.items():
            if param_name in safe_params and param_value is not None:
                span.set_attribute(f"function.{param_name}", str(param_value))

    except Exception as e:
        logger.debug(f"Failed to add function attributes: {e}")


@contextmanager
def trace_context(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
):
    """Context manager for manual span creation.

    Args:
        name: Span name
        attributes: Span attributes
        record_exception: Whether to record exceptions

    Yields:
        Current span for attribute updates

    Example:
        with trace_context("model.inference", {"model": "gpt-4"}) as span:
            response = await model.generate(prompt)
            span.set_attribute("tokens", response.tokens)
    """
    if not TRACING_ENABLED:
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        try:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            yield span

            span.set_status(Status(StatusCode.OK))

        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def trace_model_call(
    provider: str,
    model: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost: Optional[float] = None,
    **kwargs,
) -> Span:
    """Create a span for model provider calls with standard attributes.

    Args:
        provider: Model provider name (openai, anthropic, etc.)
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost: Cost of the API call
        **kwargs: Additional attributes

    Returns:
        Span object for further customization

    Example:
        span = trace_model_call("openai", "gpt-4", input_tokens=100)
        span.set_attribute("streaming", True)
    """
    span = tracer.start_span(f"model.{provider}.{model}")
    span.set_attribute("model.provider", provider)
    span.set_attribute("model.name", model)

    if input_tokens is not None:
        span.set_attribute("model.input_tokens", input_tokens)
    if output_tokens is not None:
        span.set_attribute("model.output_tokens", output_tokens)
    if cost is not None:
        span.set_attribute("model.cost", cost)

    for key, value in kwargs.items():
        span.set_attribute(f"model.{key}", value)

    return span


def trace_conversation(
    conversation_id: str,
    user_id: str,
    message_count: Optional[int] = None,
    **kwargs,
) -> Span:
    """Create a span for conversation processing.

    Args:
        conversation_id: Unique conversation identifier
        user_id: User identifier
        message_count: Number of messages in conversation
        **kwargs: Additional attributes

    Returns:
        Span object for further customization
    """
    span = tracer.start_span("conversation.process")
    span.set_attribute("conversation.id", conversation_id)
    span.set_attribute("conversation.user_id", user_id)

    if message_count is not None:
        span.set_attribute("conversation.message_count", message_count)

    for key, value in kwargs.items():
        span.set_attribute(f"conversation.{key}", value)

    return span


def trace_tool_execution(
    tool_name: str,
    success: bool,
    execution_time: Optional[float] = None,
    **kwargs,
) -> Span:
    """Create a span for tool execution.

    Args:
        tool_name: Name of the tool being executed
        success: Whether the tool execution was successful
        execution_time: Execution time in seconds
        **kwargs: Additional attributes

    Returns:
        Span object for further customization
    """
    span = tracer.start_span(f"tool.{tool_name}")
    span.set_attribute("tool.name", tool_name)
    span.set_attribute("tool.success", success)

    if execution_time is not None:
        span.set_attribute("tool.execution_time", execution_time)

    for key, value in kwargs.items():
        span.set_attribute(f"tool.{key}", value)

    return span


def get_current_span() -> Optional[Span]:
    """Get the current active span.

    Returns:
        Current span or None if no active span
    """
    if not TRACING_ENABLED:
        return None
    return trace.get_current_span()


def add_span_attribute(key: str, value: Any) -> None:
    """Add an attribute to the current span.

    Args:
        key: Attribute key
        value: Attribute value
    """
    if not TRACING_ENABLED:
        return

    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current span.

    Args:
        name: Event name
        attributes: Event attributes
    """
    if not TRACING_ENABLED:
        return

    span = get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def instrument_sqlalchemy_engine(engine: Any) -> None:
    """Instrument SQLAlchemy engine for automatic tracing.

    Args:
        engine: SQLAlchemy engine instance

    Example:
        from sqlalchemy import create_engine
        from monitoring.tracing import instrument_sqlalchemy_engine

        engine = create_engine(database_url)
        instrument_sqlalchemy_engine(engine)
    """
    if not TRACING_ENABLED:
        return

    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy engine instrumented for tracing")
    except Exception as e:
        logger.error(f"Failed to instrument SQLAlchemy engine: {e}")
