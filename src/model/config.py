"""Model configuration and provider settings.

This module defines all model configurations, provider settings, and tier classifications
for the multi-provider LLM system in Zakera.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator
import os
import logging

logger = logging.getLogger(__name__)


class ModelProviderType(Enum):
    """Supported model provider types.
    
    Attributes:
        OPENAI: OpenAI API (GPT models)
        ANTHROPIC: Anthropic API (Claude models)
        GEMINI: Google Gemini API
        OLLAMA: Local Ollama models
        HUGGINGFACE: HuggingFace Transformers
        LOCAL: Generic local model provider
    """
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class ModelTier(Enum):
    """Model capability and cost tiers.
    
    Attributes:
        FLAGSHIP: Most capable models, highest cost (e.g., GPT-4, Claude Opus)
        ADVANCED: High capability, moderate cost (e.g., Claude Sonnet)
        STANDARD: Good capability, low cost (e.g., GPT-3.5)
        FAST: Fast response, lowest cost
        LOCAL: Local models, no API cost
    """
    FLAGSHIP = "flagship"  # Most capable, highest cost
    ADVANCED = "advanced"  # High capability, moderate cost
    STANDARD = "standard"  # Good capability, low cost
    FAST = "fast"  # Fast response, lowest cost
    LOCAL = "local"  # Local models, no API cost


class ModelInfo(BaseModel):
    """Detailed information about a specific model.
    
    Attributes:
        name: Model identifier used in API calls
        provider: Provider type (OpenAI, Anthropic, etc.)
        tier: Capability tier
        context_window: Maximum input tokens
        max_output_tokens: Maximum output tokens
        supports_streaming: Whether model supports streaming responses
        supports_functions: Whether model supports function calling
        cost_per_1k_input: Cost per 1000 input tokens (USD)
        cost_per_1k_output: Cost per 1000 output tokens (USD)
        description: Human-readable description
        tags: Categories and features
    """
    name: str
    provider: ModelProviderType
    tier: ModelTier
    context_window: int = Field(gt=0, description="Maximum input tokens")
    max_output_tokens: int = Field(gt=0, description="Maximum output tokens")
    supports_streaming: bool = True
    supports_functions: bool = False
    cost_per_1k_input: float = Field(ge=0.0, description="Cost per 1K input tokens (USD)")
    cost_per_1k_output: float = Field(ge=0.0, description="Cost per 1K output tokens (USD)")
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for a request.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost
    
    def is_local(self) -> bool:
        """Check if this is a local model (no API cost)."""
        return self.tier == ModelTier.LOCAL or self.provider in [
            ModelProviderType.OLLAMA,
            ModelProviderType.HUGGINGFACE,
            ModelProviderType.LOCAL
        ]


class ProviderConfig(BaseModel):
    """Configuration for a specific provider.
    
    Attributes:
        provider_type: Type of provider
        api_key: API key for authentication (optional for local providers)
        base_url: Base URL for API endpoint
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts on failure
        rate_limit_per_minute: API rate limit
        enabled: Whether provider is enabled
        priority: Provider priority (higher tried first)
    """
    provider_type: ModelProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=3, ge=0, le=10)
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=1)
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=100)
    
    @validator('api_key')
    def validate_api_key(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate API key format based on provider type."""
        if not v:
            return v
        
        provider_type = values.get('provider_type')
        
        # Provider-specific validation
        if provider_type == ModelProviderType.OPENAI and not v.startswith('sk-'):
            logger.warning(f"OpenAI API key should start with 'sk-', got: {v[:10]}...")
        elif provider_type == ModelProviderType.ANTHROPIC and not v.startswith('sk-ant-'):
            logger.warning(f"Anthropic API key should start with 'sk-ant-', got: {v[:10]}...")
        elif provider_type == ModelProviderType.GEMINI and not v.startswith('AIza'):
            logger.warning(f"Gemini API key should start with 'AIza', got: {v[:10]}...")
        
        return v
    
    def is_available(self) -> bool:
        """Check if provider is properly configured and available.
        
        Returns:
            True if provider has necessary configuration
        """
        if not self.enabled:
            return False
        
        # Local providers don't need API keys
        if self.provider_type in [ModelProviderType.OLLAMA, ModelProviderType.HUGGINGFACE, ModelProviderType.LOCAL]:
            return True
        
        # API providers need keys
        return bool(self.api_key)


