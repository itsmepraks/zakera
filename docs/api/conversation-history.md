# Conversation History API

The Conversation History API provides endpoints for managing chat conversations, including listing, searching, archiving, and metadata tracking.

## Overview

The API enables:
- **Conversation Management**: Create, retrieve, update, delete conversations
- **Search & Filter**: Find conversations by content, date, or metadata
- **Organization**: Pin, archive, and group conversations
- **Analytics**: Track tokens, costs, and usage metrics
- **Real-time Updates**: WebSocket support for live updates

## Base URL

```
http://localhost:8000/api/v1
```

Production:
```
https://your-domain.com/api/v1
```

## Authentication

All endpoints require authentication via JWT token:

```bash
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### List Conversations

Retrieve all conversations for the authenticated user.

**Endpoint**: `GET /conversations`

**Query Parameters**:
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20, max: 100)
- `sort` (string, optional): Sort field (timestamp, title, message_count)
- `order` (string, optional): Sort order (asc, desc)
- `archived` (boolean, optional): Include archived conversations
- `pinned` (boolean, optional): Filter pinned conversations

**Example Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/conversations?page=1&limit=20&sort=timestamp&order=desc" \
  -H "Authorization: Bearer your_token_here"
```

**Example Response**:

```json
{
  "conversations": [
    {
      "id": "conv_abc123",
      "title": "Python Best Practices",
      "lastMessage": "Great! That helps clarify the concept.",
      "timestamp": "2026-03-09T22:30:00Z",
      "messageCount": 15,
      "tokenCount": 4523,
      "cost": 0.0234,
      "isPinned": true,
      "isArchived": false,
      "model": "gemini-2.0-flash-exp",
      "metadata": {
        "tags": ["programming", "python"],
        "category": "development"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

### Get Conversation

Retrieve a specific conversation with all messages.

**Endpoint**: `GET /conversations/{conversation_id}`

**Path Parameters**:
- `conversation_id` (string, required): Conversation ID

**Example Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/conversations/conv_abc123" \
  -H "Authorization: Bearer your_token_here"
```

**Example Response**:

```json
{
  "id": "conv_abc123",
  "title": "Python Best Practices",
  "createdAt": "2026-03-09T20:00:00Z",
  "updatedAt": "2026-03-09T22:30:00Z",
  "messageCount": 15,
  "tokenCount": 4523,
  "cost": 0.0234,
  "isPinned": true,
  "isArchived": false,
  "model": "gemini-2.0-flash-exp",
  "messages": [
    {
      "id": "msg_xyz789",
      "role": "user",
      "content": "What are Python best practices?",
      "timestamp": "2026-03-09T20:00:00Z",
      "tokens": 8
    },
    {
      "id": "msg_xyz790",
      "role": "assistant",
      "content": "Here are some Python best practices...",
      "timestamp": "2026-03-09T20:00:05Z",
      "tokens": 245,
      "model": "gemini-2.0-flash-exp",
      "cost": 0.0012
    }
  ],
  "metadata": {
    "tags": ["programming", "python"],
    "category": "development"
  }
}
```

### Create Conversation

Create a new conversation.

**Endpoint**: `POST /conversations`

**Request Body**:

```json
{
  "title": "New Chat",
  "model": "gemini-2.0-flash-exp",
  "metadata": {
    "tags": ["general"],
    "category": "uncategorized"
  }
}
```

**Example Request**:

```bash
curl -X POST "http://localhost:8000/api/v1/conversations" \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Chat",
    "model": "gemini-2.0-flash-exp"
  }'
```

**Example Response**:

```json
{
  "id": "conv_def456",
  "title": "New Chat",
  "createdAt": "2026-03-09T23:00:00Z",
  "updatedAt": "2026-03-09T23:00:00Z",
  "messageCount": 0,
  "tokenCount": 0,
  "cost": 0,
  "isPinned": false,
  "isArchived": false,
  "model": "gemini-2.0-flash-exp",
  "messages": [],
  "metadata": {
    "tags": ["general"],
    "category": "uncategorized"
  }
}
```

### Update Conversation

Update conversation metadata.

**Endpoint**: `PATCH /conversations/{conversation_id}`

**Request Body**:

```json
{
  "title": "Updated Title",
  "isPinned": true,
  "isArchived": false,
  "metadata": {
    "tags": ["important", "review"],
    "category": "work"
  }
}
```

**Example Request**:

```bash
curl -X PATCH "http://localhost:8000/api/v1/conversations/conv_abc123" \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "isPinned": true
  }'
```

### Delete Conversation

Delete a conversation permanently.

**Endpoint**: `DELETE /conversations/{conversation_id}`

**Example Request**:

```bash
curl -X DELETE "http://localhost:8000/api/v1/conversations/conv_abc123" \
  -H "Authorization: Bearer your_token_here"
```

**Example Response**:

```json
{
  "success": true,
  "message": "Conversation deleted successfully"
}
```

### Search Conversations

Search conversations by content or metadata.

**Endpoint**: `POST /conversations/search`

**Request Body**:

```json
{
  "query": "python best practices",
  "filters": {
    "dateFrom": "2026-03-01T00:00:00Z",
    "dateTo": "2026-03-10T00:00:00Z",
    "tags": ["programming"],
    "minTokens": 1000,
    "maxCost": 0.5
  },
  "sort": "relevance",
  "limit": 20
}
```

