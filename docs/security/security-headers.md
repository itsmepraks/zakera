# Security Headers Configuration

## Overview

HTTP security headers implemented in Zakera to protect against common web vulnerabilities.

## Implemented Headers

### Content-Security-Policy (CSP)

**Purpose**: Prevent XSS and data injection attacks

**Configuration**:
```
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' data:;
  connect-src 'self' https://api.openai.com https://api.anthropic.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
```

**Protection Against**:
- Cross-site scripting (XSS)
- Clickjacking
- Code injection

### Strict-Transport-Security (HSTS)

**Purpose**: Force HTTPS connections

**Configuration**:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Details**:
- Max age: 1 year
- Includes all subdomains
- Eligible for browser preload list

### X-Frame-Options

**Purpose**: Prevent clickjacking attacks

**Configuration**:
```
X-Frame-Options: DENY
```

**Alternatives**:
- `DENY`: Cannot be embedded in any frame
- `SAMEORIGIN`: Can only be embedded by same origin

### X-Content-Type-Options

**Purpose**: Prevent MIME-sniffing

**Configuration**:
```
X-Content-Type-Options: nosniff
```

**Protection**: Forces browsers to respect declared content type

### Referrer-Policy

**Purpose**: Control referrer information

**Configuration**:
```
Referrer-Policy: strict-origin-when-cross-origin
```

**Behavior**:
- Same-origin: Full URL
- Cross-origin: Origin only
- HTTPS to HTTP: No referrer

### Permissions-Policy

**Purpose**: Control browser features

**Configuration**:
```
Permissions-Policy: 
  geolocation=(),
  microphone=(),
  camera=(),
  payment=(),
  usb=(),
  magnetometer=()
```

**Disabled Features**:
- Geolocation
- Microphone
- Camera
- Payment API
- USB access
- Magnetometer

### X-XSS-Protection

**Purpose**: Legacy XSS protection (for older browsers)

**Configuration**:
```
X-XSS-Protection: 1; mode=block
```

**Note**: Modern browsers use CSP instead

## Implementation

### FastAPI Middleware

```python
# src/security/headers_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "frame-ancestors 'none'"
        )
        
        return response

# Add to application
app.add_middleware(SecurityHeadersMiddleware)
```

## Testing

### Manual Testing

```bash
# Check headers with curl
curl -I https://api.zakera.com

# Check specific header
curl -I https://api.zakera.com | grep "X-Frame-Options"
```

### Automated Testing

```python
import pytest
from fastapi.testclient import TestClient

def test_security_headers(client: TestClient):
    response = client.get("/")
    
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers
```

### Security Scanning Tools

- [Mozilla Observatory](https://observatory.mozilla.org/)
- [Security Headers](https://securityheaders.com/)
- [SSL Labs](https://www.ssllabs.com/ssltest/)

## Best Practices

1. **Start Strict**: Begin with strict policies, relax if needed
2. **Test Thoroughly**: Ensure headers don't break functionality
3. **Monitor CSP Violations**: Use report-uri directive
4. **Regular Reviews**: Update policies as requirements change
5. **Environment-Specific**: Different policies for dev/prod

## Environment-Specific Configuration

### Development
```python
if settings.ENVIRONMENT == "development":
    # Relaxed CSP for development
    csp = "default-src 'self' 'unsafe-inline' 'unsafe-eval'"
```

### Production
```python
if settings.ENVIRONMENT == "production":
    # Strict CSP for production
    csp = "default-src 'self'; script-src 'self'"
```

## Resources

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [MDN Security Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers#security)
- [Content Security Policy Reference](https://content-security-policy.com/)

---

**Last Updated**: February 2026
