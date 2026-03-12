"""
Per-user / per-IP sliding-window rate-limiter middleware for Zakera.

Usage in main.py
----------------
    from src.api.middleware.rate_limiter import build_rate_limit_middleware

    app.add_middleware(
        *build_rate_limit_middleware(
            authenticated_max_requests=100,
            anonymous_max_requests=20,
            window_seconds=60,
        )
    )

Or, for more control:

    from starlette.middleware import Middleware
    from src.api.middleware.rate_limiter import RateLimitMiddleware, RateLimitConfig

    app.add_middleware(
        RateLimitMiddleware,
        authenticated_config=RateLimitConfig(window_seconds=60, max_requests=100),
        anonymous_config=RateLimitConfig(window_seconds=60, max_requests=20),
    )
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Type

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

# ---------------------------------------------------------------------------
# Paths that are exempt from rate-limiting
# ---------------------------------------------------------------------------
_EXEMPT_PREFIXES: Tuple[str, ...] = (
    "/api/v1/health",
    "/api/v1/monitoring",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
    "/favicon.ico",
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class RateLimitConfig:
    """Sliding-window rate-limit configuration."""

    #: Length of the sliding window in seconds.
    window_seconds: int = 60

    #: Maximum number of requests allowed within *window_seconds*.
    max_requests: int = 60

    #: Optional burst multiplier.  When > 1 a caller may temporarily
    #: exceed *max_requests* up to ``max_requests * burst_allowance``
    #: for a single window.  Defaults to 1 (no burst).
    burst_allowance: float = 1.0

    @property
    def effective_max(self) -> int:
        """Absolute ceiling including burst allowance."""
        return math.ceil(self.max_requests * self.burst_allowance)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class RateLimitExceededError(Exception):
    """Raised by InMemoryRateLimiter when the caller is over their quota."""

    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = math.ceil(retry_after_seconds)
        super().__init__(
            f"Rate limit exceeded. Retry after {self.retry_after_seconds}s."
        )


# ---------------------------------------------------------------------------
# Core sliding-window limiter
# ---------------------------------------------------------------------------
class InMemoryRateLimiter:
    """
    Async-safe in-memory sliding-window rate limiter.

    Each *key* (e.g. a user ID or IP address) gets its own independent
    hit-timestamp list.  On every :py:meth:`check` call:

    1. Timestamps older than ``now - window_seconds`` are pruned.
    2. If the remaining count is >= ``effective_max``, a
       :exc:`RateLimitExceededError` is raised with the number of
       seconds until the oldest timestamp expires.
    3. Otherwise the current timestamp is appended and the remaining
       quota is returned.
    """

    def __init__(self) -> None:
        # key -> sorted list of UNIX timestamps of requests inside the window
        self._windows: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> Tuple[int, int, float]:
        """
        Record a hit for *key* and return rate-limit metadata.

        Returns
        -------
        (limit, remaining, reset_at)
            limit      – the effective max for this config
            remaining  – requests left in the current window
            reset_at   – UNIX timestamp when the oldest hit expires

        Raises
        ------
        RateLimitExceededError
            When the caller is at or over their quota.
        """
        now = time.monotonic()
        window_start = now - config.window_seconds

        async with self._lock:
            hits = self._windows.get(key, [])

            # Prune expired timestamps
            hits = [ts for ts in hits if ts > window_start]

            effective_max = config.effective_max

            if len(hits) >= effective_max:
                # The oldest hit is the one that will expire first.
                oldest = hits[0]
                retry_after = (oldest + config.window_seconds) - now
                raise RateLimitExceededError(retry_after_seconds=max(retry_after, 1.0))

            # Record this request
            hits.append(now)
            self._windows[key] = hits

            remaining = effective_max - len(hits)
            reset_at = (
                time.time() + ((hits[0] + config.window_seconds) - now)
                if hits
                else time.time() + config.window_seconds
            )
            return effective_max, remaining, reset_at

    async def reset(self, key: str) -> None:
        """Clear all recorded hits for *key* (useful in tests)."""
        async with self._lock:
            self._windows.pop(key, None)

    async def get_hit_count(self, key: str, config: RateLimitConfig) -> int:
        """Return the number of unexpired hits for *key* without recording a new one."""
        now = time.monotonic()
        window_start = now - config.window_seconds
        async with self._lock:
            hits = self._windows.get(key, [])
            return sum(1 for ts in hits if ts > window_start)


# Module-level singleton so all middleware instances share state
_default_limiter = InMemoryRateLimiter()


# ---------------------------------------------------------------------------
# Starlette / FastAPI middleware
# ---------------------------------------------------------------------------
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette middleware that applies per-caller rate limiting.

    Authenticated callers are identified by the ``sub`` claim in the JWT
    Bearer token.  Unauthenticated callers are identified by their
    client IP address.

    Parameters
    ----------
    app:
        The ASGI application.
    authenticated_config:
        Rate-limit config applied to authenticated users.
    anonymous_config:
        Rate-limit config applied to unauthenticated callers.
    limiter:
        Limiter instance.  Defaults to the module-level singleton so
        all middleware instances share state.  Pass a fresh
        ``InMemoryRateLimiter()`` in tests to get isolation.
    exempt_prefixes:
        Path prefixes that bypass rate-limiting entirely.
    """

    def __init__(
        self,
        app: ASGIApp,
        authenticated_config: Optional[RateLimitConfig] = None,
        anonymous_config: Optional[RateLimitConfig] = None,
        limiter: Optional[InMemoryRateLimiter] = None,
        exempt_prefixes: Tuple[str, ...] = _EXEMPT_PREFIXES,
    ) -> None:
        super().__init__(app)
        self.authenticated_config = authenticated_config or RateLimitConfig(
            window_seconds=60, max_requests=100
        )
        self.anonymous_config = anonymous_config or RateLimitConfig(
            window_seconds=60, max_requests=20
        )
        self.limiter = limiter or _default_limiter
        self.exempt_prefixes = exempt_prefixes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_jwt_subject(authorization: Optional[str]) -> Optional[str]:
        """
        Attempt to extract the ``sub`` claim from a Bearer token **without**
        full verification (the auth middleware handles that separately).
        We only need a stable identifier here, not security guarantees.
        """
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:]
        try:
            # JWT payload is the middle segment, base64url-encoded
            import base64
            parts = token.split(".")
            if len(parts) != 3:
                return None
            # Add padding
            padded = parts[1] + "==" [: (4 - len(parts[1]) % 4) % 4]
            payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
            return str(payload.get("sub")) if payload.get("sub") else None
        except Exception:
            return None

    def _get_caller_key(self, request: Request) -> Tuple[str, RateLimitConfig]:
        """
        Return (rate_limit_key, config) for the given request.

        Authenticated users get a ``user:<sub>`` key; anonymous callers
        get an ``ip:<address>`` key.
        """
        auth_header = request.headers.get("Authorization")
        subject = self._extract_jwt_subject(auth_header)
        if subject:
            return f"user:{subject}", self.authenticated_config

        # Respect X-Forwarded-For when behind a proxy/load-balancer
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else (request.client.host if request.client else "unknown")
        )
        return f"ip:{ip}", self.anonymous_config

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.exempt_prefixes)

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._is_exempt(request.url.path):
            return await call_next(request)

        caller_key, config = self._get_caller_key(request)

        try:
            limit, remaining, reset_at = await self.limiter.check(caller_key, config)
        except RateLimitExceededError as exc:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too Many Requests",
                    "retry_after": exc.retry_after_seconds,
                    "message": (
                        f"Rate limit of {config.max_requests} requests per "
                        f"{config.window_seconds}s exceeded. "
                        f"Retry after {exc.retry_after_seconds}s."
                    ),
                },
                headers={
                    "Retry-After": str(exc.retry_after_seconds),
                    "X-RateLimit-Limit": str(config.effective_max),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + exc.retry_after_seconds)),
                },
            )

        response = await call_next(request)

        # Inject informational headers into the response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))
        return response


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------
def build_rate_limit_middleware(
    authenticated_max_requests: int = 100,
    anonymous_max_requests: int = 20,
    window_seconds: int = 60,
    burst_allowance: float = 1.0,
    limiter: Optional[InMemoryRateLimiter] = None,
) -> Tuple[Type[RateLimitMiddleware], dict]:
    """
    Factory returning ``(middleware_class, kwargs)`` for use with
    ``app.add_middleware(*build_rate_limit_middleware(...))``.  This is
    the recommended integration point so callers don't have to import
    ``RateLimitConfig`` directly.
    """
    return (
        RateLimitMiddleware,
        dict(
            authenticated_config=RateLimitConfig(
                window_seconds=window_seconds,
                max_requests=authenticated_max_requests,
                burst_allowance=burst_allowance,
            ),
            anonymous_config=RateLimitConfig(
                window_seconds=window_seconds,
                max_requests=anonymous_max_requests,
                burst_allowance=burst_allowance,
            ),
            limiter=limiter or InMemoryRateLimiter(),
        ),
    )
