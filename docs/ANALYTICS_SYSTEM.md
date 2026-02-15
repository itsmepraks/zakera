# Conversation Analytics System

## Overview

The Conversation Analytics System provides comprehensive insights into user engagement, model performance, cost optimization, and system usage patterns. This production-ready feature seamlessly integrates with Zakera's existing monitoring infrastructure.

## Features

### 📊 Analytics Capabilities

#### 1. **Overview Metrics**
High-level dashboard metrics including:
- Total conversations and messages
- Active user counts
- Average messages per conversation
- Conversation success rate
- Model usage distribution

#### 2. **Conversation Analytics**
Detailed conversation insights:
- Duration statistics (avg, min, max)
- Message count distribution
- Daily conversation trends
- Top conversations by engagement
- Filtering by date range, user, or model

#### 3. **Model Performance Comparison**
Comprehensive model metrics:
- Total messages per model
- Average response times
- Token usage statistics (prompt/completion)
- Tokens per message ratios
- Performance benchmarking across providers

#### 4. **User Engagement Metrics**
User behavior analysis:
- Top users by activity
- Message patterns per user
- Weekly retention cohorts
- User activity trends
- Last activity timestamps

#### 5. **Cost Analysis**
Financial insights and optimization:
- Total estimated costs
- Daily average spending
- Monthly cost projections
- Per-model cost breakdown
- Cost per message analysis
- Token usage costs

#### 6. **Trend Analysis**
Time-series analysis:
- Daily conversation trends
- Message volume patterns
- User growth tracking
- Cost trend forecasting

#### 7. **Data Export**
Export capabilities:
- JSON format (structured)
- CSV format (tabular)
- All metric types supported
- Timestamped exports

## API Endpoints

### Base Path: `/api/v1/analytics`

All endpoints require authentication via JWT token.

#### GET `/overview`
Get high-level overview metrics.

**Query Parameters:**
- `start_date` (optional): ISO 8601 datetime, default: 30 days ago
- `end_date` (optional): ISO 8601 datetime, default: now

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/analytics/overview?start_date=2026-01-01T00:00:00"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_conversations": 1523,
    "total_messages": 8456,
    "active_users": 342,
    "avg_messages_per_conversation": 5.55,
    "success_rate": 92.3,
    "model_usage": {
      "gpt-4-turbo": 450,
      "llama3:8b": 723,
      "claude-3-sonnet": 350
    },
    "period": {
      "start": "2026-01-15T00:00:00",
      "end": "2026-02-14T23:59:59"
    }
  }
}
```

---

#### GET `/conversations`
Get detailed conversation metrics.

**Query Parameters:**
- `start_date` (optional): Filter start date
- `end_date` (optional): Filter end date
- `user_id` (optional): Filter by specific user
- `model` (optional): Filter by specific model

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/analytics/conversations?user_id=123&model=gpt-4-turbo"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "duration_stats": {
      "avg_seconds": 245.67,
      "max_seconds": 1823,
      "min_seconds": 12
    },
    "message_distribution": {
      "2": 45,
      "3": 67,
      "4": 89,
      "5": 102
    },
    "daily_counts": {
      "2026-02-10": 23,
      "2026-02-11": 34,
      "2026-02-12": 28
    },
    "top_conversations": [
      {
        "id": 456,
        "title": "Code Review Discussion",
        "message_count": 28,
        "duration_seconds": 1823,
        "created_at": "2026-02-10T14:23:45"
      }
    ]
  }
}
```

---

#### GET `/models`
Get model performance comparison.

**Query Parameters:**
- `start_date` (optional): Filter start date
- `end_date` (optional): Filter end date

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/analytics/models"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "models": {
      "gpt-4-turbo": {
        "total_messages": 450,
        "avg_response_time_ms": 2347.56,
        "total_tokens": 523456,
        "avg_prompt_tokens": 156.78,
        "avg_completion_tokens": 345.23,
        "tokens_per_message": 1163.24
      },
      "llama3:8b": {
        "total_messages": 723,
        "avg_response_time_ms": 876.34,
        "total_tokens": 456789,
        "avg_prompt_tokens": 142.34,
        "avg_completion_tokens": 289.12,
        "tokens_per_message": 631.76
      }
    },
    "period": {
      "start": "2026-01-15T00:00:00",
      "end": "2026-02-14T23:59:59"
    }
  }
}
```

---

#### GET `/users`
Get user engagement statistics.

**Query Parameters:**
- `start_date` (optional): Filter start date
- `end_date` (optional): Filter end date
- `top_n` (optional): Number of top users (1-100, default: 20)

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/analytics/users?top_n=10"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "top_users": [
      {
        "user_id": 123,
        "conversation_count": 145,
        "total_messages": 823,
        "avg_messages_per_conversation": 5.68,
        "last_activity": "2026-02-14T18:45:23"
      }
    ],
    "retention": {
      "weekly_data": [
        {
          "week": 1,
          "start_date": "2026-01-15T00:00:00",
          "end_date": "2026-01-22T00:00:00",
          "active_users": 156,
          "retention_rate": 100.0
        },
        {
          "week": 2,
          "start_date": "2026-01-22T00:00:00",
          "end_date": "2026-01-29T00:00:00",
          "active_users": 134,
          "retention_rate": 85.9
        }
      ],
      "total_weeks": 4
    }
  }
}
```

