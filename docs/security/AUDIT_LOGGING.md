# Audit Logging

Comprehensive security event logging for compliance, monitoring, and incident investigation.

## 🎯 Overview

Zakera implements enterprise-grade audit logging that tracks all security-relevant events, user actions, and system changes. This is essential for:

- ✅ **Compliance** (SOC 2, ISO 27001, GDPR, HIPAA)
- ✅ **Security monitoring** and incident detection
- ✅ **Forensic investigation** after security incidents
- ✅ **User activity tracking** and accountability
- ✅ **Anomaly detection** and threat hunting

## 📋 What Gets Logged

### Authentication Events

```python
# Login attempts (successful and failed)
audit_log("user_login_success", user_id=user.id, ip=request.client.host)
audit_log("user_login_failed", username=username, ip=request.client.host, reason="invalid_password")

# Logout
audit_log("user_logout", user_id=user.id)

# MFA events
audit_log("mfa_enabled", user_id=user.id)
audit_log("mfa_verification_success", user_id=user.id)
audit_log("mfa_verification_failed", user_id=user.id)

# Password changes
audit_log("password_changed", user_id=user.id, initiated_by="user")
audit_log("password_reset_requested", email=email, ip=request.client.host)
```

### Authorization Events

```python
# Access denials
audit_log("access_denied", user_id=user.id, resource=resource_id, action="read")

# Privilege escalation attempts
audit_log("privilege_escalation_attempt", user_id=user.id, requested_role="admin")

# Role changes
audit_log("user_role_changed", user_id=user.id, old_role="user", new_role="admin", changed_by=admin.id)
```

### Data Access Events

```python
# Read operations on sensitive data
audit_log("conversation_accessed", user_id=user.id, conversation_id=conv_id)
audit_log("user_data_accessed", accessor_id=admin.id, target_user_id=user.id)

# Write operations
audit_log("conversation_created", user_id=user.id, conversation_id=new_conv.id)
audit_log("conversation_updated", user_id=user.id, conversation_id=conv_id, changes=changed_fields)
audit_log("conversation_deleted", user_id=user.id, conversation_id=conv_id)

# Bulk operations
audit_log("bulk_delete", user_id=admin.id, count=deleted_count, resource_type="conversations")
```

### Configuration Changes

```python
# System configuration
audit_log("config_changed", user_id=admin.id, key="rate_limit", old_value="60", new_value="100")

# Security settings
audit_log("security_setting_changed", user_id=admin.id, setting="mfa_required", new_value=True)

# API key management
audit_log("api_key_created", user_id=user.id, key_id=key.id)
audit_log("api_key_revoked", user_id=user.id, key_id=key.id, reason="expired")
```

### Security Events

```python
# Rate limit violations
audit_log("rate_limit_exceeded", user_id=user.id, endpoint="/api/v1/chat", ip=request.client.host)

# Suspicious activity
audit_log("suspicious_activity", user_id=user.id, reason="multiple_failed_logins", count=5)
audit_log("account_locked", user_id=user.id, reason="failed_login_attempts")

# Security policy violations
audit_log("security_violation", user_id=user.id, violation_type="weak_password")

# SQL injection attempts
audit_log("sql_injection_attempt", ip=request.client.host, payload=sanitized_payload)
```

## 🏗️ Implementation

### Basic Usage

```python
from src.security.audit_logger import audit_log

# Simple event logging
await audit_log(
    event_type="user_login_success",
    user_id=user.id,
    ip=request.client.host
)

# With additional context
await audit_log(
    event_type="conversation_deleted",
    user_id=user.id,
    conversation_id=conv_id,
    metadata={
        "message_count": conv.message_count,
        "deletion_reason": "user_request"
    }
)
```

### Audit Logger Class

