# Redis Caching Layer

Comprehensive Redis caching implementation for Zakera AI Chat Agent.

## Overview

The Redis caching layer provides high-performance caching for:
- Conversation data
- Model responses
- Tool execution results
- User sessions
- Rate limiting

## Features

✅ **Connection Management**
- Connection pooling
- Automatic reconnection
- Health monitoring
- Circuit breaker pattern

✅ **Cache Services**
- Conversation caching
- Model response caching
- Tool result caching
- User session management
- Rate limiting

✅ **Performance**
- Pipeline operations
- Batch operations
- Cache warming
- Key compression

✅ **Reliability**
- Error handling
- Graceful degradation
- Retry logic
- Timeout management

✅ **Monitoring**
- Hit/miss rates
- Performance metrics
- Health checks
- Prometheus integration

## Quick Start

### 1. Install Dependencies

```bash
pip install redis[hiredis] aioredis
```

### 2. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Or using docker-compose
docker-compose up -d redis
```

### 3. Configure Environment

```bash
# .env file
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_ENABLE_CACHE_WARMING=true
```

### 4. Initialize in Application

```python
from src.utils.cache_manager import cache_manager

# In your FastAPI startup event
@app.on_event("startup")
async def startup():
    await cache_manager.connect()
    print("Redis cache connected")

@app.on_event("shutdown")
async def shutdown():
    await cache_manager.disconnect()
    print("Redis cache disconnected")
```

## Usage Examples

### Function Caching

```python
from src.utils.cache_decorators import cached

@cached(ttl=600, key_prefix="user")
async def get_user(user_id: str):
    # This will be cached for 10 minutes
    user = await db.get_user(user_id)
    return user

# Invalidate cache
await get_user.invalidate(user_id="123")
```

### FastAPI Route Caching

```python
from src.utils.cache_decorators import cache_route

@router.get("/conversations/{conversation_id}")
@cache_route(ttl=300, vary_on=["conversation_id", "user_id"])
async def get_conversation(
    conversation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    conversation = await db.get_conversation(conversation_id)
    return conversation
```

### Conversation Caching

```python
from src.utils.cache_services import ConversationCache

# Get from cache
conversation = await ConversationCache.get(conversation_id)

if not conversation:
    # Fetch from database
    conversation = await db.get_conversation(conversation_id)
    
    # Store in cache
    await ConversationCache.set(
        conversation_id,
        conversation.to_dict(),
        ttl=3600,
    )

# Delete from cache
await ConversationCache.delete(conversation_id)
```

### Model Response Caching

```python
from src.utils.cache_services import ModelResponseCache

# Check cache first
response = await ModelResponseCache.get(
    model="gpt-3.5-turbo",
    prompt="What is AI?",
    temperature=0.7,
    max_tokens=100,
)

if not response:
    # Call model
    response = await model_provider.generate(prompt, **params)
    
    # Cache response
    await ModelResponseCache.set(
        model="gpt-3.5-turbo",
        prompt="What is AI?",
        response=response,
        ttl=7200,
        temperature=0.7,
        max_tokens=100,
    )
```

### Tool Result Caching

```python
from src.utils.cache_services import ToolResultCache

# Check cache
result = await ToolResultCache.get(
    tool_name="calculator",
    parameters={"expression": "2+2"},
)

if not result:
    # Execute tool
    result = await tool_executor.execute("calculator", {"expression": "2+2"})
    
    # Cache result
    await ToolResultCache.set(
        tool_name="calculator",
        parameters={"expression": "2+2"},
        result=result,
        ttl=1800,
    )
```

### Rate Limiting

```python
from src.utils.cache_services import RateLimitCache
from fastapi import HTTPException

async def check_rate_limit(user_id: str, endpoint: str):
    count = await RateLimitCache.increment(
        user_id=user_id,
        endpoint=endpoint,
        window_seconds=60,
    )
    
    if count > 60:  # 60 requests per minute
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
        )
```

### User Session Management

```python
from src.utils.cache_services import UserSessionCache

# Store session
await UserSessionCache.set(
    user_id="user123",
    session_data={
        "username": "john",
        "preferences": {"theme": "dark"},
        "last_active": datetime.utcnow().isoformat(),
    },
    ttl=7200,
)

# Get session
session = await UserSessionCache.get("user123")

# Refresh session expiration
await UserSessionCache.refresh("user123", ttl=7200)

# Delete session (logout)
await UserSessionCache.delete("user123")
```

## Cache Warming

### Automatic Warming

```python
from src.utils.cache_warming import start_cache_warming

# In FastAPI startup
@app.on_event("startup")
async def startup():
    # Start cache warming background task
    await start_cache_warming(
        db_session=db.session,
        interval_minutes=30,
        priority="normal",
    )
```

### Manual Warming

```python
from src.utils.cache_warming import CacheWarmer

warmer = CacheWarmer(db_session)

# Warm popular conversations
await warmer.warm_popular_conversations(limit=100)

