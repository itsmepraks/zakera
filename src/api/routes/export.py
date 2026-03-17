"""Conversation export routes.

Exposes two endpoints consumed by the frontend export dialog:

  GET  /api/v1/export/conversations/{conversation_id}
       Stream a single conversation in the requested format.

  POST /api/v1/export/conversations/bulk
       Stream multiple conversations in a single NDJSON response,
       with per-page progress events for the UI progress-bar.

Both endpoints:
  - Require a valid JWT (``get_current_active_user`` dependency).
  - Verify the requesting user owns every conversation_id supplied.
  - Apply optional date-range filters from query params / body.
  - Honour the ``compress`` flag (gzip the payload before streaming).
  - Enforce a per-user rate-limit of 10 exports/minute stored in a
    simple in-process dict (replace with Redis in production).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Conversation, User
from ..schemas.export import BulkExportRequest, ExportFormat, ExportOptions
from ..services.export_service import ExportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])

# ---------------------------------------------------------------------------
# Per-user rate limiting (in-process; swap for Redis in production)
# ---------------------------------------------------------------------------

_RATE_LIMIT = 10  # max exports per rolling window
_RATE_WINDOW = timedelta(minutes=1)
_export_log: dict[str, list[datetime]] = {}  # user_id -> [timestamp, ...]


def _check_rate_limit(user_id: str) -> None:
    """Raise HTTP 429 if the user has exceeded the export rate limit."""
    now = datetime.utcnow()
    cutoff = now - _RATE_WINDOW
    timestamps = _export_log.get(user_id, [])
    # Prune old entries
    timestamps = [t for t in timestamps if t > cutoff]
    if len(timestamps) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Export rate limit exceeded. "
                f"Max {_RATE_LIMIT} exports per minute per user."
            ),
        )
    timestamps.append(now)
    _export_log[user_id] = timestamps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_conversation_or_404(
    conversation_id: str,
    user_id: str,
    db: Session,
) -> Conversation:
    """Fetch a conversation and verify ownership; raise 404 otherwise."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.is_deleted.is_(False),
        )
        .first()
    )
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return conv


# ---------------------------------------------------------------------------
# Single-conversation export
# ---------------------------------------------------------------------------

@router.get(
    "/conversations/{conversation_id}",
    summary="Export a single conversation",
    description=(
        "Stream the conversation as NDJSON progress events followed by the "
        "formatted payload in the requested format (json | markdown | csv)."
    ),
    responses={
        200: {"description": "NDJSON stream", "content": {"application/x-ndjson": {}}},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Conversation not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def export_single_conversation(
    conversation_id: str,
    fmt: ExportFormat = Query(
        default=ExportFormat.JSON,
        alias="format",
        description="Output format: json | markdown | csv",
    ),
    include_metadata: bool = Query(True, description="Embed token/cost metadata per message"),
    include_system_messages: bool = Query(False, description="Include system-role messages"),
    compress: bool = Query(False, description="gzip-compress the exported payload"),
    date_from: Optional[datetime] = Query(None, description="Only include messages on/after this UTC datetime"),
    date_to: Optional[datetime] = Query(None, description="Only include messages on/before this UTC datetime"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream a single conversation export with real-time progress."""
    _check_rate_limit(current_user.id)

    conversation = _get_conversation_or_404(conversation_id, current_user.id, db)

    options = ExportOptions(
        format=fmt,
        include_metadata=include_metadata,
        include_system_messages=include_system_messages,
        compress=compress,
        date_from=date_from,
        date_to=date_to,
    )

    service = ExportService(db=db, user=current_user)

    logger.info(
        "Single export requested",
        extra={
            "user_id": current_user.id,
            "conversation_id": conversation_id,
            "format": fmt.value,
            "compress": compress,
        },
    )

    media_type_map = {
        ExportFormat.JSON: "application/json",
        ExportFormat.MARKDOWN: "text/markdown",
        ExportFormat.CSV: "text/csv",
    }
    extension_map = {
        ExportFormat.JSON: "json",
        ExportFormat.MARKDOWN: "md",
        ExportFormat.CSV: "csv",
    }
    ext = extension_map[fmt]
    filename = (
        f"conversation_{conversation_id[:8]}_"
        f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
    )
    if compress:
        filename += ".gz"

    return StreamingResponse(
        service.stream_export(conversation=conversation, options=options),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Format": fmt.value,
            "X-Conversation-Id": conversation_id,
            "Cache-Control": "no-store",
        },
    )


# ---------------------------------------------------------------------------
# Bulk export
# ---------------------------------------------------------------------------

@router.post(
    "/conversations/bulk",
    summary="Bulk-export multiple conversations",
    description=(
        "Export several conversations in one streamed response.  The body "
        "specifies the conversation IDs and export options.  Progress events "
        "are emitted for each conversation so the UI can display a progress bar."
    ),
    responses={
        200: {"description": "NDJSON stream", "content": {"application/x-ndjson": {}}},
        400: {"description": "Invalid request (e.g. too many IDs)"},
        401: {"description": "Not authenticated"},
        404: {"description": "One or more conversations not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def bulk_export_conversations(
    body: BulkExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream a paginated bulk export for a list of conversation IDs."""
    _check_rate_limit(current_user.id)

    if len(body.conversation_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bulk export is limited to 50 conversations per request.",
        )

    # Verify ownership of every requested conversation up front so we fail
    # fast with a 404 rather than discovering missing IDs mid-stream.
    conversations: list[Conversation] = []
    for cid in body.conversation_ids:
        conversations.append(_get_conversation_or_404(cid, current_user.id, db))

    service = ExportService(db=db, user=current_user)

    logger.info(
        "Bulk export requested",
        extra={
            "user_id": current_user.id,
            "count": len(conversations),
            "format": body.options.format.value,
        },
    )

    return StreamingResponse(
        service.stream_bulk_export(
            conversations=conversations,
            options=body.options,
            page_size=body.page_size,
        ),
        media_type="application/x-ndjson",
        headers={
            "X-Export-Format": body.options.format.value,
            "X-Conversation-Count": str(len(conversations)),
            "Cache-Control": "no-store",
        },
    )
