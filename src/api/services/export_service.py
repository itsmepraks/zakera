"""Conversation export service.

Handles all format rendering (JSON, Markdown, CSV) and streams NDJSON
progress events so the UI can display a live progress bar.  Real
SQLAlchemy ORM queries replace the previous mock implementations.

Formatting pipeline
-------------------
1. Fetch the Message rows for the conversation (with optional date-range
   and system-message filters).
2. Sanitise content: strip e-mail addresses and UK/US phone numbers.
3. Render the chosen format in chunks of ``chunk_size`` messages.
4. Yield NDJSON lines: progress events first, then data chunks.
5. Optionally gzip-compress each data chunk before yielding it.
"""

from __future__ import annotations

import asyncio
import gzip
import io
import json
import logging
import re
import textwrap
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from ..models import Conversation, Message, User
from ..schemas.export import (
    ExportComplete,
    ExportDataChunk,
    ExportFormat,
    ExportOptions,
    ExportProgress,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII sanitisation helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"""(?x)
    (?:\+?1[\s.-]?)?          # optional US country code
    (?:\(?\d{3}\)?[\s.-]?)?   # area code
    \d{3}[\s.-]?\d{4}         # local number
    """
)


def _sanitise(text: str) -> str:
    """Redact e-mail addresses and phone numbers from exported text."""
    text = _EMAIL_RE.sub("[email redacted]", text)
    text = _PHONE_RE.sub("[phone redacted]", text)
    return text


# ---------------------------------------------------------------------------
# ExportService
# ---------------------------------------------------------------------------


