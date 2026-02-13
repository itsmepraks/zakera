"""API routes for model management and selection"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel

from src.model.model_manager import ModelManager, FallbackStrategy
from src.model.config import ModelConfig, ModelProviderType, ModelTier
from src.model.providers import Message

router = APIRouter(prefix="/models", tags=["models"])

# Initialize model manager
model_manager = ModelManager(
    default_model="gpt-3.5-turbo",
    fallback_strategy=FallbackStrategy.SEQUENTIAL,
    enable_health_checks=True
)


class GenerateRequest(BaseModel):
    """Request for text generation"""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    stream: bool = False
    enable_fallback: bool = True


class GenerateResponse(BaseModel):
    """Response from text generation"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


@router.get("/")
async def list_models(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    available_only: bool = Query(True, description="Only show available models")
):
    """
    List all available models
    
    Returns information about all configured models including their
    capabilities, pricing, and availability status.
    """
    try:
        models = await model_manager.list_available_models()
        
        # Apply filters
        if provider:
            models = [m for m in models if m["provider"] == provider]
        
        if tier:
            models = [m for m in models if m["tier"] == tier]
        
        if available_only:
            models = [m for m in models if m["is_available"]]
        
        return {
            "models": models,
            "count": len(models)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers():
    """
    List all configured providers and their status
    """
    try:
        stats = model_manager.get_statistics()
        
        providers = []
        for provider_type in ModelProviderType:
            config = ModelConfig.PROVIDER_DEFAULTS.get(provider_type)
            if config:
                health = stats["provider_health"].get(provider_type.value, {})
                
                providers.append({
                    "type": provider_type.value,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "is_available": health.get("is_available", False),
                    "consecutive_failures": health.get("consecutive_failures", 0),
                    "avg_latency": health.get("avg_latency", 0.0)
                })
        
        return {
            "providers": sorted(providers, key=lambda x: x["priority"], reverse=True)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics():
    """
    Get model usage statistics
    """
    try:
        return model_manager.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}")
async def get_model_info(model_id: str):
    """
    Get detailed information about a specific model
    """
    try:
        model_info = ModelConfig.get_model_info(model_id)
        if not model_info:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        return {
            "id": model_id,
            "name": model_info.name,
            "provider": model_info.provider.value,
            "tier": model_info.tier.value,
            "context_window": model_info.context_window,
            "max_output_tokens": model_info.max_output_tokens,
            "supports_streaming": model_info.supports_streaming,
            "supports_functions": model_info.supports_functions,
            "cost_per_1k_input": model_info.cost_per_1k_input,
            "cost_per_1k_output": model_info.cost_per_1k_output,
            "description": model_info.description,
            "tags": model_info.tags
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}/fallback-chain")
async def get_fallback_chain(model_id: str):
    """
    Get the fallback chain for a specific model
    """
    try:
        chain = ModelConfig.get_fallback_chain(model_id)
        if not chain:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
        
        return {
            "primary_model": model_id,
            "fallback_chain": chain,
            "strategy": model_manager.fallback_strategy.value
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate(request: GenerateRequest):
    """
    Generate text using specified model with automatic fallback
    
    Supports streaming and non-streaming generation with intelligent
    fallback to alternative models if the primary model fails.
    """
    try:
        # Convert messages
        messages = [
            Message(
                role=msg["role"],
                content=msg["content"],
                name=msg.get("name")
            )
            for msg in request.messages
        ]
        
        # Generate parameters
        params = {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
        }
        
        if request.stream:
            # For streaming, we'll need to handle Server-Sent Events
            # This is typically done with StreamingResponse
            from fastapi.responses import StreamingResponse
            
            async def generate_stream():
                try:
                    async for chunk in model_manager.stream_generate(
                        messages,
                        model=request.model,
                        fallback=request.enable_fallback,
                        **params
                    ):
                        yield f"data: {chunk}\n\n"
                except Exception as e:
                    yield f"data: [ERROR] {str(e)}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream"
            )
        
        else:
            # Non-streaming generation
            response = await model_manager.generate(
                messages,
                model=request.model,
                fallback=request.enable_fallback,
                **params
            )
            
            return GenerateResponse(
                content=response.content,
                model=response.model,
                usage=response.usage,
                finish_reason=response.finish_reason
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check health of all model providers
    """
    try:
        stats = model_manager.get_statistics()
        provider_health = stats.get("provider_health", {})
        
        healthy_count = sum(
            1 for health in provider_health.values()
            if health.get("is_available", False)
        )
        
        return {
            "status": "healthy" if healthy_count > 0 else "unhealthy",
            "healthy_providers": healthy_count,
            "total_providers": len(provider_health),
            "details": provider_health
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
