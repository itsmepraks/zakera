"""Security Headers Middleware

Adds comprehensive security headers to all HTTP responses to protect against
common web vulnerabilities.

Headers implemented:
- Content Security Policy (CSP)
- Strict-Transport-Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import secrets
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled or os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
        
        # Configuration from environment
        self.hsts_max_age = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year
        self.csp_report_uri = os.getenv("CSP_REPORT_URI", "")
        self.environment = os.getenv("ENVIRONMENT", "production")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        if not self.enabled:
            return await call_next(request)
        
        # Generate CSP nonce for this request
        csp_nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = csp_nonce
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        headers = self._get_security_headers(csp_nonce)
        for header, value in headers.items():
            response.headers[header] = value
        
        return response
    
    def _get_security_headers(self, csp_nonce: str) -> dict:
        """Get security headers configuration"""
        return {
            # HSTS - Force HTTPS
            "Strict-Transport-Security": (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            ),
            
            # Prevent MIME sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # XSS Protection (legacy browsers)
            "X-XSS-Protection": "1; mode=block",
            
            # Content Security Policy
            "Content-Security-Policy": self._get_csp_header(csp_nonce),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy (formerly Feature-Policy)
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Remove server header (don't leak version info)
            "Server": "Zakera",
        }
    
    def _get_csp_header(self, nonce: str) -> str:
        """Generate Content Security Policy header
        
        CSP prevents XSS attacks by controlling which resources can be loaded.
        """
        # Base CSP directives
        directives = [
            # Default: only load from same origin
            "default-src 'self'",
            
            # Scripts: self + nonce (for inline scripts)
            f"script-src 'self' 'nonce-{nonce}'",
            
            # Styles: self + unsafe-inline (for React/Vue)
            # TODO: Use nonces for styles too
            "style-src 'self' 'unsafe-inline'",
            
            # Images: self + data URIs (for inline images)
            "img-src 'self' data: https:",
            
            # Fonts: self
            "font-src 'self'",
            
            # AJAX/WebSocket: self
            "connect-src 'self' wss:",
            
            # Forms: only submit to self
            "form-action 'self'",
            
            # Frames: none
            "frame-ancestors 'none'",
            
            # Base URI restriction
            "base-uri 'self'",
            
            # Upgrade insecure requests
            "upgrade-insecure-requests",
        ]
        
        # Add report URI if configured
        if self.csp_report_uri:
            directives.append(f"report-uri {self.csp_report_uri}")
        
        # In development, be less strict
        if self.environment == "development":
            # Allow localhost connections for dev tools
            directives = [d.replace("'self'", "'self' localhost:*") for d in directives]
        
        return "; ".join(directives)


def get_csp_nonce(request: Request) -> str:
    """Get CSP nonce for current request
    
    Use this in templates to add nonce to inline scripts:
    <script nonce="{{ csp_nonce }}">...</script>
    """
    return getattr(request.state, "csp_nonce", "")
