"""
API routes for enhanced conversation memory management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from ..database import get_db
from ..auth import get_current_user
from ..models import User, Conversation
from src.model.memory_enhanced import (
    EnhancedConversationMemory,
    SummarizationStrategy,
    MemoryImportance
)


router = APIRouter()


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics"""
    conversation_id: str
    total_turns: int
    active_turns: int
    summarized_turns: int
    summaries_count: int
    important_facts_count: int
    current_messages: int
    token_count: int
    max_tokens: int
    token_usage_percent: float
    available_tokens: int
    compression_ratio: float
    strategy: str
    memory_health: str


class SummaryRequest(BaseModel):
    """Request model for creating summaries"""
    aggressive: bool = Field(False, description="Use aggressive optimization")
    min_turns: int = Field(10, description="Minimum turns before summarization")


class MemoryOptimizationResponse(BaseModel):
    """Response model for optimization results"""
    success: bool
    message: str
    stats_before: Dict
    stats_after: Dict
    turns_removed: int
    summaries_created: int


class ImportantFactsResponse(BaseModel):
    """Response model for important facts"""
    conversation_id: str
    facts: List[str]
    total_count: int


class MemoryExportResponse(BaseModel):
    """Response model for memory export"""
    conversation_id: str
    export_data: Dict
    file_size_estimate: int


