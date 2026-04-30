# API Guide

Zakera exposes a REST API on port 8000. Interactive docs are available at `/api/docs` (Swagger) and `/api/redoc` when the server is running.

## Authentication

All endpoints except health checks require a JWT token.

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "yourpassword"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "yourpassword"}'
```

This returns a JWT token. Use it in subsequent requests:
```
Authorization: Bearer <token>
```

## Core endpoints

### Conversations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/conversations` | Create a conversation |
| GET | `/api/v1/conversations` | List your conversations |
| GET | `/api/v1/conversations/{id}` | Get a conversation with messages |
| PUT | `/api/v1/conversations/{id}` | Update title, model, system prompt |
| DELETE | `/api/v1/conversations/{id}` | Delete a conversation |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Send a message, get a response |
| POST | `/api/v1/chat/stream` | Send a message, get an SSE stream |
| POST | `/api/v1/chat/retry` | Regenerate the last assistant message |
| WS | `/api/v1/ws/chat/{id}` | WebSocket streaming chat |

**Sending a message:**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "your-conversation-id",
    "message": "What is the capital of France?",
    "tools_enabled": false
  }'
```

**With tool use:**
Set `tools_enabled: true` and the model can call built-in tools (web search, calculator, etc.) before responding.

### Tools

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tools` | List available tools |
| POST | `/api/v1/tools/execute` | Execute a tool directly |

### Models

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/models` | List available model providers |
| GET | `/api/v1/models/{provider}` | Get provider details |

### Monitoring

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/monitoring/health` | Health check |
| GET | `/api/v1/monitoring/metrics` | Prometheus metrics |

## Streaming (SSE)

The `/api/v1/chat/stream` endpoint returns Server-Sent Events:

```
data: {"type": "chunk", "content": "The capital"}
data: {"type": "chunk", "content": " of France"}
data: {"type": "chunk", "content": " is Paris."}
data: {"type": "done", "content": "The capital of France is Paris."}
```

If `tools_enabled` is true and the model requests tool execution, you'll see:
```
data: {"type": "status", "message": "executing_tools"}
data: {"type": "chunk", "content": "Based on the search results..."}
data: {"type": "done", "content": "Based on the search results..."}
```

## WebSocket

Connect to `/api/v1/ws/chat/{conversation_id}` and send your auth token as the first message:

```json
{"token": "your-jwt-token"}
```

Then send messages:
```json
{"message": "Hello"}
```

Responses stream back as `{"type": "chunk", "content": "..."}` followed by `{"type": "complete", "message": {...}}`.

## Error handling

All errors return JSON with a `detail` field:

```json
{"detail": "Conversation not found", "type": "HTTPException", "request_id": "abc-123"}
```

Common status codes:
- `401` — missing or invalid token
- `404` — conversation not found or doesn't belong to you
- `502` — model provider error (upstream API failure)
- `429` — rate limited
