"""
API routes for tool management and execution.

Provides RESTful endpoints for:
- Listing available tools
- Getting tool information
- Executing tools
- Managing tool chains
- Tool statistics and history
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import logging

from src.tools import get_registry, get_tool_manager
from src.tools.base import ToolNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ToolExecutionRequest(BaseModel):
    """Request model for tool execution."""
    tool_name: str = Field(..., description="Name of tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    use_cache: bool = Field(default=True, description="Use cached results if available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "calculator",
                "parameters": {"expression": "2 + 2"},
                "use_cache": True
            }
        }


class ToolChainRequest(BaseModel):
    """Request model for tool chain execution."""
    steps: List[Dict[str, Any]] = Field(..., description="Chain of tool executions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "steps": [
                    {
                        "tool_name": "calculator",
                        "parameters": {"expression": "10 * 5"}
                    },
                    {
                        "tool_name": "calculator",
                        "parameters": {"expression": "result + 25"},
                        "output_mapping": {"result": "result"}
                    }
                ]
            }
        }


class ToolResponse(BaseModel):
    """Response model for tool information."""
    name: str
    description: str
    version: str
    category: str
    tags: List[str]
    parameters: List[Dict[str, Any]]
    enabled: bool


class ToolExecutionResponse(BaseModel):
    """Response model for tool execution results."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: Optional[float] = None


# ============================================================================
# Tool Discovery Endpoints
# ============================================================================

@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled_only: bool = Query(True, description="Only return enabled tools"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
):
    """
    List all available tools.
    
    Returns information about all registered tools that match
    the specified filters.
    """
    try:
        registry = get_registry()
        tools = registry.list_tools(
            category=category,
            enabled_only=enabled_only,
            tags=tags
        )
        
        return [
            ToolResponse(
                name=tool.name,
                description=tool.description,
                version=tool.version,
                category=tool.category,
                tags=tool.tags,
                parameters=[
                    {
                        "name": p.name,
                        "type": p.type.value,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                    }
                    for p in tool.parameters
                ],
                enabled=tool.enabled
            )
            for tool in tools
        ]
    except Exception as e:
        logger.exception("Error listing tools")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.get("/categories")
async def list_categories():
    """
    Get list of all tool categories.
    
    Returns unique categories from all registered tools.
    """
    try:
        registry = get_registry()
        categories = registry.get_categories()
        return {"categories": categories}
    except Exception as e:
        logger.exception("Error listing categories")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_tools(
    query: str = Query(..., description="Search query"),
):
    """
    Search for tools by name, description, or tags.
    
    Returns tools matching the search query.
    """
    try:
        registry = get_registry()
        tools = registry.search(query)
        
        return {
            "query": query,
            "results": [tool.to_dict() for tool in tools],
            "count": len(tools)
        }
    except Exception as e:
        logger.exception("Error searching tools")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool_info(tool_name: str):
    """
    Get detailed information about a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Detailed tool information including parameters
    """
    try:
        registry = get_registry()
        tool = registry.get(tool_name)
        
        return ToolResponse(
            name=tool.name,
            description=tool.description,
            version=tool.version,
            category=tool.category,
            tags=tool.tags,
            parameters=[
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                }
                for p in tool.parameters
            ],
            enabled=tool.enabled
        )
    except ToolNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    except Exception as e:
        logger.exception(f"Error getting tool info for {tool_name}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tool Execution Endpoints
# ============================================================================

@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(request: ToolExecutionRequest):
    """
    Execute a tool with given parameters.
    
    Args:
        request: Tool execution request with name and parameters
        
    Returns:
        Tool execution result
    """
    try:
        manager = get_tool_manager()
        
        result = await manager.execute_tool(
            tool_name=request.tool_name,
            parameters=request.parameters,
            use_cache=request.use_cache
        )
        
        return ToolExecutionResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata,
            execution_time=result.execution_time
        )
    
    except ToolNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' not found"
        )
    except Exception as e:
        logger.exception(f"Error executing tool {request.tool_name}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")


