# Security Module

> [!WARNING]
> **Legacy module documentation.** The claims below have not been verified as a supported security boundary and must not be read as a production-readiness statement.

## Overview

This module provides enterprise-grade security features for Zakera, including authentication, authorization, and protection mechanisms.

## Components

### Authentication (`auth_enhanced.py`)
- OAuth2 integration (Google, GitHub, Microsoft)
- JWT token management
- Multi-factor authentication (TOTP)
- API key generation and validation
- Password policies and validation
- Session management

### Database Models (`models.py`)
- APIKey - API key management
- Session - Session tracking
- LoginAttempt - Brute-force protection
- AuditLog - Security auditing
- OAuth2Account - OAuth provider linking
- UserMFA - MFA configuration
- PasswordHistory - Password reuse prevention
- AccountLockout - Account lockout tracking

### Middleware (`middleware.py`)
- Rate limiting (token bucket)
- Security headers (CSP, HSTS, etc.)
- IP filtering (whitelist/blacklist)
- Request validation (SQL injection, XSS)
- Audit logging
- Bot detection
- Request fingerprinting

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize security system
python scripts/init_security.py

# Run migrations
alembic upgrade head
```

### 2. Enable in Application

```python
from fastapi import FastAPI
from src.security.middleware import setup_security_middleware

app = FastAPI()
setup_security_middleware(app)
```

### 3. Protect Endpoints

```python
from src.security import (
    get_current_active_user,
    get_current_user_with_permission,
    Permission
)

@app.get("/protected")
async def protected(
    user: User = Depends(get_current_active_user)
):
    return {"user": user.username}

@app.delete("/admin/resource")
async def admin_only(
    user: User = Depends(
        get_current_user_with_permission(Permission.ADMIN_ACCESS)
    )
):
    return {"message": "Admin action"}
```

## Features

### RBAC (Role-Based Access Control)

**6 Roles**:
- Super Admin (full access)
- Admin (organization management)
- Developer (API access)
- User (standard features)
- Viewer (read-only)
- Guest (trial access)

**20+ Permissions**:
- User management (create, read, update, delete)
- Conversation management (CRUD)
- API key management
- Tool management
- Model management
- Admin functions

### OAuth2 Integration

**Supported Providers**:
- Google (Gmail, G Suite)
- GitHub (Developers)
- Microsoft (Office 365, Azure AD)

**Features**:
- Automatic user creation
- Profile synchronization
- Token refresh
- Account linking

### Multi-Factor Authentication

- TOTP-based (RFC 6238)
- Compatible with Google Authenticator, Authy
- Backup codes (10 codes)
- QR code provisioning
- Recovery options

### API Key Management

- Prefixed keys (zk_...)
- SHA-256 hashing
- Scoped permissions
- Expiration management
- Usage tracking
- Rate limiting per key

### Security Middleware

- **Rate Limiting**: 60/min, 1000/hour
- **Security Headers**: CSP, HSTS, X-Frame-Options
- **IP Filtering**: Whitelist/blacklist with CIDR
- **Request Validation**: SQL injection, XSS detection
- **Audit Logging**: All security events
- **Bot Detection**: Block malicious bots

## Configuration

See `.env.security` template or `docs/AUTHENTICATION_GUIDE.md`

## Testing

```bash
# Run security tests
pytest tests/test_auth_enhanced.py -v
pytest tests/test_security_middleware.py -v

# With coverage
pytest tests/test_auth_enhanced.py --cov=src.security
```

## Documentation

- **Complete Guide**: `docs/AUTHENTICATION_GUIDE.md`
- **Security Guide**: `docs/SECURITY.md`
- **Summary**: `SECURITY_ENHANCEMENT_SUMMARY.md`
- **API Docs**: http://localhost:8000/api/docs

## Architecture

```
Request
  ↓
[Rate Limiting] ← Token bucket
  ↓
[Security Headers] ← CSP, HSTS
  ↓
[IP Filtering] ← Whitelist/blacklist
  ↓
[Request Validation] ← SQL injection, XSS
  ↓
[Authentication] ← JWT/API key/OAuth2
  ↓
[Authorization] ← RBAC
  ↓
[Audit Logging] ← Security events
  ↓
Application
```

## Support

- **Issues**: GitHub Issues
- **Docs**: See `docs/` directory
- **Examples**: See tests and documentation

---

**Version**: 1.0.0  
**Status**: Production Ready 🔒
