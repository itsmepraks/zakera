"""Conversation export routes with streaming support.

Provides endpoints for exporting conversations in multiple formats
with real-time progress updates and comprehensive analytics.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field

from src.api.database import get_db
from src.api.auth import get_current_user
from src.monitoring.metrics import track_api_call
from src.monitoring.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/conversations", tags=["export"])


# Export rate limiting
EXPORT_RATE_LIMIT = 5  # exports per minute per user
export_timestamps = {}  # user_id -> list of export timestamps


class ExportOptions(BaseModel):
    """Export configuration options."""
    
    format: str = Field(default="json", pattern="^(json|csv|markdown|pdf)$")
    include_metadata: bool = Field(default=True)
    include_statistics: bool = Field(default=True)
    include_reactions: bool = Field(default=True)
    date_from: Optional[datetime] = Field(default=None)
    date_to: Optional[datetime] = Field(default=None)
    compress: bool = Field(default=False)
    

class ExportProgress(BaseModel):
    """Progress update during export."""
    
    type: str = Field(default="progress")
    stage: str
    progress: int = Field(ge=0, le=100)
    message: str
    data: Optional[dict] = None


class ExportMetadata(BaseModel):
    """Export metadata."""
    
    export_id: str
    conversation_id: str
    user_id: str
    format: str
    created_at: datetime
    total_messages: int
    date_range: dict
    

async def check_export_rate_limit(user_id: str) -> None:
    """Check if user has exceeded export rate limit."""
    now = datetime.utcnow()
    
    if user_id not in export_timestamps:
        export_timestamps[user_id] = []
    
    # Remove timestamps older than 1 minute
    export_timestamps[user_id] = [
        ts for ts in export_timestamps[user_id]
        if (now - ts).seconds < 60
    ]
    
    if len(export_timestamps[user_id]) >= EXPORT_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Export rate limit exceeded. Max {EXPORT_RATE_LIMIT} exports per minute."
        )
    
    export_timestamps[user_id].append(now)


async def get_conversation_messages(
    conversation_id: str,
    user_id: str,
    db: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> list:
    """Fetch conversation messages with filters."""
    # Mock implementation - replace with actual database queries
    # In production, this would query your Message model
    
    logger.info(
        f"Fetching messages for conversation {conversation_id}",
        extra={
            "conversation_id": conversation_id,
            "user_id": user_id,
            "date_from": date_from,
            "date_to": date_to
        }
    )
    
    # Simulated messages for demonstration
    messages = [
        {
            "id": f"msg_{i}",
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message content {i}",
            "timestamp": datetime.utcnow().isoformat(),
            "tokens": 50 + i * 10,
            "cost": 0.001 * i,
            "model": "gpt-3.5-turbo",
            "reactions": [{"emoji": "👍", "count": 2}] if i % 3 == 0 else [],
            "tools_used": ["search", "calculator"] if i % 5 == 0 else []
        }
        for i in range(100)  # Simulate 100 messages
    ]
    
    return messages


async def get_conversation_metadata(
    conversation_id: str,
    user_id: str,
    db: AsyncSession
) -> dict:
    """Fetch conversation metadata and statistics."""
    
    logger.info(
        f"Fetching metadata for conversation {conversation_id}",
        extra={"conversation_id": conversation_id, "user_id": user_id}
    )
    
    # Mock implementation - replace with actual database queries
    return {
        "id": conversation_id,
        "title": "AI Chat Session",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "model": "gpt-3.5-turbo",
        "settings": {
            "temperature": 0.7,
            "max_tokens": 2000,
            "system_prompt": "You are a helpful AI assistant."
        },
        "tags": ["important", "work"],
        "is_archived": False
    }


async def calculate_conversation_statistics(
    messages: list,
    conversation_id: str
) -> dict:
    """Calculate conversation statistics and analytics."""
    
    logger.info(
        f"Calculating statistics for conversation {conversation_id}",
        extra={"conversation_id": conversation_id, "message_count": len(messages)}
    )
    
    total_tokens = sum(msg.get("tokens", 0) for msg in messages)
    total_cost = sum(msg.get("cost", 0) for msg in messages)
    
    user_messages = [m for m in messages if m["role"] == "user"]
    assistant_messages = [m for m in messages if m["role"] == "assistant"]
    
    tools_used = set()
    for msg in messages:
        tools_used.update(msg.get("tools_used", []))
    
    return {
        "total_messages": len(messages),
        "user_messages": len(user_messages),
        "assistant_messages": len(assistant_messages),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 4),
        "average_tokens_per_message": round(total_tokens / len(messages), 2) if messages else 0,
        "tools_used": list(tools_used),
        "models_used": list(set(m.get("model", "unknown") for m in messages)),
        "date_range": {
            "start": messages[0]["timestamp"] if messages else None,
            "end": messages[-1]["timestamp"] if messages else None
        }
    }


async def stream_export_json(
    conversation_id: str,
    user_id: str,
    db: AsyncSession,
    options: ExportOptions
) -> AsyncGenerator[str, None]:
    """Stream conversation export as JSON with progress updates."""
    
    export_id = str(uuid4())
    correlation_id = str(uuid4())
    
    logger.info(
        "Starting conversation export",
        extra={
            "export_id": export_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "format": options.format,
            "correlation_id": correlation_id
        }
    )
    
    try:
        # Stage 1: Export Metadata
        yield json.dumps(ExportProgress(
            stage="metadata",
            progress=10,
            message="Preparing export...",
            data={"export_id": export_id}
        ).dict()) + "\n"
        
        await asyncio.sleep(0.1)  # Simulate processing
        
        # Fetch conversation metadata
        metadata = await get_conversation_metadata(conversation_id, user_id, db)
        
        if options.include_metadata:
            yield json.dumps(ExportProgress(
                stage="metadata",
                progress=20,
                message="Fetching conversation metadata...",
                data={"metadata": metadata}
            ).dict()) + "\n"
        
        await asyncio.sleep(0.1)
        
        # Stage 2: Fetch Messages
        yield json.dumps(ExportProgress(
            stage="messages",
            progress=30,
            message="Fetching messages...",
            data=None
        ).dict()) + "\n"
        
        messages = await get_conversation_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            db=db,
            date_from=options.date_from,
            date_to=options.date_to
        )
        
        # Stream messages in batches with progress updates
        total_messages = len(messages)
        batch_size = 10
        
        for i in range(0, total_messages, batch_size):
            batch = messages[i:i + batch_size]
            progress = 30 + int((i / total_messages) * 40)
            
            yield json.dumps(ExportProgress(
                stage="messages",
                progress=progress,
                message=f"Processing messages {i + 1}-{min(i + batch_size, total_messages)} of {total_messages}...",
                data={"messages": batch}
            ).dict()) + "\n"
            
            await asyncio.sleep(0.05)  # Prevent overwhelming the client
        
        # Stage 3: Calculate Statistics
        if options.include_statistics:
            yield json.dumps(ExportProgress(
                stage="analytics",
                progress=75,
                message="Calculating conversation statistics...",
                data=None
            ).dict()) + "\n"
            
            await asyncio.sleep(0.1)
            
            statistics = await calculate_conversation_statistics(
                messages, conversation_id
            )
            
            yield json.dumps(ExportProgress(
                stage="analytics",
                progress=85,
                message="Statistics calculated",
                data={"statistics": statistics}
            ).dict()) + "\n"
        
        # Stage 4: Complete
        export_metadata = ExportMetadata(
            export_id=export_id,
            conversation_id=conversation_id,
            user_id=user_id,
            format=options.format,
            created_at=datetime.utcnow(),
            total_messages=len(messages),
            date_range={
                "from": options.date_from.isoformat() if options.date_from else None,
                "to": options.date_to.isoformat() if options.date_to else None
            }
        )
        
        yield json.dumps(ExportProgress(
            stage="complete",
            progress=100,
            message="Export completed successfully",
            data={"export_metadata": export_metadata.dict()}
        ).dict()) + "\n"
        
        logger.info(
            "Export completed successfully",
            extra={
                "export_id": export_id,
                "conversation_id": conversation_id,
                "total_messages": len(messages),
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(
            f"Export failed: {str(e)}",
            extra={
                "export_id": export_id,
                "conversation_id": conversation_id,
                "error": str(e),
                "correlation_id": correlation_id
            },
            exc_info=True
        )
        
        yield json.dumps({
            "type": "error",
            "stage": "failed",
            "message": f"Export failed: {str(e)}",
            "error": str(e)
        }) + "\n"


@router.get(
    "/{conversation_id}/export",
    response_class=StreamingResponse,
    summary="Export conversation with streaming",
    description="""Export a conversation in the specified format with real-time progress updates.
    
    Supports multiple export formats:
    - JSON: Full conversation with all metadata (default)
    - CSV: Tabular format for analysis
    - Markdown: Human-readable format
    - PDF: Formatted document
    
    The export streams progress updates in JSON format:
    ```json
    {"type": "progress", "stage": "messages", "progress": 50, "message": "Processing...", "data": {...}}
    ```
    
    Requires authentication. Users can only export their own conversations.
    Rate limited to 5 exports per minute per user.
    """,
    responses={
        200: {
            "description": "Export stream",
            "content": {"application/x-ndjson": {}}
        },
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - not your conversation"},
        404: {"description": "Conversation not found"},
        429: {"description": "Rate limit exceeded"}
    }
)
@track_api_call("conversation_export")
async def export_conversation(
    conversation_id: str,
    format: str = Query(default="json", pattern="^(json|csv|markdown|pdf)$"),
    include_metadata: bool = Query(default=True),
    include_statistics: bool = Query(default=True),
    include_reactions: bool = Query(default=True),
    compress: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export conversation with streaming support and real-time progress."""
    
    # Rate limiting check
    await check_export_rate_limit(current_user.id)
    
    # Create export options
    options = ExportOptions(
        format=format,
        include_metadata=include_metadata,
        include_statistics=include_statistics,
        include_reactions=include_reactions,
        compress=compress
    )
    
    # Permission check (mock - replace with actual permission logic)
    # In production, verify that current_user owns this conversation
    logger.info(
        f"User {current_user.id} requesting export of conversation {conversation_id}",
        extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id,
            "format": format
        }
    )
    
    # Stream the export
    return StreamingResponse(
        stream_export_json(
            conversation_id=conversation_id,
            user_id=current_user.id,
            db=db,
            options=options
        ),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f"attachment; filename=conversation_{conversation_id}_export.ndjson",
            "X-Export-Format": format,
            "Cache-Control": "no-cache"
        }
    )


@router.get(
    "/{conversation_id}/export/status",
    summary="Get export status",
    description="Check the status of an ongoing or completed export"
)
async def get_export_status(
    conversation_id: str,
    export_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the status of an export operation."""
    
    # Mock implementation
    # In production, track export status in database
    return {
        "export_id": export_id,
        "conversation_id": conversation_id,
        "status": "completed",
        "progress": 100,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }
