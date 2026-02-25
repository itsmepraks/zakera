# 📝 Security Audit Logging

> **Comprehensive audit trail for security events and compliance**

[![Compliance](https://img.shields.io/badge/SOC%202-Ready-green.svg)](#compliance)
[![GDPR](https://img.shields.io/badge/GDPR-Compliant-blue.svg)](#compliance)
[![Retention](https://img.shields.io/badge/Retention-90%20days-orange.svg)](#retention-policy)

## 🎯 Overview

Zakera implements comprehensive security audit logging for:
- **Compliance** - SOC 2, GDPR, HIPAA, PCI DSS
- **Security** - Intrusion detection, forensics
- **Troubleshooting** - Issue investigation
- **Analytics** - User behavior analysis

## 📋 What Gets Logged

### Authentication Events
- ✅ User login (success/failure)
- ✅ User logout
- ✅ Password changes
- ✅ Password reset requests
- ✅ MFA enrollment
- ✅ MFA verification (success/failure)
- ✅ Session creation/expiration
- ✅ Token generation/refresh

### Authorization Events
- ✅ Permission denied (403)
- ✅ Unauthorized access (401)
- ✅ Role changes
- ✅ Permission grants/revokes
- ✅ Resource access attempts
- ✅ Admin privilege escalation

### Data Access
- ✅ Conversation reads
- ✅ Conversation modifications
- ✅ Conversation deletions
- ✅ User data exports
- ✅ Sensitive data views
- ✅ Bulk operations

### Configuration Changes
- ✅ Settings updates
- ✅ API key creation/revocation
- ✅ Webhook configuration
- ✅ Integration changes
- ✅ Security policy updates

### Security Events
- ✅ Failed authentication attempts
- ✅ Account lockouts
- ✅ Rate limit violations
- ✅ Suspicious activity
- ✅ Potential attacks (XSS, SQLi, etc.)
- ✅ CORS violations
- ✅ Invalid tokens

### System Events
- ✅ Application startup/shutdown
- ✅ Configuration reloads
- ✅ Database migrations
- ✅ Cache invalidations
- ✅ Health check failures

## 🏗️ Audit Log Structure

### JSON Format

```json
{
  "timestamp": "2026-02-24T22:15:30.123Z",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "req-123-456-789",
  "event_type": "authentication.login",
  "severity": "INFO",
  "actor": {
    "user_id": "user-123",
    "username": "john.doe@example.com",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "session_id": "sess-abc-def"
  },
  "action": {
    "type": "LOGIN",
    "resource": "authentication",
    "method": "POST",
    "endpoint": "/api/v1/auth/login"
  },
  "result": {
    "status": "SUCCESS",
    "status_code": 200,
    "message": "Login successful"
  },
  "context": {
    "mfa_enabled": true,
    "login_method": "password+totp",
    "device_fingerprint": "fp-xyz123"
  },
  "metadata": {
    "environment": "production",
    "version": "0.7.0",
    "service": "zakera-api"
  }
}
```

### Field Definitions

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `timestamp` | ISO8601 | Event timestamp (UTC) | ✅ |
| `event_id` | UUID | Unique event identifier | ✅ |
| `correlation_id` | String | Request correlation ID | ✅ |
| `event_type` | String | Event type (dot notation) | ✅ |
| `severity` | Enum | DEBUG/INFO/WARNING/ERROR/CRITICAL | ✅ |
| `actor.user_id` | UUID | User performing action | ❌ |
| `actor.username` | String | Username or email | ❌ |
| `actor.ip_address` | IP | Client IP address | ✅ |
| `actor.user_agent` | String | Client user agent | ❌ |
| `action.type` | String | Action performed | ✅ |
| `action.resource` | String | Resource affected | ✅ |
| `result.status` | Enum | SUCCESS/FAILURE/PARTIAL | ✅ |
| `result.status_code` | Integer | HTTP status code | ❌ |

## 💻 Implementation

### Basic Usage

```python
from src.security.audit_logger import AuditLogger

audit = AuditLogger()

# Log authentication event
await audit.log_auth_event(
    event_type="authentication.login",
    user_id=user.id,
    username=user.email,
    ip_address=request.client.host,
    result="SUCCESS",
    context={"mfa_enabled": True}
)

# Log authorization failure
await audit.log_authorization_failure(
    user_id=user.id,
    resource_type="conversation",
    resource_id=conversation_id,
    action="read",
    reason="User does not own resource"
)

# Log data access
await audit.log_data_access(
    user_id=user.id,
    operation="read",
    resource_type="conversation",
    resource_id=conversation_id,
    sensitivity="high"
)

# Log admin action
await audit.log_admin_action(
    admin_id=admin.id,
    action="user.delete",
    target_user_id=target_user.id,
    reason="User request"
)

# Log security event
await audit.log_security_event(
    event_type="security.attack_detected",
    severity="CRITICAL",
    attack_type="xss_attempt",
    details={"payload": sanitized_payload}
)
```

### Decorator Usage

```python
from src.security.audit_logger import audit_log

@audit_log(event_type="conversation.create")
async def create_conversation(
    user: User,
    request: ConversationCreate
) -> Conversation:
    """Create conversation with automatic audit logging."""
    conversation = await ConversationService.create(
        user_id=user.id,
        **request.dict()
    )
    return conversation

@audit_log(
    event_type="admin.user_delete",
    severity="WARNING",
    require_mfa=True
)
async def delete_user(admin: User, user_id: UUID) -> None:
    """Delete user with audit trail and MFA requirement."""
    await UserService.delete(user_id)
```

### Middleware Integration

```python
# src/middleware/audit_middleware.py
from fastapi import Request
from src.security.audit_logger import AuditLogger

class AuditMiddleware:
    async def __call__(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Execute request
        response = await call_next(request)
        
        # Log request if needed
        if self.should_log(request):
            await self.audit.log_request(
                correlation_id=correlation_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                user_id=getattr(request.state, "user_id", None),
                ip_address=request.client.host
            )
        
        return response
```

## 🗂️ Storage & Retention

### Storage Options

#### 1. File-Based (Development)
```python
# config/audit_config.py
AUDIT_LOG_STORAGE = "file"
AUDIT_LOG_PATH = "/var/log/zakera/audit"
AUDIT_LOG_ROTATION = "daily"  # daily, size, time
AUDIT_LOG_MAX_BYTES = 100_000_000  # 100 MB
AUDIT_LOG_BACKUP_COUNT = 90  # 90 days
```

#### 2. Database (Production)
```python
# Store in separate audit database
AUDIT_LOG_STORAGE = "database"
AUDIT_DATABASE_URL = "postgresql://..."
AUDIT_TABLE_NAME = "security_audit_logs"
```

#### 3. External (Enterprise)
```python
# Send to SIEM (Splunk, ELK, etc.)
AUDIT_LOG_STORAGE = "siem"
SIEM_ENDPOINT = "https://siem.company.com/api/events"
SIEM_API_KEY = "secret-key"
```

### Retention Policy

| Event Category | Retention | Reason |
|----------------|-----------|--------|
| Authentication | 90 days | Compliance (SOC 2) |
| Authorization | 90 days | Security analysis |
| Data Access | 365 days | GDPR compliance |
| Admin Actions | 730 days | Audit trail |
| Security Events | 365 days | Forensics |
| Configuration | 365 days | Change tracking |

### Automatic Cleanup

```python
# scripts/cleanup_audit_logs.py
import asyncio
from src.security.audit_logger import AuditLogger

async def cleanup_old_logs():
    """Delete audit logs older than retention period."""
    audit = AuditLogger()
    
    # Delete logs older than retention period
    deleted = await audit.cleanup(
        older_than_days=90,
        event_types=["authentication.*", "authorization.*"]
    )
    
    print(f"Deleted {deleted} audit log entries")

if __name__ == "__main__":
    asyncio.run(cleanup_old_logs())
```

```bash
# Cron job: Daily at 2 AM
0 2 * * * /usr/bin/python /app/scripts/cleanup_audit_logs.py
```

## 🔍 Querying Audit Logs

### Basic Queries

```python
from src.security.audit_logger import AuditLogger

audit = AuditLogger()

# Get all login attempts for user
logs = await audit.query(
    event_type="authentication.login",
    user_id="user-123",
    start_date="2026-02-01",
    end_date="2026-02-28"
)

# Get failed authentication attempts
failed_logins = await audit.query(
    event_type="authentication.login",
    result_status="FAILURE",
    limit=100
)

# Get admin actions
admin_actions = await audit.query(
    event_type="admin.*",
    severity=["WARNING", "CRITICAL"],
    order_by="timestamp DESC"
)

# Get security events by IP
security_events = await audit.query(
    event_type="security.*",
    ip_address="192.168.1.100",
    last_hours=24
)
```

### Advanced Queries

```python
# Detect brute force attempts
brute_force = await audit.detect_brute_force(
    window_minutes=15,
    threshold=5,  # 5 failed attempts
    event_type="authentication.login"
)

# Find unusual access patterns
anomalies = await audit.detect_anomalies(
    user_id="user-123",
    lookback_days=30
)

# Compliance report
report = await audit.generate_compliance_report(
    start_date="2026-02-01",
    end_date="2026-02-28",
    format="pdf"
)
```

## 📊 Monitoring & Alerting

### Prometheus Metrics

```python
# Metrics exposed
audit_events_total{event_type, severity, result}
audit_auth_failures_total{username, ip_address}
audit_admin_actions_total{action_type}
audit_security_events_total{attack_type}
audit_log_write_errors_total
```

### Grafana Dashboard

```json
// monitoring/grafana/dashboards/audit-logs.json
{
  "panels": [
    {"title": "Authentication Events"},
    {"title": "Failed Login Attempts"},
    {"title": "Admin Actions"},
    {"title": "Security Events"},
    {"title": "Top Users by Activity"}
  ]
}
```

### Alerts

```yaml
# monitoring/prometheus/alerts/audit.yml
groups:
  - name: audit_logs
    rules:
      # Multiple failed logins
      - alert: BruteForceAttempt
        expr: |
          sum by (ip_address) (
            rate(audit_auth_failures_total[5m])
          ) > 5
        annotations:
          summary: "Brute force attempt from {{ $labels.ip_address }}"
      
      # Unusual admin activity
      - alert: SuspiciousAdminActivity
        expr: |
          rate(audit_admin_actions_total[1h]) > 10
        annotations:
          summary: "Unusual admin activity detected"
      
      # Critical security events
      - alert: SecurityEventCritical
        expr: |
          audit_security_events_total{severity="CRITICAL"} > 0
        annotations:
          summary: "Critical security event: {{ $labels.attack_type }}"
```

## 🔐 Security Considerations

### Log Integrity

```python
# Tamper-proof logging with HMAC
import hmac
import hashlib

class SecureAuditLogger:
    def __init__(self, secret_key: bytes):
        self.secret_key = secret_key
    
    async def log_event(self, event: dict) -> None:
        # Calculate HMAC signature
        event_json = json.dumps(event, sort_keys=True)
        signature = hmac.new(
            self.secret_key,
            event_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Store with signature
        event["signature"] = signature
        await self._store(event)
    
    async def verify_integrity(self, event: dict) -> bool:
        """Verify log entry hasn't been tampered with."""
        stored_signature = event.pop("signature")
        event_json = json.dumps(event, sort_keys=True)
        expected_signature = hmac.new(
            self.secret_key,
            event_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(stored_signature, expected_signature)
```

### Data Privacy

```python
# Redact sensitive data
class PrivacyAwareAuditLogger:
    SENSITIVE_FIELDS = [
        "password", "token", "api_key", 
        "credit_card", "ssn"
    ]
    
    def redact_sensitive_data(self, data: dict) -> dict:
        """Redact sensitive fields before logging."""
        redacted = data.copy()
        for field in self.SENSITIVE_FIELDS:
            if field in redacted:
                redacted[field] = "***REDACTED***"
        return redacted
```

## 📋 Compliance

### SOC 2 Type II

✅ **CC6.1** - Logical and physical access controls
- All access attempts logged
- Failed access logged with reason

✅ **CC7.2** - System monitoring
- Continuous audit log monitoring
- Real-time alerting

### GDPR

✅ **Article 30** - Records of processing activities
- Complete audit trail of data access
- User data export logs

✅ **Article 32** - Security of processing
- Security event logging
- Incident detection and response

### HIPAA

✅ **§164.312(b)** - Audit controls
- Comprehensive audit logging
- Regular audit log reviews

✅ **§164.308(a)(1)(ii)(D)** - Information system activity review
- Automated log analysis
- Security event monitoring

## 🧪 Testing

```python
# tests/security/test_audit_logging.py
import pytest
from src.security.audit_logger import AuditLogger

@pytest.mark.asyncio
async def test_log_authentication_event():
    audit = AuditLogger()
    
    await audit.log_auth_event(
        event_type="authentication.login",
        user_id="user-123",
        result="SUCCESS"
    )
    
    # Verify log was written
    logs = await audit.query(
        event_type="authentication.login",
        user_id="user-123"
    )
    
    assert len(logs) == 1
    assert logs[0]["result"]["status"] == "SUCCESS"

@pytest.mark.asyncio
async def test_sensitive_data_redaction():
    audit = AuditLogger()
    
    await audit.log_event(
        event_type="user.create",
        context={"password": "secret123"}
    )
    
    logs = await audit.query(event_type="user.create")
    assert logs[0]["context"]["password"] == "***REDACTED***"
```

## 📚 References

- [NIST SP 800-92](https://csrc.nist.gov/publications/detail/sp/800-92/final) - Guide to Computer Security Log Management
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [CIS Critical Security Controls](https://www.cisecurity.org/controls)

---

**Last Updated:** February 2026  
**Status:** Production Ready ✅

[Back to Security](../SECURITY.md) | [OWASP Checklist](OWASP_API_SECURITY_CHECKLIST.md) | [Incident Response](SECURITY_INCIDENT_RESPONSE.md)
