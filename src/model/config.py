from typing import Dict, Any, Optional
from enum import Enum

class ModelProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

class ModelConfig:
    """
    Configuration for AI model providers
    """
    
    # Model mappings
    OPENAI_MODELS = {
        "gpt-4-turbo": "gpt-4-turbo-preview",
        "gpt-4": "gpt-4",
        "gpt-3.5": "gpt-3.5-turbo",
        "gpt-3.5-16k": "gpt-3.5-turbo-16k"
    }
    
    ANTHROPIC_MODELS = {
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
        "claude-3-haiku": "claude-3-haiku-20240307"
    }
    
    # Default parameters
    DEFAULT_PARAMS = {
        "temperature": 0.7,
        "max_tokens": 4000,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    
    # Context window sizes
    CONTEXT_WINDOWS = {
        "gpt-4-turbo-preview": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000
    }
    
    @classmethod
    def get_model_info(cls, provider: str, model_alias: str) -> Dict[str, Any]:
        """
        Get model information by provider and alias
        """
        if provider == "openai":
            model_name = cls.OPENAI_MODELS.get(model_alias, model_alias)
        elif provider == "anthropic":
            model_name = cls.ANTHROPIC_MODELS.get(model_alias, model_alias)
        else:
            model_name = model_alias
        
        return {
            "name": model_name,
            "provider": provider,
            "context_window": cls.CONTEXT_WINDOWS.get(model_name, 4096),
            "default_params": cls.DEFAULT_PARAMS.copy()
        }