@router.get("/conversations/{conversation_id}/memory/stats")
async def get_memory_stats(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MemoryStatsResponse:
    """
    Get detailed memory statistics for a conversation
    
    Shows:
    - Total turns and active/summarized breakdown
    - Token usage and available space
    - Compression ratio from summaries
    - Memory health status
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db,
        max_tokens=conversation.metadata.get("max_tokens", 4000) if conversation.metadata else 4000
    )
    
    # Get stats
    stats = memory.get_context_stats()
    stats["conversation_id"] = conversation_id
    stats["memory_health"] = memory._assess_memory_health()
    
    return MemoryStatsResponse(**stats)


@router.post("/conversations/{conversation_id}/memory/optimize")
async def optimize_memory(
    conversation_id: str,
    request: SummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MemoryOptimizationResponse:
    """
    Optimize conversation memory by creating summaries and removing old content
    
    This will:
    1. Create summaries of older conversation segments
    2. Remove low-importance summarized turns
    3. Preserve important facts and recent context
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db,
        summary_threshold=request.min_turns
    )
    
    # Get stats before
    stats_before = memory.get_context_stats()
    turns_before = len(memory.turns)
    summaries_before = len(memory.summaries)
    
    # Optimize
    try:
        memory.optimize_memory(aggressive=request.aggressive)
        
        # Get stats after
        stats_after = memory.get_context_stats()
        turns_after = len(memory.turns)
        summaries_after = len(memory.summaries)
        
        # Save updated memory state
        conversation.metadata = conversation.metadata or {}
        conversation.metadata["summaries"] = [
            {
                "summary_text": s.summary_text,
                "turn_ids": s.turn_ids,
                "start_timestamp": s.start_timestamp,
                "end_timestamp": s.end_timestamp,
                "token_count": s.token_count,
                "compression_ratio": s.compression_ratio,
                "created_at": s.created_at
            }
            for s in memory.summaries
        ]
        conversation.metadata["important_facts"] = memory.important_facts
        db.commit()
        
        return MemoryOptimizationResponse(
            success=True,
            message=f"Memory optimized successfully. Created {summaries_after - summaries_before} new summaries.",
            stats_before=stats_before,
            stats_after=stats_after,
            turns_removed=turns_before - turns_after,
            summaries_created=summaries_after - summaries_before
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error optimizing memory: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/memory/facts")
async def get_important_facts(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ImportantFactsResponse:
    """
    Get important facts extracted from the conversation
    
    Important facts include:
    - User preferences
    - Names and personal information
    - Critical context that should always be remembered
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db
    )
    
    return ImportantFactsResponse(
        conversation_id=conversation_id,
        facts=memory.important_facts,
        total_count=len(memory.important_facts)
    )


@router.delete("/conversations/{conversation_id}/memory/facts/{fact_index}")
async def delete_important_fact(
    conversation_id: str,
    fact_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific important fact by index"""
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db
    )
    
    if fact_index < 0 or fact_index >= len(memory.important_facts):
        raise HTTPException(status_code=404, detail="Fact index out of range")
    
    # Remove fact
    removed_fact = memory.important_facts.pop(fact_index)
    
    # Save
    conversation.metadata = conversation.metadata or {}
    conversation.metadata["important_facts"] = memory.important_facts
    db.commit()
    
    return {
        "success": True,
        "message": f"Fact removed: {removed_fact}",
        "remaining_facts": len(memory.important_facts)
    }


@router.get("/conversations/{conversation_id}/memory/summaries")
async def get_conversation_summaries(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all summaries created for this conversation
    
    Summaries are compact representations of older conversation segments
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db
    )
    
    summaries = [
        {
            "summary_text": s.summary_text,
            "turn_count": len(s.turn_ids),
            "start_timestamp": s.start_timestamp,
            "end_timestamp": s.end_timestamp,
            "token_count": s.token_count,
            "compression_ratio": round(s.compression_ratio, 3),
            "created_at": s.created_at
        }
        for s in memory.summaries
    ]
    
    return {
        "conversation_id": conversation_id,
        "summaries": summaries,
        "total_summaries": len(summaries),
        "total_compressed_turns": sum(len(s.turn_ids) for s in memory.summaries),
        "average_compression": round(
            sum(s.compression_ratio for s in memory.summaries) / len(memory.summaries),
            3
        ) if memory.summaries else 0
    }


@router.delete("/conversations/{conversation_id}/memory/summaries")
async def clear_summaries(
    conversation_id: str,
    keep_recent: int = Query(0, ge=0, description="Number of recent summaries to keep"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear conversation summaries (optionally keep recent N)"""
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db
    )
    
    summaries_before = len(memory.summaries)
    
    if keep_recent > 0:
        memory.clear_old_summaries(keep_recent=keep_recent)
    else:
        memory.summaries = []
    
    # Save
    conversation.metadata = conversation.metadata or {}
    conversation.metadata["summaries"] = [
        {
            "summary_text": s.summary_text,
            "turn_ids": s.turn_ids,
            "start_timestamp": s.start_timestamp,
            "end_timestamp": s.end_timestamp,
            "token_count": s.token_count,
            "compression_ratio": s.compression_ratio,
            "created_at": s.created_at
        }
        for s in memory.summaries
    ]
    db.commit()
    
    return {
        "success": True,
        "message": f"Cleared {summaries_before - len(memory.summaries)} summaries",
        "remaining_summaries": len(memory.summaries)
    }


@router.get("/conversations/{conversation_id}/memory/export")
async def export_memory(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MemoryExportResponse:
    """
    Export complete memory state for backup or migration
    
    Includes:
    - All conversation turns
    - All summaries
    - Important facts
    - Metadata
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db
    )
    
    # Export
    export_data = memory.export()
    
    # Estimate size
    import json
    file_size = len(json.dumps(export_data))
    
    return MemoryExportResponse(
        conversation_id=conversation_id,
        export_data=export_data,
        file_size_estimate=file_size
    )


@router.get("/conversations/{conversation_id}/memory/context")
async def get_context_window(
    conversation_id: str,
    optimize: bool = Query(True, description="Apply context optimization"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current context window that would be sent to the LLM
    
    Shows exactly what messages are included and why
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Load memory
    memory = EnhancedConversationMemory(
        conversation_id=conversation_id,
        db=db
    )
    
    # Get messages
    messages = memory.get_messages(optimize_context=optimize)
    
    # Categorize messages
    system_messages = [m for m in messages if m["role"] == "system"]
    user_messages = [m for m in messages if m["role"] == "user"]
    assistant_messages = [m for m in messages if m["role"] == "assistant"]
    
    return {
        "conversation_id": conversation_id,
        "total_messages": len(messages),
        "breakdown": {
            "system": len(system_messages),
            "user": len(user_messages),
            "assistant": len(assistant_messages)
        },
        "token_count": memory._count_tokens(messages),
        "max_tokens": memory.max_tokens,
        "optimization_enabled": optimize,
        "messages": messages,
        "stats": memory.get_context_stats()
    }


@router.post("/conversations/{conversation_id}/memory/settings")
async def update_memory_settings(
    conversation_id: str,
    max_tokens: Optional[int] = None,
    max_turns: Optional[int] = None,
    strategy: Optional[str] = None,
    summary_threshold: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update memory management settings for a conversation
    
    Settings:
    - max_tokens: Maximum context window size
    - max_turns: Maximum number of turns to keep in memory
    - strategy: Summarization strategy (none, sliding_window, hierarchical, adaptive)
    - summary_threshold: Number of turns before summarization triggers
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Update metadata
    if not conversation.metadata:
        conversation.metadata = {}
    
    if max_tokens is not None:
        conversation.metadata["max_tokens"] = max_tokens
    
    if max_turns is not None:
        conversation.metadata["max_turns"] = max_turns
    
    if strategy is not None:
        # Validate strategy
        try:
            SummarizationStrategy(strategy)
            conversation.metadata["summarization_strategy"] = strategy
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy. Must be one of: {[s.value for s in SummarizationStrategy]}"
            )
    
    if summary_threshold is not None:
        conversation.metadata["summary_threshold"] = summary_threshold
    
    db.commit()
    
    return {
        "success": True,
        "message": "Memory settings updated",
        "settings": {
            "max_tokens": conversation.metadata.get("max_tokens"),
            "max_turns": conversation.metadata.get("max_turns"),
            "strategy": conversation.metadata.get("summarization_strategy"),
            "summary_threshold": conversation.metadata.get("summary_threshold")
        }
    }
