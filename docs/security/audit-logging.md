# Audit Logging Configuration

## Overview

Comprehensive audit logging for security events, user actions, and system changes.

## Audit Event Categories

### 1. Authentication Events

**Events Logged:**
- User login (success/failure)
- User logout
- Token creation and refresh
- MFA verification attempts
- Password changes
- Password reset requests
- Account lockouts

**Example Log:**
```json
{
  "timestamp": "2026-02-24T22:00:00Z",
  "event_type": "auth.login",
  "severity": "INFO",
  "user_id": "user_123",
  "username": "john@example.com",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "status": "success",
  "mfa_required": true,
  "session_id": "sess_abc123"
}
```

### 2. Authorization Events

**Events Logged:**
- Permission checks
- Access denials
- Role changes
- Privilege escalations

### 3. Data Access Events

**Events Logged:**
- Conversation access
- User data retrieval
- Sensitive data exports
- Bulk data operations

### 4. Configuration Changes

**Events Logged:**
- Settings updates
- Feature flag changes
- API key creation/deletion
- Security policy modifications

### 5. Security Events

**Events Logged:**
- Suspicious activity detection
- Rate limit violations
- Invalid token usage
- SQL injection attempts
- XSS attempts

## Implementation

### Configuration

```python
# config/audit-config.yml
audit_logging:
  enabled: true
  log_level: INFO
  storage:
    type: database  # database, file, or syslog
    retention_days: 365
    rotation: daily
  
  events:
    authentication: true
    authorization: true
    data_access: true
    configuration: true
    security: true
  
  sensitive_fields:
    - password
    - api_key
    - token
    - credit_card
```

### Usage Example

```python
from src.security.audit_logger import audit_log

# Log authentication event
await audit_log.log_auth_event(
    event_type="login",
    user_id=user.id,
    status="success",
    ip_address=request.client.host,
    metadata={"mfa_used": True}
)

# Log data access
await audit_log.log_data_access(
    user_id=user.id,
    resource_type="conversation",
    resource_id=conversation_id,
    action="read"
)
```

## Monitoring and Alerting

### Real-time Alerts

- Multiple failed login attempts (5+ in 5 minutes)
- Privilege escalation attempts
- Unusual data export volumes
- Access to sensitive endpoints from new IPs
- Security event patterns

### Alert Configuration

```yaml
alerts:
  failed_logins:
    threshold: 5
    window: 5m
    action: [email, slack]
  
  privilege_escalation:
    threshold: 1
    action: [email, pagerduty]
  
  bulk_export:
    threshold: 1000
    window: 1h
    action: [email]
```

## Compliance

- **GDPR**: Right to access audit logs
- **SOC 2**: Audit trail requirements
- **HIPAA**: Access logging (if applicable)
- **PCI DSS**: Security event logging

## Query Examples

### Failed Login Attempts

```sql
SELECT * FROM audit_logs
WHERE event_type = 'auth.login'
  AND status = 'failure'
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### User Activity Timeline

```sql
SELECT * FROM audit_logs
WHERE user_id = 'user_123'
ORDER BY timestamp DESC
LIMIT 100;
```

## Retention and Archival

- **Active Storage**: 90 days
- **Archived Storage**: 365 days
- **Format**: Compressed JSON
- **Location**: S3 or equivalent

## Security

- Audit logs are **tamper-proof** (append-only)
- Access restricted to security team
- Encrypted at rest and in transit
- Regular integrity checks

---

**Last Updated**: February 2026
