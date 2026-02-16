"""Input validation and sanitization utilities."""

import re
import json
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent common security issues.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
        
    Raises:
        ValueError: If text exceeds max_length
    """
    if not isinstance(text, str):
        logger.warning(f"Non-string input provided: {type(text)}")
        text = str(text)
    
    # Check length
    if len(text) > max_length:
        logger.warning(f"Input exceeds max length: {len(text)} > {max_length}")
        raise ValueError(f"Input too long: {len(text)} characters (max: {max_length})")
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_email(email: str) -> bool:
    """Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email))
    
    if not is_valid:
        logger.debug(f"Invalid email format: {email}")
    
    return is_valid


def validate_url(url: str) -> bool:
    """Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL format
    """
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    is_valid = bool(re.match(pattern, url))
    
    if not is_valid:
        logger.debug(f"Invalid URL format: {url}")
    
    return is_valid


def is_valid_json(text: str) -> bool:
    """Check if text is valid JSON.
    
    Args:
        text: Text to validate
        
    Returns:
        True if valid JSON
    """
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    logger.debug(f"Sanitized filename: {filename}")
    return filename
