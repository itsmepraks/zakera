"""
Distributed Tracing Examples for Zakera AI Chat Agent

This file demonstrates various ways to use distributed tracing in your
Zakera application with OpenTelemetry.

Author: Prakriti Bista
Version: 1.0.0
"""

import asyncio
from typing import Dict, List

from monitoring.tracing import (
    AsyncTraceContext,
    TraceContext,
    trace_async_function,
    trace_function,
    set_span_attribute,
    add_span_event,
    record_exception,
)
from monitoring.trace_decorators import (
    trace_model_call,
    trace_conversation,
    trace_tool_execution,
    trace_database_operation,
)


# ============================================================================
# Example 1: Basic Function Tracing
# ============================================================================

@trace_async_function("process_user_message")
async def process_user_message(user_id: str, message: str) -> Dict:
    """
    Example of basic async function tracing.
    
    The @trace_async_function decorator automatically:
    - Creates a span named "process_user_message"
    - Records execution time
    - Captures exceptions
    - Sets function name and module as attributes
    """
    # Simulate message processing
    await asyncio.sleep(0.1)
    
    return {
        "user_id": user_id,
        "message": message,
        "processed": True,
    }


@trace_function("validate_input")
def validate_input(text: str) -> bool:
    """
    Example of sync function tracing.
    """
    return len(text) > 0 and len(text) < 10000


# ============================================================================
# Example 2: Model Provider Call Tracing
# ============================================================================

@trace_model_call(provider="openai", model="gpt-4")
async def call_gpt4(prompt: str, temperature: float = 0.7, max_tokens: int = 2048):
    """
    Example of tracing an AI model provider call.
    
    The @trace_model_call decorator captures:
    - Provider name (openai)
    - Model name (gpt-4)
    - Parameters (temperature, max_tokens)
    - Token usage (if available in response)
    - Cost information
    - Response time
    """
    # Simulate OpenAI API call
    await asyncio.sleep(0.5)
    
    # Mock response
    class MockResponse:
        class Usage:
            prompt_tokens = 100
            completion_tokens = 200
            total_tokens = 300
        
        usage = Usage()
        cost = 0.006  # $0.006 for this request
    
    return MockResponse()


@trace_model_call(provider="anthropic", model="claude-3-sonnet")
async def call_claude(prompt: str):
    """
    Example of tracing Anthropic Claude API call.
    """
    await asyncio.sleep(0.6)
    return {"content": "Response from Claude"}


@trace_model_call(provider="gemini", model="gemini-1.5-pro")
async def call_gemini(prompt: str, stream: bool = False):
    """
    Example of tracing Google Gemini API call with streaming.
    """
    await asyncio.sleep(0.3)
    return {"content": "Response from Gemini", "streaming": stream}


# ============================================================================
# Example 3: Conversation Flow Tracing
# ============================================================================

@trace_conversation()
async def handle_conversation(
    conversation_id: str,
    user_id: str,
    message: str,
) -> Dict:
    """
    Example of tracing a complete conversation flow.
    
    The @trace_conversation decorator automatically extracts:
    - conversation_id
    - user_id
    - message length
    - processing time
    """
    # Simulate conversation processing
    await asyncio.sleep(0.2)
    
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "response": "AI response",
        "message_count": 15,
        "cache_hit": True,
    }


# ============================================================================
# Example 4: Tool Execution Tracing
# ============================================================================

@trace_tool_execution(tool_name="web_search")
async def search_web(query: str, max_results: int = 10) -> Dict:
    """
    Example of tracing tool execution.
    
    Captures:
    - Tool name
    - Input parameters (excluding sensitive data)
    - Execution time
    - Success/failure status
    """
    await asyncio.sleep(0.4)
    
    return {
        "query": query,
        "results": ["result1", "result2", "result3"],
        "result_count": 3,
        "cache_hit": False,
    }


@trace_tool_execution(tool_name="calculator")
async def calculate(expression: str) -> float:
    """
    Example of tracing a calculator tool.
    """
    await asyncio.sleep(0.05)
    return eval(expression)  # Don't do this in production!


# ============================================================================
# Example 5: Database Operation Tracing
# ============================================================================

@trace_database_operation(operation_type="SELECT")
async def get_user(user_id: str) -> Dict:
    """
    Example of tracing database SELECT operation.
    """
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": "John Doe"}