```python
# src/security/audit_logger.py
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

class AuditLogger:
    """Enterprise-grade audit logging system"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # File handler for audit logs
        handler = logging.FileHandler("logs/audit.log")
        handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        ))
        self.logger.addHandler(handler)
        
        # Optional: SIEM integration
        if settings.SIEM_ENABLED:
            self.siem_handler = SIEMHandler(settings.SIEM_URL)
            self.logger.addHandler(self.siem_handler)
    
    async def log(self, event_type: str, user_id: Optional[str] = None, **kwargs):
        """Log an audit event"""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            **kwargs
        }
        
        # Add correlation ID if in request context
        if hasattr(asyncio.current_task(), "correlation_id"):
            event["correlation_id"] = asyncio.current_task().correlation_id
        
        # Log to file
        self.logger.info(json.dumps(event))
        
        # Store in database for querying
        await self._store_in_db(event)
        
        # Check for high-severity events that need alerting
        if self._is_critical_event(event_type):
            await self._send_alert(event)
    
    def _is_critical_event(self, event_type: str) -> bool:
        """Determine if event requires immediate alerting"""
        critical_events = [
            "privilege_escalation_attempt",
            "sql_injection_attempt",
            "multiple_failed_logins",
            "account_locked",
            "unauthorized_access_attempt",
        ]
        return event_type in critical_events
    
    async def _send_alert(self, event: Dict[str, Any]):
        """Send alert for critical security events"""
        # Send to monitoring system, Slack, PagerDuty, etc.
        pass
    
    async def _store_in_db(self, event: Dict[str, Any]):
        """Store audit event in database for querying"""
        # Store in PostgreSQL, Elasticsearch, or other store
        pass

# Global instance
audit_logger = AuditLogger()

# Convenience function
async def audit_log(event_type: str, **kwargs):
    await audit_logger.log(event_type, **kwargs)
```

### Middleware Integration

```python
# src/api/middleware/audit_middleware.py
from fastapi import Request
import time

class AuditMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        await audit_log(
            "api_request",
            method=request.method,
            path=request.url.path,
            ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        await audit_log(
            "api_response",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )
        
        return response
```

## 📊 Log Format

### JSON Structure

```json
{
  "timestamp": "2026-02-24T22:15:30.123Z",
  "event_type": "user_login_success",
  "user_id": "usr_abc123",
  "ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "correlation_id": "req_xyz789",
  "session_id": "sess_def456",
  "metadata": {
    "login_method": "password",
    "mfa_used": true,
    "device_type": "mobile"
  }
}
```

### Required Fields

- `timestamp` - ISO 8601 UTC timestamp
- `event_type` - Type of event (use snake_case)
- `user_id` - User who triggered the event (if applicable)
- `ip` - Source IP address
- `correlation_id` - Request correlation ID

### Optional Fields

- `session_id` - User session identifier
- `resource_id` - ID of affected resource
- `action` - Action performed (create, read, update, delete)
- `result` - Outcome (success, failure, denied)
- `metadata` - Additional context

## 🔍 Querying Audit Logs

### Database Queries

```sql
-- Find all failed login attempts for a user
SELECT * FROM audit_logs
WHERE event_type = 'user_login_failed'
  AND user_id = 'usr_abc123'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Find all actions by a user
SELECT event_type, timestamp, metadata
FROM audit_logs
WHERE user_id = 'usr_abc123'
  AND timestamp BETWEEN '2026-02-01' AND '2026-02-28'
ORDER BY timestamp;

-- Find suspicious activity
SELECT ip, COUNT(*) as failed_attempts
FROM audit_logs
WHERE event_type = 'user_login_failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY ip
HAVING COUNT(*) > 5;
```

### Elasticsearch Queries

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "event_type": "access_denied" }},
        { "range": { "timestamp": { "gte": "now-7d" }}}
      ]
    }
  },
  "aggs": {
    "by_user": {
      "terms": { "field": "user_id" }
    }
  }
}
```

## 🚨 Alerting

### Alert Rules

```python
# config/alert_rules.yml
alert_rules:
  - name: "Multiple Failed Logins"
    condition: "event_type = 'user_login_failed'"
    threshold: 5
    window: "5 minutes"
    severity: "high"
    action: "lock_account"
    
  - name: "Privilege Escalation Attempt"
    condition: "event_type = 'privilege_escalation_attempt'"
    threshold: 1
    severity: "critical"
    action: "alert_security_team"
    
  - name: "Unusual Data Access"
    condition: "event_type = 'conversation_accessed' AND hour(timestamp) BETWEEN 0 AND 5"
    threshold: 10
    window: "1 hour"
    severity: "medium"
    action: "notify_user"
