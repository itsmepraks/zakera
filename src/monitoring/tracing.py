"""
Distributed Tracing with OpenTelemetry

This module provides comprehensive distributed tracing capabilities for the Zakera
AI chat agent using OpenTelemetry. It includes automatic instrumentation for FastAPI,
database operations, HTTP clients, and custom tracing for model providers and
conversation flows.

Features:
- Automatic FastAPI request tracing
- Model provider call tracing with detailed metrics
- Conversation and message flow tracing
- Tool execution tracing
- Database query tracing
- HTTP client tracing
- Error and exception tracking
- Performance metrics collection
- Context propagation across async boundaries
- Configurable sampling strategies
- Multiple export formats (Jaeger, OTLP)

Usage:
    # Initialize tracing (call once at application startup)
    setup_tracing(service_name="zakera-api")
    
    # Tracing is then automatic for instrumented libraries
    # For custom tracing, use decorators:
    
    @trace_async_function
    async def my_function():
        pass
    
    # Or use context managers:
    async with TraceContext("operation_name") as span:
        span.set_attribute("custom.attribute", "value")
        await do_work()

Author: Prakriti Bista
Version: 1.0.0
"""

import logging
import os
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as OTLPGrpcExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHttpExporter,
)
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatio,
    ALWAYS_ON,
    ALWAYS_OFF,
)
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_initialized = False


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        # Create a no-op tracer if tracing is not initialized
        _tracer = trace.get_tracer(__name__)
    return _tracer


