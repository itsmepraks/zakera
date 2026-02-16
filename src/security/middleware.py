"""
Security Middleware for Request Protection and Validation
"""

from typing import Callable, Optional, Dict, List
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import time
import hashlib
import re
from collections import defaultdict
import ipaddress

from ..api.config import settings


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, requests: int, window: int):
        """
        Args:
            requests: Number of requests allowed
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self.clients: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> tuple[bool, Optional[int]]:
        """
        Check if client is within rate limit
        
        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - self.window
        
        # Clean old requests
        self.clients[client_id] = [
            req_time for req_time in self.clients[client_id]
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.clients[client_id]) >= self.requests:
            # Calculate retry after
            oldest_request = min(self.clients[client_id])
            retry_after = int(oldest_request + self.window - now) + 1
            return False, retry_after
        
        # Allow request
        self.clients[client_id].append(now)
        return True, None
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client"""
        now = time.time()
        window_start = now - self.window
        
        recent_requests = [
            req_time for req_time in self.clients[client_id]
            if req_time > window_start
        ]
        
        return max(0, self.requests - len(recent_requests))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        super().__init__(app)
        self.minute_limiter = RateLimiter(requests_per_minute, 60)
        self.hour_limiter = RateLimiter(requests_per_hour, 3600)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/monitoring/health"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check minute limit
        allowed, retry_after = self.minute_limiter.is_allowed(client_id)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Check hour limit
        allowed, retry_after = self.hour_limiter.is_allowed(client_id)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Hourly rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            self.minute_limiter.get_remaining(client_id)
        )
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            self.hour_limiter.get_remaining(client_id)
        )
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Use API key if present
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return hashlib.sha256(auth_header.encode()).hexdigest()[:16]
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return client_ip


# ============================================================================
# Security Headers
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Add security headers"""
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # Strict Transport Security
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        
        return response


# ============================================================================
# IP Filtering
# ============================================================================

class IPFilterMiddleware(BaseHTTPMiddleware):
    """IP whitelist/blacklist middleware"""
    
    def __init__(
        self,
        app,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.whitelist = whitelist or []
        self.blacklist = blacklist or []
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Filter requests by IP"""
        client_ip = self._get_client_ip(request)
        
        # Check blacklist
        if self._is_blacklisted(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        # Check whitelist (if configured)
        if self.whitelist and not self._is_whitelisted(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        try:
            client_ip = ipaddress.ip_address(ip)
            for allowed in self.whitelist:
                if "/" in allowed:
                    # CIDR notation
                    if client_ip in ipaddress.ip_network(allowed, strict=False):
                        return True
                else:
                    # Individual IP
                    if client_ip == ipaddress.ip_address(allowed):
                        return True
            return False
        except ValueError:
            return False
    
    def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        try:
            client_ip = ipaddress.ip_address(ip)
            for blocked in self.blacklist:
                if "/" in blocked:
                    # CIDR notation
                    if client_ip in ipaddress.ip_network(blocked, strict=False):
                        return True
                else:
                    # Individual IP
                    if client_ip == ipaddress.ip_address(blocked):
                        return True
            return False
        except ValueError:
            return False


# ============================================================================
# Request Validation
# ============================================================================

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests"""
    
    # Suspicious patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bor\b.*=.*)",
        r"(;.*drop\b.*table)",
        r"(exec\(|execute\()",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Validate request"""
        # Check for suspicious patterns in URL
        if self._has_suspicious_pattern(str(request.url)):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request"}
            )
        
        # Validate content length
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > 10 * 1024 * 1024:  # 10MB limit
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": "Request too large"}
                    )
            except ValueError:
                pass
        
        return await call_next(request)
    
    def _has_suspicious_pattern(self, text: str) -> bool:
        """Check for suspicious patterns"""
        text_lower = text.lower()
        
        # Check SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log security-relevant requests"""
    
    # Sensitive endpoints that should be audited
    AUDIT_PATTERNS = [
        r"/auth/.*",
        r"/api_keys/.*",
        r"/admin/.*",
        r"/users/.*/delete",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Log audit trail"""
        start_time = time.time()
        
        # Check if endpoint should be audited
        should_audit = any(
            re.match(pattern, request.url.path)
            for pattern in self.AUDIT_PATTERNS
        )
        
        if should_audit:
            # Log request (implement with your logging system)
            self._log_request(request)
        
        # Process request
        response = await call_next(request)
        
        if should_audit:
            # Log response
            duration = time.time() - start_time
            self._log_response(request, response, duration)
        
        return response
    
    def _log_request(self, request: Request):
        """Log incoming request"""
        # Implement with your logging system
        pass
    
    def _log_response(self, request: Request, response: Response, duration: float):
        """Log outgoing response"""
        # Implement with your logging system
        pass


# ============================================================================
# Bot Detection
# ============================================================================

class BotDetectionMiddleware(BaseHTTPMiddleware):
    """Detect and block bots"""
    
    # Known bot user agents
    BOT_USER_AGENTS = [
        "bot", "crawler", "spider", "scraper",
        "curl", "wget", "python-requests"
    ]
    
    def __init__(self, app, allow_good_bots: bool = True):
        super().__init__(app)
        self.allow_good_bots = allow_good_bots
        
        # Good bots (search engines, monitoring)
        self.good_bots = [
            "googlebot", "bingbot", "slackbot",
            "twitterbot", "facebookexternalhit"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Detect and handle bots"""
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Check if it's a bot
        is_bot = any(bot in user_agent for bot in self.BOT_USER_AGENTS)
        
        if is_bot:
            # Check if it's a good bot
            is_good_bot = any(bot in user_agent for bot in self.good_bots)
            
            if not is_good_bot or not self.allow_good_bots:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Bot access not allowed"}
                )
        
        return await call_next(request)


# ============================================================================
# Request Fingerprinting
# ============================================================================

class RequestFingerprint:
    """Generate fingerprint for requests"""
    
    @staticmethod
    def generate(request: Request) -> str:
        """Generate unique fingerprint for request"""
        components = [
            request.client.host if request.client else "",
            request.headers.get("user-agent", ""),
            request.headers.get("accept-language", ""),
            request.headers.get("accept-encoding", ""),
        ]
        
        fingerprint_data = "|".join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()


# ============================================================================
# CORS with Enhanced Security
# ============================================================================

def setup_cors(app, allowed_origins: List[str]):
    """Setup CORS with security"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=[
            "X-RateLimit-Remaining-Minute",
            "X-RateLimit-Remaining-Hour",
            "X-Request-ID"
        ],
        max_age=600,  # 10 minutes
    )


# ============================================================================
# Setup All Middleware
# ============================================================================

def setup_security_middleware(app):
    """Setup all security middleware"""
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=getattr(settings, "RATE_LIMIT_PER_MINUTE", 60),
        requests_per_hour=getattr(settings, "RATE_LIMIT_PER_HOUR", 1000)
    )
    
    # Request validation
    app.add_middleware(RequestValidationMiddleware)
    
    # Audit logging
    app.add_middleware(AuditLogMiddleware)
    
    # Bot detection (optional)
    if getattr(settings, "ENABLE_BOT_DETECTION", False):
        app.add_middleware(BotDetectionMiddleware)
    
    # IP filtering (if configured)
    whitelist = getattr(settings, "IP_WHITELIST", [])
    blacklist = getattr(settings, "IP_BLACKLIST", [])
    if whitelist or blacklist:
        app.add_middleware(
            IPFilterMiddleware,
            whitelist=whitelist,
            blacklist=blacklist
        )
