# Rate Limiting

## Overview

Zakera implements comprehensive rate limiting to ensure fair usage and protect against abuse. The system supports multiple strategies including per-user limits, endpoint-specific limits, and IP-based limits for unauthenticated requests.

## Features

### Multi-Backend Support

- **Redis Backend**: Distributed rate limiting for horizontal scaling
- **In-Memory Fallback**: Automatic fallback when Redis is unavailable
- **Sliding Window Algorithm**: More accurate rate limiting compared to fixed windows

### Flexible Configuration

- **Tier-Based Limits**: Different limits for free, pro, and enterprise users
- **Endpoint-Specific Limits**: Stricter limits for expensive operations
- **Burst Allowance**: Temporary burst capacity for spiky traffic

### Production-Ready

- **Low Latency**: Optimized for minimal overhead
- **Graceful Degradation**: Fails open on errors to prevent service disruption
- **Comprehensive Metrics**: Prometheus integration for monitoring
- **Standard Headers**: RFC-compliant rate limit headers

## Configuration

### Environment Variables

```bash
# Enable/disable rate limiting
ENABLE_RATE_LIMITING=true

# Redis connection (optional, falls back to in-memory)
REDIS_URL=redis://localhost:6379/1
```

### Default Limits

#### By User Tier

| Tier | Requests | Window | Burst |
|------|----------|--------|-------|
| Free | 100 | 1 hour | 10 |
| Pro | 1,000 | 1 hour | 50 |
| Enterprise | 10,000 | 1 hour | 200 |

#### By Endpoint

| Endpoint | Requests | Window |
|----------|----------|--------|
| `/api/v1/chat/send` | 60 | 1 minute |
| `/api/v1/chat/stream` | 30 | 1 minute |
| `/api/v1/tools/execute` | 100 | 1 minute |

## Usage

### Application-Wide Middleware

```python
from fastapi import FastAPI
from src.api.middleware.rate_limiter import rate_limit_middleware, rate_limiter

app = FastAPI()

@app.on_event("startup")
async def startup():
    await rate_limiter.initialize()

@app.on_event("shutdown")
async def shutdown():
    await rate_limiter.close()

app.middleware("http")(rate_limit_middleware)
```

### Endpoint-Specific Decorator

```python
from fastapi import APIRouter, Request
from src.api.middleware.rate_limiter import require_rate_limit

router = APIRouter()

@router.post("/expensive-operation")
@require_rate_limit(tier="pro")
async def expensive_operation(request: Request):
    # Only pro/enterprise users can access
    return {"status": "success"}
```

### Custom Rate Limits

```python
from src.api.middleware.rate_limiter import rate_limiter, RateLimitConfig

# Add custom endpoint limit
rate_limiter.endpoint_limits["/api/v1/custom"] = RateLimitConfig(
    requests=50,
    window=60,
    burst=10
)

# Add custom tier
rate_limiter.tier_limits["premium"] = RateLimitConfig(
    requests=5000,
    window=3600,
    burst=100
)
```

## Response Headers

All rate-limited responses include standard headers:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1709395200
```

When limit is exceeded (HTTP 429):

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1709395200
Retry-After: 30
```

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Limit: 60 per window.",
  "retry_after": 30
}
```

## Client Implementation

### Python

```python
import time
import requests

