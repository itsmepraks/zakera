"""Pydantic schemas for conversation export functionality."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"
    HTML = "html"


class ExportOptions(BaseModel):
    """Configuration options for export."""
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Output format for the export"
    )
    include_metadata: bool = Field(
        default=True,
        description="Include message metadata (timestamps, tokens, costs)"
    )
    include_system_messages: bool = Field(
        default=False,
        description="Include system-level messages"
    )
    compress: bool = Field(
        default=False,
        description="Apply gzip compression"
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Export messages from this date onwards"
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="Export messages up to this date"
    )
    
    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Validate that date_to is after date_from."""
        if v and values.get('date_from') and v < values['date_from']:
            raise ValueError('date_to must be after date_from')
        return v


class MessageExport(BaseModel):
    """Schema for exported message."""
    id: int
    role: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class ConversationExport(BaseModel):
    """Schema for exported conversation."""
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int
    messages: List[MessageExport]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        orm_mode = True


class ExportProgress(BaseModel):
    """Progress information for an ongoing export."""
    type: str = "progress"
    export_id: str
    total_messages: int
    processed_messages: int
    progress_percentage: float
    current_message_id: Optional[int] = None
    estimated_time_remaining: Optional[float] = None
    
    @validator('progress_percentage')
    def validate_percentage(cls, v):
        """Ensure percentage is between 0 and 100."""
        return max(0.0, min(100.0, v))


class ExportDataChunk(BaseModel):
    """Data chunk in streaming export."""
    type: str = "data"
    chunk_index: int
    data: Any
    is_final: bool = False


class ExportComplete(BaseModel):
    """Export completion information."""
    type: str = "complete"
    export_id: str
    total_messages: int
    total_size_bytes: int
    duration_seconds: float
    format: ExportFormat
    compressed: bool
    checksum: Optional[str] = None


class ExportError(BaseModel):
    """Export error information."""
    type: str = "error"
    error: str
    error_type: str
    export_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExportHistoryItem(BaseModel):
    """Historical export record."""
    export_id: str
    conversation_id: int
    format: ExportFormat
    created_at: datetime
    status: str
    size_bytes: Optional[int] = None
    message_count: int
    error: Optional[str] = None
