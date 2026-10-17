# Security and Authentication Guide

> [!WARNING]
> **Legacy and unverified.** This document inventories intended prototype features; it is not a security certification or statement of production readiness. See the root `SECURITY.md` for the current reporting policy.

## Overview

Zakera provides enterprise-grade security with OAuth2, RBAC, MFA, API key management, and comprehensive protection mechanisms.

---

## 🔐 Authentication Methods

### 1. Username/Password

**Basic authentication with JWT tokens**

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "SecurePass123!"}'

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 2. OAuth2 (Social Login)

**Supported Providers**: Google, GitHub, Microsoft

```javascript
// Step 1: Get authorization URL
const response = await fetch('/api/v1/auth/oauth/google/authorize');
const { authorization_url } = await response.json();

// Step 2: Redirect user
window.location.href = authorization_url;

// Step 3: Handle callback
// Your callback URL receives code and state parameters
const tokens = await fetch('/api/v1/auth/oauth/google/callback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ code, state })
});
```

### 3. API Keys

**For programmatic access**

```bash
# Create API key
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "description": "For production API access",
    "expires_in_days": 365,
    "scopes": ["conversation:read", "model:use"]
  }'

# Use API key
curl http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer zk_YOUR_API_KEY"
```

---

## 🎭 Role-Based Access Control (RBAC)

### Roles

| Role | Description | Use Case |
|------|-------------|----------|
| **Super Admin** | Full system access | Platform administrators |
| **Admin** | Organization management | Team leads, managers |
| **Developer** | API and tool access | Application developers |
| **User** | Standard features | Regular users |
| **Viewer** | Read-only access | Auditors, observers |
| **Guest** | Limited trial | Trial users |

### Permissions

**User Management**
- `user:create` - Create users
- `user:read` - View user profiles
- `user:update` - Update user information
- `user:delete` - Delete users

**Conversation Management**
- `conversation:create` - Create conversations
- `conversation:read` - View conversations
- `conversation:update` - Modify conversations
- `conversation:delete` - Delete conversations

**API Key Management**
- `api_key:create` - Create API keys
- `api_key:read` - View API keys
- `api_key:revoke` - Revoke API keys

**Tool Management**
- `tool:execute` - Execute tools
- `tool:create` - Create custom tools
- `tool:manage` - Manage tool system

**Admin Functions**
- `admin:access` - Access admin panel
- `admin:settings` - Modify system settings
- `admin:users` - Manage all users
- `admin:audit` - View audit logs

---

## 🔒 Multi-Factor Authentication (MFA)

### Setup MFA

```python
# 1. Setup MFA
response = await client.post('/api/v1/auth/mfa/setup')
mfa_data = response.json()

# Response
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_uri": "otpauth://totp/...",
  "backup_codes": ["ABCD1234", "EFGH5678", ...]
}

# 2. Show QR code to user (scan with Google Authenticator, Authy, etc.)

# 3. Verify and enable
token = input("Enter code from authenticator: ")
await client.post('/api/v1/auth/mfa/enable', json={'token': token})
```

### Login with MFA

```python
# 1. Login with password
response = await client.post('/api/v1/auth/login', json={
    'username': 'user@example.com',
    'password': 'SecurePass123!'
})

# If MFA enabled, requires token
if response.status_code == 202:
    # 2. Provide MFA token
    mfa_token = input("Enter MFA code: ")
    tokens = await client.post('/api/v1/auth/mfa/verify', json={
        'session_token': response.json()['session_token'],
        'mfa_token': mfa_token
    })
else:
    tokens = response.json()
```

### Backup Codes

```python
# Use backup code if authenticator unavailable
await client.post('/api/v1/auth/mfa/verify-backup', json={
    'session_token': session_token,
    'backup_code': 'ABCD1234'
})

# Each backup code can only be used once
```

---

## 🔑 API Key Management

### Creating API Keys

```python
# Create with specific permissions
api_key = await client.post('/api/v1/auth/api-keys', json={
    'name': 'Mobile App',
    'description': 'Production mobile application',
    'expires_in_days': 365,
    'scopes': [
        'conversation:create',
        'conversation:read',
        'model:use'
    ]
})

# Save the key - shown only once!
key = api_key['key']  # zk_xxx...
```

### Using API Keys

```bash
# Use in Authorization header
curl http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer zk_YOUR_API_KEY"
```

### Managing API Keys

```python
# List keys
keys = await client.get('/api/v1/auth/api-keys')

# Revoke key
await client.delete(f'/api/v1/auth/api-keys/{key_id}')
```

---

## 🛡️ Security Features

### Password Security

**Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*...)

**Protection**:
- Bcrypt hashing (12 rounds)
- Password history (cannot reuse last 5)
- Complexity validation
- Secure password reset

### Brute-Force Protection

- **Max attempts**: 5 failed logins
- **Lockout duration**: 15 minutes
- **Tracking**: By username and IP
- **Auto-unlock**: After lockout period

### Rate Limiting

- **Per minute**: 60 requests
- **Per hour**: 1000 requests
- **Scope**: Per IP or API key
- **Headers**: Returns remaining requests

### Security Headers

All responses include:
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy

---

## 📊 Session Management

### View Active Sessions

```bash
curl http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "sessions": [
    {
      "id": "session_123",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2026-02-15T10:00:00Z",
      "last_activity": "2026-02-15T15:30:00Z"
    }
  ]
}
```

### Revoke Sessions

```bash
# Revoke specific session
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/session_123 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Revoke all sessions
curl -X DELETE http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔍 Audit Logging

### Tracked Events

- User login/logout
- Failed login attempts
- Password changes
- MFA enable/disable
- API key creation/revocation
- Permission denials
- Role changes
- Account lockouts

### Audit Log Format

```json
{
  "id": "audit_123",
  "user_id": "user_456",
  "action": "user.login",
  "resource_type": "session",
  "status": "success",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2026-02-15T10:00:00Z",
  "severity": "info"
}
```

---

## 🚨 Security Best Practices

### For Developers

1. **Always use HTTPS in production**
2. **Implement RBAC for all sensitive endpoints**
3. **Rotate secrets regularly**
4. **Use API keys for programmatic access**
5. **Enable audit logging**
6. **Monitor security metrics**
7. **Keep dependencies updated**
8. **Follow principle of least privilege**

### For Users

1. **Use strong, unique passwords**
2. **Enable MFA**
3. **Review active sessions regularly**
4. **Rotate API keys periodically**
5. **Never share credentials**
6. **Use API keys instead of passwords for apps**
7. **Monitor account activity**

---

## 🛠️ Configuration

### Minimal Production Config

```env
# Required
SECRET_KEY=generate-random-32-char-key-here
DATABASE_URL=postgresql://user:pass@localhost/zakera

# OAuth2 (at least one provider)
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# Security
ALLOWED_ORIGINS=https://yourdomain.com
ENABLE_MFA=true
ENABLE_RATE_LIMITING=true
```

### Advanced Config

```env
# Token lifetimes
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
API_KEY_DEFAULT_EXPIRE_DAYS=365

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Security
ENABLE_BOT_DETECTION=true
IP_WHITELIST=["10.0.0.0/8"]
IP_BLACKLIST=[]

# MFA
MFA_ISSUER_NAME=YourCompany
MFA_BACKUP_CODES_COUNT=10

# Audit
AUDIT_LOG_RETENTION_DAYS=90
```

---

## 📈 Monitoring Security

### Metrics

- `auth_login_attempts_total{status="success|failure"}`
- `auth_mfa_verifications_total{status="success|failure"}`
- `auth_api_key_requests_total{key_id}`
- `auth_rate_limit_exceeded_total`
- `auth_sessions_active`

### Alerts

- High failed login rate
- Account lockouts
- MFA failures
- Suspicious IP activity
- API key abuse

---

## 🚀 Quick Start

### 1. Enable Security Features

```python
# In main.py
from src.security.middleware import setup_security_middleware

app = FastAPI()
setup_security_middleware(app)
```

### 2. Protect Endpoints

```python
from src.security.auth_enhanced import (
    get_current_active_user,
    get_current_user_with_permission,
    Permission
)

@router.post("/admin/action")
async def admin_action(
    user: User = Depends(
        get_current_user_with_permission(Permission.ADMIN_ACCESS)
    )
):
    return {"message": "Admin action executed"}
```

### 3. Configure OAuth2

```python
# Get credentials from:
# - Google: https://console.cloud.google.com/
# - GitHub: https://github.com/settings/developers
# - Microsoft: https://portal.azure.com/

# Add to .env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

---

## 📚 API Reference

### Authentication Endpoints

- `POST /auth/login` - Login with username/password
- `POST /auth/register` - Register new user
- `POST /auth/logout` - Logout current session
- `POST /auth/token/refresh` - Refresh access token

### OAuth2 Endpoints

- `GET /auth/oauth/{provider}/authorize` - Get OAuth URL
- `POST /auth/oauth/{provider}/callback` - Handle callback

### MFA Endpoints

- `POST /auth/mfa/setup` - Setup MFA
- `POST /auth/mfa/enable` - Enable MFA
- `POST /auth/mfa/disable` - Disable MFA
- `POST /auth/mfa/verify` - Verify MFA token

### API Key Endpoints

- `POST /auth/api-keys` - Create API key
- `GET /auth/api-keys` - List API keys
- `DELETE /auth/api-keys/{id}` - Revoke API key

### Session Endpoints

- `GET /auth/sessions` - List active sessions
- `DELETE /auth/sessions/{id}` - Revoke session
- `DELETE /auth/sessions` - Revoke all sessions

### Password Endpoints

- `POST /auth/password/change` - Change password
- `POST /auth/password/reset-request` - Request reset
- `POST /auth/password/reset` - Reset with token

---

## 🔧 Troubleshooting

### Issue: "Permission denied"

**Solution**: Check user role and permissions
```python
user_role = UserRole(user.role)
perms = RBACManager.get_role_permissions(user_role)
print(f"User has permissions: {perms}")
```

### Issue: "Rate limit exceeded"

**Solution**: Wait or increase limits
```env
RATE_LIMIT_PER_MINUTE=120
RATE_LIMIT_PER_HOUR=2000
```

### Issue: "MFA token invalid"

**Solutions**:
1. Check time sync on device
2. Use backup code
3. Regenerate secret

### Issue: "API key not working"

**Checklist**:
1. Key not expired?
2. Key not revoked?
3. Correct scopes assigned?
4. Using Bearer authentication?

---

## 📞 Support

- **Documentation**: `docs/SECURITY.md`
- **API Docs**: http://localhost:8000/api/docs
- **Issues**: GitHub Issues

---

**Status**: Production Ready 🔒  
**Last Updated**: February 2026