def make_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json={...})
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retrying in {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

### JavaScript

```javascript
async function makeRequestWithRetry(url, options, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const response = await fetch(url, options);
    
    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
      console.log(`Rate limited. Retrying in ${retryAfter}s...`);
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      continue;
    }
    
    return response;
  }
  
  throw new Error('Max retries exceeded');
}
```

## Monitoring

### Metrics

Prometheus metrics available:

```promql
# Total rate limit checks
rate_limit_requests_total{identifier, endpoint, status}

# Rate limit violations
rate_limit_exceeded_total{endpoint, user_tier}

# Active rate limit entries
active_rate_limits{backend}
```

### Example Queries

```promql
# Rate limit violation rate by endpoint
rate(rate_limit_exceeded_total[5m])

# Top users hitting rate limits
topk(10, sum by (identifier) (rate_limit_requests_total{status="blocked"}))

# Average remaining quota
avg(rate_limit_remaining) by (endpoint)
```

### Grafana Dashboard

Import the pre-built dashboard: `monitoring/grafana/dashboards/rate-limiting.json`

Key panels:
- Rate limit violations over time
- Top rate-limited endpoints
- Remaining quota distribution
- Backend performance (Redis vs memory)

## Architecture

### Sliding Window Algorithm

The rate limiter uses a sliding window algorithm for accurate counting:

```
Window: 60 seconds
Limit: 10 requests

Time:  0s    10s   20s   30s   40s   50s   60s
Reqs:  |--|  |-|   |--|  |--|  |-|   |--|  |
Count: 2     1     2     2     1     2     1

At 35s: Count last 60s = 2+1+2+2 = 7 (within limit ✓)
At 50s: Count last 60s = 1+2+2+1 = 6 (within limit ✓)
```

### Redis Storage

Requests are stored as sorted sets:

```
Key: ratelimit:hash(user:123:/api/v1/chat/send)
Value: Sorted Set {
  timestamp1: score1,
  timestamp2: score2,
  ...
}
TTL: window_size + 10 seconds
```

### In-Memory Storage

Fallback cache structure:

```python
{
  "ratelimit:hash": {
    "requests": [timestamp1, timestamp2, ...],
    "reset_at": unix_timestamp
  }
}
```

## Performance

### Benchmarks

| Backend | Latency (p50) | Latency (p99) | Throughput |
|---------|---------------|---------------|------------|
| Redis | 2ms | 5ms | 50,000 req/s |
| In-Memory | 0.1ms | 0.5ms | 100,000 req/s |

### Optimization Tips

1. **Use Redis for Production**: Better for distributed systems
2. **Adjust Window Size**: Larger windows = less overhead
3. **Monitor Cache Size**: In-memory cache auto-cleans at 10k entries
4. **Use Connection Pooling**: Redis connection pooling reduces latency

## Troubleshooting

### Redis Connection Issues

```log
WARNING: Failed to connect to Redis, using in-memory fallback
```

**Solution**: Check Redis connection string and ensure Redis is running:

```bash
redis-cli ping
# Should return: PONG
```

### High Rate Limit Violations

```log
WARNING: Rate limit exceeded - identifier=user:123, endpoint=/api/v1/chat/send
```

**Solutions**:
1. Increase limits for legitimate users
2. Implement client-side rate limiting
3. Cache responses when possible
4. Use batch endpoints for bulk operations

### Memory Issues (In-Memory Backend)

If in-memory cache grows too large:

1. Switch to Redis backend
2. Reduce window sizes
3. Adjust cleanup threshold (default: 10k entries)

## Security Considerations

### DDoS Protection

- Rate limiting helps mitigate DDoS attacks
- Combine with WAF (Web Application Firewall) for comprehensive protection
- Monitor for unusual traffic patterns

### Bypass Prevention

- Limits applied at application layer (not just IP)
- User authentication required for higher limits
- IP rotation detection via X-Forwarded-For monitoring

## Future Enhancements

- [ ] Dynamic rate limit adjustment based on system load
- [ ] Distributed rate limiting across multiple Redis instances
- [ ] Machine learning-based anomaly detection
- [ ] Per-resource rate limiting (e.g., per model, per tool)
- [ ] Rate limit purchase/upgrade flow
- [ ] Detailed rate limit analytics dashboard

## References

- [RFC 6585 - Additional HTTP Status Codes](https://tools.ietf.org/html/rfc6585)
- [IETF Draft - RateLimit Header Fields](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)
- [Redis Sorted Sets](https://redis.io/topics/data-types#sorted-sets)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Sliding Window Algorithm](https://en.wikipedia.org/wiki/Sliding_window_protocol)
