"""Enhanced structured logging with provider context.

Provides structured logging with correlation IDs, provider-specific contexts,
and sensitive data masking.
"""

import logging
import json
import uuid
import re
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class ProviderContextFilter(logging.Filter):
    """Add provider context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID and provider context to record.
        
        Args:
            record: Log record
            
        Returns:
            Always True (we want to keep all records)
        """
        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        
        # Add timestamp in ISO format
        record.timestamp = datetime.utcnow().isoformat()
        
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from logs."""
    
    # Patterns to mask
    PATTERNS = [
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]+)', r'\1***REDACTED***'),
        (r'(bearer\s+)([a-zA-Z0-9_\-\.]+)', r'\1***REDACTED***'),
        (r'(sk-[a-zA-Z0-9]{20,})', r'***REDACTED***'),
        (r'(password["\']?\s*[:=]\s*["\']?)([^"\s]+)', r'\1***REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log message.
        
        Args:
            record: Log record
            
        Returns:
            Always True
        """
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            for pattern, replacement in self.PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            record.msg = msg
        
        return True


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': getattr(record, 'timestamp', datetime.utcnow().isoformat()),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                             'levelname', 'lineno', 'module', 'msecs', 'message',
                             'pathname', 'process', 'processName', 'relativeCreated',
                             'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                             'timestamp', 'correlation_id']:
                    try:
                        # Only add JSON-serializable values
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data)


def setup_enhanced_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    json_format: bool = True
):
    """Setup enhanced logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Whether to use JSON formatting
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Add filters
    console_handler.addFilter(ProviderContextFilter())
    console_handler.addFilter(SensitiveDataFilter())
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.addFilter(ProviderContextFilter())
        file_handler.addFilter(SensitiveDataFilter())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.info("Enhanced logging configured")


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current context.
    
    Args:
        correlation_id: Correlation ID (generates new if not provided)
        
    Returns:
        Correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID.
    
    Returns:
        Current correlation ID or None
    """
    return correlation_id_var.get()


def clear_correlation_id():
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)


def log_provider_request(
    logger: logging.Logger,
    provider: str,
    model: str,
    **kwargs
):
    """Log provider request with context.
    
    Args:
        logger: Logger instance
        provider: Provider name
        model: Model name
        **kwargs: Additional context
    """
    logger.info(
        f"Provider request: {provider}/{model}",
        extra={
            'provider': provider,
            'model': model,
            'event_type': 'provider_request',
            **kwargs
        }
    )


def log_provider_response(
    logger: logging.Logger,
    provider: str,
    model: str,
    duration: float,
    tokens: Optional[int] = None,
    cost: Optional[float] = None,
    **kwargs
):
    """Log provider response with metrics.
    
    Args:
        logger: Logger instance
        provider: Provider name
        model: Model name
        duration: Request duration in seconds
        tokens: Total tokens used
        cost: Request cost in USD
        **kwargs: Additional context
    """
    extra = {
        'provider': provider,
        'model': model,
        'duration': duration,
        'event_type': 'provider_response',
        **kwargs
    }
    
    if tokens is not None:
        extra['tokens'] = tokens
    
    if cost is not None:
        extra['cost'] = cost
    
    logger.info(
        f"Provider response: {provider}/{model} in {duration:.2f}s",
        extra=extra
    )


def log_provider_error(
    logger: logging.Logger,
    provider: str,
    model: str,
    error: Exception,
    **kwargs
):
    """Log provider error with context.
    
    Args:
        logger: Logger instance
        provider: Provider name
        model: Model name
        error: Exception that occurred
        **kwargs: Additional context
    """
    logger.error(
        f"Provider error: {provider}/{model} - {str(error)}",
        extra={
            'provider': provider,
            'model': model,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'event_type': 'provider_error',
            **kwargs
        },
        exc_info=True
    )