class ModelConfig:
    """Comprehensive configuration for AI model providers and models.
    
    This class centralizes all model and provider configurations, making it easy
    to manage multiple providers and understand capabilities/costs of each model.
    """
    
    # OpenAI Models
    OPENAI_MODELS: Dict[str, ModelInfo] = {
        "gpt-4-turbo": ModelInfo(
            name="gpt-4-turbo-preview",
            provider=ModelProviderType.OPENAI,
            tier=ModelTier.FLAGSHIP,
            context_window=128000,
            max_output_tokens=4096,
            supports_functions=True,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.03,
            description="Most capable GPT-4 model with extended context",
            tags=["reasoning", "coding", "analysis", "long-context"]
        ),
        "gpt-4": ModelInfo(
            name="gpt-4",
            provider=ModelProviderType.OPENAI,
            tier=ModelTier.FLAGSHIP,
            context_window=8192,
            max_output_tokens=4096,
            supports_functions=True,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
            description="Original GPT-4 model",
            tags=["reasoning", "coding"]
        ),
        "gpt-3.5-turbo": ModelInfo(
            name="gpt-3.5-turbo",
            provider=ModelProviderType.OPENAI,
            tier=ModelTier.FAST,
            context_window=16385,
            max_output_tokens=4096,
            supports_functions=True,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
            description="Fast and cost-effective model",
            tags=["fast", "efficient", "cost-effective"]
        ),
    }
    
    # Anthropic Models
    ANTHROPIC_MODELS: Dict[str, ModelInfo] = {
        "claude-3-opus": ModelInfo(
            name="claude-3-opus-20240229",
            provider=ModelProviderType.ANTHROPIC,
            tier=ModelTier.FLAGSHIP,
            context_window=200000,
            max_output_tokens=4096,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            description="Most intelligent Claude model",
            tags=["reasoning", "analysis", "writing", "long-context"]
        ),
        "claude-3-sonnet": ModelInfo(
            name="claude-3-sonnet-20240229",
            provider=ModelProviderType.ANTHROPIC,
            tier=ModelTier.ADVANCED,
            context_window=200000,
            max_output_tokens=4096,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            description="Balanced performance and cost",
            tags=["balanced", "efficient"]
        ),
        "claude-3-haiku": ModelInfo(
            name="claude-3-haiku-20240307",
            provider=ModelProviderType.ANTHROPIC,
            tier=ModelTier.FAST,
            context_window=200000,
            max_output_tokens=4096,
            cost_per_1k_input=0.00025,
            cost_per_1k_output=0.00125,
            description="Fastest Claude model",
            tags=["fast", "efficient", "cost-effective"]
        ),
    }
    
    # Gemini Models
    GEMINI_MODELS: Dict[str, ModelInfo] = {
        "gemini-1.5-pro": ModelInfo(
            name="gemini-1.5-pro",
            provider=ModelProviderType.GEMINI,
            tier=ModelTier.FLAGSHIP,
            context_window=1000000,
            max_output_tokens=8192,
            supports_functions=True,
            cost_per_1k_input=0.0035,
            cost_per_1k_output=0.0105,
            description="Most capable Gemini with 1M token context",
            tags=["multimodal", "long-context", "advanced"]
        ),
        "gemini-pro": ModelInfo(
            name="gemini-pro",
            provider=ModelProviderType.GEMINI,
            tier=ModelTier.ADVANCED,
            context_window=32000,
            max_output_tokens=2048,
            supports_functions=True,
            cost_per_1k_input=0.00025,
            cost_per_1k_output=0.0005,
            description="Capable multimodal model",
            tags=["efficient", "multimodal"]
        ),
    }
    
    # Ollama Local Models
    OLLAMA_MODELS: Dict[str, ModelInfo] = {
        "llama3:8b": ModelInfo(
            name="llama3:8b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Llama 3 8B - Fast and capable local model",
            tags=["local", "open-source", "fast", "free"]
        ),
        "llama3:70b": ModelInfo(
            name="llama3:70b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Llama 3 70B - Most capable local model",
            tags=["local", "open-source", "powerful", "free"]
        ),
        "mistral:7b": ModelInfo(
            name="mistral:7b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Mistral 7B - Excellent performance for size",
            tags=["local", "open-source", "efficient", "free"]
        ),
        "codellama:13b": ModelInfo(
            name="codellama:13b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=16384,
            max_output_tokens=2048,
            description="CodeLlama 13B - Specialized for code generation",
            tags=["local", "coding", "open-source", "free"]
        ),
        "mixtral:8x7b": ModelInfo(
            name="mixtral:8x7b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=32768,
            max_output_tokens=4096,
            description="Mixtral 8x7B - Mixture of experts architecture",
            tags=["local", "open-source", "advanced", "free"]
        ),
    }
    
    # HuggingFace Models
    HUGGINGFACE_MODELS: Dict[str, ModelInfo] = {
        "mistralai/Mistral-7B-Instruct-v0.2": ModelInfo(
            name="mistralai/Mistral-7B-Instruct-v0.2",
            provider=ModelProviderType.HUGGINGFACE,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Mistral 7B Instruct from HuggingFace Hub",
            tags=["local", "instruction-following", "free"]
        ),
        "meta-llama/Llama-2-7b-chat-hf": ModelInfo(
            name="meta-llama/Llama-2-7b-chat-hf",
            provider=ModelProviderType.HUGGINGFACE,
            tier=ModelTier.LOCAL,
            context_window=4096,
            max_output_tokens=2048,
            description="Llama 2 7B Chat from HuggingFace Hub",
            tags=["local", "chat", "free"]
        ),
    }
    
    # Default generation parameters
    DEFAULT_PARAMS: Dict[str, Any] = {
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": True,
    }
    
    # Provider defaults
    PROVIDER_DEFAULTS: Dict[ModelProviderType, ProviderConfig] = {
        ModelProviderType.OPENAI: ProviderConfig(
            provider_type=ModelProviderType.OPENAI,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1",
            timeout=60,
            max_retries=3,
            rate_limit_per_minute=60,
            priority=10
        ),
        ModelProviderType.ANTHROPIC: ProviderConfig(
            provider_type=ModelProviderType.ANTHROPIC,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url="https://api.anthropic.com/v1",
            timeout=60,
            max_retries=3,
            rate_limit_per_minute=50,
            priority=9
        ),
        ModelProviderType.GEMINI: ProviderConfig(
            provider_type=ModelProviderType.GEMINI,
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout=60,
            max_retries=3,
            priority=8
        ),
        ModelProviderType.OLLAMA: ProviderConfig(
            provider_type=ModelProviderType.OLLAMA,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            timeout=120,
            max_retries=2,
            priority=7
        ),
        ModelProviderType.HUGGINGFACE: ProviderConfig(
            provider_type=ModelProviderType.HUGGINGFACE,
            timeout=180,
            max_retries=1,
            priority=6
        ),
    }
    
    @classmethod
    def get_all_models(cls) -> Dict[str, ModelInfo]:
        """Get all available models across all providers.
        
        Returns:
            Dictionary mapping model identifiers to ModelInfo objects
        """
        all_models: Dict[str, ModelInfo] = {}
        all_models.update(cls.OPENAI_MODELS)
        all_models.update(cls.ANTHROPIC_MODELS)
        all_models.update(cls.GEMINI_MODELS)
        all_models.update(cls.OLLAMA_MODELS)
        all_models.update(cls.HUGGINGFACE_MODELS)
        
        logger.debug(f"Loaded {len(all_models)} model configurations")
        return all_models
    
    @classmethod
    def get_model_info(cls, model_identifier: str) -> Optional[ModelInfo]:
        """Get model information by identifier or alias.
        
        Args:
            model_identifier: Model name or alias
            
        Returns:
            ModelInfo object if found, None otherwise
        """
        all_models = cls.get_all_models()
        model_info = all_models.get(model_identifier)
        
        if not model_info:
            logger.warning(f"Model not found: {model_identifier}")
        
        return model_info
    
    @classmethod
    def get_models_by_provider(cls, provider: ModelProviderType) -> Dict[str, ModelInfo]:
        """Get all models for a specific provider.
        
        Args:
            provider: Provider type to filter by
            
        Returns:
            Dictionary of models for the specified provider
        """
        all_models = cls.get_all_models()
        filtered = {k: v for k, v in all_models.items() if v.provider == provider}
        
        logger.debug(f"Found {len(filtered)} models for provider {provider.value}")
        return filtered
    
    @classmethod
    def get_models_by_tier(cls, tier: ModelTier) -> Dict[str, ModelInfo]:
        """Get all models in a specific tier.
        
        Args:
            tier: Model tier to filter by
            
        Returns:
            Dictionary of models in the specified tier
        """
        all_models = cls.get_all_models()
        filtered = {k: v for k, v in all_models.items() if v.tier == tier}
        
        logger.debug(f"Found {len(filtered)} models in tier {tier.value}")
        return filtered
    
    @classmethod
    def get_fallback_chain(cls, primary_model: str) -> List[str]:
        """Get recommended fallback models for a given primary model.
        
        Builds an intelligent fallback chain based on model tier, capabilities,
        and provider diversity to maximize reliability.
        
        Args:
            primary_model: Primary model identifier
            
        Returns:
            List of model identifiers in fallback order (includes primary)
        """
        model_info = cls.get_model_info(primary_model)
        if not model_info:
            logger.warning(f"Cannot build fallback chain for unknown model: {primary_model}")
            return []
        
        # Build fallback chain based on tier and capabilities
        fallback_chain = [primary_model]
        
        if model_info.tier == ModelTier.FLAGSHIP:
            # Fallback to advanced, then standard, then local
            advanced = [k for k, v in cls.get_models_by_tier(ModelTier.ADVANCED).items()]
            standard = [k for k, v in cls.get_models_by_tier(ModelTier.STANDARD).items()]
            local = [k for k, v in cls.get_models_by_tier(ModelTier.LOCAL).items()]
            
            fallback_chain.extend(advanced[:2])
            fallback_chain.extend(standard[:1])
            fallback_chain.extend(local[:1])  # Last resort: free local model
            
        elif model_info.tier == ModelTier.ADVANCED:
            # Fallback to other advanced, then standard
            other_advanced = [
                k for k, v in cls.get_models_by_tier(ModelTier.ADVANCED).items() 
                if k != primary_model
            ]
            standard = [k for k, v in cls.get_models_by_tier(ModelTier.STANDARD).items()]
            
            fallback_chain.extend(other_advanced[:1])
            fallback_chain.extend(standard[:1])
        
        logger.info(f"Built fallback chain for {primary_model}: {fallback_chain}")
        return fallback_chain
    
    @classmethod
    def get_available_providers(cls) -> List[ModelProviderType]:
        """Get list of currently available (configured) providers.
        
        Returns:
            List of available provider types
        """
        available = []
        for provider_type, config in cls.PROVIDER_DEFAULTS.items():
            if config.is_available():
                available.append(provider_type)
        
        logger.info(f"Available providers: {[p.value for p in available]}")
        return available
    
    @classmethod
    def validate_configuration(cls) -> Dict[str, Any]:
        """Validate current configuration and return status.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "available_providers": [],
            "total_models": 0
        }
        
        # Check providers
        available_providers = cls.get_available_providers()
        results["available_providers"] = [p.value for p in available_providers]
        
        if not available_providers:
            results["valid"] = False
            results["errors"].append("No model providers configured")
        
        # Check default model
        default_model = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        if not cls.get_model_info(default_model):
            results["warnings"].append(
                f"Default model '{default_model}' not found in configuration"
            )
        
        # Count available models
        all_models = cls.get_all_models()
        results["total_models"] = len(all_models)
        
        logger.info(f"Configuration validation: {results}")
        return results
