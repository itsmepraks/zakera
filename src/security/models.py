"""
Database models for enhanced authentication and security system
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from ..api.models import Base
from .auth_enhanced import UserRole, Permission, OAuth2Provider, TokenType


def generate_uuid():
    """Generate a UUID string"""
    return str(uuid.uuid4())


class APIKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Key information
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    key_hash = Column(String(64), nullable=False, unique=True)  # SHA256 hash
    key_prefix = Column(String(10), nullable=False)  # First few chars for identification
    
    # Permissions and scopes
    scopes = Column(JSON, default=list)  # List of permissions
    
    # Status and lifecycle
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    created_from_ip = Column(String(45), nullable=True)  # IPv6 support
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    __table_args__ = (
        Index('idx_api_key_user', 'user_id'),
        Index('idx_api_key_hash', 'key_hash'),
    )


class Session(Base):
    """User sessions for tracking active logins"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Session information
    session_token = Column(String(256), nullable=False, unique=True)
    refresh_token_hash = Column(String(64), nullable=True)
    
    # Device and location
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=False)
    device_fingerprint = Column(String(64), nullable=True)
    
    # Geolocation
    country = Column(String(2), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Lifecycle
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_user', 'user_id'),
        Index('idx_session_token', 'session_token'),
        Index('idx_session_active', 'is_active', 'expires_at'),
    )


class LoginAttempt(Base):
    """Track login attempts for brute-force protection"""
    __tablename__ = "login_attempts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    # User information
    username = Column(String(100), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Attempt details
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255), nullable=True)
    
    # Request information
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text, nullable=True)
    
    # Metadata
    attempted_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="login_attempts")
    
    __table_args__ = (
        Index('idx_login_username', 'username', 'attempted_at'),
        Index('idx_login_ip', 'ip_address', 'attempted_at'),
        Index('idx_login_user', 'user_id', 'attempted_at'),
    )


class AuditLog(Base):
    """Audit log for security-relevant actions"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    # Actor information
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(100), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "user.login", "api_key.create"
    resource_type = Column(String(50), nullable=True)  # e.g., "user", "conversation"
    resource_id = Column(String(36), nullable=True)
    
    # Status
    status = Column(String(20), nullable=False)  # success, failure, error
    
    # Details
    description = Column(Text, nullable=True)
    changes = Column(JSON, nullable=True)  # Before/after state
    
    # Request information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    severity = Column(String(20), default="info")  # info, warning, critical
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_user', 'user_id', 'created_at'),
        Index('idx_audit_action', 'action', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )


class OAuth2Account(Base):
    """OAuth2 provider accounts linked to users"""
    __tablename__ = "oauth2_accounts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Provider information
    provider = Column(SQLEnum(OAuth2Provider), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_username = Column(String(255), nullable=True)
    provider_email = Column(String(255), nullable=True)
    
    # Tokens (encrypted in production)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Profile data
    profile_data = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="oauth2_accounts")
    
    __table_args__ = (
        Index('idx_oauth_user', 'user_id'),
        Index('idx_oauth_provider', 'provider', 'provider_user_id'),
    )


class UserMFA(Base):
    """Multi-factor authentication configuration"""
    __tablename__ = "user_mfa"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # MFA configuration
    is_enabled = Column(Boolean, default=False)
    secret = Column(String(255), nullable=False)  # TOTP secret (encrypted)
    
    # Backup codes (hashed)
    backup_codes = Column(JSON, default=list)
    
    # Status
    enabled_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Recovery
    recovery_email = Column(String(255), nullable=True)
    recovery_phone = Column(String(20), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="mfa", uselist=False)
    
    __table_args__ = (
        Index('idx_mfa_user', 'user_id'),
    )


class PasswordHistory(Base):
    """Track password history to prevent reuse"""
    __tablename__ = "password_history"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Password hash
    password_hash = Column(String(255), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="password_history")
    
    __table_args__ = (
        Index('idx_password_history_user', 'user_id', 'created_at'),
    )


class AccountLockout(Base):
    """Track account lockouts due to failed login attempts"""
    __tablename__ = "account_lockouts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Lockout information
    reason = Column(String(255), nullable=False)
    locked_at = Column(DateTime, default=func.now())
    unlocked_at = Column(DateTime, nullable=True)
    auto_unlock_at = Column(DateTime, nullable=True)
    
    # Attempt tracking
    failed_attempts = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="lockouts")
    
    __table_args__ = (
        Index('idx_lockout_user', 'user_id', 'is_active'),
    )


# Add relationships to existing User model
# These would be added to the User model in src/api/models.py:
"""
# In User model, add these relationships:

api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
login_attempts = relationship("LoginAttempt", back_populates="user")
audit_logs = relationship("AuditLog", back_populates="user")
oauth2_accounts = relationship("OAuth2Account", back_populates="user", cascade="all, delete-orphan")
mfa = relationship("UserMFA", back_populates="user", uselist=False, cascade="all, delete-orphan")
password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan")
lockouts = relationship("AccountLockout", back_populates="user", cascade="all, delete-orphan")

# Also add these columns to User model:
role = Column(String(20), default="user")  # UserRole enum
mfa_enabled = Column(Boolean, default=False)
email_verified = Column(Boolean, default=False)
phone_verified = Column(Boolean, default=False)
last_login_at = Column(DateTime, nullable=True)
last_password_change = Column(DateTime, nullable=True)
password_reset_token = Column(String(255), nullable=True)
password_reset_expires = Column(DateTime, nullable=True)
"""
