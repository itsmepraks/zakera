from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
import os


class ModelProviderType(Enum):
    """Supported model provider types"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class ModelTier(Enum):
    """Model capability tiers"""
    FLAGSHIP = "flagship"  # Most capable, highest cost
    ADVANCED = "advanced"  # High capability, moderate cost
    STANDARD = "standard"  # Good capability, low cost
    FAST = "fast"  # Fast response, lowest cost
    LOCAL = "local"  # Local models, no API cost


class ModelInfo(BaseModel):
    """Detailed information about a model"""
    name: str
    provider: ModelProviderType
    tier: ModelTier
    context_window: int
    max_output_tokens: int
    supports_streaming: bool = True
    supports_functions: bool = False
    cost_per_1k_input: float = 0.0  # USD
    cost_per_1k_output: float = 0.0  # USD
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ProviderConfig(BaseModel):
    """Configuration for a specific provider"""
    provider_type: ModelProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    rate_limit_per_minute: Optional[int] = None
    enabled: bool = True
    priority: int = 0  # Higher priority providers tried first


class ModelConfig:
    """
    Comprehensive configuration for AI model providers and models
    """
    
    # OpenAI Models
    OPENAI_MODELS = {
        "gpt-4-turbo": ModelInfo(
            name="gpt-4-turbo-preview",
            provider=ModelProviderType.OPENAI,
            tier=ModelTier.FLAGSHIP,
            context_window=128000,
            max_output_tokens=4096,
            supports_functions=True,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.03,
            description="Most capable GPT-4 model",
            tags=["reasoning", "coding", "analysis"]
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
            tags=["fast", "efficient"]
        ),
    }
    
    # Anthropic Models
    ANTHROPIC_MODELS = {
        "claude-3-opus": ModelInfo(
            name="claude-3-opus-20240229",
            provider=ModelProviderType.ANTHROPIC,
            tier=ModelTier.FLAGSHIP,
            context_window=200000,
            max_output_tokens=4096,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            description="Most intelligent Claude model",
            tags=["reasoning", "analysis", "writing"]
        ),
        "claude-3-sonnet": ModelInfo(
            name="claude-3-sonnet-20240229",
            provider=ModelProviderType.ANTHROPIC,
            tier=ModelTier.ADVANCED,
            context_window=200000,
            max_output_tokens=4096,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
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
            tags=["fast", "efficient"]
        ),
    }
    
    # Gemini Models
    GEMINI_MODELS = {
        "gemini-1.5-pro": ModelInfo(
            name="gemini-1.5-pro",
            provider=ModelProviderType.GEMINI,
            tier=ModelTier.FLAGSHIP,
            context_window=1000000,
            max_output_tokens=8192,
            supports_functions=True,
            cost_per_1k_input=0.0035,
            cost_per_1k_output=0.0105,
            tags=["multimodal", "long-context"]
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
            tags=["efficient", "multimodal"]
        ),
    }
    
    # Ollama Local Models
    OLLAMA_MODELS = {
        "llama3:8b": ModelInfo(
            name="llama3:8b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Llama 3 8B - Fast and capable",
            tags=["local", "open-source", "fast"]
        ),
        "llama3:70b": ModelInfo(
            name="llama3:70b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Llama 3 70B - Most capable",
            tags=["local", "open-source", "powerful"]
        ),
        "mistral:7b": ModelInfo(
            name="mistral:7b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Mistral 7B - Excellent performance",
            tags=["local", "open-source", "efficient"]
        ),
        "codellama:13b": ModelInfo(
            name="codellama:13b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=16384,
            max_output_tokens=2048,
            description="CodeLlama 13B - Code generation",
            tags=["local", "coding", "open-source"]
        ),
        "mixtral:8x7b": ModelInfo(
            name="mixtral:8x7b",
            provider=ModelProviderType.OLLAMA,
            tier=ModelTier.LOCAL,
            context_window=32768,
            max_output_tokens=4096,
            description="Mixtral 8x7B - Mixture of experts",
            tags=["local", "open-source", "advanced"]
        ),
    }
    
    # HuggingFace Models
    HUGGINGFACE_MODELS = {
        "mistralai/Mistral-7B-Instruct-v0.2": ModelInfo(
            name="mistralai/Mistral-7B-Instruct-v0.2",
            provider=ModelProviderType.HUGGINGFACE,
            tier=ModelTier.LOCAL,
            context_window=8192,
            max_output_tokens=2048,
            description="Mistral 7B Instruct from HuggingFace",
            tags=["local", "instruction-following"]
        ),
        "meta-llama/Llama-2-7b-chat-hf": ModelInfo(
            name="meta-llama/Llama-2-7b-chat-hf",
            provider=ModelProviderType.HUGGINGFACE,
            tier=ModelTier.LOCAL,
            context_window=4096,
            max_output_tokens=2048,
            description="Llama 2 7B Chat from HuggingFace",
            tags=["local", "chat"]
        ),
    }
    
    # Default generation parameters
    DEFAULT_PARAMS = {
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": True,
    }
    
    # Provider defaults
    PROVIDER_DEFAULTS = {
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
        """Get all available models across all providers"""
        all_models = {}
        all_models.update(cls.OPENAI_MODELS)
        all_models.update(cls.ANTHROPIC_MODELS)
        all_models.update(cls.GEMINI_MODELS)
        all_models.update(cls.OLLAMA_MODELS)
        all_models.update(cls.HUGGINGFACE_MODELS)
        return all_models
    
    @classmethod
    def get_model_info(cls, model_identifier: str) -> Optional[ModelInfo]:
        """Get model information by identifier or alias"""
        all_models = cls.get_all_models()
        return all_models.get(model_identifier)
    
    @classmethod
    def get_models_by_provider(cls, provider: ModelProviderType) -> Dict[str, ModelInfo]:
        """Get all models for a specific provider"""
        all_models = cls.get_all_models()
        return {k: v for k, v in all_models.items() if v.provider == provider}
    
    @classmethod
    def get_models_by_tier(cls, tier: ModelTier) -> Dict[str, ModelInfo]:
        """Get all models in a specific tier"""
        all_models = cls.get_all_models()
        return {k: v for k, v in all_models.items() if v.tier == tier}
    
    @classmethod
    def get_fallback_chain(cls, primary_model: str) -> List[str]:
        """Get recommended fallback models for a given primary model"""
        model_info = cls.get_model_info(primary_model)
        if not model_info:
            return []
        
        # Build fallback chain based on tier and capabilities
        fallback_chain = [primary_model]
        
        if model_info.tier == ModelTier.FLAGSHIP:
            # Fallback to advanced, then standard
            advanced = [k for k, v in cls.get_models_by_tier(ModelTier.ADVANCED).items()]
            standard = [k for k, v in cls.get_models_by_tier(ModelTier.STANDARD).items()]
            fallback_chain.extend(advanced[:2])
            fallback_chain.extend(standard[:1])
        elif model_info.tier == ModelTier.ADVANCED:
            # Fallback to other advanced, then standard
            other_advanced = [k for k, v in cls.get_models_by_tier(ModelTier.ADVANCED).items() if k != primary_model]
            standard = [k for k, v in cls.get_models_by_tier(ModelTier.STANDARD).items()]
            fallback_chain.extend(other_advanced[:1])
            fallback_chain.extend(standard[:1])
        
        return fallback_chain
