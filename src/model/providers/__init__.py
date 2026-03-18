"""
Model provider registry.

Import all providers here so that the registry is populated on package load.
"""

from .gemini_flash import GeminiFlashProvider

# Provider registry maps provider_id -> provider class
PROVIDER_REGISTRY: dict = {
    GeminiFlashProvider.PROVIDER_ID: GeminiFlashProvider,
}

__all__ = [
    "GeminiFlashProvider",
    "PROVIDER_REGISTRY",
]
