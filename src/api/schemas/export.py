"""Pydantic schemas for the conversation export system.

Used by both the route layer (request/response validation) and the
service layer (progress event construction).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExportFormat(str, Enum):
    """Supported export formats.

    HTML is intentionally excluded; the service only renders JSON,
    Markdown, and CSV so callers receive a clear validation error if
    they pass an unsupported format.
    """

    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ExportOptions(BaseModel):
    """Configuration options for a single-conversation export."""

    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Output format: json | markdown | csv",
    )
    include_metadata: bool = Field(
        default=True,
        description="Include per-message token counts, costs, and model name",
    )
    include_system_messages: bool = Field(
        default=False,
        description="Include system-role messages in the export",
    )
    compress: bool = Field(
        default=False,
        description="gzip-compress data chunks before streaming",
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Only include messages created on or after this UTC datetime",
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="Only include messages created on or before this UTC datetime",
    )

    @model_validator(mode="after")
    def _validate_date_range(self) -> "ExportOptions":
        """Ensure date_to is not before date_from."""
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("'date_to' must be equal to or later than 'date_from'")
        return self


class BulkExportRequest(BaseModel):
    """Request body for the bulk-export endpoint."""

    conversation_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of conversation UUIDs to export (max 50)",
    )
    options: ExportOptions = Field(
        default_factory=ExportOptions,
        description="Export options applied to every conversation in the batch",
    )
    page_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="How many conversations to process per progress page",
    )

    @field_validator("conversation_ids")
    @classmethod
    def _deduplicate_ids(cls, v: List[str]) -> List[str]:
        """Remove duplicate IDs while preserving order."""
        seen: set[str] = set()
        deduped: list[str] = []
        for cid in v:
            if cid not in seen:
                seen.add(cid)
                deduped.append(cid)
        return deduped


# ---------------------------------------------------------------------------
# Streaming event schemas  (yielded as NDJSON lines)
# ---------------------------------------------------------------------------


class ExportProgress(BaseModel):
    """Progress update emitted while messages are being processed."""

    type: str = "progress"
    export_id: str
    total_messages: int
    processed_messages: int
    progress_percentage: float
    current_message_id: Optional[str] = None
    estimated_time_remaining: Optional[float] = None

    @field_validator("progress_percentage")
    @classmethod
    def _clamp_pct(cls, v: float) -> float:
        return max(0.0, min(100.0, v))


class ExportDataChunk(BaseModel):
    """A chunk of export data."""

    type: str = "data"
    export_id: str
    chunk_index: int
    data: Any
    is_final: bool = False


class ExportComplete(BaseModel):
    """Final event emitted when an export finishes successfully."""

    type: str = "complete"
    export_id: str
    total_messages: int
    total_size_bytes: int
    duration_seconds: float
    format: ExportFormat
    compressed: bool
    checksum: Optional[str] = None


class ExportError(BaseModel):
    """Error event emitted when an export fails."""

    type: str = "error"
    export_id: Optional[str] = None
    detail: str
    error_type: str = "ExportError"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# History / status schemas
# ---------------------------------------------------------------------------


class ExportHistoryItem(BaseModel):
    """Record of a past export, returned by the history endpoint."""

    export_id: str
    conversation_id: str
    format: ExportFormat
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # pending | processing | completed | failed
    total_messages: int = 0
    size_bytes: Optional[int] = None
    error: Optional[str] = None


class BulkExportResponse(BaseModel):
    """Synchronous acknowledgement returned before the stream begins.

    In the streaming path this is not used directly; it is kept here as
    documentation of the final ``bulk_complete`` event shape.
    """

    export_id: str
    total_conversations: int
    total_messages: int
    duration_seconds: float
    format: ExportFormat


# ---------------------------------------------------------------------------
# Legacy aliases kept for backwards compatibility
# ---------------------------------------------------------------------------

class MessageExport(BaseModel):
    """Schema for a single exported message (used in JSON format)."""

    id: str
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class ConversationExport(BaseModel):
    """Schema for a full exported conversation (used in JSON format)."""

    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    messages: List[MessageExport]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}
