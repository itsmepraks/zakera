# Input Sanitization Guide

Comprehensive guide to input validation and sanitization to prevent injection attacks and data corruption.

## 🎯 Overview

Input sanitization is critical for preventing:
- SQL Injection
- Cross-Site Scripting (XSS)
- Command Injection
- Path Traversal
- NoSQL Injection
- LDAP Injection
- XML External Entity (XXE)

## 🛡️ Defense Layers

### 1. Type Validation (Pydantic)

```python
from pydantic import BaseModel, validator, constr, conint
from typing import Optional
import re

class MessageRequest(BaseModel):
    """Validate message input"""
    message: constr(min_length=1, max_length=10000)  # Length limits
    conversation_id: Optional[str] = None
    model: constr(regex=r'^[a-zA-Z0-9-]+$')  # Only alphanumeric and hyphens
    
    @validator('message')
    def sanitize_message(cls, v):
        # Remove null bytes
        v = v.replace('\x00', '')
        # Normalize unicode
        import unicodedata
        v = unicodedata.normalize('NFKC', v)
        return v
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        if v is not None:
            # UUID format validation
            import uuid
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError('Invalid conversation_id format')
        return v
```

### 2. SQL Injection Prevention

```python
# ✅ GOOD: Use parameterized queries
from sqlalchemy import text

# SQLAlchemy ORM (automatically parameterized)
conversation = await db.query(Conversation).filter(
    Conversation.id == conversation_id,
    Conversation.user_id == user_id
).first()

# Raw SQL with parameters
result = await db.execute(
    text("SELECT * FROM conversations WHERE id = :id AND user_id = :user_id"),
    {"id": conversation_id, "user_id": user_id}
)

# ❌ BAD: String concatenation
# query = f"SELECT * FROM conversations WHERE id = '{conversation_id}'"  # VULNERABLE!
```

### 3. XSS Prevention

```python
import bleach
import html

class XSSProtection:
    """Sanitize user input to prevent XSS"""
    
    # Allowed HTML tags for rich text (if needed)
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li', 'code', 'pre']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}
    
    @staticmethod
    def sanitize_html(input_str: str) -> str:
        """Remove dangerous HTML/JavaScript"""
        # For markdown/HTML user input
        return bleach.clean(
            input_str,
            tags=XSSProtection.ALLOWED_TAGS,
            attributes=XSSProtection.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def escape_html(input_str: str) -> str:
        """HTML entity encoding"""
        # For plain text that will be displayed in HTML
        return html.escape(input_str)
    
    @staticmethod
    def sanitize_json(data: dict) -> dict:
        """Recursively sanitize JSON data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = XSSProtection.escape_html(value)
            elif isinstance(value, dict):
                sanitized[key] = XSSProtection.sanitize_json(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    XSSProtection.escape_html(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

# Usage
from src.security.input_sanitizer import XSSProtection

# Sanitize user input before storing
message = XSSProtection.sanitize_html(user_input)

# Escape before rendering in templates
rendered = XSSProtection.escape_html(user_data)
```

### 4. Command Injection Prevention

