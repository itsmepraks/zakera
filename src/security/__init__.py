"""
Security module for Zakera AI Chat Agent

Provides:
- Enhanced authentication (OAuth2, JWT, API keys)
- Role-Based Access Control (RBAC)
- Multi-Factor Authentication (MFA)
- Security middleware
- Audit logging
- Session management
"""

from .auth_enhanced import (
    # Enums
    UserRole,
    Permission,
    OAuth2Provider,
    TokenType,
    
    # Managers
    TokenManager,
    MFAManager,
    APIKeyManager,
    SessionManager,
    RBACManager,
    PasswordPolicy,
    
    # Functions
    hash_password,
    verify_password,
    
    # Dependencies
    get_current_user,
    get_current_active_user,
    get_current_user_with_permission,
    require_role,
)

from .middleware import (
    RateLimiter,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    IPFilterMiddleware,
    AuditLogMiddleware,
    BotDetectionMiddleware,
    setup_security_middleware,
)

__all__ = [
    # Enums
    "UserRole",
    "Permission",
    "OAuth2Provider",
    "TokenType",
    
    # Managers
    "TokenManager",
    "MFAManager",
    "APIKeyManager",
    "SessionManager",
    "RBACManager",
    "PasswordPolicy",
    
    # Functions
    "hash_password",
    "verify_password",
    
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_user_with_permission",
    "require_role",
    
    # Middleware
    "RateLimiter",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "RequestValidationMiddleware",
    "IPFilterMiddleware",
    "AuditLogMiddleware",
    "BotDetectionMiddleware",
    "setup_security_middleware",
]

__version__ = "1.0.0"