# Warm active user sessions
await warmer.warm_active_user_sessions(hours=24)

# Warm all
results = await warmer.warm_all(priority="high")
```

## Monitoring

### Cache Status API

```bash
# Get cache status
curl http://localhost:8000/api/v1/monitoring/cache/status

# Get statistics
curl http://localhost:8000/api/v1/monitoring/cache/stats

# Health check
curl http://localhost:8000/api/v1/monitoring/cache/health
```

### Response

```json
{
  "healthy": true,
  "connected": true,
  "statistics": {
    "hits": 1250,
    "misses": 150,
    "sets": 200,
    "deletes": 10,
    "errors": 2,
    "hit_rate": 0.893
  },
  "circuit_breaker": {
    "is_open": false,
    "failures": 0,
    "threshold": 5
  }
}
```

### Prometheus Metrics

```python
# Add to your metrics collection
from prometheus_client import Counter, Histogram, Gauge

cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')
cache_latency = Histogram('cache_operation_seconds', 'Cache operation latency')
cache_size = Gauge('cache_keys_total', 'Total cached keys')
```

## Configuration

### Environment Variables

```bash
# Redis Connection
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_password  # Optional
REDIS_SSL=false

# Connection Pool
REDIS_MAX_CONNECTIONS=50
REDIS_MIN_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_RETRY_ON_TIMEOUT=true
REDIS_MAX_RETRIES=3

# TTL Defaults (seconds)
REDIS_DEFAULT_TTL=300
REDIS_CONVERSATION_TTL=3600
REDIS_MODEL_RESPONSE_TTL=7200
REDIS_TOOL_RESULT_TTL=1800
REDIS_SESSION_TTL=7200

# Cache Warming
REDIS_ENABLE_CACHE_WARMING=true
REDIS_WARMING_INTERVAL_MINUTES=30
REDIS_WARMING_PRIORITY=normal

# Circuit Breaker
REDIS_CIRCUIT_BREAKER_THRESHOLD=5
REDIS_CIRCUIT_BREAKER_TIMEOUT=60
```

### Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  app:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy

volumes:
  redis_data:
```

## Best Practices

### 1. Use Appropriate TTLs

```python
# Short TTL for frequently changing data
await cache_manager.set("user_status", status, ttl=60)

# Long TTL for static data
await cache_manager.set("model_metadata", metadata, ttl=86400)

# No TTL for permanent cache
await cache_manager.set("app_config", config)
```

### 2. Implement Cache-Aside Pattern

```python
async def get_conversation(conversation_id: str):
    # Try cache first
    cached = await ConversationCache.get(conversation_id)
    if cached:
        return cached
    
    # Fetch from database
    conversation = await db.get_conversation(conversation_id)
    
    # Update cache
    await ConversationCache.set(conversation_id, conversation)
    
    return conversation
```

### 3. Handle Cache Failures Gracefully

```python
try:
    result = await cache_manager.get(key)
except Exception as e:
    logger.error(f"Cache error: {e}")
    # Fall back to database
    result = await db.query(...)
```

### 4. Use Cache Warming for Hot Data

```python
# Warm cache during off-peak hours
await warmer.warm_popular_conversations(limit=1000)
```

### 5. Monitor Cache Performance

```python
# Track metrics
stats = await cache_manager.get_stats()
if stats["hit_rate"] < 0.7:
    logger.warning("Low cache hit rate, consider adjusting TTLs")
```

## Troubleshooting

### Connection Issues

```python
# Check connection
if not await cache_manager.is_healthy():
    logger.error("Redis not healthy")
    await cache_manager.connect()
```

### Memory Issues

```bash
# Monitor Redis memory
redis-cli info memory

# Set eviction policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Performance Issues

```python
# Use pipelines for bulk operations
async with cache_manager.redis.pipeline() as pipe:
    for key, value in data.items():
        pipe.set(key, value)
    await pipe.execute()
```

### Circuit Breaker Open

```python
# Check circuit breaker status
if cache_manager.circuit_breaker["is_open"]:
    logger.warning("Circuit breaker open, cache unavailable")
    # Wait for timeout or manually reset
```

## Performance Tips

1. **Use Connection Pooling**: Configure appropriate pool size
2. **Batch Operations**: Use `get_many` and `set_many` for multiple keys
3. **Compression**: Enable compression for large values
4. **Key Design**: Use consistent, hierarchical key naming
5. **TTL Strategy**: Balance between freshness and hit rate

## Security

1. **Authentication**: Use Redis passwords in production
2. **Encryption**: Enable TLS for sensitive data
3. **Network**: Use private networks for Redis
4. **Access Control**: Limit Redis commands
5. **Data Privacy**: Don't cache PII without encryption

## Resources

- [Redis Documentation](https://redis.io/documentation)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [Caching Best Practices](https://aws.amazon.com/caching/best-practices/)

---

**Last Updated**: February 2026  
**Version**: 1.0.0
