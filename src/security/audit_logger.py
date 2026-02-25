"""Audit logging system for security events.

Provides structured logging for authentication, authorization, data access,
and security events with support for various storage backends.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Audit event types."""
    # Authentication events
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_TOKEN_CREATED = "auth.token_created"
    AUTH_TOKEN_REFRESHED = "auth.token_refreshed"
    AUTH_PASSWORD_CHANGED = "auth.password_changed"
    AUTH_MFA_ENABLED = "auth.mfa_enabled"
    AUTH_MFA_VERIFIED = "auth.mfa_verified"
    
    # Authorization events
    AUTHZ_ACCESS_GRANTED = "authz.access_granted"
    AUTHZ_ACCESS_DENIED = "authz.access_denied"
    AUTHZ_ROLE_CHANGED = "authz.role_changed"
    
    # Data access events
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    
    # Security events
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious_activity"
    SECURITY_RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    SECURITY_INVALID_TOKEN = "security.invalid_token"
    SECURITY_ATTACK_DETECTED = "security.attack_detected"
    
    # Configuration events
    CONFIG_CHANGED = "config.changed"
    CONFIG_API_KEY_CREATED = "config.api_key_created"
    CONFIG_API_KEY_DELETED = "config.api_key_deleted"


class EventSeverity(str, Enum):
    """Event severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEvent(BaseModel):
    """Audit event model."""
    timestamp: datetime
    event_type: EventType
    severity: EventSeverity
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    status: str  # success, failure, error
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None


class AuditLogger:
    """Audit logging manager."""

    def __init__(self, storage_backend: str = "database"):
        """Initialize audit logger.
        
        Args:
            storage_backend: Storage type (database, file, syslog)
        """
        self.storage_backend = storage_backend
        self.logger = logging.getLogger("audit")

    async def log_event(
        self,
        event_type: EventType,
        severity: EventSeverity = EventSeverity.INFO,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        """Log an audit event."""
        
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            message=message,
            metadata=metadata or {},
            session_id=session_id,
            trace_id=trace_id,
        )

        # Log to file/console
        log_message = self._format_log_message(event)
        
        if severity == EventSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif severity == EventSeverity.ERROR:
            self.logger.error(log_message)
        elif severity == EventSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        # Store in database (if configured)
        if self.storage_backend == "database":
            await self._store_in_database(event)

    def _format_log_message(self, event: AuditEvent) -> str:
        """Format audit event as JSON log message."""
        return json.dumps(event.dict(), default=str, ensure_ascii=False)

    async def _store_in_database(self, event: AuditEvent) -> None:
        """Store audit event in database.
        
        This is a placeholder - implement with actual database storage.
        """
        # TODO: Implement database storage
        pass

    async def log_auth_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log authentication event."""
        await self.log_event(
            event_type=EventType(f"auth.{event_type}"),
            severity=EventSeverity.INFO if status == "success" else EventSeverity.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            status=status,
            metadata=metadata,
        )

    async def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        status: str = "success",
    ) -> None:
        """Log data access event."""
        await self.log_event(
            event_type=EventType.DATA_READ if action == "read" else EventType.DATA_WRITE,
            severity=EventSeverity.INFO,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
        )

    async def log_security_event(
        self,
        event_description: str,
        ip_address: Optional[str] = None,
        severity: EventSeverity = EventSeverity.WARNING,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security event."""
        await self.log_event(
            event_type=EventType.SECURITY_SUSPICIOUS_ACTIVITY,
            severity=severity,
            ip_address=ip_address,
            message=event_description,
            status="detected",
            metadata=metadata,
        )


# Global audit logger instance
audit_log = AuditLogger()