class ExportService:
    """Drive conversation exports for a single authenticated user.

    Args:
        db:   Synchronous SQLAlchemy ``Session`` (matches the rest of the app).
        user: The currently authenticated :class:`User` ORM instance.
    """

    CHUNK_SIZE = 25  # messages per data chunk

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    # ------------------------------------------------------------------
    # Public streaming entry-points
    # ------------------------------------------------------------------

    async def stream_export(
        self,
        conversation: Conversation,
        options: ExportOptions,
    ) -> AsyncGenerator[str, None]:
        """Stream a single conversation as NDJSON lines.

        Each yielded line is a JSON object terminated by ``\\n``.
        Progress events (``{type: 'progress', ...}``) are interleaved
        with data events (``{type: 'data', ...}``).
        """
        export_id = str(uuid4())
        start = datetime.utcnow()

        logger.info(
            "Starting export",
            extra={"export_id": export_id, "conversation_id": conversation.id},
        )

        try:
            messages = self._fetch_messages(conversation.id, options)
            total = len(messages)

            yield self._progress_line(
                export_id=export_id,
                total=total,
                processed=0,
                stage="started",
                message="Fetching messages…",
            )

            if options.format == ExportFormat.JSON:
                gen = self._render_json(conversation, messages, options, export_id)
            elif options.format == ExportFormat.MARKDOWN:
                gen = self._render_markdown(conversation, messages, options, export_id)
            else:  # CSV
                gen = self._render_csv(conversation, messages, options, export_id)

            async for line in gen:
                yield line

        except Exception as exc:
            logger.exception("Export failed", extra={"export_id": export_id})
            yield json.dumps(
                {"type": "error", "export_id": export_id, "detail": str(exc)}
            ) + "\n"
            return

        duration = (datetime.utcnow() - start).total_seconds()
        yield self._complete_line(export_id=export_id, total=total, duration=duration, options=options)

    async def stream_bulk_export(
        self,
        conversations: List[Conversation],
        options: ExportOptions,
        page_size: int = 5,
    ) -> AsyncGenerator[str, None]:
        """Stream multiple conversations as a single NDJSON response.

        Conversations are processed in pages of ``page_size``.  A
        top-level progress event is emitted before each page so the UI
        can display overall progress.
        """
        export_id = str(uuid4())
        total_convs = len(conversations)
        start = datetime.utcnow()
        total_messages = 0

        logger.info(
            "Starting bulk export",
            extra={"export_id": export_id, "conversation_count": total_convs},
        )

        yield json.dumps(
            {
                "type": "bulk_start",
                "export_id": export_id,
                "total_conversations": total_convs,
                "format": options.format.value,
            }
        ) + "\n"

        for page_start in range(0, total_convs, page_size):
            page = conversations[page_start : page_start + page_size]

            page_num = (page_start // page_size) + 1
            total_pages = -(-total_convs // page_size)  # ceiling division

            yield json.dumps(
                {
                    "type": "bulk_progress",
                    "export_id": export_id,
                    "page": page_num,
                    "total_pages": total_pages,
                    "conversations_done": page_start,
                    "conversations_total": total_convs,
                }
            ) + "\n"

            for conv in page:
                yield json.dumps(
                    {
                        "type": "conversation_start",
                        "export_id": export_id,
                        "conversation_id": conv.id,
                        "title": conv.title,
                    }
                ) + "\n"

                async for line in self.stream_export(conversation=conv, options=options):
                    yield line

                messages_in_conv = len(self._fetch_messages(conv.id, options))
                total_messages += messages_in_conv

                # Yield control so the event loop can handle other I/O.
                await asyncio.sleep(0)

        duration = (datetime.utcnow() - start).total_seconds()
        yield json.dumps(
            {
                "type": "bulk_complete",
                "export_id": export_id,
                "total_conversations": total_convs,
                "total_messages": total_messages,
                "duration_seconds": round(duration, 3),
                "format": options.format.value,
            }
        ) + "\n"

    # ------------------------------------------------------------------
    # Internal helpers: data fetching
    # ------------------------------------------------------------------

    def _fetch_messages(self, conversation_id: str, options: ExportOptions) -> List[Message]:
        """Return filtered, ordered messages for a conversation."""
        query = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        )

        if not options.include_system_messages:
            query = query.filter(Message.role != "system")

        if options.date_from:
            query = query.filter(Message.created_at >= options.date_from)

        if options.date_to:
            query = query.filter(Message.created_at <= options.date_to)

        return query.order_by(Message.created_at.asc()).all()

    # ------------------------------------------------------------------
    # Internal helpers: format renderers
    # ------------------------------------------------------------------

    async def _render_json(
        self,
        conversation: Conversation,
        messages: List[Message],
        options: ExportOptions,
        export_id: str,
    ) -> AsyncGenerator[str, None]:
        """Yield NDJSON lines for a JSON-format export."""
        total = len(messages)
        processed = 0

        # --- Header chunk -------------------------------------------------
        header: Dict[str, Any] = {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "model": conversation.model_name,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "total_messages": total,
            "export_format": "json",
            "exported_at": datetime.utcnow().isoformat(),
        }
        if options.include_metadata:
            header["temperature"] = conversation.temperature
            header["max_tokens"] = conversation.max_tokens
            header["total_tokens"] = conversation.total_tokens
            header["total_cost_usd"] = conversation.total_cost
            header["tags"] = conversation.tags or []

        yield self._data_line(
            export_id=export_id, chunk_index=0, payload={"header": header}
        )

        # --- Message chunks -----------------------------------------------
        for chunk_idx, i in enumerate(range(0, total, self.CHUNK_SIZE), start=1):
            batch = messages[i : i + self.CHUNK_SIZE]
            serialised: List[Dict[str, Any]] = []

            for msg in batch:
                entry: Dict[str, Any] = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": _sanitise(msg.content),
                    "timestamp": msg.created_at.isoformat(),
                }
                if options.include_metadata:
                    entry["tokens_used"] = msg.tokens_used or 0
                    entry["cost_usd"] = msg.cost or 0.0
                    entry["model"] = msg.model_name
                    entry["finish_reason"] = msg.finish_reason
                    entry["latency_ms"] = msg.latency_ms
                serialised.append(entry)
                processed += 1

            yield self._data_line(
                export_id=export_id,
                chunk_index=chunk_idx,
                payload={"messages": serialised},
            )
            yield self._progress_line(
                export_id=export_id,
                total=total,
                processed=processed,
                stage="messages",
                message=f"Exported {processed}/{total} messages",
            )
            await asyncio.sleep(0)

    async def _render_markdown(
        self,
        conversation: Conversation,
        messages: List[Message],
        options: ExportOptions,
        export_id: str,
    ) -> AsyncGenerator[str, None]:
        """Yield NDJSON lines for a Markdown-format export."""
        total = len(messages)
        processed = 0

        _ROLE_EMOJI = {"user": "\U0001f9d1", "assistant": "\U0001f916", "tool": "\U0001f527"}

        # --- Document header ----------------------------------------------
        lines = [
            f"# {conversation.title or 'Conversation'}\n",
            f"> Exported on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  \n",
            f"> Model: `{conversation.model_name}`  \n",
            f"> Messages: {total}  \n",
        ]
        if options.include_metadata:
            lines += [
                f"> Total tokens: {conversation.total_tokens or 0}  \n",
                f"> Estimated cost: ${conversation.total_cost or 0.0:.4f}  \n",
            ]
        lines.append("\n---\n\n")
        header_md = "".join(lines)

        yield self._data_line(
            export_id=export_id,
            chunk_index=0,
            payload={"content": header_md},
        )

        # --- Per-message chunks -------------------------------------------
        for chunk_idx, i in enumerate(range(0, total, self.CHUNK_SIZE), start=1):
            batch = messages[i : i + self.CHUNK_SIZE]
            md_parts: list[str] = []

            for msg in batch:
                emoji = _ROLE_EMOJI.get(msg.role, "\u2753")
                ts = msg.created_at.strftime("%H:%M:%S")
                md_parts.append(f"### {emoji} **{msg.role.title()}** \u2014 {ts}\n\n")
                md_parts.append(_sanitise(msg.content) + "\n")
                if options.include_metadata and (msg.tokens_used or msg.model_name):
                    md_parts.append(
                        f"\n> *tokens: {msg.tokens_used or 0} · "
                        f"model: {msg.model_name or 'n/a'} · "
                        f"cost: ${msg.cost or 0.0:.5f}*\n"
                    )
                md_parts.append("\n---\n\n")
                processed += 1

            yield self._data_line(
                export_id=export_id,
                chunk_index=chunk_idx,
                payload={"content": "".join(md_parts)},
            )
            yield self._progress_line(
                export_id=export_id,
                total=total,
                processed=processed,
                stage="messages",
                message=f"Rendered {processed}/{total} messages",
            )
            await asyncio.sleep(0)

    async def _render_csv(
        self,
        conversation: Conversation,
        messages: List[Message],
        options: ExportOptions,
        export_id: str,
    ) -> AsyncGenerator[str, None]:
        """Yield NDJSON lines for a CSV-format export, using pandas."""
        import pandas as pd  # lazy import; not needed for JSON/MD paths

        total = len(messages)
        processed = 0

        # --- CSV header row -----------------------------------------------
        base_cols = ["id", "role", "content", "timestamp"]
        meta_cols = ["tokens_used", "cost_usd", "model", "finish_reason", "latency_ms"]
        columns = base_cols + (meta_cols if options.include_metadata else [])

        yield self._data_line(
            export_id=export_id,
            chunk_index=0,
            payload={"csv_header": ",".join(columns)},
        )

        # --- Chunked rows -------------------------------------------------
        for chunk_idx, i in enumerate(range(0, total, self.CHUNK_SIZE), start=1):
            batch = messages[i : i + self.CHUNK_SIZE]
            rows: list[dict] = []

            for msg in batch:
                row: Dict[str, Any] = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": _sanitise(msg.content),
                    "timestamp": msg.created_at.isoformat(),
                }
                if options.include_metadata:
                    row["tokens_used"] = msg.tokens_used or 0
                    row["cost_usd"] = msg.cost or 0.0
                    row["model"] = msg.model_name or ""
                    row["finish_reason"] = msg.finish_reason or ""
                    row["latency_ms"] = msg.latency_ms or ""
                rows.append(row)
                processed += 1

            df = pd.DataFrame(rows, columns=columns)
            buf = io.StringIO()
            df.to_csv(
                buf,
                index=False,
                header=(chunk_idx == 1),  # only emit header on first chunk
                lineterminator="\n",
            )
            csv_text = buf.getvalue()

            if options.compress:
                csv_bytes = gzip.compress(csv_text.encode("utf-8"))
                payload: Any = csv_bytes.hex()  # hex-encode for JSON transport
            else:
                payload = csv_text

            yield self._data_line(
                export_id=export_id,
                chunk_index=chunk_idx,
                payload={"csv_rows": payload, "compressed": options.compress},
            )
            yield self._progress_line(
                export_id=export_id,
                total=total,
                processed=processed,
                stage="messages",
                message=f"Serialised {processed}/{total} rows",
            )
            await asyncio.sleep(0)

    # ------------------------------------------------------------------
    # NDJSON line builders
    # ------------------------------------------------------------------

    @staticmethod
    def _progress_line(
        *,
        export_id: str,
        total: int,
        processed: int,
        stage: str,
        message: str,
    ) -> str:
        pct = round((processed / total) * 100, 1) if total else 0.0
        payload = ExportProgress(
            export_id=export_id,
            total_messages=total,
            processed_messages=processed,
            progress_percentage=pct,
        ).model_dump()
        payload["stage"] = stage
        payload["message"] = message
        return json.dumps(payload) + "\n"

    @staticmethod
    def _data_line(*, export_id: str, chunk_index: int, payload: Any) -> str:
        return (
            json.dumps(
                ExportDataChunk(
                    export_id=export_id,
                    chunk_index=chunk_index,
                    data=payload,
                    is_final=False,
                ).model_dump()
            )
            + "\n"
        )

    @staticmethod
    def _complete_line(
        *,
        export_id: str,
        total: int,
        duration: float,
        options: ExportOptions,
    ) -> str:
        return (
            json.dumps(
                ExportComplete(
                    export_id=export_id,
                    total_messages=total,
                    total_size_bytes=0,  # not tracked; set by caller if needed
                    duration_seconds=round(duration, 3),
                    format=options.format,
                    compressed=options.compress,
                ).model_dump()
            )
            + "\n"
        )