---

#### GET `/costs`
Get cost analysis and breakdown.

**Query Parameters:**
- `start_date` (optional): Filter start date
- `end_date` (optional): Filter end date

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/analytics/costs"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_cost_usd": 234.56,
    "daily_avg_cost_usd": 7.82,
    "monthly_projected_cost_usd": 234.60,
    "cost_breakdown": [
      {
        "model": "gpt-4-turbo",
        "message_count": 450,
        "prompt_tokens": 70551,
        "completion_tokens": 155354,
        "total_tokens": 225905,
        "estimated_cost_usd": 156.78,
        "cost_per_message": 0.348
      },
      {
        "model": "llama3:8b",
        "message_count": 723,
        "prompt_tokens": 102912,
        "completion_tokens": 209234,
        "total_tokens": 312146,
        "estimated_cost_usd": 0.0,
        "cost_per_message": 0.0
      }
    ],
    "period": {
      "start": "2026-01-15T00:00:00",
      "end": "2026-02-14T23:59:59",
      "days": 30
    }
  }
}
```

---

#### GET `/export`
Export analytics data in JSON or CSV format.

**Query Parameters:**
- `format`: Export format (`json` or `csv`)
- `metric_type`: Type of metrics (`overview`, `conversations`, `models`, `users`, `costs`)
- `start_date` (optional): Filter start date
- `end_date` (optional): Filter end date

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  -o analytics_export.json \
  "http://localhost:8000/api/v1/analytics/export?format=json&metric_type=overview"
```

---

#### GET `/trends`
Get time-series trend analysis.

**Query Parameters:**
- `metric`: Metric to analyze (`conversations`, `messages`, `users`, `costs`)
- `days`: Number of days to analyze (7-365, default: 30)

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/analytics/trends?metric=conversations&days=30"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "metric": "conversations",
    "daily_data": {
      "2026-01-15": 45,
      "2026-01-16": 52,
      "2026-01-17": 48
    },
    "trend": {
      "direction": "increasing",
      "percentage_change": 15.3
    },
    "period": {
      "days": 30,
      "start": "2026-01-15T00:00:00",
      "end": "2026-02-14T23:59:59"
    }
  }
}
```

---

## Enhanced Model Manager

The enhanced model manager provides robust error handling and reliability improvements.

### Features

#### 1. **Exponential Backoff Retry**
- Automatic retry with exponential backoff
- Configurable max retries (default: 3)
- Jitter to prevent thundering herd
- Smart error categorization

#### 2. **Circuit Breaker Pattern**
- Prevents cascading failures
- Three states: CLOSED, OPEN, HALF_OPEN
- Automatic recovery testing
- Configurable thresholds

#### 3. **Request Deduplication**
- Prevents duplicate API calls
- Hash-based request caching
- Configurable TTL (default: 5 seconds)
- Pending request coordination

#### 4. **Provider Health Tracking**
- Real-time health scores (0.0 to 1.0)
- Error rate monitoring
- Success/failure tracking
- Historical request data

### Configuration

```python
from src.model.enhanced_model_manager import (
    EnhancedModelManager,
    RetryConfig,
    CircuitBreakerConfig,
)

# Configure retry mechanism
retry_config = RetryConfig(
    max_retries=3,
    initial_delay=1.0,  # seconds
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)

# Configure circuit breaker
cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout=60.0,  # seconds
    window_size=100,
)

# Initialize manager
manager = EnhancedModelManager(
    retry_config=retry_config,
    circuit_breaker_config=cb_config,
)

# Generate with automatic retry
response = await manager.generate_with_retry(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": "Hello"}],
)

# Get provider health status
health = manager.get_provider_health_status()
print(health)
# {
#   "openai": {
#     "state": "closed",
#     "health_score": 0.98,
#     "error_rate": 0.02,
#     "total_requests": 1523,
#     "total_failures": 31
#   }
# }
```

### Error Categories

The system categorizes errors for appropriate handling:

- **RATE_LIMIT**: HTTP 429, retryable with longer delay
- **TIMEOUT**: Connection/read timeout, retryable
- **API_ERROR**: 500/503 errors, retryable
- **NETWORK_ERROR**: Connection issues, retryable
- **AUTHENTICATION**: 401/403, not retryable
- **INVALID_REQUEST**: 400 errors, not retryable
- **UNKNOWN**: Other errors, retryable with caution

## Integration

### Adding Analytics to API Routes

```python
from src.api.routes.analytics import router as analytics_router

