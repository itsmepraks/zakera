"""
Unit and integration tests for src/api/middleware/rate_limiter.py

Run with:
    pytest tests/test_rate_limiter.py -v
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from starlette.responses import PlainTextResponse

from src.api.middleware.rate_limiter import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    RateLimitMiddleware,
    build_rate_limit_middleware,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(sub: str) -> str:
    """Produce a minimal (unsigned) JWT with the given sub claim."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.fakesignature"


def _auth_headers(sub: str = "user-123") -> dict:
    return {"Authorization": f"Bearer {_make_jwt(sub)}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def limiter() -> InMemoryRateLimiter:
    """Fresh limiter instance per test — no shared state."""
    return InMemoryRateLimiter()


@pytest.fixture()
def tight_config() -> RateLimitConfig:
    """Config that allows 5 requests per 30-second window."""
    return RateLimitConfig(window_seconds=30, max_requests=5)


@pytest.fixture()
def app(limiter: InMemoryRateLimiter) -> FastAPI:
    """Minimal FastAPI app with rate-limiting middleware attached."""
    _app = FastAPI()
    middleware_cls, middleware_kwargs = build_rate_limit_middleware(
        authenticated_max_requests=10,
        anonymous_max_requests=3,
        window_seconds=60,
        limiter=limiter,
    )
    _app.add_middleware(middleware_cls, **middleware_kwargs)

    @_app.get("/chat")
    async def chat_endpoint():
        return {"message": "ok"}

    @_app.get("/api/v1/health")
    async def health_endpoint():
        return {"status": "ok"}

    return _app


# ---------------------------------------------------------------------------
# InMemoryRateLimiter unit tests
# ---------------------------------------------------------------------------

class TestInMemoryRateLimiter:

    @pytest.mark.asyncio
    async def test_allow_requests_within_limit(self, limiter, tight_config):
        """All requests within the quota must be allowed."""
        for i in range(tight_config.max_requests):
            limit, remaining, _ = await limiter.check("user:alice", tight_config)
            assert remaining == tight_config.max_requests - (i + 1)
            assert limit == tight_config.effective_max

    @pytest.mark.asyncio
    async def test_block_request_over_limit(self, limiter, tight_config):
        """The (max_requests + 1)-th request must raise RateLimitExceededError."""
        for _ in range(tight_config.max_requests):
            await limiter.check("user:bob", tight_config)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check("user:bob", tight_config)

        assert exc_info.value.retry_after_seconds >= 1

    @pytest.mark.asyncio
    async def test_sliding_window_expires_old_hits(self, limiter):
        """Hits older than window_seconds should fall out and free up quota."""
        config = RateLimitConfig(window_seconds=1, max_requests=2)

        await limiter.check("user:carol", config)
        await limiter.check("user:carol", config)

        # Both slots consumed — should now be blocked
        with pytest.raises(RateLimitExceededError):
            await limiter.check("user:carol", config)

        # Wait for the window to expire
        await asyncio.sleep(1.05)

        # Should be allowed again
        limit, remaining, _ = await limiter.check("user:carol", config)
        assert remaining == 1  # 2 effective_max - 1 new hit

    @pytest.mark.asyncio
    async def test_burst_allowance_respected(self, limiter):
        """Burst multiplier should extend the effective max correctly."""
        config = RateLimitConfig(window_seconds=60, max_requests=4, burst_allowance=1.5)
        assert config.effective_max == 6  # ceil(4 * 1.5)

        # 6 requests should all succeed
        for _ in range(6):
            await limiter.check("user:dave", config)

        # 7th should fail
        with pytest.raises(RateLimitExceededError):
            await limiter.check("user:dave", config)

    @pytest.mark.asyncio
    async def test_different_keys_are_isolated(self, limiter, tight_config):
        """Exceeding the limit for one key must not affect another."""
        # Exhaust alice's quota
        for _ in range(tight_config.max_requests):
            await limiter.check("user:alice", tight_config)
        with pytest.raises(RateLimitExceededError):
            await limiter.check("user:alice", tight_config)

        # Bob's quota must still be untouched
        limit, remaining, _ = await limiter.check("user:bob", tight_config)
        assert remaining == tight_config.effective_max - 1

    @pytest.mark.asyncio
    async def test_retry_after_seconds_is_positive(self, limiter, tight_config):
        """retry_after_seconds must always be >= 1."""
        for _ in range(tight_config.max_requests):
            await limiter.check("user:eve", tight_config)

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check("user:eve", tight_config)

        assert exc_info.value.retry_after_seconds >= 1

    @pytest.mark.asyncio
    async def test_reset_clears_state(self, limiter, tight_config):
        """reset() must wipe all recorded hits for the key."""
        for _ in range(tight_config.max_requests):
            await limiter.check("user:frank", tight_config)

        await limiter.reset("user:frank")

        # Should be allowed again after reset
        limit, remaining, _ = await limiter.check("user:frank", tight_config)
        assert remaining == tight_config.effective_max - 1

    @pytest.mark.asyncio
    async def test_concurrent_requests_thread_safe(self, limiter):
        """Concurrent coroutines must not race-condition the counter."""
        config = RateLimitConfig(window_seconds=60, max_requests=50)
        results = {"allowed": 0, "blocked": 0}

        async def make_request():
            try:
                await limiter.check("user:concurrent", config)
                results["allowed"] += 1
            except RateLimitExceededError:
                results["blocked"] += 1

        await asyncio.gather(*[make_request() for _ in range(60)])

        # Exactly max_requests should be allowed; the rest blocked
        assert results["allowed"] == 50
        assert results["blocked"] == 10


# ---------------------------------------------------------------------------
# RateLimitMiddleware integration tests (via HTTPX async client)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticated_user_higher_quota(app: FastAPI):
    """Authenticated users should have 10 requests/min, not 3."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            resp = await client.get("/chat", headers=_auth_headers("user-abc"))
            assert resp.status_code == 200

        # 11th request must be rate-limited
        resp = await client.get("/chat", headers=_auth_headers("user-abc"))
        assert resp.status_code == 429
        body = resp.json()
        assert "retry_after" in body
        assert body["retry_after"] >= 1


@pytest.mark.asyncio
async def test_anonymous_user_lower_quota(app: FastAPI):
    """Anonymous callers should be capped at 3 requests/min."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(3):
            resp = await client.get("/chat")  # no auth header
            assert resp.status_code == 200

        resp = await client.get("/chat")
        assert resp.status_code == 429


@pytest.mark.asyncio
async def test_skipped_paths_not_rate_limited(app: FastAPI):
    """Health and monitoring paths must bypass the rate limiter."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(20):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_headers_present(app: FastAPI):
    """Every non-exempt response must carry the three X-RateLimit-* headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/chat", headers=_auth_headers("header-user"))
        assert resp.status_code == 200
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers
        assert "x-ratelimit-reset" in resp.headers

        remaining = int(resp.headers["x-ratelimit-remaining"])
        limit = int(resp.headers["x-ratelimit-limit"])
        assert 0 <= remaining < limit