**Example Response**:

```json
{
  "results": [
    {
      "id": "conv_abc123",
      "title": "Python Best Practices",
      "snippet": "...Python best practices include using virtual environments...",
      "relevanceScore": 0.95,
      "timestamp": "2026-03-09T22:30:00Z",
      "messageCount": 15,
      "tokenCount": 4523
    }
  ],
  "total": 3
}
```

### Pin/Unpin Conversation

**Endpoint**: `POST /conversations/{conversation_id}/pin`

**Example Request**:

```bash
curl -X POST "http://localhost:8000/api/v1/conversations/conv_abc123/pin" \
  -H "Authorization: Bearer your_token_here"
```

### Archive/Unarchive Conversation

**Endpoint**: `POST /conversations/{conversation_id}/archive`

**Example Request**:

```bash
curl -X POST "http://localhost:8000/api/v1/conversations/conv_abc123/archive" \
  -H "Authorization: Bearer your_token_here"
```

### Get Conversation Statistics

Retrieve aggregated statistics.

**Endpoint**: `GET /conversations/stats`

**Example Response**:

```json
{
  "totalConversations": 45,
  "totalMessages": 892,
  "totalTokens": 234567,
  "totalCost": 12.34,
  "averageMessagesPerConversation": 19.8,
  "byModel": {
    "gemini-2.0-flash-exp": 30,
    "claude-3-5-sonnet-20241022": 15
  },
  "byPeriod": {
    "today": 5,
    "thisWeek": 12,
    "thisMonth": 45
  }
}
```

## WebSocket API

Real-time updates for conversation changes.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/conversations');

// Send authentication
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your_jwt_token'
}));
```

### Events

#### Conversation Created

```json
{
  "type": "conversation.created",
  "data": {
    "id": "conv_new123",
    "title": "New Chat",
    "timestamp": "2026-03-09T23:00:00Z"
  }
}
```

#### Conversation Updated

```json
{
  "type": "conversation.updated",
  "data": {
    "id": "conv_abc123",
    "changes": {
      "title": "Updated Title",
      "isPinned": true
    }
  }
}
```

#### Conversation Deleted

```json
{
  "type": "conversation.deleted",
  "data": {
    "id": "conv_abc123"
  }
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "ValidationError",
  "message": "Invalid request parameters",
  "details": {
    "field": "limit",
    "message": "Must be between 1 and 100"
  }
}
```

### 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Invalid or expired authentication token"
}
```

### 404 Not Found

```json
{
  "error": "NotFound",
  "message": "Conversation not found"
}
```

### 429 Too Many Requests

```json
{
  "error": "RateLimitExceeded",
  "message": "Too many requests",
  "retryAfter": 60
}
```

## Rate Limits

- **Anonymous**: 10 requests/minute
- **Authenticated**: 100 requests/minute
- **Premium**: 1000 requests/minute

## Best Practices

### 1. Use Pagination

Always paginate large result sets:

```bash
GET /conversations?page=1&limit=20
```

### 2. Implement Caching

Cache conversation lists client-side:

```javascript
const cache = new Map();
const cacheKey = `conversations-${page}-${limit}`;

if (cache.has(cacheKey)) {
  return cache.get(cacheKey);
}
```

### 3. Use WebSocket for Updates

Subscribe to real-time updates instead of polling:

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'conversation.updated') {
    updateConversationInUI(data.data);
  }
};
```

### 4. Handle Errors Gracefully

```javascript
try {
  const response = await fetch('/api/v1/conversations');
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
} catch (error) {
  console.error('Failed to fetch conversations:', error);
  showErrorToUser(error.message);
}
```

## SDK Examples

### JavaScript/TypeScript

```typescript
import { ConversationClient } from '@zakera/sdk';

const client = new ConversationClient({
  baseUrl: 'http://localhost:8000',
  token: 'your_jwt_token'
});

// List conversations
const conversations = await client.list({
  page: 1,
  limit: 20,
  sort: 'timestamp',
  order: 'desc'
});

// Get conversation
const conversation = await client.get('conv_abc123');

// Create conversation
const newConv = await client.create({
  title: 'New Chat',
  model: 'gemini-2.0-flash-exp'
});

// Update conversation
await client.update('conv_abc123', {
  isPinned: true
});

// Delete conversation
await client.delete('conv_abc123');
```

### Python

```python
from zakera_sdk import ConversationClient

client = ConversationClient(
    base_url="http://localhost:8000",
    token="your_jwt_token"
)

# List conversations
conversations = client.list(
    page=1,
    limit=20,
    sort="timestamp",
    order="desc"
)

# Get conversation
conversation = client.get("conv_abc123")

# Create conversation
new_conv = client.create(
    title="New Chat",
    model="gemini-2.0-flash-exp"
)

# Update conversation
client.update("conv_abc123", is_pinned=True)

# Delete conversation
client.delete("conv_abc123")
```

## Additional Resources

- [Authentication Guide](../AUTHENTICATION_GUIDE.md)
- [Rate Limiting Documentation](../RATE_LIMITING.md)
- [WebSocket Guide](../websockets.md)
- [Error Handling Best Practices](../error-handling.md)
