"""
File Reader tool for reading local text files.

Provides safe, configurable reading of local text files with metadata
extraction including file size, line count, and encoding detection.
Supports common text-based file formats and enforces a maximum file
size limit to prevent memory issues.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

from src.tools.base import (
    Tool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)

# Default maximum file size: 1 MB
DEFAULT_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB

# Supported text file extensions
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
}

# Encodings to attempt, in order of preference
ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]


class FileReaderTool(Tool):
    """
    Tool for reading local text files safely.

    Reads the contents of a local file and returns the text along with
    metadata such as file size, line count, and detected encoding.

    Supported file types:
        .txt, .md, .py, .js, .ts, .json, .yaml, .yml, .csv

    Safety limits:
        - Enforces a configurable maximum file size (default: 1 MB)
        - Rejects binary files
        - Restricts reads to allowed file extensions
        - Handles permission errors and missing files gracefully

    Configuration:
        Pass ``max_file_size`` (in bytes) to ``__init__`` to override the
        default 1 MB limit::

            tool = FileReaderTool(max_file_size=512 * 1024)  # 512 KB

    Examples:
        Read a markdown file::

            result = await tool.execute(file_path="/home/user/notes.md")

        Read only the first 50 lines of a CSV::

            result = await tool.execute(
                file_path="data/report.csv",
                max_lines=50,
            )
    """

    def __init__(self, max_file_size: int = DEFAULT_MAX_FILE_SIZE_BYTES) -> None:
        """
        Initialise the FileReaderTool.

        Args:
            max_file_size: Maximum allowed file size in bytes.
                           Defaults to 1 MB (1_048_576 bytes).
        """
        super().__init__()
        if max_file_size <= 0:
            raise ValueError("max_file_size must be a positive integer.")
        self._max_file_size = max_file_size

    # ------------------------------------------------------------------
    # Tool identity
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a local text file and return the text "
            "together with metadata (file size, line count, encoding). "
            "Supported extensions: .txt .md .py .js .ts .json .yaml .yml .csv. "
            f"Maximum file size: {self._max_file_size // 1024} KB."
        )

    @property
    def category(self) -> str:
        return "filesystem"

    @property
    def tags(self) -> List[str]:
        return ["file", "read", "filesystem", "text", "local"]

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type=ToolParameterType.STRING,
                description=(
                    "Absolute or relative path to the file to read "
                    "(e.g. '/home/user/notes.txt' or 'data/config.yaml')."
                ),
                required=True,
            ),
            ToolParameter(
                name="max_lines",
                type=ToolParameterType.INTEGER,
                description=(
                    "Maximum number of lines to return. "
                    "Omit or set to 0 to return the entire file."
                ),
                required=False,
                default=0,
                min_value=0,
                max_value=100_000,
            ),
            ToolParameter(
                name="encoding",
                type=ToolParameterType.STRING,
                description=(
                    "Character encoding to use when reading the file. "
                    "Leave empty to auto-detect (tries utf-8, latin-1, cp1252)."
                ),
                required=False,
                default="",
            ),
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve and validate the supplied path string.

        Args:
            file_path: Raw path string from the caller.

        Returns:
            A resolved :class:`pathlib.Path` object.

        Raises:
            ToolExecutionError: If the path is empty or resolves to a
                directory rather than a file.
        """
        raw = file_path.strip()
        if not raw:
            raise ToolExecutionError("file_path must not be empty.")
        return Path(raw).expanduser().resolve()

    def _validate_extension(self, path: Path) -> None:
        """
        Ensure the file has a supported text extension.

        Args:
            path: Resolved file path.

        Raises:
            ToolExecutionError: For unsupported or missing extensions.
        """
        ext = path.suffix.lower()
        if not ext:
            raise ToolExecutionError(
                f"File '{path.name}' has no extension. "
                f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        if ext not in SUPPORTED_EXTENSIONS:
            raise ToolExecutionError(
                f"Unsupported file extension '{ext}'. "
                f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

    def _check_file_size(self, path: Path) -> int:
        """
        Return the file size in bytes and raise if it exceeds the limit.

        Args:
            path: Resolved file path.

        Returns:
            File size in bytes.

        Raises:
            ToolExecutionError: If the file exceeds :attr:`_max_file_size`.
        """
        size = path.stat().st_size
        if size > self._max_file_size:
            raise ToolExecutionError(
                f"File size {size:,} bytes exceeds the maximum allowed size "
                f"of {self._max_file_size:,} bytes "
                f"({self._max_file_size // 1024} KB)."
            )
        return size

    def _read_with_encoding(
        self,
        path: Path,
        preferred_encoding: Optional[str],
    ) -> tuple[str, str]:
        """
        Read the file, trying multiple encodings if necessary.

        Args:
            path:               Resolved file path.
            preferred_encoding: Caller-supplied encoding, or empty string
                                to trigger auto-detection.

        Returns:
            A ``(content, detected_encoding)`` tuple.

        Raises:
            ToolExecutionError: If no encoding succeeds or the file
                                appears to be binary.
        """
        encodings = (
            [preferred_encoding]
            if preferred_encoding
            else ENCODINGS_TO_TRY
        )

        last_error: Optional[Exception] = None
        for enc in encodings:
            try:
                content = path.read_text(encoding=enc)
                # Quick binary-content heuristic: reject files whose
                # decoded text contains a high proportion of null bytes
                # or replacement characters (U+FFFD).
                null_ratio = content.count("\x00") / max(len(content), 1)
                replacement_ratio = content.count("\ufffd") / max(len(content), 1)
                if null_ratio > 0.01 or replacement_ratio > 0.10:
                    raise UnicodeDecodeError(
                        enc, b"", 0, 1,
                        "file appears to be binary (high null/replacement-char ratio)",
                    )
                return content, enc
            except UnicodeDecodeError as exc:
                last_error = exc
                continue

        if preferred_encoding:
            raise ToolExecutionError(
                f"Cannot decode '{path.name}' with encoding '{preferred_encoding}'. "
                "Try omitting the encoding parameter to enable auto-detection."
            )
        raise ToolExecutionError(
            f"Cannot read '{path.name}' as a text file. "
            "The file may be binary or use an unsupported encoding. "
            f"Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    async def execute(
        self,
        file_path: str,
        max_lines: int = 0,
        encoding: str = "",
        **kwargs,
    ) -> ToolResult:
        """
        Read a local text file and return its contents with metadata.

        Args:
            file_path: Path to the file (absolute or relative).
            max_lines: Maximum number of lines to return.
                       ``0`` means return the whole file.
            encoding:  Explicit character encoding (e.g. ``'utf-8'``).
                       Leave empty to auto-detect.

        Returns:
            :class:`ToolResult` whose ``data`` dict contains:

            .. code-block:: python

                {
                    "file_path":  str,   # resolved absolute path
                    "file_name":  str,   # basename
                    "extension":  str,   # e.g. '.py'
                    "content":    str,   # file text (possibly truncated)
                    "truncated":  bool,  # True if max_lines was applied
                    "lines_returned": int,
                    "total_lines":    int,
                    "file_size_bytes": int,
                    "file_size_kb":   float,
                    "encoding":       str,
                }
        """
        try:
            # ---- 1. Resolve and validate path ----------------------------
            path = self._resolve_path(file_path)

            if not path.exists():
                return ToolResult.error_result(
                    f"File not found: '{file_path}'"
                )

            if path.is_dir():
                return ToolResult.error_result(
                    f"'{file_path}' is a directory, not a file."
                )

            # ---- 2. Validate extension -----------------------------------
            self._validate_extension(path)

            # ---- 3. Check file size before reading ----------------------
            file_size = self._check_file_size(path)

            # ---- 4. Read file contents ----------------------------------
            content, detected_encoding = self._read_with_encoding(
                path,
                preferred_encoding=encoding.strip() or None,
            )

            # ---- 5. Split into lines ------------------------------------
            all_lines = content.splitlines()
            total_lines = len(all_lines)

            # ---- 6. Apply optional max_lines truncation -----------------
            truncated = False
            if max_lines and max_lines > 0:
                if total_lines > max_lines:
                    all_lines = all_lines[:max_lines]
                    truncated = True

            returned_content = os.linesep.join(all_lines)
            lines_returned = len(all_lines)

            logger.info(
                "FileReaderTool: read '%s' — %d/%d lines, %d bytes, enc=%s",
                path.name,
                lines_returned,
                total_lines,
                file_size,
                detected_encoding,
            )

            return ToolResult.success_result(
                data={
                    "file_path": str(path),
                    "file_name": path.name,
                    "extension": path.suffix.lower(),
                    "content": returned_content,
                    "truncated": truncated,
                    "lines_returned": lines_returned,
                    "total_lines": total_lines,
                    "file_size_bytes": file_size,
                    "file_size_kb": round(file_size / 1024, 2),
                    "encoding": detected_encoding,
                },
                metadata={
                    "max_lines_param": max_lines,
                    "encoding_param": encoding or "auto",
                    "max_file_size_bytes": self._max_file_size,
                },
            )

        except ToolExecutionError as exc:
            return ToolResult.error_result(str(exc))
        except PermissionError:
            return ToolResult.error_result(
                f"Permission denied: cannot read '{file_path}'."
            )
        except OSError as exc:
            return ToolResult.error_result(
                f"OS error while reading '{file_path}': {exc.strerror}"
            )
        except Exception as exc:
            logger.exception("Unexpected error in FileReaderTool")
            return ToolResult.error_result(
                f"Unexpected error reading file: {str(exc)}"
            )
