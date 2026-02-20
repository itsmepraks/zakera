"""Conversation export API routes with streaming support."""
import asyncio
import json
import csv
import io
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from ..database import get_db
from ..auth import get_current_user
from ..models import User, Conversation, Message
from ..schemas.export import ExportFormat, ExportOptions, ExportProgress
from ..services.export_service import ExportService
from ...monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["exports"])


class ExportRequest(BaseModel):
    """Request model for conversation export."""
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Export format (json, markdown, csv)"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include metadata (timestamps, token counts, costs)"
    )
    include_system_messages: bool = Field(
        default=False,
        description="Include system messages in export"
    )
    compress: bool = Field(
        default=False,
        description="Compress export with gzip"
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Filter messages from this date"
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="Filter messages until this date"
    )


class ExportResponse(BaseModel):
    """Response model for export status."""
    export_id: str
    status: str
    total_messages: int
    processed_messages: int
    progress_percentage: float
    estimated_time_remaining: Optional[float] = None
    error: Optional[str] = None


@router.post(
    "/{conversation_id}/export",
    response_class=StreamingResponse,
    summary="Export conversation with streaming",
    description="""
    Stream conversation data in real-time with progress updates.
    
    Supports multiple formats:
    - JSON: Full structured data with metadata
    - Markdown: Human-readable chat transcript
    - CSV: Tabular format for analysis
    
    Features:
    - Real-time progress updates via SSE
    - Chunked streaming for memory efficiency
    - Optional compression for large exports
    - Filtering by date range
    - Metadata inclusion (tokens, costs, timestamps)
    
    Returns a stream of Server-Sent Events with:
    - Progress updates
    - Data chunks
    - Completion status
    - Error information if applicable
    """,
)
async def export_conversation(
    conversation_id: int,
    export_request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a conversation with real-time streaming."""
    
    # Record export request metrics
    metrics_collector.increment_counter(
        "conversation_exports_total",
        labels={"format": export_request.format.value, "user": current_user.username}
    )
    
    try:
        # Verify conversation exists and user has access
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation {conversation_id} not found or access denied"
            )
        
        # Initialize export service
        export_service = ExportService(db, current_user)
        
        # Create async generator for streaming
        async def generate_export_stream() -> AsyncGenerator[str, None]:
            """Generate SSE stream with export data and progress."""
            try:
                export_id = f"export_{conversation_id}_{datetime.utcnow().timestamp()}"
                
                # Send initial status
                yield f"data: {json.dumps({'type': 'status', 'export_id': export_id, 'status': 'started'})}\n\n"
                
                # Stream export with progress
                async for chunk in export_service.export_conversation_stream(
                    conversation=conversation,
                    options=ExportOptions(
                        format=export_request.format,
                        include_metadata=export_request.include_metadata,
                        include_system_messages=export_request.include_system_messages,
                        compress=export_request.compress,
                        date_from=export_request.date_from,
                        date_to=export_request.date_to,
                    )
                ):
                    if chunk["type"] == "progress":
                        # Send progress update
                        yield f"data: {json.dumps(chunk)}\n\n"
                        await asyncio.sleep(0)  # Allow other tasks to run
                    
                    elif chunk["type"] == "data":
                        # Send data chunk
                        yield f"data: {json.dumps(chunk)}\n\n"
                    
                    elif chunk["type"] == "complete":
                        # Send completion status
                        yield f"data: {json.dumps(chunk)}\n\n"
                        logger.info(f"Export {export_id} completed successfully")
                
                # Record successful export
                metrics_collector.increment_counter(
                    "conversation_exports_successful",
                    labels={"format": export_request.format.value}
                )
                
            except Exception as e:
                logger.error(f"Export error: {str(e)}", exc_info=True)
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                
                # Record failed export
                metrics_collector.increment_counter(
                    "conversation_exports_failed",
                    labels={"format": export_request.format.value, "error": type(e).__name__}
                )
        
        # Return streaming response with SSE
        return StreamingResponse(
            generate_export_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in export endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.get(
    "/{conversation_id}/export/status/{export_id}",
    response_model=ExportResponse,
    summary="Get export status",
)
async def get_export_status(
    conversation_id: int,
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the status of an ongoing or completed export."""
    export_service = ExportService(db, current_user)
    status = await export_service.get_export_status(export_id)
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Export {export_id} not found"
        )
    
    return status


@router.get(
    "/exports/history",
    summary="Get export history",
    description="Retrieve history of conversation exports for the current user",
)
async def get_export_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get export history for the current user."""
    export_service = ExportService(db, current_user)
    history = await export_service.get_export_history(limit=limit, offset=offset)
    
    return {
        "total": len(history),
        "limit": limit,
        "offset": offset,
        "exports": history
    }


@router.delete(
    "/exports/{export_id}",
    summary="Delete export record",
)
async def delete_export(
    export_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an export record and associated data."""
    export_service = ExportService(db, current_user)
    success = await export_service.delete_export(export_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Export {export_id} not found"
        )
    
    return {"message": "Export deleted successfully", "export_id": export_id}