```python
import shlex
import subprocess
from pathlib import Path

class CommandSanitizer:
    """Prevent command injection"""
    
    @staticmethod
    def safe_execute(command: str, args: list) -> str:
        """Execute command safely with argument validation"""
        # Whitelist allowed commands
        ALLOWED_COMMANDS = {'ls', 'cat', 'grep', 'wc'}
        
        if command not in ALLOWED_COMMANDS:
            raise ValueError(f"Command '{command}' not allowed")
        
        # Validate arguments (no shell metacharacters)
        for arg in args:
            if any(char in arg for char in ';|&$`\n'):
                raise ValueError(f"Invalid argument: {arg}")
        
        # Use subprocess with argument list (not shell=True)
        result = subprocess.run(
            [command] + args,
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        return result.stdout

# ✅ GOOD
CommandSanitizer.safe_execute('ls', ['-la', '/tmp'])

# ❌ BAD: Never use shell=True with user input
# subprocess.run(f"ls {user_input}", shell=True)  # VULNERABLE!
```

### 5. Path Traversal Prevention

```python
from pathlib import Path
import os

class PathValidator:
    """Prevent path traversal attacks"""
    
    @staticmethod
    def safe_path(base_dir: str, user_path: str) -> Path:
        """Validate user-provided path is within base directory"""
        # Resolve to absolute path
        base = Path(base_dir).resolve()
        target = (base / user_path).resolve()
        
        # Check if target is within base directory
        if not target.is_relative_to(base):
            raise ValueError("Path traversal attempt detected")
        
        # Additional validation
        if target.is_symlink():
            raise ValueError("Symlinks not allowed")
        
        return target
    
    @staticmethod
    def validate_filename(filename: str) -> str:
        """Validate filename has no path components"""
        # Remove path separators
        if '/' in filename or '\\' in filename:
            raise ValueError("Filename cannot contain path separators")
        
        # Remove null bytes
        if '\x00' in filename:
            raise ValueError("Filename cannot contain null bytes")
        
        # Check for .. 
        if filename.startswith('.') or '..' in filename:
            raise ValueError("Invalid filename")
        
        return filename

# Usage
from src.security.input_sanitizer import PathValidator

base_dir = "/var/uploads"
user_filename = request.form.get("filename")

# Validate filename
safe_filename = PathValidator.validate_filename(user_filename)

# Get safe path
safe_path = PathValidator.safe_path(base_dir, safe_filename)

# Now safe to use
with open(safe_path, 'w') as f:
    f.write(content)
```

### 6. File Upload Validation

```python
import magic
from PIL import Image
import io

class FileValidator:
    """Validate uploaded files"""
    
    # Allowed MIME types
    ALLOWED_TYPES = {
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/pdf',
        'text/plain',
    }
    
    # Max file size (10MB)
    MAX_SIZE = 10 * 1024 * 1024
    
    @staticmethod
    async def validate_upload(file: UploadFile) -> bool:
        """Validate uploaded file"""
        # Check file size
        content = await file.read()
        if len(content) > FileValidator.MAX_SIZE:
            raise ValueError("File too large")
        
        # Reset file pointer
        await file.seek(0)
        
        # Verify MIME type (don't trust client)
        mime = magic.from_buffer(content, mime=True)
        if mime not in FileValidator.ALLOWED_TYPES:
            raise ValueError(f"File type {mime} not allowed")
        
        # For images, validate it's actually an image
        if mime.startswith('image/'):
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()  # Verify it's a valid image
            except Exception:
                raise ValueError("Invalid image file")
        
        # Sanitize filename
        safe_filename = PathValidator.validate_filename(file.filename)
        
        return True

# Usage
@router.post("/upload")
async def upload_file(file: UploadFile):
    await FileValidator.validate_upload(file)
    # Now safe to process
```

### 7. Email Validation

```python
import re
from email_validator import validate_email, EmailNotValidError

class EmailValidator:
    """Validate email addresses"""
    
    @staticmethod
    def validate(email: str) -> str:
        """Validate and normalize email"""
        try:
            # Use email-validator library
            validated = validate_email(email, check_deliverability=False)
            return validated.email.lower()  # Normalize to lowercase
        except EmailNotValidError as e:
            raise ValueError(f"Invalid email: {e}")
    
    @staticmethod
    def is_disposable(email: str) -> bool:
        """Check if email is from disposable email service"""
        disposable_domains = {
            'tempmail.com', 'guerrillamail.com', '10minutemail.com'
        }
        domain = email.split('@')[1].lower()
        return domain in disposable_domains
```

### 8. URL Validation

```python
from urllib.parse import urlparse
import ipaddress

class URLValidator:
    """Validate URLs to prevent SSRF"""
    
    # Allowed schemes
    ALLOWED_SCHEMES = {'http', 'https'}
    
    @staticmethod
    def validate(url: str) -> str:
        """Validate URL is safe"""
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in URLValidator.ALLOWED_SCHEMES:
            raise ValueError(f"Scheme {parsed.scheme} not allowed")
        
        # Check hostname exists
        if not parsed.hostname:
            raise ValueError("Invalid URL: no hostname")
        
        # Prevent SSRF to internal IPs
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError("Access to private IPs not allowed")
        except ValueError:
            # Not an IP, check against blacklist
            blocked_domains = {'localhost', '127.0.0.1', '169.254.169.254'}
            if parsed.hostname.lower() in blocked_domains:
                raise ValueError(f"Domain {parsed.hostname} not allowed")
        
        return url
```

### 9. JSON Schema Validation

```python
import jsonschema
from jsonschema import validate, ValidationError

class JSONValidator:
    """Validate JSON payloads against schema"""
    
    # Define schemas
    MESSAGE_SCHEMA = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "minLength": 1, "maxLength": 10000},
            "conversation_id": {"type": "string", "pattern": "^[a-f0-9-]{36}$"},
            "model": {"type": "string", "enum": ["gpt-4", "claude-3", "gemini-pro"]},
        },
        "required": ["message"],
        "additionalProperties": False
    }
    
    @staticmethod
    def validate_message(data: dict) -> dict:
        """Validate message payload"""
        try:
            validate(instance=data, schema=JSONValidator.MESSAGE_SCHEMA)
            return data
        except ValidationError as e:
            raise ValueError(f"Invalid message payload: {e.message}")
