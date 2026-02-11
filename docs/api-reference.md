# Zakera AI Chat Agent - API Reference

## Table of Contents

1. [Authentication](#authentication)
2. [Chat Endpoints](#chat-endpoints)
3. [Conversation Management](#conversation-management)
4. [Analytics & Export](#analytics--export)
5. [Search](#search)
6. [Rate Limiting](#rate-limiting)
7. [Error Handling](#error-handling)

## Base URL

```
Production: https://api.zakera.ai/v1
Development: http://localhost:8000/v1
```

## Authentication

All API requests require authentication using JWT tokens.

### Register User

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "username": "johndoe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "username": "johndoe"
  }
}
```

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

### Using Authentication Token

Include the token in the Authorization header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Chat Endpoints

### Send Message

Send a message and receive AI response.

```http
POST /chat/message
Authorization: Bearer {token}
Content-Type: application/json

{
  "conversation_id": "conv_123",
  "message": "What is machine learning?",
  "model": "gpt-4",
  "stream": false
}
```

**Response:**
```json
{
  "message_id": "msg_456",
  "conversation_id": "conv_123",
  "role": "assistant",
  "content": "Machine learning is a subset of artificial intelligence...",
  "timestamp": "2026-02-10T22:00:00Z",
  "tokens_used": 245
}
```

### Stream Message (WebSocket)

For real-time streaming responses:

```javascript
const ws = new WebSocket('ws://localhost:8000/chat/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    token: 'bearer_token',
    conversation_id: 'conv_123',
    message: 'Tell me about AI'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.content);
};
```

## Conversation Management

### Create Conversation

```http
POST /conversations
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Machine Learning Discussion",
  "model": "gpt-4"
}
```

### List Conversations

```http
GET /conversations?page=1&per_page=20
Authorization: Bearer {token}
```

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_123",
      "title": "Machine Learning Discussion",
      "created_at": "2026-02-10T20:00:00Z",
      "updated_at": "2026-02-10T22:00:00Z",
      "message_count": 15
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20
}
```

### Get Conversation Details

```http
GET /conversations/{conversation_id}
Authorization: Bearer {token}
```

### Delete Conversation

```http
DELETE /conversations/{conversation_id}
Authorization: Bearer {token}
```

## Analytics & Export

### Get Analytics Overview

```http
GET /analytics/overview?days=30
Authorization: Bearer {token}
```

**Response:**
```json
{
  "total_conversations": 45,
  "total_messages": 678,
  "avg_messages_per_conversation": 15.07,
  "total_tokens_used": 125430,
  "active_conversations_today": 5,
  "active_conversations_week": 18
}
```

### Export Conversations

```http
GET /analytics/export/conversations?format=json&start_date=2026-01-01
Authorization: Bearer {token}
```

Supports formats: `json`, `csv`

### Export Single Conversation

```http
GET /analytics/export/conversation/{conversation_id}?format=txt
Authorization: Bearer {token}
```

Supports formats: `json`, `csv`, `txt`

## Search

### Search Messages

```http
GET /search/messages?query=machine%20learning&limit=20
Authorization: Bearer {token}
```

**Query Parameters:**
- `query` (required): Search term
- `conversation_id` (optional): Filter by conversation
- `role` (optional): Filter by role (user/assistant/system)
- `start_date` (optional): Filter by date range
- `end_date` (optional): Filter by date range
- `limit` (optional, default: 20): Results per page
- `offset` (optional, default: 0): Pagination offset

### Search Conversations

```http
GET /search/conversations?query=ML%20tutorial
Authorization: Bearer {token}
```

### Universal Search

```http
GET /search/all?query=python
Authorization: Bearer {token}
```

Searches across both conversations and messages.

## Rate Limiting

API requests are rate-limited per user:

- **Standard Plan:** 100 requests/minute
- **Pro Plan:** 500 requests/minute
- **Enterprise:** Custom limits

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1644537600
```

## Error Handling

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The conversation_id field is required",
    "details": {
      "field": "conversation_id",
      "issue": "missing_field"
    }
  },
  "request_id": "req_abc123"
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request parameters |
| `AUTHENTICATION_ERROR` | 401 | Invalid or expired token |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Pagination

All list endpoints support pagination:

```http
GET /conversations?page=2&per_page=50
```

**Response includes pagination metadata:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 50,
    "total": 234,
    "total_pages": 5,
    "has_next": true,
    "has_prev": true
  }
}
```

## Webhooks

*(Coming Soon)*

Subscribe to events:
- `conversation.created`
- `conversation.updated`
- `message.created`
- `usage.limit_reached`

## SDK Examples

### Python

```python
import requests

class ZakeraClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.zakera.ai/v1"
    
    def send_message(self, conversation_id, message):
        response = requests.post(
            f"{self.base_url}/chat/message",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "conversation_id": conversation_id,
                "message": message
            }
        )
        return response.json()

client = ZakeraClient("your_api_key")
response = client.send_message("conv_123", "Hello!")
```

### JavaScript/TypeScript

```typescript
class ZakeraClient {
  constructor(private apiKey: string) {}
  
  async sendMessage(conversationId: string, message: string) {
    const response = await fetch('https://api.zakera.ai/v1/chat/message', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message: message
      })
    });
    return response.json();
  }
}

const client = new ZakeraClient('your_api_key');
const response = await client.sendMessage('conv_123', 'Hello!');
```

## Support

For API support:
- Email: api-support@zakera.ai
- Documentation: https://docs.zakera.ai
- Status Page: https://status.zakera.ai
