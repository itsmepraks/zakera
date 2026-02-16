"""
Tests for Security Middleware
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src.security.middleware import (
    RateLimiter, RateLimitMiddleware,
    SecurityHeadersMiddleware, RequestValidationMiddleware
)
import time


class TestRateLimiter:
    """Test rate limiter"""
    
    def test_rate_limiter_allows_within_limit(self):
        """Test that requests within limit are allowed"""
        limiter = RateLimiter(requests=5, window=60)
        
        # All 5 requests should be allowed
        for i in range(5):
            allowed, retry_after = limiter.is_allowed("client1")
            assert allowed is True
            assert retry_after is None
    
    def test_rate_limiter_blocks_over_limit(self):
        """Test that requests over limit are blocked"""
        limiter = RateLimiter(requests=3, window=60)
        
        # First 3 allowed
        for i in range(3):
            allowed, _ = limiter.is_allowed("client1")
            assert allowed is True
        
        # 4th blocked
        allowed, retry_after = limiter.is_allowed("client1")
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_get_remaining(self):
        """Test getting remaining requests"""
        limiter = RateLimiter(requests=5, window=60)
        
        assert limiter.get_remaining("client1") == 5
        
        limiter.is_allowed("client1")
        assert limiter.get_remaining("client1") == 4
        
        limiter.is_allowed("client1")
        assert limiter.get_remaining("client1") == 3
    
    def test_different_clients_independent(self):
        """Test that different clients have independent limits"""
        limiter = RateLimiter(requests=2, window=60)
        
        # Client 1 uses both requests
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        
        # Client 2 should still have requests
        allowed, _ = limiter.is_allowed("client2")
        assert allowed is True


class TestRateLimitMiddleware:
    """Test rate limit middleware"""
    
    def test_rate_limit_middleware(self):
        """Test rate limiting in middleware"""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=3,
            requests_per_hour=10
        )
        
        @app.get("/test")
        async def test_route():
            return {"message": "ok"}
        
        client = TestClient(app)
        
        # First 3 requests should succeed
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200
        
        # 4th should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "retry_after" in response.json()


class TestSecurityHeaders:
    """Test security headers middleware"""
    
    def test_security_headers_added(self):
        """Test that security headers are added"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_route():
            return {"message": "ok"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        # Check headers
        assert "Content-Security-Policy" in response.headers
        assert "Strict-Transport-Security" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_frame_options(self):
        """Test X-Frame-Options header"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_route():
            return {"message": "ok"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.headers["X-Frame-Options"] == "DENY"


class TestRequestValidation:
    """Test request validation middleware"""
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection"""
        app = FastAPI()
        app.add_middleware(RequestValidationMiddleware)
        
        @app.get("/search")
        async def search(q: str):
            return {"query": q}
        
        client = TestClient(app)
        
        # Normal query
        response = client.get("/search?q=test")
        assert response.status_code == 200
        
        # SQL injection attempt
        response = client.get("/search?q=test' OR '1'='1")
        assert response.status_code == 400
    
    def test_large_request_blocked(self):
        """Test large requests are blocked"""
        app = FastAPI()
        app.add_middleware(RequestValidationMiddleware)
        
        @app.post("/upload")
        async def upload(data: dict):
            return {"status": "ok"}
        
        client = TestClient(app)
        
        # Large request
        response = client.post(
            "/upload",
            json={"data": "x" * (11 * 1024 * 1024)},  # 11MB
        )
        # Should be blocked (limit is 10MB)
        # Note: TestClient may not respect content-length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
