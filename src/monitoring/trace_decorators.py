"""
Custom Tracing Decorators for Model Providers and Business Logic

This module provides specialized tracing decorators for tracking model provider
calls, conversation flows, tool executions, and other business-critical operations.

Author: Prakriti Bista
Version: 1.0.0
"""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .tracing import get_tracer, AsyncTraceContext


def trace_model_call(
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    """
    Decorator for tracing AI model provider calls.
    
    Automatically captures:
    - Provider name (OpenAI, Anthropic, Gemini, etc.)
    - Model name (gpt-4, claude-3, gemini-1.5-pro, etc.)
    - Token usage (input, output, total)
    - Response time
    - Cost information
    - Streaming status
    - Error information
    
    Args:
        provider: Model provider name (auto-detected if not provided)
        model: Model name (auto-detected if not provided)
    
    Usage:
        @trace_model_call(provider="openai", model="gpt-4")
        async def call_openai(prompt: str):
            response = await openai.ChatCompletion.create(...)
            return response
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation_name = f"model.{provider or 'unknown'}.{func.__name__}"
            
            async with AsyncTraceContext(
                operation_name,
                kind=trace.SpanKind.CLIENT,
            ) as span:
                # Set provider and model attributes
                if provider:
                    span.set_attribute("ai.model.provider", provider)
                if model:
                    span.set_attribute("ai.model.name", model)
                
                # Extract parameters from kwargs
                if "temperature" in kwargs:
                    span.set_attribute("ai.model.temperature", kwargs["temperature"])
                if "max_tokens" in kwargs:
                    span.set_attribute("ai.model.max_tokens", kwargs["max_tokens"])
                if "stream" in kwargs:
                    span.set_attribute("ai.model.streaming", kwargs["stream"])
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record timing
                    duration = time.time() - start_time
                    span.set_attribute("ai.response.duration_ms", duration * 1000)
                    
                    # Extract token usage from result if available
                    if hasattr(result, "usage"):
                        usage = result.usage
                        if hasattr(usage, "prompt_tokens"):
                            span.set_attribute("ai.usage.input_tokens", usage.prompt_tokens)
                        if hasattr(usage, "completion_tokens"):
                            span.set_attribute("ai.usage.output_tokens", usage.completion_tokens)
                        if hasattr(usage, "total_tokens"):
                            span.set_attribute("ai.usage.total_tokens", usage.total_tokens)
                    
                    # Extract cost information if available
                    if hasattr(result, "cost"):
                        span.set_attribute("ai.cost.total", result.cost)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    span.set_attribute("ai.response.duration_ms", duration * 1000)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_conversation(
    conversation_id: Optional[str] = None,
):
    """
    Decorator for tracing conversation-related operations.
    
    Captures:
    - Conversation ID
    - User ID
    - Message count
    - Processing time
    - Cache hits/misses
    
    Args:
        conversation_id: Conversation identifier (auto-detected if not provided)
    
    Usage:
        @trace_conversation()
        async def process_conversation(conv_id: str, message: str):
            # Process conversation
            return response
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation_name = f"conversation.{func.__name__}"
            
            async with AsyncTraceContext(
                operation_name,
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                # Extract conversation details from kwargs
                conv_id = conversation_id or kwargs.get("conversation_id") or kwargs.get("conv_id")
                if conv_id:
                    span.set_attribute("conversation.id", conv_id)
                
                if "user_id" in kwargs:
                    span.set_attribute("user.id", kwargs["user_id"])
                
                if "message" in kwargs:
                    message = kwargs["message"]
                    if isinstance(message, str):
                        span.set_attribute("message.length", len(message))
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    span.set_attribute("processing.duration_ms", duration * 1000)
                    
                    # Extract result metadata
                    if isinstance(result, dict):
                        if "message_count" in result:
                            span.set_attribute("conversation.message_count", result["message_count"])
                        if "cache_hit" in result:
                            span.set_attribute("cache.hit", result["cache_hit"])
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    span.set_attribute("processing.duration_ms", duration * 1000)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_tool_execution(
    tool_name: Optional[str] = None,
):
    """
    Decorator for tracing tool execution.
    
    Captures:
    - Tool name
    - Input parameters
    - Execution time
    - Success/failure status
    - Cache hits
    
    Args:
        tool_name: Name of the tool being executed
    
    Usage:
        @trace_tool_execution(tool_name="web_search")
        async def execute_web_search(query: str):
            results = await search(query)
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = tool_name or func.__name__
            operation_name = f"tool.{name}"
            
            async with AsyncTraceContext(
                operation_name,
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                span.set_attribute("tool.name", name)
                
                # Record input parameters (excluding sensitive data)
                safe_params = {}
                for key, value in kwargs.items():
                    if key not in ["api_key", "password", "token", "secret"]:
                        if isinstance(value, (str, int, float, bool)):
                            safe_params[key] = value
                
                for key, value in safe_params.items():
                    span.set_attribute(f"tool.param.{key}", str(value)[:100])  # Limit length
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    span.set_attribute("tool.execution.duration_ms", duration * 1000)
                    span.set_attribute("tool.execution.status", "success")
                    
                    # Record result metadata
                    if isinstance(result, dict):
                        if "cache_hit" in result:
                            span.set_attribute("cache.hit", result["cache_hit"])
                        if "result_count" in result:
                            span.set_attribute("tool.result.count", result["result_count"])
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    span.set_attribute("tool.execution.duration_ms", duration * 1000)
                    span.set_attribute("tool.execution.status", "failure")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_database_operation(
    operation_type: str = "query",
):
    """
    Decorator for tracing database operations.
    
    Captures:
    - Operation type (SELECT, INSERT, UPDATE, DELETE)
    - Execution time
    - Row count
    - Error information
    
    Args:
        operation_type: Type of database operation
    
    Usage:
        @trace_database_operation(operation_type="insert")
        async def create_user(user_data: dict):
            result = await db.execute(insert_query)
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation_name = f"db.{operation_type}.{func.__name__}"
            
            async with AsyncTraceContext(
                operation_name,
                kind=trace.SpanKind.CLIENT,
            ) as span:
                span.set_attribute("db.operation", operation_type)
                span.set_attribute("db.system", "postgresql")  # or detect dynamically
                
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    span.set_attribute("db.execution.duration_ms", duration * 1000)
                    
                    # Record row count if available
                    if hasattr(result, "rowcount"):
                        span.set_attribute("db.rows_affected", result.rowcount)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    span.set_attribute("db.execution.duration_ms", duration * 1000)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator
