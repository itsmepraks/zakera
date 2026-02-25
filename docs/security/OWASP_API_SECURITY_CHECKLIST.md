# OWASP API Security Top 10 Checklist

This checklist helps ensure Zakera complies with the OWASP API Security Top 10 (2023). Use this for security audits, penetration testing prep, and continuous security improvement.

## 📋 Checklist Overview

**Last Review**: February 2026  
**Next Review**: May 2026 (Quarterly)  
**Compliance Status**: ✅ 95% Compliant

---

## API1:2023 - Broken Object Level Authorization (BOLA)

**Risk**: Attackers can access objects belonging to other users

### Controls Implemented

- [x] **Object ownership validation** - Every API endpoint checks user owns requested resource
- [x] **Authorization middleware** - Centralized authorization logic
- [x] **Resource-level permissions** - Fine-grained access control
- [x] **Audit logging** - All access attempts logged
- [ ] **Automated BOLA testing** - TODO: Add to CI/CD

### Implementation

```python
# src/api/middleware/authorization.py
async def check_resource_ownership(user_id: str, resource_id: str, resource_type: str):
    """Verify user owns the requested resource"""
    resource = await get_resource(resource_id, resource_type)
    if resource.owner_id != user_id:
        await audit_log("unauthorized_access_attempt", user_id, resource_id)
        raise HTTPException(status_code=403, detail="Access denied")
    return resource
```

### Testing

```bash
# Test BOLA protection
pytest tests/security/test_bola.py -v
```

**Status**: ✅ **COMPLIANT**

---

## API2:2023 - Broken Authentication

**Risk**: Authentication mechanisms can be compromised

### Controls Implemented

- [x] **JWT with short expiry** - Tokens expire in 15 minutes
- [x] **Refresh token rotation** - New refresh token on every use
- [x] **Multi-factor authentication (MFA)** - TOTP support
- [x] **Password complexity requirements** - Min 12 chars, complexity rules
- [x] **Rate limiting on auth endpoints** - Max 5 attempts per minute
- [x] **Account lockout** - Lock after 5 failed attempts
- [x] **Secure session management** - HttpOnly, Secure, SameSite cookies
- [x] **Failed login attempt monitoring** - Alert on suspicious patterns

### Configuration

```python
# config/security.py
AUTH_CONFIG = {
    "jwt_expiry_minutes": 15,
    "refresh_token_expiry_days": 7,
    "password_min_length": 12,
    "max_login_attempts": 5,
    "lockout_duration_minutes": 30,
    "require_mfa": True,  # For production
}
```

### Testing

- [ ] Brute force attack simulation
- [x] Token expiry validation
- [x] MFA bypass attempts
- [x] Session hijacking tests

**Status**: ✅ **COMPLIANT**

---

## API3:2023 - Broken Object Property Level Authorization

**Risk**: Users can access/modify properties they shouldn't

### Controls Implemented

- [x] **Schema-based validation** - Pydantic models enforce allowed fields
- [x] **Property-level ACL** - Different users see different fields
- [x] **Input/output filtering** - Sensitive fields automatically removed
- [x] **Mass assignment protection** - Explicit field whitelisting

### Implementation

```python
# API responses automatically filter based on user role
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    # Sensitive fields only for admins
    api_keys: Optional[List[str]] = None
    
    @classmethod
    def from_orm(cls, user: User, requester_role: str):
        data = user.dict()
        if requester_role != "admin":
            data.pop("api_keys", None)
        return cls(**data)
```

**Status**: ✅ **COMPLIANT**

---

## API4:2023 - Unrestricted Resource Consumption

**Risk**: API can be overwhelmed by excessive requests

### Controls Implemented

- [x] **Rate limiting** - Per-user, per-endpoint limits
- [x] **Request size limits** - Max 10MB payload
- [x] **Pagination** - All list endpoints paginated (max 100 items)
- [x] **Timeout limits** - 30s max request time
- [x] **Connection limits** - Max concurrent connections per IP
- [x] **Resource quotas** - Per-user monthly limits
- [x] **Cost tracking** - Monitor AI model usage costs

### Configuration

```yaml
# config/rate_limits.yml
rate_limits:
  default: 60/minute
  auth: 5/minute
  chat: 20/minute
  export: 10/hour
  
resource_limits:
  max_request_size: 10485760  # 10MB
  max_response_size: 52428800  # 50MB
  max_conversation_length: 1000
  max_concurrent_connections: 100
```

**Status**: ✅ **COMPLIANT**

---

## API5:2023 - Broken Function Level Authorization

**Risk**: Users can access admin/privileged functions

### Controls Implemented

- [x] **Role-based access control (RBAC)** - Admin, User, Guest roles
- [x] **Permission decorators** - `@require_role("admin")`
- [x] **Function-level ACL** - Every admin endpoint protected
- [x] **Privilege escalation monitoring** - Audit log suspicious access

### Implementation

```python
# Decorator ensures only admins can access
@router.delete("/api/v1/users/{user_id}")
@require_role("admin")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    await audit_log("admin_delete_user", current_user.id, user_id)
    return await user_service.delete(user_id)
```

**Status**: ✅ **COMPLIANT**

---

## API6:2023 - Unrestricted Access to Sensitive Business Flows

**Risk**: Automated abuse of critical business functions

### Controls Implemented

- [x] **CAPTCHA on sensitive operations** - Account creation, password reset
- [x] **Email/SMS verification** - For high-value operations
- [x] **Anomaly detection** - Unusual usage patterns flagged
- [x] **Manual review triggers** - Suspicious activity queued for review
- [ ] **Device fingerprinting** - TODO: Implement

