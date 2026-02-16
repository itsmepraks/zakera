"""Model-related helper utilities."""

import os
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def get_available_models() -> List[str]:
    """Get list of currently available model identifiers.
    
    Checks configuration and returns models that are accessible
    based on enabled providers and available API keys.
    
    Returns:
        List of available model identifiers
    """
    from src.model.config import ModelConfig
    
    available = []
    all_models = ModelConfig.get_all_models()
    
    for model_id, model_info in all_models.items():
        # Check if provider is enabled
        provider = model_info.provider
        
        # Local providers (Ollama, HuggingFace)
        if provider.value in ["ollama", "huggingface", "local"]:
            provider_env = f"ENABLE_{provider.value.upper()}"
            if os.getenv(provider_env, "false").lower() == "true":
                available.append(model_id)
        
        # API providers (need keys)
        else:
            key_env = f"{provider.value.upper()}_API_KEY"
            if os.getenv(key_env):
                available.append(model_id)
    
    logger.debug(f"Found {len(available)} available models")
    return available


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate token count for text.
    
    Args:
        text: Text to count tokens for
        model: Model identifier for encoding
        
    Returns:
        Estimated token count
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str
) -> Tuple[float, Dict[str, float]]:
    """Calculate cost for a model request.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier
        
    Returns:
        Tuple of (total_cost, cost_breakdown)
    """
    from src.model.config import ModelConfig
    
    model_info = ModelConfig.get_model_info(model)
    
    if not model_info:
        logger.warning(f"Unknown model for cost calculation: {model}")
        return 0.0, {"input": 0.0, "output": 0.0}
    
    input_cost = (input_tokens / 1000) * model_info.cost_per_1k_input
    output_cost = (output_tokens / 1000) * model_info.cost_per_1k_output
    total = input_cost + output_cost
    
    breakdown = {
        "input": input_cost,
        "output": output_cost,
        "total": total
    }
    
    logger.debug(
        f"Cost calculated for {model}: ${total:.4f} "
        f"({input_tokens} in + {output_tokens} out)"
    )
    
    return total, breakdown


def recommend_model(
    task_type: str = "chat",
    priority: str = "balanced"
) -> Optional[str]:
    """Recommend a model based on task type and priority.
    
    Args:
        task_type: Type of task (chat, code, analysis, creative)
        priority: Priority (quality, speed, cost)
        
    Returns:
        Recommended model identifier or None
    """
    from src.model.config import ModelConfig
    
    # Get available models
    available = get_available_models()
    all_models = ModelConfig.get_all_models()
    
    if not available:
        logger.warning("No models available for recommendation")
        return None
    
    # Filter by task type
    candidates = []
    
    for model_id in available:
        model_info = all_models.get(model_id)
        if not model_info:
            continue
        
        # Match task type to tags
        if task_type == "code" and "coding" in model_info.tags:
            candidates.append((model_id, model_info))
        elif task_type == "analysis" and "reasoning" in model_info.tags:
            candidates.append((model_id, model_info))
        elif task_type == "creative" and "creative" in model_info.tags:
            candidates.append((model_id, model_info))
        else:
            # Default: all available
            candidates.append((model_id, model_info))
    
    if not candidates:
        candidates = [(m, all_models[m]) for m in available if m in all_models]
    
    # Sort by priority
    if priority == "quality":
        # Prefer flagship tier
        candidates.sort(
            key=lambda x: (x[1].tier.value != "flagship", x[1].cost_per_1k_output)
        )
    elif priority == "speed":
        # Prefer fast tier or local
        candidates.sort(
            key=lambda x: (x[1].tier.value not in ["fast", "local"], x[1].cost_per_1k_output)
        )
    elif priority == "cost":
        # Prefer local first, then cheapest
        candidates.sort(
            key=lambda x: (x[1].tier.value != "local", x[1].cost_per_1k_input)
        )
    else:  # balanced
        # Prefer advanced tier
        candidates.sort(
            key=lambda x: (x[1].tier.value != "advanced", x[1].cost_per_1k_output)
        )
    
    recommended = candidates[0][0] if candidates else None
    
    if recommended:
        logger.info(
            f"Recommended {recommended} for {task_type} task with {priority} priority"
        )
    
    return recommended


def main() -> None:
    """Run startup diagnostics."""
    print_header("Zakera Startup Diagnostics")
    
    # Check environment
    env_results = check_environment()
    
    # Validate configuration
    print("\n🔍 Configuration Validation")
    print("-" * 70)
    
    try:
        from src.utils.config_validator import validate_config
        is_valid = validate_config(verbose=False)
        
        if is_valid:
            print("✅ Configuration is valid")
        else:
            print("❌ Configuration has errors")
            print("\nRun for details: python scripts/health_check.py")
    except Exception as e:
        print(f"⚠️  Could not validate config: {e}")
    
    # Model recommendations
    print("\n💡 Model Recommendations")
    print("-" * 70)
    
    try:
        from src.utils.model_helpers import recommend_model, get_available_models
        
        available = get_available_models()
        print(f"Available models: {len(available)}")
        
        if available:
            recommendations = {
                "General Chat": recommend_model("chat", "balanced"),
                "Code Generation": recommend_model("code", "quality"),
                "Fast Responses": recommend_model("chat", "speed"),
                "Cost-Effective": recommend_model("chat", "cost"),
            }
            
            for use_case, model in recommendations.items():
                if model:
                    print(f"  {use_case:.<30} {model}")
        else:
            print("  ⚠️  No models available - configure a provider")
    except Exception as e:
        print(f"  ⚠️  Could not generate recommendations: {e}")
    
    # Print next steps
    print("\n🚀 Next Steps")
    print("-" * 70)
    print("""
1. Start the server:
   python -m uvicorn src.api.main:app --reload

2. Access API documentation:
   http://localhost:8000/api/docs

3. Run health checks:
   python scripts/health_check.py

4. View detailed configuration:
   python scripts/health_check.py --quick
    """)
    
    print_header("Diagnostics Complete")


if __name__ == "__main__":
    main()
