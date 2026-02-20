"""Service for handling conversation exports with streaming support."""
import asyncio
import json
import gzip
import hashlib
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

from ..models import User, Conversation, Message
from ..schemas.export import (
    ExportOptions,
    ExportFormat,
    ExportProgress,
    ExportDataChunk,
    ExportComplete,
    MessageExport,
    ConversationExport,
    ExportHistoryItem,
)

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting conversations in various formats."""
    
    # In-memory cache for export status (in production, use Redis)
    _export_status: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, db: Session, user: User):
        """Initialize export service."""
        self.db = db
        self.user = user
        self.chunk_size = 50  # Messages per chunk
    
    async def export_conversation_stream(
        self,
        conversation: Conversation,
        options: ExportOptions,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream conversation export with progress updates."""
        export_id = f"export_{conversation.id}_{datetime.utcnow().timestamp()}"
        start_time = datetime.utcnow()
        total_size = 0
        
        try:
            # Initialize export status
            self._export_status[export_id] = {
                "status": "processing",
                "started_at": start_time,
                "conversation_id": conversation.id,
            }
            
            # Query messages with filters
            query = self.db.query(Message).filter(
                Message.conversation_id == conversation.id
            )
            
            # Apply date filters
            if options.date_from:
                query = query.filter(Message.created_at >= options.date_from)
            if options.date_to:
                query = query.filter(Message.created_at <= options.date_to)
            
            # Optionally filter out system messages
            if not options.include_system_messages:
                query = query.filter(Message.role != "system")
            
            # Get total count for progress tracking
            total_messages = query.count()
            messages = query.order_by(Message.created_at.asc()).all()
            
            # Generate export based on format
            if options.format == ExportFormat.JSON:
                async for chunk in self._export_json(
                    conversation, messages, options, export_id, total_messages
                ):
                    if chunk["type"] == "data":
                        total_size += len(json.dumps(chunk["data"]))
                    yield chunk
            
            elif options.format == ExportFormat.MARKDOWN:
                async for chunk in self._export_markdown(
                    conversation, messages, options, export_id, total_messages
                ):
                    if chunk["type"] == "data":
                        total_size += len(chunk["data"])
                    yield chunk
            
            elif options.format == ExportFormat.CSV:
                async for chunk in self._export_csv(
                    conversation, messages, options, export_id, total_messages
                ):
                    if chunk["type"] == "data":
                        total_size += len(chunk["data"])
                    yield chunk
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Send completion
            completion = ExportComplete(
                export_id=export_id,
                total_messages=total_messages,
                total_size_bytes=total_size,
                duration_seconds=duration,
                format=options.format,
                compressed=options.compress,
            )
            
            yield completion.dict()
            
            # Update export status
            self._export_status[export_id]["status"] = "completed"
            self._export_status[export_id]["completed_at"] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Export {export_id} failed: {str(e)}", exc_info=True)
            self._export_status[export_id]["status"] = "failed"
            self._export_status[export_id]["error"] = str(e)
            raise
    
    async def _export_json(
        self,
        conversation: Conversation,
        messages: List[Message],
        options: ExportOptions,
        export_id: str,
        total_messages: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Export conversation as JSON with streaming."""
        processed = 0
        
        # Send header
        header = {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.isoformat(),
            "total_messages": total_messages,
            "export_options": options.dict(exclude={"date_from", "date_to"}),
        }
        
        yield {"type": "data", "chunk_index": 0, "data": {"header": header}}
        
        # Stream messages in chunks
        for i in range(0, len(messages), self.chunk_size):
            chunk = messages[i:i + self.chunk_size]
            
            # Convert messages to export format
            message_exports = []
            for msg in chunk:
                msg_data = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                }
                
                if options.include_metadata:
                    msg_data["metadata"] = {
                        "tokens": getattr(msg, "tokens", None),
                        "model": getattr(msg, "model", None),
                        "cost": getattr(msg, "cost", None),
                    }
                
                message_exports.append(msg_data)
                processed += 1
            
            # Send data chunk
            yield {
                "type": "data",
                "chunk_index": (i // self.chunk_size) + 1,
                "data": {"messages": message_exports},
            }
            
            # Send progress update
            progress = ExportProgress(
                export_id=export_id,
                total_messages=total_messages,
                processed_messages=processed,
                progress_percentage=(processed / total_messages) * 100,
            )
            yield progress.dict()
            
            # Yield control to allow other tasks
            await asyncio.sleep(0)
    
    async def _export_markdown(
        self,
        conversation: Conversation,
        messages: List[Message],
        options: ExportOptions,
        export_id: str,
        total_messages: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Export conversation as Markdown."""
        processed = 0
        
        # Send header
        header = f"# {conversation.title or 'Conversation'}\n\n"
        header += f"**Created:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"**Messages:** {total_messages}\n\n"
        header += "---\n\n"
        
        yield {"type": "data", "chunk_index": 0, "data": header}
        
        # Stream messages
        for i, msg in enumerate(messages):
            # Format message
            role_emoji = "🤖" if msg.role == "assistant" else "👤"
            timestamp = msg.created_at.strftime('%H:%M:%S')
            
            md_message = f"### {role_emoji} {msg.role.title()} ({timestamp})\n\n"
            md_message += f"{msg.content}\n\n"
            
            if options.include_metadata:
                md_message += f"*Tokens: {getattr(msg, 'tokens', 'N/A')} | "
                md_message += f"Model: {getattr(msg, 'model', 'N/A')}*\n\n"
            
            md_message += "---\n\n"
            
            yield {
                "type": "data",
                "chunk_index": i + 1,
                "data": md_message,
            }
            
            processed += 1
            
            # Send progress every 10 messages
            if processed % 10 == 0:
                progress = ExportProgress(
                    export_id=export_id,
                    total_messages=total_messages,
                    processed_messages=processed,
                    progress_percentage=(processed / total_messages) * 100,
                )
                yield progress.dict()
            
            await asyncio.sleep(0)
    
    async def _export_csv(
        self,
        conversation: Conversation,
        messages: List[Message],
        options: ExportOptions,
        export_id: str,
        total_messages: int,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Export conversation as CSV."""
        processed = 0
        
        # Send CSV header
        header = "id,role,content,timestamp"
        if options.include_metadata:
            header += ",tokens,model,cost"
        header += "\n"
        
        yield {"type": "data", "chunk_index": 0, "data": header}
        
        # Stream messages
        for i, msg in enumerate(messages):
            # Escape content for CSV
            content = msg.content.replace('"', '""')
            
            row = f"{msg.id},{msg.role},\"{content}\",{msg.created_at.isoformat()}"
            
            if options.include_metadata:
                tokens = getattr(msg, 'tokens', '')
                model = getattr(msg, 'model', '')
                cost = getattr(msg, 'cost', '')
                row += f",{tokens},{model},{cost}"
            
            row += "\n"
            
            yield {
                "type": "data",
                "chunk_index": i + 1,
                "data": row,
            }
            
            processed += 1
            
            # Send progress every 10 messages
            if processed % 10 == 0:
                progress = ExportProgress(
                    export_id=export_id,
                    total_messages=total_messages,
                    processed_messages=processed,
                    progress_percentage=(processed / total_messages) * 100,
                )
                yield progress.dict()
            
            await asyncio.sleep(0)
    
    async def get_export_status(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an export."""
        return self._export_status.get(export_id)
    
    async def get_export_history(
        self, limit: int = 50, offset: int = 0
    ) -> List[ExportHistoryItem]:
        """Get export history for the user."""
        # In production, query from database
        # For now, return from in-memory cache
        user_exports = [
            {
                "export_id": export_id,
                "conversation_id": data["conversation_id"],
                "created_at": data["started_at"],
                "status": data["status"],
                "message_count": 0,  # Would be stored in DB
            }
            for export_id, data in self._export_status.items()
        ]
        
        return user_exports[offset:offset + limit]
    
    async def delete_export(self, export_id: str) -> bool:
        """Delete an export record."""
        if export_id in self._export_status:
            del self._export_status[export_id]
            return True
        return False