@trace_database_operation(operation_type="INSERT")
async def create_message(conversation_id: str, content: str) -> Dict:
    """
    Example of tracing database INSERT operation.
    """
    await asyncio.sleep(0.05)
    return {"id": "msg_123", "conversation_id": conversation_id}


@trace_database_operation(operation_type="UPDATE")
async def update_conversation(conversation_id: str, metadata: Dict) -> Dict:
    """
    Example of tracing database UPDATE operation.
    """
    await asyncio.sleep(0.08)
    return {"id": conversation_id, "updated": True}


# ============================================================================
# Example 6: Context Manager Usage
# ============================================================================

async def complex_operation_with_context():
    """
    Example of using AsyncTraceContext for manual span creation.
    
    Use this when you need more control over the span lifecycle
    and want to add custom attributes and events.
    """
    async with AsyncTraceContext("complex_operation") as span:
        # Add custom attributes
        span.set_attribute("operation.type", "batch_processing")
        span.set_attribute("batch.size", 100)
        
        # Add event at start
        span.add_event("processing_started")
        
        # Simulate work
        await asyncio.sleep(0.3)
        
        # Add more attributes during processing
        span.set_attribute("items.processed", 100)
        span.set_attribute("items.failed", 2)
        
        # Add event at completion
        span.add_event("processing_completed", {
            "success_rate": 0.98,
            "duration_ms": 300,
        })
        
        return {"success": True, "processed": 100}


def sync_operation_with_context():
    """
    Example of using TraceContext for synchronous operations.
    """
    with TraceContext("sync_operation") as span:
        span.set_attribute("operation.mode", "synchronous")
        
        # Simulate work
        import time
        time.sleep(0.1)
        
        span.set_attribute("result", "completed")
        return True


# ============================================================================
# Example 7: Nested Spans (Parent-Child Relationship)
# ============================================================================

@trace_async_function("parent_operation")
async def parent_operation(data: List[str]):
    """
    Example of creating nested spans (parent-child relationship).
    
    The parent span automatically includes all child spans,
    showing the complete operation hierarchy.
    """
    results = []
    
    for item in data:
        # Each child operation creates a child span
        result = await child_operation(item)
        results.append(result)
    
    return results


@trace_async_function("child_operation")
async def child_operation(item: str):
    """
    Child operation that will appear as a child span.
    """
    await asyncio.sleep(0.05)
    return f"processed: {item}"


# ============================================================================
# Example 8: Adding Custom Attributes and Events
# ============================================================================

async def operation_with_custom_tracking():
    """
    Example of adding custom attributes and events to the current span.
    """
    async with AsyncTraceContext("custom_tracked_operation") as span:
        # Add business metrics
        set_span_attribute("user.subscription_tier", "premium")
        set_span_attribute("feature.enabled", True)
        
        # Add event for important milestones
        add_span_event("data_validation_started")
        
        await asyncio.sleep(0.1)
        
        add_span_event("data_validation_completed", {
            "validation_errors": 0,
            "validation_warnings": 2,
        })
        
        # Add performance metrics
        set_span_attribute("cache.hits", 15)
        set_span_attribute("cache.misses", 3)
        set_span_attribute("cache.hit_rate", 0.83)
        
        return {"success": True}


# ============================================================================
# Example 9: Error Handling and Exception Tracking
# ============================================================================

@trace_async_function("operation_with_error_handling")
async def operation_with_errors():
    """
    Example of proper error handling with distributed tracing.
    
    Exceptions are automatically recorded in the span, including:
    - Exception type
    - Exception message
    - Stack trace
    """
    try:
        # Simulate an operation that might fail
        if True:  # Simulate error condition
            raise ValueError("Simulated error for demonstration")
        
        await asyncio.sleep(0.1)
        return {"success": True}
        
    except ValueError as e:
        # Exception is automatically recorded by the decorator
        # You can also manually record additional context
        set_span_attribute("error.recovery_attempted", True)
        set_span_attribute("error.severity", "medium")
        
        # Re-raise to let the decorator mark the span as failed
        raise


async def manual_error_recording():
    """
    Example of manually recording exceptions.
    """
    async with AsyncTraceContext("operation") as span:
        try:
            # Risky operation
            result = await some_risky_operation()
            return result
        except Exception as e:
            # Manually record the exception
            record_exception(e, attributes={
                "error.handled": True,
                "error.action": "fallback_used",
            })
            
            # Return fallback value
            return {"fallback": True}


async def some_risky_operation():
    """Simulated risky operation."""
    raise RuntimeError("Something went wrong")


