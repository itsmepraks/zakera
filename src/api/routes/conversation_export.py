"""
Conversation Export API Routes

This module provides streaming export functionality for conversations,
allowing users to export their conversation history in various formats
with real-time progress updates.

Author: Prakriti Bista
Created: 2026-02-19
"""

import json
import csv
import io
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.api.database import get_db
from src.api.auth import get_current_user
from src.api.models import User, Conversation, Message, ToolExecution
from src.monitoring.metrics import (
    export_requests_total,
    export_duration_seconds,
    export_errors_total,
    export_messages_total,
)
from src.monitoring.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class ConversationExporter:
    """Handle conversation export with streaming and progress updates."""

    def __init__(
        self,
        conversation_id: int,
        user_id: int,
        format: str,
        include_metadata: bool,
        include_tools: bool,
        batch_size: int,
    ):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.format = format
        self.include_metadata = include_metadata
        self.include_tools = include_tools
        self.batch_size = batch_size
        self.total_messages = 0
        self.processed_messages = 0

    async def validate_conversation(self, db: AsyncSession) -> Conversation:
        """Validate conversation exists and user has access."""
        query = (
            select(Conversation)
            .where(Conversation.id == self.conversation_id)
            .where(Conversation.user_id == self.user_id)
        )
        result = await db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {self.conversation_id} not found or access denied",
            )

        return conversation

    async def get_total_messages(self, db: AsyncSession) -> int:
        """Get total message count for progress calculation."""
        query = select(func.count(Message.id)).where(
            Message.conversation_id == self.conversation_id
        )
        result = await db.execute(query)
        return result.scalar() or 0

    async def get_messages_batch(
        self, db: AsyncSession, offset: int, limit: int
    ) -> List[Message]:
        """Fetch messages in batches with optional tool execution data."""
        query = (
            select(Message)
            .where(Message.conversation_id == self.conversation_id)
            .order_by(Message.created_at)
            .offset(offset)
            .limit(limit)
        )

        if self.include_tools:
            query = query.options(selectinload(Message.tool_executions))

        result = await db.execute(query)
        return list(result.scalars().all())

    def format_message_json(self, message: Message) -> Dict[str, Any]:
        """Format message as JSON object."""
        data = {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
        }

        if self.include_metadata:
            data.update(
                {
                    "model": message.model_name,
                    "tokens": message.token_count,
                    "cost": float(message.cost) if message.cost else None,
                    "latency_ms": message.latency_ms,
                    "provider": message.provider,
                }
            )

        if self.include_tools and hasattr(message, "tool_executions"):
            data["tools_used"] = [
                {
                    "tool_name": tool.tool_name,
                    "status": tool.status,
                    "execution_time_ms": tool.execution_time_ms,
                    "result": tool.result,
                }
                for tool in message.tool_executions
            ]

        return data

    def format_message_markdown(self, message: Message) -> str:
        """Format message as Markdown."""
        lines = [
            f"### {message.role.upper()} - {message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            message.content,
            "",
        ]

        if self.include_metadata:
            lines.extend(
                [
                    f"**Model:** {message.model_name}",
                    f"**Tokens:** {message.token_count}",
                    f"**Cost:** ${message.cost or 0:.4f}",
                    "",
                ]
            )

        if self.include_tools and hasattr(message, "tool_executions"):
            if message.tool_executions:
                lines.append("**Tools Used:**")
                for tool in message.tool_executions:
                    lines.append(f"- {tool.tool_name} ({tool.status})")
                lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    def format_message_text(self, message: Message) -> str:
        """Format message as plain text."""
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] {message.role.upper()}: {message.content}\n\n"

    def format_message_csv_row(self, message: Message) -> Dict[str, Any]:
        """Format message as CSV row."""
        row = {
            "id": message.id,
            "timestamp": message.created_at.isoformat(),
            "role": message.role,
            "content": message.content.replace("\n", " "),
        }

        if self.include_metadata:
            row.update(
                {
                    "model": message.model_name,
                    "tokens": message.token_count,
                    "cost": message.cost or 0,
                    "latency_ms": message.latency_ms,
                }
            )

        return row

    async def stream_json(
        self, db: AsyncSession, conversation: Conversation
    ) -> AsyncGenerator[str, None]:
        """Stream conversation as JSON with progress updates."""
        # Send initial metadata
        yield json.dumps(
            {
                "type": "metadata",
                "conversation_id": self.conversation_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "total_messages": self.total_messages,
            }
        ) + "\n"

        # Stream messages in batches
        offset = 0
        messages_data = []

        while offset < self.total_messages:
            messages = await self.get_messages_batch(db, offset, self.batch_size)

            for message in messages:
                messages_data.append(self.format_message_json(message))
                self.processed_messages += 1

                # Send progress update every 10 messages
                if self.processed_messages % 10 == 0:
                    progress = (self.processed_messages / self.total_messages) * 100
                    yield json.dumps(
                        {
                            "type": "progress",
                            "processed": self.processed_messages,
                            "total": self.total_messages,
                            "percentage": round(progress, 2),
                        }
                    ) + "\n"

            offset += self.batch_size

        # Send final data
        yield json.dumps(
            {
                "type": "data",
                "messages": messages_data,
            }
        ) + "\n"

        # Send completion
        yield json.dumps(
            {
                "type": "complete",
                "total_messages": self.processed_messages,
            }
        ) + "\n"

    async def stream_markdown(
        self, db: AsyncSession, conversation: Conversation
    ) -> AsyncGenerator[str, None]:
        """Stream conversation as Markdown."""
        # Header
        yield f"# Conversation: {conversation.title}\n\n"
        yield f"**Created:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        yield f"**Total Messages:** {self.total_messages}\n\n"
        yield "---\n\n"

        # Stream messages
        offset = 0
        while offset < self.total_messages:
            messages = await self.get_messages_batch(db, offset, self.batch_size)

            for message in messages:
                yield self.format_message_markdown(message)
                self.processed_messages += 1

            offset += self.batch_size

    async def stream_text(
        self, db: AsyncSession, conversation: Conversation
    ) -> AsyncGenerator[str, None]:
        """Stream conversation as plain text."""
        # Header
        yield f"Conversation: {conversation.title}\n"
        yield f"Created: {conversation.created_at}\n"
        yield f"Total Messages: {self.total_messages}\n"
        yield "=" * 80 + "\n\n"

        # Stream messages
        offset = 0
        while offset < self.total_messages:
            messages = await self.get_messages_batch(db, offset, self.batch_size)

            for message in messages:
                yield self.format_message_text(message)
                self.processed_messages += 1

            offset += self.batch_size

    async def stream_csv(
        self, db: AsyncSession, conversation: Conversation
    ) -> AsyncGenerator[str, None]:
        """Stream conversation as CSV."""
        output = io.StringIO()
        fieldnames = ["id", "timestamp", "role", "content"]

        if self.include_metadata:
            fieldnames.extend(["model", "tokens", "cost", "latency_ms"])

        writer = csv.DictWriter(output, fieldnames=fieldnames)

        # Write header
        writer.writeheader()
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        # Stream messages
        offset = 0
        while offset < self.total_messages:
            messages = await self.get_messages_batch(db, offset, self.batch_size)

            for message in messages:
                writer.writerow(self.format_message_csv_row(message))
                self.processed_messages += 1

            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

            offset += self.batch_size

    async def export(self, db: AsyncSession) -> AsyncGenerator[str, None]:
        """Main export method that delegates to format-specific streamers."""
        start_time = datetime.utcnow()

        try:
            # Validate and get conversation
            conversation = await self.validate_conversation(db)
            self.total_messages = await self.get_total_messages(db)

            logger.info(
                f"Starting export for conversation {self.conversation_id}, "
                f"format={self.format}, messages={self.total_messages}",
                extra={
                    "conversation_id": self.conversation_id,
                    "user_id": self.user_id,
                    "format": self.format,
                    "total_messages": self.total_messages,
                },
            )

            # Stream based on format
            if self.format == "json":
                async for chunk in self.stream_json(db, conversation):
                    yield chunk
            elif self.format == "markdown":
                async for chunk in self.stream_markdown(db, conversation):
                    yield chunk
            elif self.format == "text":
                async for chunk in self.stream_text(db, conversation):
                    yield chunk
            elif self.format == "csv":
                async for chunk in self.stream_csv(db, conversation):
                    yield chunk

            # Record metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            export_requests_total.labels(format=self.format, status="success").inc()
            export_duration_seconds.labels(format=self.format).observe(duration)
            export_messages_total.labels(format=self.format).inc(self.processed_messages)

            logger.info(
                f"Export completed for conversation {self.conversation_id}, "
                f"processed {self.processed_messages} messages in {duration:.2f}s",
                extra={
                    "conversation_id": self.conversation_id,
                    "messages_processed": self.processed_messages,
                    "duration_seconds": duration,
                },
            )

        except HTTPException:
            export_errors_total.labels(format=self.format, error_type="not_found").inc()
            raise
        except Exception as e:
            export_errors_total.labels(format=self.format, error_type="internal").inc()
            logger.error(
                f"Export failed for conversation {self.conversation_id}: {str(e)}",
                extra={
                    "conversation_id": self.conversation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Export failed. Please try again later.",
            )


@router.get(
    "/{conversation_id}/export",
    summary="Export conversation with streaming",
    description="""
    Export a conversation in various formats with real-time progress updates.
    
    Supports streaming large conversations efficiently by processing messages
    in batches and providing progress updates.
    
    **Supported Formats:**
    - `json`: Structured JSON with full metadata (default)
    - `markdown`: Human-readable Markdown format
    - `text`: Plain text conversation log
    - `csv`: CSV format for data analysis
    
    **Features:**
    - Real-time progress updates for JSON format
    - Batch processing for memory efficiency
    - Optional metadata (tokens, costs, latency)
    - Optional tool execution results
    - Authenticated access with ownership validation
    
    **Example Usage:**
    ```bash
    # Export as JSON with metadata
    curl -H "Authorization: Bearer <token>" \\
         "http://localhost:8000/api/v1/conversations/123/export?format=json&include_metadata=true"
    
    # Export as Markdown
    curl -H "Authorization: Bearer <token>" \\
         "http://localhost:8000/api/v1/conversations/123/export?format=markdown" > conversation.md
    
    # Export as CSV for analysis
    curl -H "Authorization: Bearer <token>" \\
         "http://localhost:8000/api/v1/conversations/123/export?format=csv" > conversation.csv
    ```
    
    **Response Format (JSON):**
    The JSON format returns a stream of newline-delimited JSON objects:
    1. Metadata object with conversation details
    2. Progress objects during processing
    3. Data object with all messages
    4. Complete object marking end of stream
    """,
    responses={
        200: {
            "description": "Conversation exported successfully",
            "content": {
                "application/json": {
                    "example": {
                        "type": "metadata",
                        "conversation_id": 123,
                        "title": "AI Discussion",
                        "total_messages": 50
                    }
                }
            },
        },
        404: {"description": "Conversation not found or access denied"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Export failed"},
    },
)
async def export_conversation(
    conversation_id: int,
    format: str = Query(
        "json",
        description="Export format",
        regex="^(json|markdown|text|csv)$",
    ),
    include_metadata: bool = Query(
        True,
        description="Include message metadata (tokens, costs, latency)",
    ),
    include_tools: bool = Query(
        True,
        description="Include tool execution results",
    ),
    batch_size: int = Query(
        50,
        ge=10,
        le=500,
        description="Number of messages to process per batch",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export conversation with streaming support.
    
    This endpoint provides efficient export of conversation history with
    real-time progress updates and support for multiple formats.
    """
    exporter = ConversationExporter(
        conversation_id=conversation_id,
        user_id=current_user.id,
        format=format,
        include_metadata=include_metadata,
        include_tools=include_tools,
        batch_size=batch_size,
    )

    # Determine content type based on format
    content_types = {
        "json": "application/json",
        "markdown": "text/markdown",
        "text": "text/plain",
        "csv": "text/csv",
    }

    return StreamingResponse(
        exporter.export(db),
        media_type=content_types[format],
        headers={
            "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.{format}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        },
    )
