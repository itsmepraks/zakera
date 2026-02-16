"""Helper utility functions."""

import uuid
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique identifier string
    """
    uid = str(uuid.uuid4())
    return f"{prefix}{uid}" if prefix else uid


def format_tokens(tokens: int) -> str:
    """Format token count for display.
    
    Args:
        tokens: Number of tokens
        
    Returns:
        Formatted string (e.g., "1.2K", "500")
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    else:
        return str(tokens)


def format_cost(cost: float, currency: str = "USD") -> str:
    """Format cost for display.
    
    Args:
        cost: Cost amount
        currency: Currency code
        
    Returns:
        Formatted string (e.g., "$0.05", "$1.23")
    """
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.0:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def parse_duration(duration_str: str) -> int:
    """Parse duration string to seconds.
    
    Args:
        duration_str: Duration string (e.g., "5m", "2h", "30s")
        
    Returns:
        Duration in seconds
        
    Raises:
        ValueError: If format is invalid
    """
    pattern = r'^(\d+)([smhd])$'
    match = re.match(pattern, duration_str.lower())
    
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")
    
    value, unit = match.groups()
    value = int(value)
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    seconds = value * multipliers[unit]
    logger.debug(f"Parsed duration '{duration_str}' to {seconds} seconds")
    
    return seconds
