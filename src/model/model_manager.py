"""Model manager with fallback strategies and provider management"""

from typing import List, Dict, Optional, AsyncIterator, Callable
import asyncio
import time
from dataclasses import dataclass
from enum import Enum
import logging

from .providers import ModelProvider, Message, ModelResponse
from .providers_ollama import OllamaProvider
from .providers_huggingface import HuggingFaceProvider
from .config import ModelConfig, ModelProviderType, ModelInfo, ProviderConfig

logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Strategies for handling provider failures"""
    NONE = "none"  # No fallback, fail immediately
    SEQUENTIAL = "sequential"  # Try fallback models one by one
    FASTEST = "fastest"  # Try multiple in parallel, return first success
    CHEAPEST = "cheapest"  # Fallback to cheaper models


@dataclass
class ProviderHealth:
    """Health status of a provider"""
    provider_type: ModelProviderType
    is_available: bool
    last_check: float
    consecutive_failures: int = 0
    avg_latency: float = 0.0


class ModelManager:
    """
    Central manager for all model providers with intelligent fallback,
    health checking, and request routing.
    """
    
    def __init__(
        self,
        default_model: str = "gpt-3.5-turbo",
        fallback_strategy: FallbackStrategy = FallbackStrategy.SEQUENTIAL,
        enable_health_checks: bool = True
    ):
        self.default_model = default_model
        self.fallback_strategy = fallback_strategy
        self.enable_health_checks = enable_health_checks
        
        # Provider registry
        self.providers: Dict[ModelProviderType, ModelProvider] = {}
        self.provider_configs: Dict[ModelProviderType, ProviderConfig] = {}
        self.provider_health: Dict[ModelProviderType, ProviderHealth] = {}
        
        # Statistics
        self.request_count: Dict[str, int] = {}
        self.failure_count: Dict[str, int] = {}
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers"""
        # Load provider configurations
        for provider_type, config in ModelConfig.PROVIDER_DEFAULTS.items():
            if config.enabled:
                self.provider_configs[provider_type] = config
                self.provider_health[provider_type] = ProviderHealth(
                    provider_type=provider_type,
                    is_available=True,
                    last_check=time.time()
                )
        
        logger.info(f"Initialized {len(self.provider_configs)} model providers")
    
    def _get_provider(self, model_identifier: str) -> Optional[ModelProvider]:
        """Get or create provider for a model"""
        model_info = ModelConfig.get_model_info(model_identifier)
        if not model_info:
            raise ValueError(f"Unknown model: {model_identifier}")
        
        provider_type = model_info.provider
        
        # Check if provider is already instantiated
        if provider_type in self.providers:
            provider = self.providers[provider_type]
            # Update model name if different
            provider.model_name = model_info.name
            return provider
        
        # Create new provider instance
        config = self.provider_configs.get(provider_type)
        if not config:
            raise ValueError(f"Provider {provider_type.value} is not configured")
        
        try:
            if provider_type == ModelProviderType.OPENAI:
                from .providers import OpenAIProvider
                provider = OpenAIProvider(
                    api_key=config.api_key,
                    model_name=model_info.name
                )
            elif provider_type == ModelProviderType.ANTHROPIC:
                from .providers import AnthropicProvider
                provider = AnthropicProvider(
                    api_key=config.api_key,
                    model_name=model_info.name
                )
            elif provider_type == ModelProviderType.GEMINI:
                from .providers import GeminiProvider
                provider = GeminiProvider(
                    api_key=config.api_key,
                    model_name=model_info.name
                )
            elif provider_type == ModelProviderType.OLLAMA:
                provider = OllamaProvider(
                    base_url=config.base_url or "http://localhost:11434",
                    model_name=model_info.name
                )
            elif provider_type == ModelProviderType.HUGGINGFACE:
                provider = HuggingFaceProvider(
                    model_name=model_info.name
                )
            else:
                raise ValueError(f"Unsupported provider: {provider_type.value}")
            
            self.providers[provider_type] = provider
            return provider
        
        except Exception as e:
            logger.error(f"Failed to initialize {provider_type.value} provider: {e}")
            return None
    
    async def _check_provider_health(self, provider_type: ModelProviderType) -> bool:
        """Check if a provider is healthy and available"""
        if not self.enable_health_checks:
            return True
        
        health = self.provider_health.get(provider_type)
        if not health:
            return False
        
        # Don't check too frequently
        if time.time() - health.last_check < 30:  # 30 seconds
            return health.is_available
        
        # Perform health check
        try:
            provider = self.providers.get(provider_type)
            if not provider:
                return False
            
            # Provider-specific health checks
            if provider_type == ModelProviderType.OLLAMA:
                is_available = await provider.check_availability()
            else:
                # For API providers, assume available unless too many failures
                is_available = health.consecutive_failures < 3
            
            health.is_available = is_available
            health.last_check = time.time()
            
            if is_available:
                health.consecutive_failures = 0
            
            return is_available
        
        except Exception as e:
            logger.warning(f"Health check failed for {provider_type.value}: {e}")
            health.is_available = False
            health.consecutive_failures += 1
            return False
    
    async def generate(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response with automatic fallback
        
        Args:
            messages: Conversation messages
            model: Model identifier (uses default if None)
            fallback: Enable fallback to alternative models
            **kwargs: Generation parameters
        
        Returns:
            ModelResponse from successful provider
        """
        model = model or self.default_model
        
        # Get fallback chain
        models_to_try = [model]
        if fallback and self.fallback_strategy != FallbackStrategy.NONE:
            fallback_models = ModelConfig.get_fallback_chain(model)
            models_to_try = fallback_models
        
        last_error = None
        
        for model_to_try in models_to_try:
            try:
                # Track request
                self.request_count[model_to_try] = self.request_count.get(model_to_try, 0) + 1
                
                # Get provider
                provider = self._get_provider(model_to_try)
                if not provider:
                    continue
                
                # Check health
                model_info = ModelConfig.get_model_info(model_to_try)
                if not await self._check_provider_health(model_info.provider):
                    logger.warning(f"Provider {model_info.provider.value} is unhealthy, skipping")
                    continue
                
                logger.info(f"Attempting generation with {model_to_try}")
                
                # Generate with timeout
                config = self.provider_configs[model_info.provider]
                response = await asyncio.wait_for(
                    provider.generate(messages, **kwargs),
                    timeout=config.timeout
                )
                
                logger.info(f"Successfully generated with {model_to_try}")
                return response
            
            except asyncio.TimeoutError:
                last_error = f"Timeout with {model_to_try}"
                logger.warning(last_error)
                self.failure_count[model_to_try] = self.failure_count.get(model_to_try, 0) + 1
            
            except Exception as e:
                last_error = f"Error with {model_to_try}: {str(e)}"
                logger.error(last_error)
                self.failure_count[model_to_try] = self.failure_count.get(model_to_try, 0) + 1
                
                # Update provider health
                model_info = ModelConfig.get_model_info(model_to_try)
                if model_info:
                    health = self.provider_health.get(model_info.provider)
                    if health:
                        health.consecutive_failures += 1
        
        # All providers failed
        raise Exception(f"All model providers failed. Last error: {last_error}")
    
    async def stream_generate(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream generation with automatic fallback
        
        Args:
            messages: Conversation messages
            model: Model identifier
            fallback: Enable fallback
            **kwargs: Generation parameters
        
        Yields:
            Text chunks from successful provider
        """
        model = model or self.default_model
        
        # Get fallback chain
        models_to_try = [model]
        if fallback and self.fallback_strategy != FallbackStrategy.NONE:
            fallback_models = ModelConfig.get_fallback_chain(model)
            models_to_try = fallback_models
        
        for model_to_try in models_to_try:
            try:
                # Get provider
                provider = self._get_provider(model_to_try)
                if not provider:
                    continue
                
                # Check health
                model_info = ModelConfig.get_model_info(model_to_try)
                if not await self._check_provider_health(model_info.provider):
                    continue
                
                logger.info(f"Attempting streaming with {model_to_try}")
                
                # Stream generate
                async for chunk in provider.stream_generate(messages, **kwargs):
                    yield chunk
                
                # If we get here, streaming succeeded
                logger.info(f"Successfully streamed with {model_to_try}")
                return
            
            except Exception as e:
                logger.error(f"Streaming error with {model_to_try}: {e}")
                continue
        
        raise Exception("All model providers failed for streaming")
    
    def get_statistics(self) -> Dict:
        """Get usage statistics"""
        return {
            "request_count": self.request_count,
            "failure_count": self.failure_count,
            "provider_health": {
                k.value: {
                    "is_available": v.is_available,
                    "consecutive_failures": v.consecutive_failures,
                    "avg_latency": v.avg_latency
                }
                for k, v in self.provider_health.items()
            }
        }
    
    async def list_available_models(self) -> List[Dict]:
        """List all available models across all providers"""
        available_models = []
        
        all_models = ModelConfig.get_all_models()
        for model_id, model_info in all_models.items():
            # Check if provider is healthy
            is_available = await self._check_provider_health(model_info.provider)
            
            available_models.append({
                "id": model_id,
                "name": model_info.name,
                "provider": model_info.provider.value,
                "tier": model_info.tier.value,
                "context_window": model_info.context_window,
                "supports_streaming": model_info.supports_streaming,
                "is_available": is_available,
                "description": model_info.description,
                "tags": model_info.tags
            })
        
        return available_models