```

## 📦 Storage & Retention

### Storage Strategy

```python
# config/audit_logging.yml
storage:
  # Hot storage (fast queries, recent data)
  hot:
    backend: "postgresql"
    retention_days: 30
    
  # Warm storage (slower queries, historical data)
  warm:
    backend: "elasticsearch"
    retention_days: 365
    
  # Cold storage (archival, compliance)
  cold:
    backend: "s3"
    retention_years: 7
    compression: "gzip"
```

### Retention Policy

- **Hot**: 30 days in PostgreSQL (fast queries)
- **Warm**: 1 year in Elasticsearch (searchable)
- **Cold**: 7 years in S3 (compliance, compressed)
- **Deletion**: After 7 years (or per regulation)

## 🔐 Security & Privacy

### Sensitive Data Handling

```python
# Never log sensitive data directly
# BAD: audit_log("password_changed", password=new_password)

# GOOD: audit_log("password_changed", user_id=user.id)

# Hash or redact sensitive fields
def sanitize_for_logging(data: dict) -> dict:
    sensitive_fields = ["password", "api_key", "credit_card", "ssn"]
    sanitized = data.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "[REDACTED]"
    return sanitized
```

### Access Control

```python
# Only security team and admins can access audit logs
@router.get("/api/v1/audit-logs")
@require_role("security_admin")
async def get_audit_logs(current_user: User = Depends(get_current_user)):
    # Log the access to audit logs
    await audit_log("audit_log_accessed", user_id=current_user.id)
    return await fetch_audit_logs()
```

## 📈 Monitoring & Analytics

### Grafana Dashboard

Create dashboards to visualize:
- Failed login attempts over time
- API usage by user/endpoint
- Security events by type
- Response time trends
- Error rates

### Anomaly Detection

```python
# Detect unusual patterns
async def detect_anomalies():
    # Login from new location
    # Access outside business hours
    # Unusual data volume
    # Rapid successive actions
    pass
```

## 🧪 Testing

```python
# tests/security/test_audit_logging.py
import pytest
from src.security.audit_logger import audit_log

@pytest.mark.asyncio
async def test_audit_log_creation(db_session):
    await audit_log("test_event", user_id="test_user")
    
    # Verify event was logged
    event = await db_session.query(AuditLog).filter_by(
        event_type="test_event"
    ).first()
    
    assert event is not None
    assert event.user_id == "test_user"
    assert event.timestamp is not None

@pytest.mark.asyncio
async def test_critical_event_alert():
    with pytest.raises(AlertSent):
        await audit_log("privilege_escalation_attempt", user_id="test_user")
```

## 📚 Compliance

### SOC 2 Requirements

✅ Log all authentication events  
✅ Log all authorization failures  
✅ Log all data access  
✅ Log all configuration changes  
✅ Protect logs from tampering  
✅ Retain logs for required period  
✅ Monitor logs for security events  

### GDPR Requirements

✅ Log data access (right to know)  
✅ Log data modifications  
✅ Log data deletions  
✅ Retain logs per regulation  
✅ Allow user to access their audit trail  
✅ Protect PII in logs  

## 🔗 Integration

### SIEM Integration

```python
# Send to Splunk, DataDog, Elastic Security
class SIEMHandler(logging.Handler):
    def emit(self, record):
        # Send to SIEM via HTTP/syslog
        requests.post(
            settings.SIEM_URL,
            json=json.loads(record.getMessage())
        )
```

---

**Last Updated**: February 24, 2026  
**Next Review**: May 24, 2026