def setup_tracing(
    service_name: str = "zakera-api",
    service_version: str = "0.6.0",
    environment: str = "development",
    enable_tracing: bool = None,
    sampling_rate: float = None,
    jaeger_endpoint: str = None,
    otlp_endpoint: str = None,
    export_to_console: bool = False,
) -> None:
    """
    Setup OpenTelemetry distributed tracing.
    
    This function initializes the tracer provider, configures exporters,
    and sets up automatic instrumentation for supported libraries.
    
    Args:
        service_name: Name of the service (default: zakera-api)
        service_version: Version of the service
        environment: Deployment environment (development, staging, production)
        enable_tracing: Enable/disable tracing (default: from env ENABLE_TRACING)
        sampling_rate: Trace sampling rate 0.0-1.0 (default: from env or 0.1)
        jaeger_endpoint: Jaeger collector endpoint (default: from env)
        otlp_endpoint: OTLP collector endpoint (default: from env)
        export_to_console: Export traces to console for debugging
    
    Environment Variables:
        ENABLE_TRACING: Enable distributed tracing (default: false)
        TRACE_SAMPLING_RATE: Sampling rate 0.0-1.0 (default: 0.1)
        JAEGER_AGENT_HOST: Jaeger agent hostname (default: localhost)
        JAEGER_AGENT_PORT: Jaeger agent port (default: 6831)
        JAEGER_ENDPOINT: Jaeger HTTP collector endpoint
        OTLP_ENDPOINT: OTLP gRPC endpoint (default: http://localhost:4317)
        OTLP_HTTP_ENDPOINT: OTLP HTTP endpoint (default: http://localhost:4318)
        TRACE_EXPORTER: Exporter type (jaeger, otlp, console, or multiple)
        OTEL_SERVICE_NAME: Alternative way to set service name
    """
    global _tracer, _initialized
    
    if _initialized:
        logger.warning("Tracing already initialized, skipping setup")
        return
    
    # Check if tracing is enabled
    if enable_tracing is None:
        enable_tracing = os.getenv("ENABLE_TRACING", "false").lower() == "true"
    
    if not enable_tracing:
        logger.info("Distributed tracing is disabled")
        return
    
    try:
        # Get configuration from environment
        if sampling_rate is None:
            sampling_rate = float(os.getenv("TRACE_SAMPLING_RATE", "0.1"))
        
        # Ensure sampling rate is valid
        sampling_rate = max(0.0, min(1.0, sampling_rate))
        
        # Create resource with service information
        resource = Resource.create(
            {
                SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", service_name),
                "service.version": service_version,
                "deployment.environment": environment,
                "service.namespace": "zakera",
            }
        )
        
        # Configure sampling strategy
        if sampling_rate >= 1.0:
            sampler = ALWAYS_ON
        elif sampling_rate <= 0.0:
            sampler = ALWAYS_OFF
        else:
            # Parent-based sampling with ratio
            sampler = ParentBasedTraceIdRatio(sampling_rate)
        
        # Create tracer provider
        provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )
        
        # Configure exporters
        exporters = []
        exporter_type = os.getenv("TRACE_EXPORTER", "jaeger").lower()
        
        # Jaeger exporter
        if "jaeger" in exporter_type or jaeger_endpoint:
            try:
                if jaeger_endpoint:
                    # HTTP collector endpoint
                    jaeger_exp = JaegerExporter(
                        collector_endpoint=jaeger_endpoint,
                    )
                else:
                    # UDP agent endpoint
                    agent_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
                    agent_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
                    jaeger_exp = JaegerExporter(
                        agent_host_name=agent_host,
                        agent_port=agent_port,
                    )
                exporters.append(("jaeger", jaeger_exp))
                logger.info("Jaeger exporter configured")
            except Exception as e:
                logger.error(f"Failed to configure Jaeger exporter: {e}")
        
        # OTLP gRPC exporter
        if "otlp" in exporter_type or otlp_endpoint:
            try:
                endpoint = otlp_endpoint or os.getenv(
                    "OTLP_ENDPOINT", "http://localhost:4317"
                )
                otlp_grpc_exp = OTLPGrpcExporter(endpoint=endpoint)
                exporters.append(("otlp-grpc", otlp_grpc_exp))
                logger.info(f"OTLP gRPC exporter configured: {endpoint}")
            except Exception as e:
                logger.error(f"Failed to configure OTLP gRPC exporter: {e}")
        
        # OTLP HTTP exporter
        if "otlp-http" in exporter_type:
            try:
                http_endpoint = os.getenv(
                    "OTLP_HTTP_ENDPOINT", "http://localhost:4318/v1/traces"
                )
                otlp_http_exp = OTLPHttpExporter(endpoint=http_endpoint)
                exporters.append(("otlp-http", otlp_http_exp))
                logger.info(f"OTLP HTTP exporter configured: {http_endpoint}")
            except Exception as e:
                logger.error(f"Failed to configure OTLP HTTP exporter: {e}")
        
        # Console exporter for debugging
        if export_to_console or "console" in exporter_type:
            console_exp = ConsoleSpanExporter()
            exporters.append(("console", console_exp))
            logger.info("Console exporter configured")
        
        # Add exporters to provider
        if not exporters:
            logger.warning("No trace exporters configured, using console exporter")
            exporters.append(("console", ConsoleSpanExporter()))
        
        for name, exporter in exporters:
            # Use BatchSpanProcessor for better performance
            processor = BatchSpanProcessor(
                exporter,
                max_queue_size=2048,
                max_export_batch_size=512,
                schedule_delay_millis=5000,
            )
            provider.add_span_processor(processor)
            logger.info(f"Added {name} span processor")
        
        # Set the tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer
        _tracer = trace.get_tracer(__name__, service_version)
        
        # Setup automatic instrumentation
        _setup_auto_instrumentation()
        
        _initialized = True
        logger.info(
            f"Distributed tracing initialized: service={service_name}, "
            f"sampling={sampling_rate}, exporters={[n for n, _ in exporters]}"
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize distributed tracing: {e}", exc_info=True)
        # Don't fail application startup if tracing fails
        _tracer = trace.get_tracer(__name__)  # No-op tracer


def _setup_auto_instrumentation() -> None:
    """Setup automatic instrumentation for supported libraries."""
    try:
        # Instrument HTTP clients
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX client instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTPX: {e}")
    
    try:
        AioHttpClientInstrumentor().instrument()
        logger.info("AioHTTP client instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument AioHTTP: {e}")
    
    try:
        RequestsInstrumentor().instrument()
        logger.info("Requests library instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Requests: {e}")
    
    try:
        # SQLAlchemy instrumentation will be done when engine is created
        # SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumentation available")
    except Exception as e:
        logger.warning(f"Failed to setup SQLAlchemy instrumentation: {e}")


def instrument_sqlalchemy_engine(engine: Any) -> None:
    """Instrument SQLAlchemy engine for query tracing.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,
        )
        logger.info("SQLAlchemy engine instrumented for tracing")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy engine: {e}")


@contextmanager
def TraceContext(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    """
    Context manager for creating custom trace spans.
    
    Args:
        operation_name: Name of the operation being traced
        attributes: Dictionary of attributes to add to the span
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)
    
    Usage:
        with TraceContext("process_data", {"data.size": 100}) as span:
            result = process_data()
            span.set_attribute("result.count", len(result))
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(operation_name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


@asynccontextmanager
async def AsyncTraceContext(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    """
    Async context manager for creating custom trace spans.
    
    Args:
        operation_name: Name of the operation being traced
        attributes: Dictionary of attributes to add to the span
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)
    
    Usage:
        async with AsyncTraceContext("async_process") as span:
            result = await async_process()
            span.set_attribute("result", result)
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(operation_name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_function(operation_name: Optional[str] = None):
    """
    Decorator for tracing synchronous functions.
    
    Args:
        operation_name: Custom name for the operation (default: function name)
    
    Usage:
        @trace_function("my_operation")
        def my_function(arg1, arg2):
            return arg1 + arg2
    """
    def decorator(func: Callable) -> Callable:
        span_name = operation_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TraceContext(span_name) as span:
                # Add function details
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_async_function(operation_name: Optional[str] = None):
    """
    Decorator for tracing asynchronous functions.
    
    Args:
        operation_name: Custom name for the operation (default: function name)
    
    Usage:
        @trace_async_function("async_operation")
        async def my_async_function(arg1, arg2):
            result = await async_work()
            return result
    """
    def decorator(func: Callable) -> Callable:
        span_name = operation_name or func.__name__
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with AsyncTraceContext(span_name) as span:
                # Add function details
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def get_current_span() -> Optional[trace.Span]:
    """
    Get the current active span.
    
    Returns:
        Current span or None if no span is active
    """
    return trace.get_current_span()


def set_span_attribute(key: str, value: Any) -> None:
    """
    Add an attribute to the current span.
    
    Args:
        key: Attribute key
        value: Attribute value
    """
    span = get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def record_exception(exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record an exception in the current span.
    
    Args:
        exception: Exception to record
        attributes: Additional attributes to add
    """
    span = get_current_span()
    if span and span.is_recording():
        span.record_exception(exception, attributes=attributes)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.
    
    Args:
        name: Event name
        attributes: Event attributes
    """
    span = get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})