# ============================================================================
# Example 10: Complete End-to-End Request Tracing
# ============================================================================

@trace_async_function("handle_chat_request")
async def handle_complete_chat_request(
    user_id: str,
    conversation_id: str,
    message: str,
    model: str = "gpt-4",
):
    """
    Complete example showing how all the pieces fit together.
    
    This creates a trace with the following span hierarchy:
    
    handle_chat_request
    ├── validate_input
    ├── get_user
    ├── handle_conversation
    ├── call_gpt4 (or other model)
    ├── create_message
    └── update_conversation
    """
    # Add request metadata
    set_span_attribute("request.user_id", user_id)
    set_span_attribute("request.conversation_id", conversation_id)
    set_span_attribute("request.model", model)
    
    # Validate input (creates child span)
    if not validate_input(message):
        raise ValueError("Invalid message")
    
    # Get user information (creates child span)
    user = await get_user(user_id)
    set_span_attribute("user.subscription", user.get("subscription", "free"))
    
    # Process conversation (creates child span)
    conversation = await handle_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        message=message,
    )
    
    # Call AI model (creates child span)
    if model == "gpt-4":
        response = await call_gpt4(message)
    elif model == "claude-3-sonnet":
        response = await call_claude(message)
    elif model == "gemini-1.5-pro":
        response = await call_gemini(message)
    else:
        raise ValueError(f"Unsupported model: {model}")
    
    # Save message (creates child span)
    await create_message(conversation_id, message)
    
    # Update conversation metadata (creates child span)
    await update_conversation(conversation_id, {"last_activity": "now"})
    
    # Add final metrics
    set_span_attribute("response.length", len(str(response)))
    set_span_attribute("processing.complete", True)
    
    return {
        "conversation_id": conversation_id,
        "response": response,
        "user": user,
    }


# ============================================================================
# Main Example Runner
# ============================================================================

async def main():
    """
    Run all examples to generate sample traces.
    """
    print("Running distributed tracing examples...")
    print("View traces at http://localhost:16686\n")
    
    # Example 1: Basic tracing
    print("1. Basic function tracing...")
    await process_user_message("user_123", "Hello, AI!")
    
    # Example 2: Model provider calls
    print("2. Model provider tracing...")
    await call_gpt4("Explain quantum computing")
    await call_claude("What is machine learning?")
    await call_gemini("Tell me about AI", stream=True)
    
    # Example 3: Conversation flow
    print("3. Conversation flow tracing...")
    await handle_conversation(
        conversation_id="conv_456",
        user_id="user_123",
        message="How does this work?",
    )
    
    # Example 4: Tool executions
    print("4. Tool execution tracing...")
    await search_web("OpenTelemetry tutorial", max_results=5)
    await calculate("2 + 2")
    
    # Example 5: Database operations
    print("5. Database operation tracing...")
    await get_user("user_123")
    await create_message("conv_456", "Test message")
    await update_conversation("conv_456", {"status": "active"})
    
    # Example 6: Context managers
    print("6. Context manager usage...")
    await complex_operation_with_context()
    
    # Example 7: Nested spans
    print("7. Nested spans...")
    await parent_operation(["item1", "item2", "item3"])
    
    # Example 8: Custom tracking
    print("8. Custom attributes and events...")
    await operation_with_custom_tracking()
    
    # Example 9: Error handling
    print("9. Error handling...")
    try:
        await operation_with_errors()
    except ValueError:
        print("   (Error was expected and traced)")
    
    try:
        await manual_error_recording()
    except Exception:
        pass
    
    # Example 10: Complete end-to-end
    print("10. Complete end-to-end request...")
    await handle_complete_chat_request(
        user_id="user_123",
        conversation_id="conv_456",
        message="Explain distributed tracing",
        model="gpt-4",
    )
    
    print("\nAll examples completed!")
    print("Check Jaeger UI at http://localhost:16686 to view traces.")
    print("Look for service 'zakera-api' in the service dropdown.")


if __name__ == "__main__":
    # Note: In a real application, tracing would be initialized at app startup
    # This is just for demonstration purposes
    from monitoring.tracing import setup_tracing
    
    # Initialize tracing
    setup_tracing(
        service_name="zakera-examples",
        enable_tracing=True,
        sampling_rate=1.0,  # 100% for examples
        export_to_console=True,  # Also print to console
    )
    
    # Run examples
    asyncio.run(main())
