"""Structured logging configuration"""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
import traceback


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        if hasattr(record, "duration"):
            log_data["duration_ms"] = record.duration
        
        # Add custom fields from extra
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in log_data:
                try:
                    json.dumps(value)  # Check if serializable
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = True,
    enable_rotation: bool = True,
    max_file_size: str = "10 MB",
    retention: str = "7 days"
) -> None:
    """
    Setup application logging with structured format
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for stdout only)
        json_logs: Use JSON structured logging
        enable_rotation: Enable log file rotation
        max_file_size: Maximum log file size before rotation
        retention: How long to keep rotated logs
    """
    # Remove default loguru handler
    logger.remove()
    
    # Console handler with color
    if json_logs:
        logger.add(
            sys.stdout,
            format="{message}",
            level=log_level,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True,
        )
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        if enable_rotation:
            logger.add(
                log_file,
                format="{message}",
                level=log_level,
                serialize=True,
                rotation=max_file_size,
                retention=retention,
                compression="zip",
                enqueue=True,  # Thread-safe
            )
        else:
            logger.add(
                log_file,
                format="{message}",
                level=log_level,
                serialize=True,
                enqueue=True,
            )
    
    # Configure standard logging to use loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


class RequestLogger:
    """Context manager for request logging with correlation ID"""
    
    def __init__(self, request_id: str, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.start_time = None
        self.context = {}
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.context = logger.contextualize(
            request_id=self.request_id,
            user_id=self.user_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        if exc_type:
            logger.error(
                f"Request failed: {exc_val}",
                request_id=self.request_id,
                user_id=self.user_id,
                duration_ms=duration,
                exception_type=exc_type.__name__
            )
        else:
            logger.info(
                "Request completed",
                request_id=self.request_id,
                user_id=self.user_id,
                duration_ms=duration
            )
    
    def log_info(self, message: str, **kwargs):
        """Log info with context"""
        logger.info(
            message,
            request_id=self.request_id,
            user_id=self.user_id,
            **kwargs
        )
    
    def log_warning(self, message: str, **kwargs):
        """Log warning with context"""
        logger.warning(
            message,
            request_id=self.request_id,
            user_id=self.user_id,
            **kwargs
        )
    
    def log_error(self, message: str, **kwargs):
        """Log error with context"""
        logger.error(
            message,
            request_id=self.request_id,
            user_id=self.user_id,
            **kwargs
        )


# Helper functions for common logging patterns

def log_api_request(method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    """Log API request"""
    logger.info(
        f"{method} {path} - {status_code}",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_model_request(
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    **kwargs
):
    """Log model request"""
    logger.info(
        f"Model request: {model} via {provider}",
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        duration_ms=duration_ms,
        **kwargs
    )


def log_tool_execution(tool_name: str, duration_ms: float, success: bool, **kwargs):
    """Log tool execution"""
    level = "info" if success else "error"
    logger.log(
        level,
        f"Tool execution: {tool_name} - {'success' if success else 'failed'}",
        tool_name=tool_name,
        duration_ms=duration_ms,
        success=success,
        **kwargs
    )


def log_database_query(
    operation: str,
    table: str,
    duration_ms: float,
    rows_affected: Optional[int] = None,
    **kwargs
):
    """Log database query"""
    log_data = {
        "operation": operation,
        "table": table,
        "duration_ms": duration_ms,
    }
    
    if rows_affected is not None:
        log_data["rows_affected"] = rows_affected
    
    log_data.update(kwargs)
    
    logger.debug(f"Database {operation} on {table}", **log_data)


def log_error_with_context(error: Exception, context: Dict[str, Any]):
    """Log error with full context"""
    logger.error(
        f"Error: {str(error)}",
        error_type=type(error).__name__,
        error_message=str(error),
        **context,
        exc_info=True
    )
