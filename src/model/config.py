# This file has been updated with Claude-3.5 Sonnet configuration
# Appending to existing ANTHROPIC_MODELS dictionary

# Add to ANTHROPIC_MODELS section (line ~170):
"claude-3.5-sonnet": ModelInfo(
    name="claude-3-5-sonnet-20241022",
    provider=ModelProviderType.ANTHROPIC,
    tier=ModelTier.FLAGSHIP,
    context_window=200000,
    max_output_tokens=8192,
    supports_streaming=True,
    supports_functions=False,
    cost_per_1k_input=0.003,
    cost_per_1k_output=0.015,
    description="Claude 3.5 Sonnet - Most intelligent and capable model with extended context",
    tags=["reasoning", "analysis", "writing", "coding", "long-context", "flagship"]
),
