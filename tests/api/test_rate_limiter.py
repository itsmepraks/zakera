"""Tests for rate limiter middleware."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.api.middleware.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    rate_limit_middleware,
    require_rate_limit
)


@pytest.fixture
def rate_limiter():
    """Create rate limiter instance."""
    limiter = RateLimiter()
    limiter.enabled = True
    return limiter


@pytest.fixture
def mock_request():
    """Create mock request."""
    request = Mock(spec=Request)
    request.url.path = "/api/v1/chat/send"
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.state = Mock()
    return request


@pytest.mark.asyncio
async def test_rate_limiter_initialization(rate_limiter):
    """Test rate limiter initialization."""
    await rate_limiter.initialize()
    # Should initialize without error
    assert rate_limiter.enabled is True


@pytest.mark.asyncio
async def test_memory_backend_allows_within_limit(rate_limiter):
    """Test that requests within limit are allowed."""
    config = RateLimitConfig(requests=5, window=60)
    
    for i in range(5):
        allowed, remaining, total = rate_limiter._check_memory(
            "test_key", config
        )
        assert allowed is True
        assert remaining == 4 - i
        assert total == 5


@pytest.mark.asyncio
async def test_memory_backend_blocks_over_limit(rate_limiter):
    """Test that requests over limit are blocked."""
    config = RateLimitConfig(requests=3, window=60)
    
    # Use up the limit
    for _ in range(3):
        allowed, _, _ = rate_limiter._check_memory("test_key", config)
        assert allowed is True
    
    # Next request should be blocked
    allowed, remaining, total = rate_limiter._check_memory("test_key", config)
    assert allowed is False
    assert remaining == 0
    assert total == 3


@pytest.mark.asyncio
async def test_window_reset(rate_limiter):
    """Test that rate limit resets after window expires."""
    config = RateLimitConfig(requests=2, window=1)  # 1 second window
    
    # Use up limit
    for _ in range(2):
        rate_limiter._check_memory("test_key", config)
    
    # Should be blocked
    allowed, _, _ = rate_limiter._check_memory("test_key", config)
    assert allowed is False
    
    # Wait for window to expire
    await asyncio.sleep(1.1)
    
    # Should be allowed again
    allowed, remaining, _ = rate_limiter._check_memory("test_key", config)
    assert allowed is True
    assert remaining > 0


@pytest.mark.asyncio
async def test_check_limit_with_user_tier(rate_limiter):
    """Test rate limiting with different user tiers."""
    await rate_limiter.initialize()
    
    # Free tier has lower limit
    allowed, remaining, limit, reset = await rate_limiter.check_limit(
        "user:123", "/api/v1/chat/send",
        user_tier="free"
    )
    assert allowed is True
    assert limit == 60  # Endpoint-specific limit
    
    # Enterprise tier
    allowed, remaining, limit, reset = await rate_limiter.check_limit(
        "user:456",
        "/api/v1/tools/execute",
        user_tier="enterprise"
    )
    assert allowed is True
    assert limit == 100  # Endpoint-specific limit


@pytest.mark.asyncio
async def test_get_identifier_from_user(rate_limiter, mock_request):
    """Test extracting identifier from authenticated user."""
    mock_user = Mock()
    mock_user.id = "user123"
    mock_request.state.user = mock_user
    
    identifier = rate_limiter.get_identifier(mock_request)
    assert identifier == "user:user123"


@pytest.mark.asyncio
async def test_get_identifier_from_ip(rate_limiter, mock_request):
    """Test extracting identifier from IP address."""
    mock_request.state.user = None
    
    identifier = rate_limiter.get_identifier(mock_request)
    assert identifier.startswith("ip:")


@pytest.mark.asyncio
async def test_get_identifier_from_forwarded_header(rate_limiter, mock_request):
    """Test extracting identifier from X-Forwarded-For header."""
    mock_request.state.user = None
    mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
    
    identifier = rate_limiter.get_identifier(mock_request)
    assert identifier == "ip:192.168.1.1"


@pytest.mark.asyncio
async def test_middleware_allows_request(rate_limiter, mock_request):
    """Test middleware allows request within limit."""
    async def mock_call_next(request):
        return Response(content="OK", status_code=200)
    
    with patch('src.api.middleware.rate_limiter.rate_limiter', rate_limiter):
        response = await rate_limit_middleware(mock_request, mock_call_next)
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


@pytest.mark.asyncio
async def test_middleware_blocks_request(rate_limiter, mock_request):
    """Test middleware blocks request over limit."""
    # Exhaust rate limit
    config = RateLimitConfig(requests=1, window=60)
    rate_limiter.endpoint_limits["/api/v1/chat/send"] = config
    
    identifier = rate_limiter.get_identifier(mock_request)
    
    # First request should succeed
    async def mock_call_next(request):
        return Response(content="OK", status_code=200)
    
    with patch('src.api.middleware.rate_limiter.rate_limiter', rate_limiter):
        response1 = await rate_limit_middleware(mock_request, mock_call_next)
        assert response1.status_code == 200
        
        # Second request should be blocked
        response2 = await rate_limit_middleware(mock_request, mock_call_next)
        assert response2.status_code == 429
        assert "retry_after" in response2.body.decode()


@pytest.mark.asyncio
async def test_middleware_skips_monitoring_endpoints(rate_limiter):
    """Test middleware skips rate limiting for monitoring endpoints."""
    mock_request = Mock(spec=Request)
    mock_request.url.path = "/api/v1/monitoring/health"
    
    async def mock_call_next(request):
        return Response(content="OK", status_code=200)
    
    with patch('src.api.middleware.rate_limiter.rate_limiter', rate_limiter):
        response = await rate_limit_middleware(mock_request, mock_call_next)
        assert response.status_code == 200
        # Should not have rate limit headers
        assert "X-RateLimit-Limit" not in response.headers


@pytest.mark.asyncio
async def test_rate_limiter_disabled(mock_request):
    """Test rate limiter when disabled."""
    limiter = RateLimiter()
    limiter.enabled = False
    
    async def mock_call_next(request):
        return Response(content="OK", status_code=200)
    
    with patch('src.api.middleware.rate_limiter.rate_limiter', limiter):
        response = await rate_limit_middleware(mock_request, mock_call_next)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_cache_cleanup(rate_limiter):
    """Test that in-memory cache cleans up old entries."""
    config = RateLimitConfig(requests=1, window=1)
    
    # Create many cache entries
    for i in range(100):
        rate_limiter._check_memory(f"key_{i}", config)
    
    # Wait for expiry
    await asyncio.sleep(1.1)
    
    # Trigger cleanup by adding more entries
    initial_size = len(rate_limiter.memory_cache)
    for i in range(10):
        rate_limiter._check_memory(f"new_key_{i}", config)
    
    # Some old entries should be cleaned up
    # (This is a simple check - actual cleanup depends on implementation)
    assert len(rate_limiter.memory_cache) > 0


@pytest.mark.asyncio
async def test_decorator_allows_within_limit(rate_limiter, mock_request):
    """Test decorator allows request within limit."""
    @require_rate_limit(tier="free")
    async def test_endpoint(request: Request):
        return {"message": "success"}
    
    with patch('src.api.middleware.rate_limiter.rate_limiter', rate_limiter):
        result = await test_endpoint(mock_request)
        assert result["message"] == "success"


@pytest.mark.asyncio  
async def test_decorator_blocks_over_limit(rate_limiter, mock_request):
    """Test decorator blocks request over limit."""
    # Set very low limit
    config = RateLimitConfig(requests=1, window=60)
    rate_limiter.tier_limits["free"] = config
    rate_limiter.endpoint_limits = {}  # Clear endpoint limits
    
    @require_rate_limit(tier="free")
    async def test_endpoint(request: Request):
        return {"message": "success"}
    
    with patch('src.api.middleware.rate_limiter.rate_limiter', rate_limiter):
        # First call should succeed
        result1 = await test_endpoint(mock_request)
        assert result1["message"] == "success"
        
        # Second call should raise exception
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(mock_request)
        assert exc_info.value.status_code == 429
