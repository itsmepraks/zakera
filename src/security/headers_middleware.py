"""Security headers middleware for FastAPI.

Implements comprehensive HTTP security headers to protect against
common web vulnerabilities including XSS, clickjacking, and MIME sniffing.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all HTTP responses."""

    def __init__(self, app, environment: str = "production"):
        super().__init__(app)
        self.environment = environment
        self.headers = self._get_security_headers()

    def _get_security_headers(self) -> dict:
        """Get security headers based on environment."""
        
        # Base headers for all environments
        headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=()"
            ),
        }

        # HSTS - only for production with HTTPS
        if self.environment == "production":
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy
        if self.environment == "production":
            headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.openai.com https://api.anthropic.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # Relaxed CSP for development
            headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' http://localhost:* ws://localhost:*; "
                "frame-ancestors 'none'"
            )

        return headers

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Add security headers to response."""
        
        try:
            response = await call_next(request)
            
            # Add all security headers
            for header, value in self.headers.items():
                response.headers[header] = value
            
            # Add server header (minimal info)
            response.headers["Server"] = "Zakera"
            
            # Remove potentially revealing headers
            response.headers.pop("X-Powered-By", None)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in security headers middleware: {e}")
            raise


def get_cors_headers(allowed_origins: list = None) -> dict:
    """Get CORS headers configuration.
    
    Args:
        allowed_origins: List of allowed origin domains
    
    Returns:
        Dictionary of CORS headers
    """
    if allowed_origins is None:
        allowed_origins = ["https://zakera.com"]
    
    return {
        "Access-Control-Allow-Origin": ", ".join(allowed_origins),
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "3600",
        "Access-Control-Allow-Credentials": "true",
    }