```

## 🧪 Testing

```python
# tests/security/test_input_sanitization.py
import pytest
from src.security.input_sanitizer import XSSProtection, PathValidator

def test_xss_prevention():
    malicious = '<script>alert("XSS")</script>'
    sanitized = XSSProtection.sanitize_html(malicious)
    assert '<script>' not in sanitized
    assert '&lt;script&gt;' in sanitized or sanitized == ''

def test_path_traversal_prevention():
    with pytest.raises(ValueError):
        PathValidator.safe_path('/var/uploads', '../../../etc/passwd')

def test_sql_injection_prevention():
    malicious = "'; DROP TABLE users; --"
    # Should be handled safely by parameterized queries
    # (test that ORM escapes properly)

def test_command_injection_prevention():
    from src.security.input_sanitizer import CommandSanitizer
    with pytest.raises(ValueError):
        CommandSanitizer.safe_execute('ls', ['; rm -rf /'])
```

## 📋 Checklist

### Input Validation
- [ ] All user inputs validated with Pydantic models
- [ ] Length limits enforced
- [ ] Type validation in place
- [ ] Regular expression validation where needed
- [ ] Email validation using email-validator
- [ ] URL validation for external links

### SQL Injection
- [ ] Using ORM (SQLAlchemy) for all queries
- [ ] Parameterized queries for raw SQL
- [ ] No string concatenation in queries
- [ ] Input validation before database operations

### XSS Prevention
- [ ] HTML escaping on output
- [ ] Content Security Policy headers
- [ ] Sanitizing user HTML with bleach
- [ ] Using templating engine auto-escaping

### File Uploads
- [ ] File size limits enforced
- [ ] MIME type validation
- [ ] Filename sanitization
- [ ] Antivirus scanning (if needed)
- [ ] Storage in non-executable location

### Command Injection
- [ ] Never using shell=True
- [ ] Command whitelist
- [ ] Argument validation
- [ ] Using subprocess.run with list arguments

### Path Traversal
- [ ] Path validation
- [ ] Canonical path checking
- [ ] Symlink prevention
- [ ] Filename sanitization

---

**Last Updated**: February 24, 2026  
**Security Contact**: security@zakera.ai
