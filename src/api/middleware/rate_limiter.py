"""Advanced rate limiting middleware with Redis support."""
import time
import hashlib
from typing import Optional, Dict, Callable
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis
from pydantic import BaseModel

from src.utils.config import get_settings
from src.monitoring.metrics import rate_limit_counter, rate_limit_exceeded_counter
import structlog

logger = structlog.get_logger(__name__)


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int  # Time window in seconds
    burst: Optional[int] = None  # Burst allowance (optional)


class RateLimiter:
    """Advanced rate limiter with Redis backend and fallback to in-memory."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[aioredis.Redis] = None
        self.memory_cache: Dict[str, Dict] = {}  # Fallback cache
        self.enabled = self.settings.ENABLE_RATE_LIMITING
        
        # Default rate limits by user tier
        self.tier_limits = {
            "free": RateLimitConfig(requests=100, window=3600, burst=10),  # 100/hour
            "pro": RateLimitConfig(requests=1000, window=3600, burst=50),  # 1000/hour
            "enterprise": RateLimitConfig(requests=10000, window=3600, burst=200),  # 10k/hour
        }
        
        # Endpoint-specific limits (stricter for expensive operations)
        self.endpoint_limits = {
            "/api/v1/chat/send": RateLimitConfig(requests=60, window=60),  # 60/min
            "/api/v1/chat/stream": RateLimitConfig(requests=30, window=60),  # 30/min
            "/api/v1/tools/execute": RateLimitConfig(requests=100, window=60),  # 100/min
        }
        
    async def initialize(self):
        """Initialize Redis connection."""
        if not self.enabled:
            logger.info("Rate limiting disabled")
            return
            
        try:
            redis_url = self.settings.REDIS_URL or "redis://localhost:6379/1"
            self.redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            await self.redis.ping()
            logger.info("Rate limiter initialized with Redis backend")
        except Exception as e:
            logger.warning(
                "Failed to connect to Redis, using in-memory fallback",
                error=str(e)
            )
            self.redis = None
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate cache key for rate limiting."""
        key_hash = hashlib.sha256(f"{identifier}:{endpoint}".encode()).hexdigest()[:16]
        return f"ratelimit:{key_hash}"
    
    async def _check_redis(self, key: str, limit: RateLimitConfig) -> tuple[bool, int, int]:
        """Check rate limit using Redis (sliding window)."""
        now = time.time()
        window_start = now - limit.window
        
        pipe = self.redis.pipeline()
        
        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count requests in current window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, limit.window + 10)
        
        results = await pipe.execute()
        current_count = results[1]
        
        allowed = current_count < limit.requests
        remaining = max(0, limit.requests - current_count - 1)
        
        return allowed, remaining, limit.requests
    
    def _check_memory(self, key: str, limit: RateLimitConfig) -> tuple[bool, int, int]:
        """Check rate limit using in-memory cache (fallback)."""
        now = time.time()
        
        if key not in self.memory_cache:
            self.memory_cache[key] = {"requests": [], "reset_at": now + limit.window}
        
        cache_entry = self.memory_cache[key]
        
        # Reset if window expired
        if now >= cache_entry["reset_at"]:
            cache_entry["requests"] = []
            cache_entry["reset_at"] = now + limit.window
        
        # Remove old requests outside window
        window_start = now - limit.window
        cache_entry["requests"] = [
            ts for ts in cache_entry["requests"] if ts > window_start
        ]
        
        current_count = len(cache_entry["requests"])
        allowed = current_count < limit.requests
        
        if allowed:
            cache_entry["requests"].append(now)
        
        remaining = max(0, limit.requests - current_count - 1)
        
        # Cleanup old entries
        if len(self.memory_cache) > 10000:
            oldest_keys = sorted(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k]["reset_at"]
            )[:1000]
            for k in oldest_keys:
                if self.memory_cache[k]["reset_at"] < now:
                    del self.memory_cache[k]
        
        return allowed, remaining, limit.requests
    
    async def check_limit(
        self,
        identifier: str,
        endpoint: str,
        user_tier: str = "free"
    ) -> tuple[bool, int, int, int]:
        """Check if request is within rate limit.
        
        Args:
            identifier: User ID or IP address
            endpoint: API endpoint path
            user_tier: User's subscription tier
            
        Returns:
            Tuple of (allowed, remaining, limit, reset_at)
        """
        if not self.enabled:
            return True, 999999, 999999, int(time.time() + 3600)
        
        # Get applicable limit (endpoint-specific or tier-based)
        limit = self.endpoint_limits.get(endpoint) or self.tier_limits.get(user_tier, self.tier_limits["free"])
        
        key = self._get_key(identifier, endpoint)
        
        try:
            if self.redis:
                allowed, remaining, total = await self._check_redis(key, limit)
            else:
                allowed, remaining, total = self._check_memory(key, limit)
            
            reset_at = int(time.time() + limit.window)
            
            # Emit metrics
            if allowed:
                rate_limit_counter.labels(
                    identifier=identifier[:16],
                    endpoint=endpoint,
                    status="allowed"
                ).inc()
            else:
                rate_limit_counter.labels(
                    identifier=identifier[:16],
                    endpoint=endpoint,
                    status="blocked"
                ).inc()
                rate_limit_exceeded_counter.labels(
                    endpoint=endpoint,
                    user_tier=user_tier
                ).inc()
                
                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier[:16],
                    endpoint=endpoint,
                    user_tier=user_tier,
                    limit=total,
                    window=limit.window
                )
            
            return allowed, remaining, total, reset_at
            
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            # Fail open - allow request on error
            return True, 0, limit.requests, int(time.time() + limit.window)
    
    def get_identifier(self, request: Request) -> str:
        """Extract identifier from request (user ID or IP)."""
        # Try to get user ID from auth
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def get_user_tier(self, request: Request) -> str:
        """Get user's subscription tier."""
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "tier"):
            return user.tier
        return "free"


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next: Callable):
    """Rate limiting middleware for FastAPI."""
    if not rate_limiter.enabled:
        return await call_next(request)
    
    # Skip rate limiting for health checks and monitoring
    if request.url.path.startswith("/api/v1/monitoring/"):
        return await call_next(request)
    
    identifier = rate_limiter.get_identifier(request)
    user_tier = rate_limiter.get_user_tier(request)
    endpoint = request.url.path
    
    allowed, remaining, limit, reset_at = await rate_limiter.check_limit(
        identifier, endpoint, user_tier
    )
    
    if not allowed:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {limit} per window.",
                "retry_after": reset_at - int(time.time())
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
                "Retry-After": str(reset_at - int(time.time()))
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_at)
    
    return response


def require_rate_limit(tier: str = "free"):
    """Decorator for applying rate limits to specific endpoints."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            identifier = rate_limiter.get_identifier(request)
            endpoint = request.url.path
            
            allowed, remaining, limit, reset_at = await rate_limiter.check_limit(
                identifier, endpoint, tier
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "retry_after": reset_at - int(time.time())
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at)
                    }
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