@router.post("/execute-chain", response_model=List[ToolExecutionResponse])
async def execute_tool_chain(request: ToolChainRequest):
    """
    Execute a chain of tools where each output feeds the next.
    
    Args:
        request: Tool chain configuration
        
    Returns:
        List of results from each step
    """
    try:
        manager = get_tool_manager()
        
        # Validate chain first
        is_valid, error = await manager.validate_tool_chain(request.steps)
        if not is_valid:
            raise HTTPException(status_code=422, detail=error)
        
        # Execute chain
        results = await manager.execute_tool_chain(request.steps)
        
        return [
            ToolExecutionResponse(
                success=result.success,
                data=result.data,
                error=result.error,
                metadata=result.metadata,
                execution_time=result.execution_time
            )
            for result in results
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing tool chain")
        raise HTTPException(status_code=500, detail=f"Chain execution failed: {str(e)}")


@router.post("/execute-parallel")
async def execute_tools_parallel(
    tool_calls: List[ToolExecutionRequest]
):
    """
    Execute multiple tools in parallel.
    
    Args:
        tool_calls: List of tool execution requests
        
    Returns:
        List of results in same order as requests
    """
    try:
        manager = get_tool_manager()
        
        # Convert requests to tuples
        calls = [
            (req.tool_name, req.parameters)
            for req in tool_calls
        ]
        
        # Execute in parallel
        results = await manager.execute_tools_parallel(calls)
        
        return {
            "results": [
                ToolExecutionResponse(
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    metadata=result.metadata,
                    execution_time=result.execution_time
                )
                for result in results
            ],
            "total": len(results)
        }
    
    except Exception as e:
        logger.exception("Error executing tools in parallel")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tool Management Endpoints
# ============================================================================

@router.get("/statistics")
async def get_tool_statistics(
    tool_name: Optional[str] = Query(None, description="Filter by tool name")
):
    """
    Get execution statistics for tools.
    
    Args:
        tool_name: Optional tool name filter
        
    Returns:
        Execution statistics
    """
    try:
        manager = get_tool_manager()
        stats = manager.get_statistics(tool_name)
        return stats
    except Exception as e:
        logger.exception("Error getting statistics")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_execution_history(
    tool_name: Optional[str] = Query(None, description="Filter by tool name"),
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return")
):
    """
    Get tool execution history.
    
    Args:
        tool_name: Optional tool name filter
        limit: Maximum entries to return
        
    Returns:
        List of execution records
    """
    try:
        manager = get_tool_manager()
        history = manager.get_execution_history(tool_name, limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.exception("Error getting execution history")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_cache(
    tool_name: Optional[str] = Query(None, description="Tool name to clear cache for")
):
    """
    Clear cached tool results.
    
    Args:
        tool_name: Optional tool name (clears all if not provided)
        
    Returns:
        Number of cache entries cleared
    """
    try:
        manager = get_tool_manager()
        count = manager.clear_cache(tool_name)
        return {"cleared": count, "tool": tool_name or "all"}
    except Exception as e:
        logger.exception("Error clearing cache")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_tool_schemas():
    """
    Get tool schemas in OpenAI function calling format.
    
    Returns schemas for all available tools in a format compatible
    with OpenAI's function calling API.
    """
    try:
        registry = get_registry()
        schemas = registry.export_schema()
        return {"schemas": schemas, "count": len(schemas)}
    except Exception as e:
        logger.exception("Error exporting schemas")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def tool_system_health():
    """
    Check health of tool system.
    
    Returns status of tool registry and manager.
    """
    try:
        registry = get_registry()
        manager = get_tool_manager()
        stats = manager.get_statistics()
        
        return {
            "status": "healthy",
            "tools_registered": len(registry),
            "tools_enabled": len(registry.list_tools(enabled_only=True)),
            "total_executions": stats.get("total_executions", 0),
            "success_rate": stats.get("success_rate", 0),
            "cache_size": stats.get("cache_size", 0),
        }
    except Exception as e:
        logger.exception("Error checking tool system health")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
