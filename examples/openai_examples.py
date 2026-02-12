#!/usr/bin/env python3
"""
OpenAI Integration Examples for Zakera

This file demonstrates various use cases of the OpenAI provider.
"""

import asyncio
import json
import os
from typing import List

from src.model.providers import OpenAIProvider, OpenAIError, Message


async def example_basic_chat():
    """Basic chat completion example"""
    print("\n=== Basic Chat Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is the capital of France?")
    ]
    
    try:
        response = await provider.generate(messages)
        print(f"Response: {response.content}")
        print(f"Tokens used: {response.usage['total_tokens']}")
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def example_streaming():
    """Streaming response example"""
    print("\n=== Streaming Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    messages = [
        Message(role="user", content="Write a short poem about coding.")
    ]
    
    print("Response: ", end="", flush=True)
    try:
        async for chunk in provider.stream_generate(messages):
            print(chunk, end="", flush=True)
        print()  # New line after streaming
    except OpenAIError as e:
        print(f"\nError: {e.message}")


async def example_function_calling():
    """Function calling example"""
    print("\n=== Function Calling Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    # Define a function
    functions = [
        {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location"]
            }
        }
    ]
    
    messages = [
        Message(role="user", content="What's the weather like in Boston?")
    ]
    
    try:
        response = await provider.generate(messages, functions=functions)
        
        if "get_weather" in response.content:
            function_call = json.loads(response.content)
            print(f"Function to call: {function_call}")
            print("\nIn a real application, you would:")
            print("1. Parse the function call")
            print("2. Execute the function with the arguments")
            print("3. Send the result back to the model")
        else:
            print(f"Response: {response.content}")
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def example_json_mode():
    """JSON mode example"""
    print("\n=== JSON Mode Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo-1106")  # Requires newer model
    
    messages = [
        Message(
            role="system",
            content="You are a helpful assistant that outputs JSON."
        ),
        Message(
            role="user",
            content="Extract the name, age, and occupation from: 'Alice Johnson is a 32-year-old software engineer.'"
        )
    ]
    
    try:
        response = await provider.generate(
            messages,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.content)
        print("Extracted data:")
        print(json.dumps(data, indent=2))
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def example_multi_turn_conversation():
    """Multi-turn conversation example"""
    print("\n=== Multi-Turn Conversation Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    # Initialize conversation
    conversation = [
        Message(role="system", content="You are a helpful math tutor.")
    ]
    
    # Simulate multi-turn conversation
    user_inputs = [
        "What is 15 * 23?",
        "Can you show me how to calculate that?",
        "Thanks! What about 15 * 24?"
    ]
    
    try:
        for user_input in user_inputs:
            # Add user message
            conversation.append(Message(role="user", content=user_input))
            print(f"\nUser: {user_input}")
            
            # Get response
            response = await provider.generate(conversation)
            print(f"Assistant: {response.content}")
            
            # Add assistant response to conversation
            conversation.append(
                Message(role="assistant", content=response.content)
            )
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def example_with_parameters():
    """Example with various generation parameters"""
    print("\n=== Parameters Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    messages = [
        Message(role="user", content="Write a creative story about a robot.")
    ]
    
    print("High creativity (temperature=1.5):")
    try:
        response = await provider.generate(
            messages,
            temperature=1.5,
            max_tokens=100
        )
        print(response.content[:200] + "...\n")
    except OpenAIError as e:
        print(f"Error: {e.message}")
    
    print("Low creativity (temperature=0.3):")
    try:
        response = await provider.generate(
            messages,
            temperature=0.3,
            max_tokens=100
        )
        print(response.content[:200] + "...")
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def example_error_handling():
    """Error handling example"""
    print("\n=== Error Handling Example ===")
    
    # Test with invalid API key
    try:
        provider = OpenAIProvider(api_key="invalid-key")
        messages = [Message(role="user", content="Hello")]
        await provider.generate(messages)
    except OpenAIError as e:
        print(f"Caught OpenAI error: {e.message}")
        if e.status_code:
            print(f"Status code: {e.status_code}")


async def example_token_counting():
    """Token usage tracking example"""
    print("\n=== Token Counting Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    # Test different message lengths
    test_cases = [
        "Hi",
        "What is the capital of France?",
        "Can you explain quantum computing in detail with examples?"
    ]
    
    try:
        for i, content in enumerate(test_cases, 1):
            messages = [Message(role="user", content=content)]
            response = await provider.generate(messages, max_tokens=50)
            
            print(f"\nTest {i}: '{content}'")
            print(f"  Prompt tokens: {response.usage['prompt_tokens']}")
            print(f"  Completion tokens: {response.usage['completion_tokens']}")
            print(f"  Total tokens: {response.usage['total_tokens']}")
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def example_rate_limiting():
    """Rate limiting example"""
    print("\n=== Rate Limiting Example ===")
    
    provider = OpenAIProvider(model_name="gpt-3.5-turbo")
    
    # Send multiple requests with delay
    messages = [Message(role="user", content="Say hello")]
    
    print("Sending 3 requests with 1 second delay...")
    try:
        for i in range(3):
            response = await provider.generate(messages)
            print(f"Request {i+1}: {response.content[:50]}...")
            await asyncio.sleep(1)  # Simple rate limiting
    except OpenAIError as e:
        print(f"Error: {e.message}")


async def main():
    """Run all examples"""
    print("OpenAI Integration Examples for Zakera")
    print("=" * 50)
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    # Run examples
    examples = [
        example_basic_chat,
        example_streaming,
        example_function_calling,
        example_json_mode,
        example_multi_turn_conversation,
        example_with_parameters,
        example_token_counting,
        example_rate_limiting,
        example_error_handling,
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Example failed: {str(e)}")
        
        # Small delay between examples
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
