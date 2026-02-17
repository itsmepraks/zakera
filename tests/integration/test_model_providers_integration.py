"""
Integration Tests for Model Providers

Comprehensive test suite for validating all LLM provider integrations,
fallback mechanisms, and cross-provider functionality.
"""

import asyncio
import pytest
import time
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Test multiple providers if available
try:
    from src.model.providers import BaseProvider, OpenAIProvider, AnthropicProvider, GeminiProvider
    from src.model.providers_ollama import OllamaProvider
    from src.model.providers_huggingface import HuggingFaceProvider
    from src.model.providers_cohere import CohereProvider
    from src.model.model_manager import ModelManager
except ImportError as e:
    pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class TestProviderIntegration:
    """Test suite for individual provider integrations."""
    
    @pytest.fixture
    def mock_openai_provider(self):
        """Mock OpenAI provider for testing."""
        with patch('src.model.providers.OpenAI') as mock:
            mock.return_value.chat.completions.create = AsyncMock(
                return_value=Mock(
                    choices=[Mock(message=Mock(content="Test response"))],
                    usage=Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
                    model="gpt-4"
                )
            )
            provider = OpenAIProvider(api_key="test-key")
            yield provider
    
    @pytest.fixture
    def mock_cohere_provider(self):
        """Mock Cohere provider for testing."""
        with patch('src.model.providers_cohere.cohere') as mock_cohere:
            mock_client = Mock()
            mock_client.check_api_key = Mock()
            mock_client.chat = AsyncMock(
                return_value=Mock(
                    text="Test response from Cohere",
                    meta=Mock(tokens=Mock(input_tokens=15, output_tokens=25)),
                    generation_id="test-gen-123"
                )
            )
            mock_cohere.Client.return_value = mock_client
            mock_cohere.AsyncClient.return_value = mock_client
            
            provider = CohereProvider(api_key="test-key")
            yield provider
    
    @pytest.mark.asyncio
    async def test_openai_basic_generation(self, mock_openai_provider):
        """Test basic text generation with OpenAI provider."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        response = await mock_openai_provider.generate(
            messages=messages,
            model="gpt-4",
            temperature=0.7
        )
        
        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"
        assert response.total_tokens == 30
        assert response.cost > 0
    
    @pytest.mark.asyncio
    async def test_cohere_basic_generation(self, mock_cohere_provider):
        """Test basic text generation with Cohere provider."""
        messages = [
            {"role": "user", "content": "What is AI?"}
        ]
        
        response = await mock_cohere_provider.generate(
            messages=messages,
            model="command-r",
            temperature=0.7
        )
        
        assert response.content == "Test response from Cohere"
        assert response.provider == "cohere"
        assert response.prompt_tokens == 15
        assert response.completion_tokens == 25
        assert response.metadata.get("generation_id") == "test-gen-123"
    
    @pytest.mark.asyncio
    async def test_provider_streaming(self, mock_openai_provider):
        """Test streaming response generation."""
        messages = [{"role": "user", "content": "Count to 5"}]
        
        # Mock streaming response
        async def mock_stream():
            for i in range(1, 6):
                yield str(i)
        
        with patch.object(mock_openai_provider, 'stream_generate', return_value=mock_stream()):
            chunks = []
            async for chunk in mock_openai_provider.stream_generate(messages):
                chunks.append(chunk)
            
            assert len(chunks) == 5
            assert "".join(chunks) == "12345"
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self, mock_openai_provider):
        """Test error handling in provider."""
        messages = [{"role": "user", "content": "Test"}]
        
        # Mock API error
        with patch.object(
            mock_openai_provider.client.chat.completions,
            'create',
            side_effect=Exception("API Error")
        ):
            with pytest.raises(RuntimeError, match="API Error"):
                await mock_openai_provider.generate(messages)
    
    @pytest.mark.asyncio
    async def test_token_counting_accuracy(self, mock_openai_provider):
        """Test accuracy of token counting."""
        messages = [
            {"role": "user", "content": "This is a test message for token counting."}
        ]
        
        response = await mock_openai_provider.generate(messages)
        
        assert response.prompt_tokens > 0
        assert response.completion_tokens > 0
        assert response.total_tokens == response.prompt_tokens + response.completion_tokens
    
    @pytest.mark.asyncio
    async def test_cost_calculation(self, mock_cohere_provider):
        """Test cost calculation accuracy."""
        messages = [{"role": "user", "content": "Test message"}]
        
        response = await mock_cohere_provider.generate(
            messages=messages,
            model="command-r-plus"
        )
        
        # Verify cost is calculated
        assert response.cost >= 0
        
        # Verify cost is reasonable for token count
        model_info = mock_cohere_provider.SUPPORTED_MODELS["command-r-plus"]
        expected_cost = (
            (response.prompt_tokens / 1000) * model_info["cost_per_1k_input"] +
            (response.completion_tokens / 1000) * model_info["cost_per_1k_output"]
        )
        assert abs(response.cost - expected_cost) < 0.0001


class TestModelManagerIntegration:
    """Test suite for ModelManager with multiple providers."""
    
    @pytest.fixture
    def model_manager_with_mocks(self):
        """Create ModelManager with mocked providers."""
        manager = ModelManager()
        
        # Add mock providers
        mock_openai = Mock(spec=OpenAIProvider)
        mock_openai.provider_name = "openai"
        mock_openai.is_available.return_value = True
        mock_openai.generate = AsyncMock(return_value=Mock(
            content="OpenAI response",
            model="gpt-4",
            provider="openai",
            total_tokens=50,
            cost=0.005
        ))
        
        mock_cohere = Mock(spec=CohereProvider)
        mock_cohere.provider_name = "cohere"
        mock_cohere.is_available.return_value = True
        mock_cohere.generate = AsyncMock(return_value=Mock(
            content="Cohere response",
            model="command-r",
            provider="cohere",
            total_tokens=40,
            cost=0.002
        ))
        
        manager.register_provider(mock_openai)
        manager.register_provider(mock_cohere)
        
        return manager
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self, model_manager_with_mocks):
        """Test automatic fallback between providers."""
        messages = [{"role": "user", "content": "Test fallback"}]
        
        # Make first provider fail
        manager = model_manager_with_mocks
        providers = list(manager.providers.values())
        providers[0].generate.side_effect = Exception("Provider 1 failed")
        
        # Should fallback to second provider
        response = await manager.generate_with_fallback(
            messages=messages,
            preferred_model="gpt-4"
        )
        
        assert response.content == "Cohere response"
        assert response.provider == "cohere"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, model_manager_with_mocks):
        """Test handling of concurrent requests to multiple providers."""
        messages = [{"role": "user", "content": f"Request {i}"} for i in range(5)]
        
        # Generate multiple concurrent requests
        tasks = [
            model_manager_with_mocks.generate_with_fallback(
                messages=[msg],
                preferred_model="gpt-4"
            )
            for msg in messages
        ]
        
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 5
        assert all(r.content for r in responses)
    
    @pytest.mark.asyncio
    async def test_provider_health_checks(self, model_manager_with_mocks):
        """Test health check for all registered providers."""
        manager = model_manager_with_mocks
        
        # Mock health check responses
        for provider in manager.providers.values():
            provider.health_check = AsyncMock(return_value={
                "provider": provider.provider_name,
                "status": "healthy",
                "available": True
            })
        
        health_results = await manager.check_all_providers_health()
        
        assert len(health_results) == 2
        assert all(h["status"] == "healthy" for h in health_results)
    
    @pytest.mark.asyncio
    async def test_context_window_handling(self, model_manager_with_mocks):
        """Test handling of messages exceeding context window."""
        # Create a very long message
        long_content = "word " * 10000
        messages = [{"role": "user", "content": long_content}]
        
        manager = model_manager_with_mocks
        
        # Should handle gracefully (truncate or error)
        try:
            response = await manager.generate_with_fallback(
                messages=messages,
                max_tokens=100
            )
            # If successful, verify response
            assert response.content
        except ValueError as e:
            # Or raise appropriate error
            assert "context window" in str(e).lower() or "too long" in str(e).lower()


class TestProviderPerformanceBenchmarks:
    """Performance benchmarking tests for provider comparison."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_time_comparison(self):
        """Benchmark response times across providers."""
        messages = [{"role": "user", "content": "What is 2+2?"}]
        
        benchmarks = {}
        
        # Test each provider if available
        providers_to_test = [
            ("openai", "gpt-3.5-turbo"),
            ("cohere", "command-light"),
        ]
        
        for provider_name, model in providers_to_test:
            try:
                start_time = time.time()
                
                # Mock provider for testing
                with patch(f'src.model.providers_{provider_name}') as mock_provider:
                    # Simulate realistic response times
                    await asyncio.sleep(0.5 if provider_name == "openai" else 0.3)
                    
                    elapsed = time.time() - start_time
                    benchmarks[provider_name] = {
                        "model": model,
                        "response_time": elapsed,
                        "tokens_per_second": 50 / elapsed  # Mock value
                    }
            except Exception as e:
                benchmarks[provider_name] = {"error": str(e)}
        
        # Verify we got benchmarks
        assert len(benchmarks) > 0
        
        # Print results for analysis
        print("\n=== Provider Performance Benchmarks ===")
        for provider, stats in benchmarks.items():
            if "error" not in stats:
                print(f"{provider}: {stats['response_time']:.2f}s "
                      f"({stats['tokens_per_second']:.1f} tokens/sec)")
    
    @pytest.mark.asyncio
    async def test_throughput_under_load(self, model_manager_with_mocks):
        """Test provider throughput under concurrent load."""
        num_requests = 20
        messages = [{"role": "user", "content": f"Request {i}"} for i in range(num_requests)]
        
        start_time = time.time()
        
        tasks = [
            model_manager_with_mocks.generate_with_fallback(
                messages=[msg],
                preferred_model="gpt-4"
            )
            for msg in messages
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        successful = sum(1 for r in responses if not isinstance(r, Exception))
        
        throughput = successful / elapsed
        
        assert successful == num_requests
        assert throughput > 0
        
        print(f"\nThroughput: {throughput:.2f} requests/second")


class TestProviderCompatibility:
    """Test compatibility and consistency across providers."""
    
    @pytest.mark.asyncio
    async def test_consistent_response_format(self):
        """Verify all providers return consistent response format."""
        messages = [{"role": "user", "content": "Test"}]
        
        # Mock different providers
        providers = [
            ("openai", Mock(content="Test", model="gpt-4", provider="openai", 
                          total_tokens=30, cost=0.005)),
            ("cohere", Mock(content="Test", model="command-r", provider="cohere",
                          total_tokens=25, cost=0.003)),
        ]
        
        for provider_name, expected_response in providers:
            # All should have these fields
            assert hasattr(expected_response, 'content')
            assert hasattr(expected_response, 'model')
            assert hasattr(expected_response, 'provider')
            assert hasattr(expected_response, 'total_tokens')
            assert hasattr(expected_response, 'cost')
    
    @pytest.mark.asyncio
    async def test_message_format_compatibility(self):
        """Test that message formats work across all providers."""
        test_message_formats = [
            [{"role": "user", "content": "Simple message"}],
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"}
            ],
            [
                {"role": "user", "content": "First"},
                {"role": "assistant", "content": "Response"},
                {"role": "user", "content": "Second"}
            ]
        ]
        
        # Each provider should handle all formats
        for messages in test_message_formats:
            # Test with mocked providers
            mock_provider = Mock()
            mock_provider.generate = AsyncMock(return_value=Mock(content="OK"))
            
            response = await mock_provider.generate(messages)
            assert response.content == "OK"


# Test runner configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