### Sensitive Flows Protected

1. **Account Creation** - CAPTCHA + email verification
2. **Password Reset** - Rate limited + email verification
3. **API Key Generation** - MFA required
4. **Bulk Operations** - Admin approval required
5. **Data Export** - Rate limited + logged

**Status**: ⚠️ **MOSTLY COMPLIANT** (Device fingerprinting pending)

---

## API7:2023 - Server Side Request Forgery (SSRF)

**Risk**: Attacker can make server send requests to internal services

### Controls Implemented

- [x] **URL validation** - Whitelist of allowed domains
- [x] **Private IP blocking** - Reject requests to RFC1918 addresses
- [x] **Protocol restrictions** - Only HTTPS allowed
- [x] **Timeout limits** - 5s timeout on external requests
- [x] **Response size limits** - Max 10MB from external sources

### Implementation

```python
# src/security/url_validator.py
BLOCKED_NETWORKS = [
    "127.0.0.0/8",    # Loopback
    "10.0.0.0/8",     # Private
    "172.16.0.0/12",  # Private
    "192.168.0.0/16", # Private
    "169.254.0.0/16", # Link-local
]

async def validate_external_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS URLs allowed")
    ip = await resolve_hostname(parsed.hostname)
    if is_private_ip(ip):
        raise ValueError("Access to private networks not allowed")
```

**Status**: ✅ **COMPLIANT**

---

## API8:2023 - Security Misconfiguration

**Risk**: Insecure defaults and missing security features

### Controls Implemented

- [x] **Security headers** - All OWASP recommended headers
- [x] **HTTPS enforced** - Redirect HTTP to HTTPS
- [x] **Secure defaults** - Security features on by default
- [x] **Error message sanitization** - No stack traces in production
- [x] **CORS properly configured** - Specific origins only
- [x] **Debug mode disabled** - Never enabled in production
- [x] **Dependency scanning** - Automated vulnerability checks
- [x] **Secret management** - No secrets in code/env files

### Security Headers

```python
# Automatically applied to all responses
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}
```

**Status**: ✅ **COMPLIANT**

---

## API9:2023 - Improper Inventory Management

**Risk**: Exposed debugging endpoints, old API versions

### Controls Implemented

- [x] **API versioning** - `/api/v1/` prefix on all endpoints
- [x] **Endpoint inventory** - OpenAPI/Swagger documentation
- [x] **Deprecated version sunset** - Old versions removed after 6 months
- [x] **Environment separation** - Staging uses separate infrastructure
- [x] **Debug endpoints removed** - No debug routes in production
- [x] **Documentation up-to-date** - Auto-generated from code

### API Lifecycle

```
v1.0 → v1.1 (current) → v2.0 (planned)
        ↑                    ↑
    6 months              Deprecation notice
    deprecation           3 months before
```

**Status**: ✅ **COMPLIANT**

---

## API10:2023 - Unsafe Consumption of APIs

**Risk**: Trusting third-party APIs without validation

### Controls Implemented

- [x] **Input validation** - All external API responses validated
- [x] **Schema validation** - Pydantic models for all external data
- [x] **Timeout limits** - Max 30s for external API calls
- [x] **Circuit breaker** - Fail fast on repeated external failures
- [x] **Provider fallback** - Automatic failover between LLM providers
- [x] **Response size limits** - Max 50MB from external APIs
- [x] **Error handling** - Never expose external API errors directly

### External API Integration

```python
# All external API responses validated
async def call_external_llm(prompt: str, provider: str):
    try:
        response = await provider_client.chat(
            prompt,
            timeout=30,
            max_tokens=4096
        )
        # Validate response structure
        validated = LLMResponse.parse_obj(response)
        return validated
    except ValidationError as e:
        await audit_log("external_api_invalid_response", provider)
        # Fallback to different provider
        return await fallback_provider(prompt)
```

**Status**: ✅ **COMPLIANT**

---

## 📊 Compliance Summary

| Risk Category | Status | Priority |
|--------------|--------|----------|
| API1 - BOLA | ✅ Compliant | Critical |
| API2 - Broken Authentication | ✅ Compliant | Critical |
| API3 - Property Authorization | ✅ Compliant | High |
| API4 - Resource Consumption | ✅ Compliant | High |
| API5 - Function Authorization | ✅ Compliant | Critical |
| API6 - Business Flows | ⚠️ Partial | Medium |
| API7 - SSRF | ✅ Compliant | High |
| API8 - Misconfiguration | ✅ Compliant | High |
| API9 - API Inventory | ✅ Compliant | Medium |
| API10 - Unsafe Consumption | ✅ Compliant | High |

**Overall Compliance**: 95% ✅

---

## 🔄 Continuous Improvement

### Quarterly Review Tasks

- [ ] Re-run this checklist
- [ ] Update controls based on new threats
- [ ] Review and update configurations
- [ ] Conduct penetration testing
- [ ] Update security documentation
- [ ] Train team on new security features

### Automated Security Testing

```bash
# Run OWASP ZAP security scan
make security-scan

# Run security-specific tests
pytest tests/security/ -v

# Check for known vulnerabilities
make dependency-check
```

---

## 📚 References

- [OWASP API Security Top 10 2023](https://owasp.org/www-project-api-security/)
- [OWASP API Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [Zakera Security Documentation](./README.md)

**Last Updated**: February 24, 2026  
**Next Review Due**: May 24, 2026