app.include_router(analytics_router, prefix="/api/v1")
```

### Using in Your Application

```python
from src.api.analytics import analytics_service

# Get overview metrics
metrics = await analytics_service.get_overview_metrics(
    db=db_session,
    start_date=datetime.utcnow() - timedelta(days=7),
    end_date=datetime.utcnow(),
)

# Get cost analysis
costs = await analytics_service.get_cost_analysis(
    db=db_session,
)
```

## Prometheus Metrics

New metrics exposed for monitoring:

### Analytics Metrics
- `analytics_requests_total` - Total analytics requests (by endpoint, user)
- `analytics_request_duration_seconds` - Request duration histogram
- `analytics_query_duration_seconds` - Database query duration
- `analytics_cache_hits_total` - Cache hit counter
- `analytics_cache_misses_total` - Cache miss counter

### Model Reliability Metrics
- `model_retry_attempts_total` - Retry attempts by model and error category
- `model_circuit_breaker_state` - Circuit breaker state gauge
- `model_request_dedup_total` - Deduplicated request counter
- `model_provider_health_score` - Provider health score (0.0-1.0)
- `model_provider_error_rate` - Provider error rate gauge

## Grafana Dashboard Queries

### Analytics Overview Panel
```promql
# Total conversations in last 24h
increase(analytics_requests_total{endpoint="overview"}[24h])

# Average query duration
rate(analytics_query_duration_seconds_sum[5m]) 
  / rate(analytics_query_duration_seconds_count[5m])

# Cache hit rate
rate(analytics_cache_hits_total[5m]) 
  / (rate(analytics_cache_hits_total[5m]) + rate(analytics_cache_misses_total[5m]))
```

### Model Reliability Panel
```promql
# Retry rate by model
rate(model_retry_attempts_total[5m])

# Circuit breaker state
model_circuit_breaker_state{state="open"} > 0

# Provider health score
model_provider_health_score
```

## Performance Considerations

### Caching Strategy
- Overview metrics cached for 5 minutes
- Model performance cached for 5 minutes
- Request deduplication cache: 5 seconds
- Automatic cache cleanup

### Query Optimization
- Indexed date range filters
- Limited result sets (top N)
- Efficient aggregation queries
- Parameterized SQL to prevent injection

### Rate Limiting
- Consider rate limiting analytics endpoints
- Suggested: 10 requests/minute per user
- Export endpoint: 1 request/5 minutes

## Security

### Authentication
- All endpoints require JWT authentication
- User context available in `current_user`

### Authorization
- Consider role-based access control
- Admin-only access for sensitive metrics
- User can only see their own detailed data

### Data Privacy
- No PII exposed in analytics
- User IDs only (no names/emails)
- Message content not included
- Aggregate statistics only

## Testing

### Unit Tests
```python
# Test analytics service
async def test_overview_metrics():
    metrics = await analytics_service.get_overview_metrics(
        db=test_db,
        start_date=test_start,
        end_date=test_end,
    )
    assert metrics["total_conversations"] >= 0
    assert "model_usage" in metrics

# Test enhanced model manager
async def test_retry_mechanism():
    manager = EnhancedModelManager()
    response = await manager.generate_with_retry(
        model="test-model",
        messages=[{"role": "user", "content": "test"}],
    )
    assert response is not None
```

### Integration Tests
```bash
# Test analytics endpoints
pytest tests/test_analytics.py -v

# Test model manager reliability
pytest tests/test_enhanced_model_manager.py -v
```

## Troubleshooting

### High Query Duration
- Check database indexes
- Review query complexity
- Consider caching more aggressively
- Limit date ranges

### Circuit Breaker Opens Frequently
- Check provider API status
- Review rate limits
- Adjust failure threshold
- Increase timeout duration

### Cache Invalidation Issues
- Verify TTL settings
- Check cache cleanup job
- Monitor memory usage
- Review cache key generation

## Future Enhancements

- [ ] Real-time streaming analytics
- [ ] Custom metric definitions
- [ ] Scheduled report generation
- [ ] Email digest notifications
- [ ] Anomaly detection alerts
- [ ] A/B testing support
- [ ] Funnel analysis
- [ ] Cohort analysis enhancements

## Support

For questions or issues:
1. Check the [main README](../README.md)
2. Review [API documentation](./api-reference.md)
3. Open an issue on GitHub
4. Contact: Prakriti Bista

---

**Version**: 1.0.0  
**Status**: Production-Ready  
**Last Updated**: February 14, 2026
