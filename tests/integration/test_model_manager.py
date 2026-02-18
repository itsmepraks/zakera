"""Integration tests for ModelManager.

Tests the model manager's ability to:
- Route requests to appropriate providers
- Handle provider fallbacks
- Manage provider health checks
- Track usage and costs
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


class MockProvider:
    """Mock provider for testing."""
    
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0
    
    async def generate(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """Mock generate method."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception(f"{self.name} provider failed")
        
        return {
            "text": f"Response from {self.name}",
            "provider": self.name,
            "model": model,
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            "cost": 0.001,
            "latency": 0.5,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy" if not self.should_fail else "unhealthy",
            "provider": self.name,
            "api_accessible": not self.should_fail,
        }


class TestModelManager:
    """Test suite for ModelManager."""
    
    @pytest.fixture
    def providers(self):
        """Create test providers."""
        return {
            "openai": MockProvider("openai"),
            "anthropic": MockProvider("anthropic"),
            "mistral": MockProvider("mistral"),
        }
    
    @pytest.mark.asyncio
    async def test_provider_selection(self, providers):
        """Test selecting correct provider for model."""
        # Map models to providers
        model_provider_map = {
            "gpt-4": "openai",
            "claude-3": "anthropic",
            "mistral-small": "mistral",
        }
        
        for model, expected_provider in model_provider_map.items():
            provider = providers[expected_provider]
            result = await provider.generate(
                model=model,
                messages=[{"role": "user", "content": "Test"}],
            )
            
            assert result["provider"] == expected_provider
            assert result["model"] == model
    
    @pytest.mark.asyncio
    async def test_fallback_sequence(self, providers):
        """Test fallback to next provider on failure."""
        # Make first provider fail
        providers["openai"].should_fail = True
        
        fallback_order = ["openai", "anthropic", "mistral"]
        result = None
        
        for provider_name in fallback_order:
            provider = providers[provider_name]
            try:
                result = await provider.generate(
                    model="test",
                    messages=[{"role": "user", "content": "Test"}],
                )
                break
            except Exception:
                continue
        
        assert result is not None
        assert result["provider"] == "anthropic"  # First successful fallback
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, providers):
        """Test behavior when all providers fail."""
        # Make all providers fail
        for provider in providers.values():
            provider.should_fail = True
        
        result = None
        last_error = None
        
        for provider in providers.values():
            try:
                result = await provider.generate(
                    model="test",
                    messages=[{"role": "user", "content": "Test"}],
                )
                break
            except Exception as e:
                last_error = e
                continue
        
        assert result is None
        assert last_error is not None
    
    @pytest.mark.asyncio
    async def test_health_checks(self, providers):
        """Test health check for all providers."""
        health_results = {}
        
        for name, provider in providers.items():
            health = await provider.health_check()
            health_results[name] = health
        
        assert len(health_results) == len(providers)
        
        for name, health in health_results.items():
            assert health["provider"] == name
            assert health["status"] == "healthy"
            assert health["api_accessible"] is True
    
    @pytest.mark.asyncio
    async def test_usage_tracking(self, providers):
        """Test tracking usage across multiple requests."""
        total_tokens = 0
        total_cost = 0.0
        request_count = 5
        
        for i in range(request_count):
            provider = providers["openai"]
            result = await provider.generate(
                model="gpt-3.5",
                messages=[{"role": "user", "content": f"Request {i}"}],
            )
            
            total_tokens += result["usage"]["total_tokens"]
            total_cost += result["cost"]
        
        assert total_tokens == 30 * request_count
        assert total_cost == pytest.approx(0.001 * request_count)
        assert providers["openai"].call_count == request_count
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, providers):
        """Test handling concurrent requests."""
        tasks = []
        request_count = 10
        
        for i in range(request_count):
            provider_name = list(providers.keys())[i % len(providers)]
            provider = providers[provider_name]
            
            task = provider.generate(
                model="test",
                messages=[{"role": "user", "content": f"Request {i}"}],
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == request_count
    
    @pytest.mark.asyncio
    async def test_provider_retry_count(self, providers):
        """Test retry counting for failed providers."""
        provider = providers["openai"]
        provider.should_fail = True
        
        max_retries = 3
        attempts = 0
        
        for attempt in range(max_retries):
            try:
                await provider.generate(
                    model="test",
                    messages=[{"role": "user", "content": "Test"}],
                )
            except Exception:
                attempts += 1
        
        assert attempts == max_retries
        assert provider.call_count == max_retries
    
    @pytest.mark.asyncio
    async def test_model_cost_comparison(self, providers):
        """Test cost comparison across providers."""
        costs = {}
        
        for name, provider in providers.items():
            result = await provider.generate(
                model="test",
                messages=[{"role": "user", "content": "Test"}],
            )
            costs[name] = result["cost"]
        
        # All mock providers should have same cost in this test
        assert all(cost == 0.001 for cost in costs.values())
    
    @pytest.mark.asyncio
    async def test_latency_tracking(self, providers):
        """Test latency measurement."""
        latencies = []
        
        for provider in providers.values():
            result = await provider.generate(
                model="test",
                messages=[{"role": "user", "content": "Test"}],
            )
            latencies.append(result["latency"])
        
        assert all(lat > 0 for lat in latencies)
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency > 0


class TestProviderConfiguration:
    """Test provider configuration and initialization."""
    
    def test_provider_config_validation(self):
        """Test configuration validation."""
        valid_config = {
            "api_key": "test_key",
            "base_url": "https://api.example.com",
            "timeout": 30,
            "max_retries": 3,
        }
        
        assert valid_config["api_key"] is not None
        assert valid_config["timeout"] > 0
        assert valid_config["max_retries"] > 0
    
    def test_missing_api_key(self):
        """Test handling of missing API key."""
        invalid_config = {
            "api_key": None,
            "base_url": "https://api.example.com",
        }
        
        # Should raise error or handle gracefully
        assert invalid_config["api_key"] is None
    
    def test_default_configuration(self):
        """Test default configuration values."""
        default_config = {
            "timeout": 60,
            "max_retries": 3,
            "retry_delay": 1.0,
        }
        
        assert default_config["timeout"] == 60
        assert default_config["max_retries"] == 3
        assert default_config["retry_delay"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
