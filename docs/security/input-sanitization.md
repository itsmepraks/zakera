# Input Sanitization and Validation Guide

## Overview

Comprehensive input validation and sanitization to prevent injection attacks and ensure data integrity.

## Input Validation Principles

1. **Validate Early**: Validate at API boundary
2. **Whitelist Approach**: Allow known good, reject everything else
3. **Fail Securely**: Reject invalid input with clear error messages
4. **Encode Output**: Escape data before rendering
5. **Use Parameterized Queries**: Prevent SQL injection

## XSS (Cross-Site Scripting) Prevention

### HTML Content Sanitization

```python
from bleach import clean

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'a']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}

def sanitize_html(content: str) -> str:
    """Sanitize HTML content to prevent XSS."""
    return clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
```

### Markdown Content

```python
import markdown
from markdown.extensions import fenced_code, tables

def safe_markdown(content: str) -> str:
    """Convert markdown safely without script execution."""
    html = markdown.markdown(
        content,
        extensions=['fenced_code', 'tables'],
        output_format='html5'
    )
    return sanitize_html(html)
```

## SQL Injection Prevention

### Use ORMs and Parameterized Queries

✅ **CORRECT**:
```python
# Using SQLAlchemy ORM (safe)
user = session.query(User).filter(User.email == email).first()

# Using parameterized query (safe)
result = session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": email}
)
```

❌ **INCORRECT**:
```python
# String concatenation (VULNERABLE)
query = f"SELECT * FROM users WHERE email = '{email}'"
result = session.execute(query)
```

## Command Injection Prevention

### Subprocess Validation

```python
import shlex
from pathlib import Path

def safe_file_operation(filename: str):
    """Safely handle file operations."""
    # Validate filename
    if not filename.replace('_', '').replace('-', '').isalnum():
        raise ValueError("Invalid filename")
    
    # Use Path for safe path handling
    safe_path = Path(UPLOAD_DIR) / filename
    
    # Ensure path is within allowed directory
    if not safe_path.resolve().is_relative_to(UPLOAD_DIR):
        raise ValueError("Path traversal detected")
    
    return safe_path
```

## Path Traversal Prevention

```python
from pathlib import Path

def validate_file_path(user_input: str, base_dir: str) -> Path:
    """Validate file path to prevent directory traversal."""
    # Resolve to absolute path
    requested_path = (Path(base_dir) / user_input).resolve()
    base = Path(base_dir).resolve()
    
    # Check if path is within base directory
    if not requested_path.is_relative_to(base):
        raise ValueError("Invalid file path")
    
    return requested_path
```

## File Upload Validation

```python
from typing import BinaryIO
import magic

ALLOWED_EXTENSIONS = {'.jpg', '.png', '.pdf', '.txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file_upload(file: BinaryIO, filename: str):
    """Validate uploaded file."""
    # Check file extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {ext} not allowed")
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset
    
    if size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    
    # Verify MIME type (magic bytes)
    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)
    
    allowed_mimes = {'image/jpeg', 'image/png', 'application/pdf', 'text/plain'}
    if mime not in allowed_mimes:
        raise ValueError("Invalid file type")
```

## JSON/API Input Validation

### Using Pydantic Models

```python
from pydantic import BaseModel, Field, validator
import re

class CreateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=10000)
    model: str = Field(..., regex=r'^[a-z0-9-]+$')
    
    @validator('title')
    def validate_title(cls, v):
        # Remove potentially dangerous characters
        if re.search(r'[<>"\'\\/]', v):
            raise ValueError('Title contains invalid characters')
        return v.strip()
    
    @validator('message')
    def validate_message(cls, v):
        # Limit message length
        if len(v) > 10000:
            raise ValueError('Message too long')
        return v
```

## Email Validation

```python
from pydantic import EmailStr, BaseModel
import re

class UserRegistration(BaseModel):
    email: EmailStr  # Built-in email validation
    
    @validator('email')
    def validate_email_domain(cls, v):
        # Additional domain validation
        allowed_domains = ['example.com', 'company.com']
        domain = v.split('@')[1]
        if domain not in allowed_domains:
            raise ValueError(f'Email domain {domain} not allowed')
        return v
```

## URL Validation

```python
from pydantic import HttpUrl, BaseModel
import urllib.parse

class WebhookConfig(BaseModel):
    url: HttpUrl
    
    @validator('url')
    def validate_url(cls, v):
        parsed = urllib.parse.urlparse(str(v))
        
        # Only allow HTTPS
        if parsed.scheme != 'https':
            raise ValueError('Only HTTPS URLs allowed')
        
        # Block internal IPs
        hostname = parsed.hostname
        if hostname in ['localhost', '127.0.0.1'] or hostname.startswith('192.168.'):
            raise ValueError('Internal URLs not allowed')
        
        return v
```

## Rate Limiting

```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat")
@limiter.limit("60/minute")
async def chat_endpoint(request: Request):
    # Rate limited to 60 requests per minute
    pass
```

## Content-Type Validation

```python
from fastapi import Header, HTTPException

@app.post("/api/upload")
async def upload(content_type: str = Header(...)):
    allowed_types = ['application/json', 'multipart/form-data']
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Content-Type {content_type} not supported"
        )
```

## Security Checklist

- ✅ All user input validated with Pydantic models
- ✅ HTML content sanitized before storage/display
- ✅ Parameterized queries for all database operations
- ✅ File uploads validated (size, type, content)
- ✅ URLs validated and internal IPs blocked
- ✅ Rate limiting on all public endpoints
- ✅ Request size limits enforced
- ✅ Content-Type validation
- ✅ Path traversal prevention
- ✅ Command injection prevention

---

**Last Updated**: February 2026
