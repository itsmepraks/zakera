# Zakera AI Chat Agent — REST API Reference

> **Version:** v1  
> **Base URL:** `http://localhost:8000/api/v1`  
> **Content-Type:** `application/json` (all requests and responses unless noted)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication](#2-authentication)
3. [Chat Completions](#3-chat-completions)
4. [Conversations](#4-conversations)
5. [Models](#5-models)
6. [Health & Metrics](#6-health--metrics)
7. [Error Reference](#7-error-reference)
8. [Rate Limiting](#8-rate-limiting)
9. [Streaming SSE Format](#9-streaming-sse-format)
10. [SDK Snippets](#10-sdk-snippets)

---

## 1. Architecture Overview

```
Browser / API Client
       │
       │  HTTPS
       ▼
  ┌─────────────┐
  │  Nginx (TLS) │   ← SSL termination, static assets, WS upgrade
  └─────┬───────┘
         │  HTTP/1.1
         ▼
  ┌─────────────────────────┐
  │   FastAPI (Uvicorn)        │   ← JWT auth, rate-limit, CORS middlewares
  │   src/api/main.py          │
  └──────┬──────────────────┘
         │
    ┌───┴─────────┐
    │             │
    ▼             ▼
┌────────────┐  ┌──────────────┐
│ ModelManager │  │  ConvService  │   ← SQLAlchemy + aiosqlite / Postgres
│ src/model/   │  │  src/api/     │
└───┬────────┘  └──────────────┘
     │
     ▼
┌────────────────────────────────────────────────────┐
│  Provider Registry                                  │
│  Anthropic | OpenAI | Gemini | Groq | Ollama | …   │
└────────────────────────────────────────────────────┘
```

All AI calls are **async** and support **server-sent events (SSE)** for
streaming.  The `ModelManager` selects the correct provider module based on
the `provider` field in the request.

---

## 2. Authentication

Zakera uses **JWT Bearer tokens** for all protected endpoints.

### 2.1 Register

```
POST /auth/register
```

**Request body**

```jsonc
{
  "email": "user@example.com",
  "password": "S3cretP@ss!",
  "full_name": "Prakriti Bista"  // optional
}
```

**Response `201 Created`**

```jsonc
{
  "id": "usr_01j9z4...",
  "email": "user@example.com",
  "full_name": "Prakriti Bista",
  "created_at": "2026-03-10T22:00:00Z"
}
```

---

### 2.2 Login

```
POST /auth/login
```

Accepts `application/x-www-form-urlencoded` **or** JSON.

**Request body**

```jsonc
{
  "username": "user@example.com",
  "password": "S3cretP@ss!"
}
```

**Response `200 OK`**

```jsonc
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800   // seconds
}
```

---

### 2.3 Refresh Token

```
POST /auth/refresh
```

**Request body**

```jsonc
{ "refresh_token": "eyJhbGciOiJIUzI1NiJ9..." }
```

**Response `200 OK`** — same shape as `/auth/login`.

---

### 2.4 Using the Access Token

Add the `Authorization` header to every protected request:

```
Authorization: Bearer <access_token>
```

---

## 3. Chat Completions

### 3.1 Non-Streaming Completion

```
POST /chat/completions
```

> Requires authentication.

**Request body**

```jsonc
{
  // Required
  "messages": [
    { "role": "system",    "content": "You are a helpful assistant." },
    { "role": "user",      "content": "Explain quantum entanglement simply." }
  ],

  // Optional — model selection
  "model":    "claude-3-7-sonnet-20250219",  // default: env DEFAULT_MODEL
  "provider": "anthropic",                   // auto-detected if omitted

  // Optional — generation parameters
  "temperature":  0.7,    // 0.0 – 1.0, default 0.7
  "max_tokens":   2048,   // default 4096
  "top_p":        1.0,
  "stream":       false,  // set true → see 3.2

  // Optional — conversation linkage
  "conversation_id": "conv_abc123",  // links reply to an existing conversation

  // Optional — Claude extended thinking
  "extended_thinking": true,    // only valid on claude-3-7-sonnet-20250219
  "thinking_budget":   8192     // token budget for thinking block
}
```

**Response `200 OK`**

```jsonc
{
  "id":      "chatcmpl_xyz789",
  "object":  "chat.completion",
  "created": 1741647600,
  "model":   "claude-3-7-sonnet-20250219",
  "provider": "anthropic",
  "choices": [
    {
      "index": 0,
      "message": {
        "role":    "assistant",
        "content": "Quantum entanglement is when two particles..."
      },
      "finish_reason": "end_turn"
    }
  ],
  "usage": {
    "prompt_tokens":     42,
    "completion_tokens": 187,
    "total_tokens":      229,
    "cost_usd":          0.003427
  },
  // Present only when extended_thinking=true
  "thinking": "Let me reason through this step by step..."
}
```

**curl example**

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role":"user","content":"Hello!"}],
    "model": "gpt-4o",
    "provider": "openai"
  }'
```

---

### 3.2 Streaming Completion (SSE)

Set `"stream": true` in the request body above.  The response changes to
`text/event-stream` with chunked transfer encoding.

See [Section 9](#9-streaming-sse-format) for the full SSE event format.

**curl example**

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Count to 5."}],"stream":true}'
```

---

## 4. Conversations

Conversations persist message history and link to a user account.

### 4.1 List Conversations

```
GET /conversations?page=1&per_page=20&sort=updated_at&order=desc
```

**Query parameters**

| Name       | Type    | Default | Description                          |
|------------|---------|---------|--------------------------------------|
| `page`     | integer | `1`     | Page number (1-indexed)              |
| `per_page` | integer | `20`    | Items per page, max `100`            |
| `sort`     | string  | `updated_at` | `created_at` \| `updated_at` \| `title` |
| `order`    | string  | `desc`  | `asc` \| `desc`                     |
| `search`   | string  | —       | Full-text search across titles       |
| `model`    | string  | —       | Filter by model used                 |

**Response `200 OK`**

```jsonc
{
  "items": [
    {
      "id":          "conv_abc123",
      "title":       "Quantum Physics Q&A",
      "model":       "claude-3-7-sonnet-20250219",
      "provider":    "anthropic",
      "message_count": 14,
      "created_at":  "2026-03-10T20:00:00Z",
      "updated_at":  "2026-03-10T22:00:00Z"
    }
  ],
  "total":    42,
  "page":     1,
  "per_page": 20,
  "pages":    3
}
```

---

### 4.2 Get Conversation

```
GET /conversations/{conversation_id}
```

Returns the conversation metadata **and** its full message list.

**Response `200 OK`**

```jsonc
{
  "id":       "conv_abc123",
  "title":    "Quantum Physics Q&A",
  "model":    "claude-3-7-sonnet-20250219",
  "messages": [
    { "id": "msg_1", "role": "user",      "content": "Explain entanglement.", "created_at": "2026-03-10T20:01:00Z" },
    { "id": "msg_2", "role": "assistant", "content": "Quantum entanglement...", "created_at": "2026-03-10T20:01:05Z",
      "tokens_used": 187, "cost_usd": 0.003427 }
  ],
  "created_at": "2026-03-10T20:00:00Z",
  "updated_at": "2026-03-10T22:00:00Z"
}
```

---

### 4.3 Create Conversation

```
POST /conversations
```

**Request body**

```jsonc
{
  "title":    "My new chat",      // optional, auto-generated if omitted
  "model":    "gemini-2.0-flash",  // optional, defaults to env DEFAULT_MODEL
  "provider": "gemini"             // optional
}
```

**Response `201 Created`** — returns the new conversation object (without messages).

---

### 4.4 Update Conversation

```
PATCH /conversations/{conversation_id}
```

**Request body** (all fields optional)

```jsonc
{ "title": "Updated title" }
```

**Response `200 OK`** — returns the updated conversation.

---

### 4.5 Delete Conversation

```
DELETE /conversations/{conversation_id}
```

**Response `204 No Content`**

---

### 4.6 Export Conversation

```
GET /conversations/{conversation_id}/export?format=json
```

**Query parameters**

| Name     | Values                   | Default |
|----------|--------------------------|---------|
| `format` | `json` \| `markdown` \| `txt` | `json` |

Returns the conversation serialised in the requested format.
`markdown` and `txt` responses are `text/plain; charset=utf-8`.

---

## 5. Models

### 5.1 List Available Models

```
GET /models
```

No authentication required.

**Response `200 OK`**

```jsonc
{
  "models": [
    {
      "id":          "claude-3-7-sonnet-20250219",
      "provider":    "anthropic",
      "tier":        "advanced",
      "context_window": 200000,
      "max_output_tokens": 64000,
      "cost_per_1k_input":  0.003,
      "cost_per_1k_output": 0.015,
      "supports_streaming":         true,
      "supports_tools":             true,
      "supports_vision":            true,
      "supports_extended_thinking": true
    },
    {
      "id":       "gpt-4o",
      "provider": "openai",
      "tier":     "advanced",
      "context_window": 128000,
      "max_output_tokens": 16384,
      "cost_per_1k_input":  0.005,
      "cost_per_1k_output": 0.015,
      "supports_streaming": true,
      "supports_tools":     true,
      "supports_vision":    true,
      "supports_extended_thinking": false
    }
    // … more models
  ]
}
```

---

### 5.2 Get Model Details

```
GET /models/{model_id}
```

Returns a single model object from the list above.

---

## 6. Health & Metrics

### 6.1 Liveness Probe

```
GET /health
```

**Response `200 OK`**

```jsonc
{ "status": "ok", "timestamp": "2026-03-10T22:00:00Z" }
```

---

### 6.2 Readiness Probe

```
GET /health/ready
```

Checks DB connectivity and provider key validity.

**Response `200 OK`**

```jsonc
{
  "status": "ready",
  "checks": {
    "database":         "ok",
    "provider_openai":  "ok",
    "provider_anthropic": "ok",
    "provider_gemini":  "degraded"  // e.g. missing API key
  }
}
```

**Response `503 Service Unavailable`** — same shape but `status: "not_ready"`.

---

### 6.3 Prometheus Metrics

```
GET /metrics
```

Returns Prometheus-format text metrics exposed via
`prometheus-fastapi-instrumentator`.  Scraped automatically by the
bundled Grafana/Prometheus stack when running `make monitoring-up`.

Key metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method/path/status |
| `http_request_duration_seconds` | Histogram | Latency distribution |
| `ai_completions_total` | Counter | Completions by provider/model |
| `ai_tokens_total` | Counter | Tokens used by provider/model/direction |
| `ai_cost_usd_total` | Counter | Cumulative spend in USD |
| `active_conversations` | Gauge | Currently open conversation sessions |

---

## 7. Error Reference

All errors follow the same envelope:

```jsonc
{
  "error": {
    "code":    "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests.  Retry after 42 seconds.",
    "details": {}          // optional machine-readable context
  }
}
```

### HTTP Status Codes

| Status | Code | Meaning |
|--------|------|---------|
| `400` | `INVALID_REQUEST` | Malformed JSON or missing required field |
| `401` | `UNAUTHORIZED` | Missing or invalid Bearer token |
| `403` | `FORBIDDEN` | Authenticated but not authorised for resource |
| `404` | `NOT_FOUND` | Resource (conversation, model, …) does not exist |
| `409` | `CONFLICT` | Duplicate resource (e.g. email already registered) |
| `422` | `VALIDATION_ERROR` | Request passes JSON parse but fails schema validation |
| `429` | `RATE_LIMIT_EXCEEDED` | Per-user rate limit hit; see `Retry-After` header |
| `500` | `INTERNAL_ERROR` | Unexpected server error; file a bug report |
| `502` | `PROVIDER_ERROR` | Upstream AI provider returned a non-2xx response |
| `503` | `SERVICE_UNAVAILABLE` | API is starting up or a required dependency is down |

---

## 8. Rate Limiting

Rate limiting is applied per authenticated user.  Limits are set via
environment variables (see `.env.example`).

| Variable | Default | Scope |
|----------|---------|-------|
| `RATE_LIMIT_PER_MINUTE` | `60` | API requests / min |
| `RATE_LIMIT_BURST` | `10` | Burst allowance above the per-minute cap |

When a request is throttled the response includes:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 42
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1741647642
```

---

## 9. Streaming SSE Format

When `"stream": true` the server opens a long-lived `text/event-stream`
response.  Each event is separated by a blank line and looks like:

```
data: {"type":"content_delta","delta":"Hello, "}

data: {"type":"content_delta","delta":"world!"}

data: {"type":"usage","input_tokens":12,"output_tokens":6,"cost_usd":0.000108}

data: {"type":"done","finish_reason":"end_turn"}

data: [DONE]
```

### Event Types

| `type` | Fields | Description |
|--------|--------|--------------|
| `content_delta` | `delta: string` | Incremental text chunk |
| `thinking_delta` | `delta: string` | Incremental thinking chunk (Claude 3.7 only) |
| `usage` | `input_tokens`, `output_tokens`, `cost_usd` | Token accounting at stream end |
| `error` | `code`, `message` | Mid-stream error (stream then closes) |
| `done` | `finish_reason` | Normal end of generation |

Clients should:
1. Buffer `content_delta` strings and render them progressively.
2. Ignore unknown event types (forward-compatibility).
3. Treat a `data: [DONE]` line as the end sentinel.
4. Handle `error` events and surface them to the user.

---

## 10. SDK Snippets

### Python (async)

```python
import asyncio
import httpx

BASE = "http://localhost:8000/api/v1"

async def chat(token: str, prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "model": "claude-3-7-sonnet-20250219",
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def stream_chat(token: str, prompt: str) -> None:
    import json
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{BASE}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            json={"messages": [{"role": "user", "content": prompt}], "stream": True},
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                event = json.loads(payload)
                if event["type"] == "content_delta":
                    print(event["delta"], end="", flush=True)
```

### TypeScript (browser fetch)

```typescript
async function streamChat(token: string, prompt: string): Promise<void> {
  const response = await fetch('/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: prompt }],
      stream: true,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6);
      if (payload === '[DONE]') return;
      const event = JSON.parse(payload);
      if (event.type === 'content_delta') {
        process.stdout.write(event.delta); // or update React state
      }
    }
  }
}
```

---

## Environment Variable Quick-Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For OpenAI models | OpenAI platform key |
| `ANTHROPIC_API_KEY` | For Claude models | Anthropic console key |
| `GOOGLE_API_KEY` | For Gemini models | Google AI Studio key |
| `GROQ_API_KEY` | For Groq models | Groq console key |
| `OLLAMA_BASE_URL` | For local models | Default `http://localhost:11434` |
| `DATABASE_URL` | Yes | SQLAlchemy URL, e.g. `sqlite:///./zakera.db` |
| `JWT_SECRET_KEY` | Yes | Random 32-byte hex string |
| `DEFAULT_MODEL` | No | Fallback model, default `gpt-3.5-turbo` |
| `RATE_LIMIT_PER_MINUTE` | No | Requests/min per user, default `60` |
| `ENABLE_STREAMING` | No | `true` / `false`, default `true` |

See `.env.example` for the full list with comments.
