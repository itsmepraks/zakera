# Zakera AI Chat Agent - API Integration Guide

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Code Examples](#code-examples)
5. [Real-World Use Cases](#real-world-use-cases)
6. [Best Practices](#best-practices)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [WebSocket Integration](#websocket-integration)
10. [Production Deployment](#production-deployment)

---

## Quick Start

### 5-Minute Quick Start

Get up and running with Zakera in under 5 minutes:

```bash
# 1. Install the client library
pip install zakera-client  # or npm install zakera-sdk

# 2. Set your API key
export ZAKERA_API_KEY="your-api-key-here"

# 3. Send your first message
curl -X POST https://api.zakera.app/v1/chat/send \
  -H "Authorization: Bearer $ZAKERA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Can you help me understand quantum computing?",
    "model": "gemini-1.5-pro"
  }'
```

### Python Example

```python
from zakera import ZakeraClient

# Initialize client
client = ZakeraClient(api_key="your-api-key")

# Send a message
response = await client.chat.send(
    message="Explain quantum computing simply",
    model="gemini-1.5-pro"
)

print(response.content)
print(f"Tokens used: {response.total_tokens}")
print(f"Cost: ${response.cost:.4f}")
```

### JavaScript Example

```javascript
import { ZakeraClient } from 'zakera-sdk';

const client = new ZakeraClient({
  apiKey: process.env.ZAKERA_API_KEY
});

const response = await client.chat.send({
  message: 'Explain quantum computing simply',
  model: 'gemini-1.5-pro'
});

console.log(response.content);
console.log(`Tokens: ${response.totalTokens}`);
console.log(`Cost: $${response.cost.toFixed(4)}`);
```

---

## Authentication

### API Key Authentication

The simplest authentication method:

```bash
curl -X GET https://api.zakera.app/v1/models \
  -H "X-API-Key: your-api-key-here"
```

### JWT Token Authentication

For user-based authentication:

```python
import requests

# Login to get JWT token
response = requests.post(
    "https://api.zakera.app/v1/auth/login",
    json={
        "username": "your-username",
        "password": "your-password"
    }
)

token = response.json()["access_token"]

# Use token for subsequent requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "https://api.zakera.app/v1/chat/send",
    headers=headers,
    json={"message": "Hello!"}
)
```

### OAuth2 Integration

```python
from authlib.integrations.requests_client import OAuth2Session

client_id = "your-client-id"
client_secret = "your-client-secret"
token_url = "https://api.zakera.app/v1/oauth/token"

client = OAuth2Session(
    client_id=client_id,
    client_secret=client_secret,
    token_endpoint=token_url
)

token = client.fetch_token(scope="chat.write conversations.read")
```

---

## API Endpoints

### Chat Endpoints

#### POST /v1/chat/send

Send a message to the AI agent:

```bash
curl -X POST https://api.zakera.app/v1/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?",
    "model": "gpt-4-turbo",
    "conversation_id": "conv_123",
    "temperature": 0.7,
    "max_tokens": 1000,
    "stream": false
  }'
```

**Response:**
```json
{
  "id": "msg_abc123",
  "content": "Machine learning is...",
  "model": "gpt-4-turbo",
  "conversation_id": "conv_123",
  "created_at": "2026-02-21T10:30:00Z",
  "tokens": {
    "prompt": 15,
    "completion": 250,
    "total": 265
  },
  "cost": 0.0053,
  "finish_reason": "stop"
}
```

#### POST /v1/chat/stream

Stream responses for real-time interaction:

```python
import sseclient
import requests

headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "https://api.zakera.app/v1/chat/stream",
    headers=headers,
    json={"message": "Tell me a story", "model": "gemini-1.5-flash"},
    stream=True
)

client = sseclient.SSEClient(response)
for event in client.events():
    if event.data:
        chunk = json.loads(event.data)
        print(chunk["content"], end="", flush=True)
```

### Conversation Endpoints

#### GET /v1/conversations

List all conversations:

```bash
curl -X GET "https://api.zakera.app/v1/conversations?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

#### GET /v1/conversations/{id}

Get conversation details:

```bash
curl -X GET https://api.zakera.app/v1/conversations/conv_123 \
  -H "Authorization: Bearer $TOKEN"
```

#### GET /v1/conversations/{id}/export

Export conversation in various formats:

```bash
# Export as JSON with streaming
curl -X GET "https://api.zakera.app/v1/conversations/conv_123/export?format=json&stream=true" \
  -H "Authorization: Bearer $TOKEN"

# Export as Markdown
curl -X GET "https://api.zakera.app/v1/conversations/conv_123/export?format=markdown" \
  -H "Authorization: Bearer $TOKEN" \
  -o conversation.md
```

### Model Endpoints

#### GET /v1/models

List available models:

```bash
curl -X GET https://api.zakera.app/v1/models \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "models": [
    {
      "id": "gpt-4-turbo",
      "name": "GPT-4 Turbo",
      "provider": "openai",
      "context_window": 128000,
      "max_output": 4096,
      "cost_per_1k": {"input": 0.01, "output": 0.03},
      "capabilities": ["chat", "streaming", "tools"]
    },
    {
      "id": "gemini-1.5-pro",
      "name": "Gemini 1.5 Pro",
      "provider": "google",
      "context_window": 2048000,
      "max_output": 8192,
      "cost_per_1k": {"input": 0.00125, "output": 0.005},
      "capabilities": ["chat", "streaming", "tools", "multimodal"]
    }
  ]
}
```

#### GET /v1/models/health

Check model provider health:

```bash
curl -X GET https://api.zakera.app/v1/models/health \
  -H "Authorization: Bearer $TOKEN"
```

### Tool Endpoints

#### GET /v1/tools

List available tools:

```bash
curl -X GET https://api.zakera.app/v1/tools \
  -H "Authorization: Bearer $TOKEN"
```

#### POST /v1/tools/execute

Execute a tool:

```bash
curl -X POST https://api.zakera.app/v1/tools/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "web_search",
    "parameters": {
      "query": "latest AI news",
      "num_results": 5
    }
  }'
```

---

## Code Examples

### Python Integration

#### Basic Chat

```python
import asyncio
from zakera import ZakeraClient

async def main():
    client = ZakeraClient(api_key="your-api-key")
    
    # Simple chat
    response = await client.chat.send(
        message="What's the capital of France?",
        model="gemini-1.5-flash"  # Fast and cost-effective
    )
    
    print(f"AI: {response.content}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.total_tokens}")
    print(f"Cost: ${response.cost:.6f}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Streaming Chat

```python
import asyncio
from zakera import ZakeraClient

async def streaming_chat():
    client = ZakeraClient(api_key="your-api-key")
    
    print("AI: ", end="", flush=True)
    async for chunk in client.chat.stream(
        message="Write a short poem about coding",
        model="gpt-4-turbo"
    ):
        print(chunk.content, end="", flush=True)
    
    print()  # New line at end

asyncio.run(streaming_chat())
```

#### Conversation Management

```python
import asyncio
from zakera import ZakeraClient

async def conversation_demo():
    client = ZakeraClient(api_key="your-api-key")
    
    # Create a new conversation
    conversation = await client.conversations.create(
        title="Math Tutoring Session"
    )
    
    # Send multiple messages in the same conversation
    messages = [
        "What is calculus?",
        "Can you give me an example of a derivative?",
        "How is this used in real life?"
    ]
    
    for msg in messages:
        response = await client.chat.send(
            message=msg,
            conversation_id=conversation.id
        )
        print(f"User: {msg}")
        print(f"AI: {response.content}\n")
    
    # Export the conversation
    export = await client.conversations.export(
        conversation_id=conversation.id,
        format="markdown"
    )
    
    with open("tutoring_session.md", "w") as f:
        f.write(export.content)

asyncio.run(conversation_demo())
```

#### Error Handling

```python
import asyncio
from zakera import ZakeraClient, ZakeraError, RateLimitError, AuthenticationError

async def robust_chat():
    client = ZakeraClient(
        api_key="your-api-key",
        max_retries=3,
        timeout=30.0
    )
    
    try:
        response = await client.chat.send(
            message="Explain quantum entanglement",
            model="gpt-4-turbo"
        )
        print(response.content)
        
    except AuthenticationError:
        print("Invalid API key. Please check your credentials.")
    
    except RateLimitError as e:
        print(f"Rate limit exceeded. Retry after {e.retry_after} seconds.")
        await asyncio.sleep(e.retry_after)
        # Retry the request
    
    except ZakeraError as e:
        print(f"API error: {e.message}")
        print(f"Error code: {e.code}")
        print(f"Request ID: {e.request_id}")

asyncio.run(robust_chat())
```

### JavaScript/TypeScript Integration

#### Basic Chat (Node.js)

```typescript
import { ZakeraClient } from 'zakera-sdk';

const client = new ZakeraClient({
  apiKey: process.env.ZAKERA_API_KEY!,
  baseURL: 'https://api.zakera.app/v1'
});

async function basicChat() {
  try {
    const response = await client.chat.send({
      message: 'What is TypeScript?',
      model: 'gemini-1.5-flash',
      temperature: 0.7
    });

    console.log('AI:', response.content);
    console.log(`Tokens: ${response.totalTokens}`);
    console.log(`Cost: $${response.cost.toFixed(6)}`);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

basicChat();
```

#### Streaming Chat (Browser)

```typescript
import { ZakeraClient } from 'zakera-sdk';

const client = new ZakeraClient({
  apiKey: 'your-api-key'
});

async function streamingChat() {
  const outputDiv = document.getElementById('output')!;
  outputDiv.textContent = '';

  try {
    const stream = await client.chat.stream({
      message: 'Tell me about the history of JavaScript',
      model: 'gpt-4-turbo'
    });

    for await (const chunk of stream) {
      outputDiv.textContent += chunk.content;
      
      // Smooth scrolling
      outputDiv.scrollTop = outputDiv.scrollHeight;
    }
  } catch (error) {
    outputDiv.textContent = `Error: ${error.message}`;
  }
}

// Call when button is clicked
document.getElementById('sendBtn')!.addEventListener('click', streamingChat);
```

#### React Hook Example

```typescript
import { useState, useCallback } from 'react';
import { ZakeraClient } from 'zakera-sdk';

const client = new ZakeraClient({
  apiKey: process.env.REACT_APP_ZAKERA_API_KEY!
});

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    setLoading(true);
    setError(null);

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await client.chat.send({
        message: content,
        model: 'gemini-1.5-pro'
      });

      // Add AI response
      const aiMessage: Message = {
        id: response.id,
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
        tokens: response.totalTokens,
        cost: response.cost
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  return { messages, loading, error, sendMessage };
}

// Usage in component
function ChatComponent() {
  const { messages, loading, sendMessage } = useChat();
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="typing-indicator">AI is typing...</div>}
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
```

### cURL Examples

#### Basic Chat

```bash
curl -X POST https://api.zakera.app/v1/chat/send \
  -H "Authorization: Bearer $ZAKERA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain REST APIs",
    "model": "gemini-1.5-flash",
    "temperature": 0.7,
    "max_tokens": 500
  }' | jq
```

#### Streaming with SSE

```bash
curl -N -X POST https://api.zakera.app/v1/chat/stream \
  -H "Authorization: Bearer $ZAKERA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Write a haiku about coding",
    "model": "gpt-4-turbo"
  }'
```

#### Conversation Export

```bash
# Export as Markdown
curl -X GET "https://api.zakera.app/v1/conversations/conv_123/export?format=markdown" \
  -H "Authorization: Bearer $ZAKERA_API_KEY" \
  -o conversation.md

# Export as JSON
curl -X GET "https://api.zakera.app/v1/conversations/conv_123/export?format=json" \
  -H "Authorization: Bearer $ZAKERA_API_KEY" | jq > conversation.json
```

---

## Real-World Use Cases

### 1. Customer Support Chatbot

```python
import asyncio
from zakera import ZakeraClient
from typing import Dict, List

class SupportChatbot:
    def __init__(self, api_key: str, knowledge_base: Dict):
        self.client = ZakeraClient(api_key=api_key)
        self.knowledge_base = knowledge_base
        self.conversation_history: Dict[str, str] = {}
    
    async def handle_query(self, user_id: str, query: str) -> str:
        """Handle a customer support query."""
        
        # Get or create conversation ID
        conv_id = self.conversation_history.get(user_id)
        if not conv_id:
            conv = await self.client.conversations.create(
                title=f"Support for {user_id}"
            )
            conv_id = conv.id
            self.conversation_history[user_id] = conv_id
        
        # Build context from knowledge base
        context = self._build_context(query)
        
        # Send message with context
        response = await self.client.chat.send(
            message=f"Context: {context}\n\nUser query: {query}",
            conversation_id=conv_id,
            model="gemini-1.5-pro",
            system_prompt="You are a helpful customer support agent. "
                         "Provide accurate, friendly responses based on the context."
        )
        
        return response.content
    
    def _build_context(self, query: str) -> str:
        """Search knowledge base for relevant info."""
        # Simple keyword matching (replace with vector search in production)
        relevant_docs = []
        keywords = query.lower().split()
        
        for doc_id, doc_content in self.knowledge_base.items():
            if any(kw in doc_content.lower() for kw in keywords):
                relevant_docs.append(doc_content)
        
        return "\n\n".join(relevant_docs[:3])  # Top 3 relevant docs

# Usage
async def main():
    knowledge_base = {
        "shipping": "We offer free shipping on orders over $50...",
        "returns": "Returns are accepted within 30 days...",
        "warranty": "All products come with a 1-year warranty..."
    }
    
    chatbot = SupportChatbot(
        api_key="your-api-key",
        knowledge_base=knowledge_base
    )
    
    response = await chatbot.handle_query(
        user_id="user_123",
        query="What's your return policy?"
    )
    print(f"Bot: {response}")

asyncio.run(main())
```

### 2. Documentation Q&A System

```typescript
import { ZakeraClient } from 'zakera-sdk';
import { createEmbedding, searchDocuments } from './vectordb';

class DocumentationQA {
  private client: ZakeraClient;
  
  constructor(apiKey: string) {
    this.client = new ZakeraClient({ apiKey });
  }
  
  async answer(question: string): Promise<string> {
    // 1. Find relevant documentation sections
    const embedding = await createEmbedding(question);
    const relevantDocs = await searchDocuments(embedding, topK: 5);
    
    // 2. Build context from relevant docs
    const context = relevantDocs
      .map(doc => `${doc.title}\n${doc.content}`)
      .join('\n\n---\n\n');
    
    // 3. Ask AI with context
    const response = await this.client.chat.send({
      message: `Based on the following documentation, answer this question:\n\nQuestion: ${question}\n\nDocumentation:\n${context}`,
      model: 'gpt-4-turbo',
      systemPrompt: 'You are a technical documentation assistant. Provide accurate answers based solely on the given documentation. If the answer is not in the documentation, say so.'
    });
    
    return response.content;
  }
}

// Usage
const qa = new DocumentationQA(process.env.ZAKERA_API_KEY!);
const answer = await qa.answer('How do I authenticate API requests?');
console.log(answer);
```

### 3. Code Assistant

```python
import asyncio
from zakera import ZakeraClient
from pathlib import Path

class CodeAssistant:
    def __init__(self, api_key: str):
        self.client = ZakeraClient(api_key=api_key)
    
    async def explain_code(self, code: str, language: str) -> str:
        """Explain what a piece of code does."""
        response = await self.client.chat.send(
            message=f"Explain this {language} code:\n\n```{language}\n{code}\n```",
            model="gpt-4-turbo",
            temperature=0.3  # Lower temperature for more focused responses
        )
        return response.content
    
    async def review_code(self, code: str, language: str) -> Dict:
        """Review code for issues and suggest improvements."""
        response = await self.client.chat.send(
            message=f"""Review this {language} code and provide:
            1. Potential bugs or issues
            2. Performance improvements
            3. Code quality suggestions
            4. Security concerns
            
            Code:
            ```{language}
            {code}
            ```
            
            Provide response in JSON format.""",
            model="gpt-4-turbo",
            temperature=0.2
        )
        
        # Parse JSON response
        import json
        return json.loads(response.content)
    
    async def generate_tests(self, code: str, language: str) -> str:
        """Generate unit tests for code."""
        framework = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "java": "JUnit"
        }.get(language.lower(), "appropriate test framework")
        
        response = await self.client.chat.send(
            message=f"""Generate comprehensive unit tests for this {language} code using {framework}:
            
            ```{language}
            {code}
            ```
            
            Include:
            - Happy path tests
            - Edge cases
            - Error handling tests
            - Mock external dependencies""",
            model="gpt-4-turbo",
            temperature=0.4
        )
        return response.content

# Usage
async def main():
    assistant = CodeAssistant(api_key="your-api-key")
    
    # Read code from file
    code = Path("myfunction.py").read_text()
    
    # Explain the code
    explanation = await assistant.explain_code(code, "python")
    print("Explanation:", explanation)
    
    # Review the code
    review = await assistant.review_code(code, "python")
    print("\nReview:", review)
    
    # Generate tests
    tests = await assistant.generate_tests(code, "python")
    print("\nGenerated Tests:", tests)

asyncio.run(main())
```

---

## Best Practices

### 1. Connection Management

```python
from zakera import ZakeraClient
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def zakera_client(api_key: str):
    """Context manager for proper resource management."""
    client = ZakeraClient(
        api_key=api_key,
        timeout=30.0,
        max_connections=100,
        keepalive_timeout=30.0
    )
    try:
        yield client
    finally:
        await client.close()

# Usage
async def main():
    async with zakera_client("your-api-key") as client:
        response = await client.chat.send(
            message="Hello!",
            model="gemini-1.5-flash"
        )
        print(response.content)

asyncio.run(main())
```

### 2. Retry Logic with Exponential Backoff

```python
import asyncio
import random
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> T:
    """Retry function with exponential backoff."""
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            # Calculate delay with jitter
            delay = min(
                base_delay * (exponential_base ** attempt),
                max_delay
            )
            jitter = random.uniform(0, 0.1 * delay)
            wait_time = delay + jitter
            
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f}s...")
            await asyncio.sleep(wait_time)

# Usage
async def send_message():
    client = ZakeraClient(api_key="your-api-key")
    return await client.chat.send(message="Hello!")

response = await retry_with_backoff(send_message)
```

### 3. Rate Limiting

```python
import asyncio
import time
from collections import deque

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int, per: float):
        self.rate = rate  # Number of requests
        self.per = per    # Time period in seconds
        self.allowance = rate
        self.last_check = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until a token is available."""
        async with self.lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current
            
            # Refill tokens
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            
            if self.allowance < 1.0:
                # Calculate wait time
                wait_time = (1.0 - self.allowance) * (self.per / self.rate)
                await asyncio.sleep(wait_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0

# Usage
limiter = RateLimiter(rate=10, per=60.0)  # 10 requests per minute

async def rate_limited_request(client, message):
    await limiter.acquire()
    return await client.chat.send(message=message)

# Make multiple requests
client = ZakeraClient(api_key="your-api-key")
tasks = [rate_limited_request(client, f"Message {i}") for i in range(20)]
responses = await asyncio.gather(*tasks)
```

### 4. Caching Responses

```python
import hashlib
import json
from functools import wraps
from typing import Optional
import aioredis

class ResponseCache:
    def __init__(self, redis_url: str, ttl: int = 3600):
        self.redis = aioredis.from_url(redis_url)
        self.ttl = ttl
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[str]:
        """Get cached response."""
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str):
        """Cache response."""
        await self.redis.setex(key, self.ttl, value)
    
    def cached(self, func):
        """Decorator to cache function results."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self._generate_key(*args, **kwargs)
            
            # Try to get from cache
            cached_result = await self.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await self.set(cache_key, json.dumps(result))
            
            return result
        return wrapper

# Usage
cache = ResponseCache(redis_url="redis://localhost:6379")
client = ZakeraClient(api_key="your-api-key")

@cache.cached
async def get_definition(term: str):
    response = await client.chat.send(
        message=f"Define: {term}",
        model="gemini-1.5-flash"
    )
    return {"term": term, "definition": response.content}

# First call - hits API
result1 = await get_definition("quantum computing")

# Second call - served from cache
result2 = await get_definition("quantum computing")
```

---

## Error Handling

### Error Types

```python
from zakera.exceptions import (
    ZakeraError,           # Base exception
    AuthenticationError,   # Invalid API key
    RateLimitError,        # Rate limit exceeded
    ModelError,            # Model-related errors
    ValidationError,       # Invalid request data
    ServerError,           # Server-side errors
    TimeoutError,          # Request timeout
    NetworkError           # Network connectivity issues
)

async def comprehensive_error_handling():
    client = ZakeraClient(api_key="your-api-key")
    
    try:
        response = await client.chat.send(
            message="Hello!",
            model="gpt-4-turbo"
        )
        print(response.content)
        
    except AuthenticationError as e:
        # Handle auth errors
        print(f"Authentication failed: {e.message}")
        print("Please check your API key")
        # Trigger key rotation or alert
        
    except RateLimitError as e:
        # Handle rate limiting
        print(f"Rate limit exceeded. Retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        # Retry the request
        
    except ModelError as e:
        # Handle model-specific errors
        print(f"Model error: {e.message}")
        if "not available" in str(e):
            # Fallback to different model
            print("Falling back to gemini-1.5-flash...")
            response = await client.chat.send(
                message="Hello!",
                model="gemini-1.5-flash"
            )
        
    except ValidationError as e:
        # Handle validation errors
        print(f"Invalid request: {e.message}")
        print(f"Errors: {e.errors}")
        # Fix request and retry
        
    except TimeoutError as e:
        # Handle timeouts
        print(f"Request timed out after {e.timeout}s")
        # Retry with longer timeout or different model
        
    except NetworkError as e:
        # Handle network issues
        print(f"Network error: {e.message}")
        # Implement retry logic
        
    except ServerError as e:
        # Handle server errors (5xx)
        print(f"Server error: {e.message}")
        print(f"Status code: {e.status_code}")
        # Alert monitoring system
        
    except ZakeraError as e:
        # Catch-all for any Zakera errors
        print(f"Unexpected error: {e.message}")
        print(f"Request ID: {e.request_id}")  # For support
        
    except Exception as e:
        # Catch any other errors
        print(f"Unexpected error: {e}")
        # Log and alert
```

---

## Rate Limiting

### Understanding Rate Limits

Zakera implements the following rate limits:

| Tier | Requests/min | Requests/day | Concurrent |
|------|-------------|--------------|------------|
| Free | 10 | 1,000 | 2 |
| Starter | 60 | 10,000 | 5 |
| Pro | 300 | 100,000 | 20 |
| Enterprise | Custom | Custom | Custom |

### Rate Limit Headers

Each API response includes rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1645564800
X-RateLimit-Resource: chat
```

### Handling Rate Limits

```python
import asyncio
import time
from zakera import ZakeraClient, RateLimitError

async def rate_limit_aware_request(client, message):
    """Make request with rate limit awareness."""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.chat.send(message=message)
            
            # Check remaining rate limit
            if response.rate_limit_remaining < 10:
                # Approaching limit, slow down
                print(f"Approaching rate limit. Remaining: {response.rate_limit_remaining}")
                await asyncio.sleep(2)
            
            return response
            
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            
            # Wait for rate limit reset
            reset_time = e.rate_limit_reset
            wait_time = max(reset_time - time.time(), 0) + 1
            
            print(f"Rate limit exceeded. Waiting {wait_time:.0f}s until reset...")
            await asyncio.sleep(wait_time)
```

---

## WebSocket Integration

### Real-Time Chat with WebSocket

```python
import asyncio
import websockets
import json
from zakera import ZakeraClient

async def websocket_chat():
    """Real-time bidirectional chat via WebSocket."""
    
    uri = "wss://api.zakera.app/v1/chat/ws"
    headers = {"Authorization": "Bearer your-api-key"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        print("Connected to Zakera WebSocket")
        
        # Start conversation
        await websocket.send(json.dumps({
            "type": "start",
            "model": "gemini-1.5-pro",
            "conversation_id": "conv_123"
        }))
        
        # Send a message
        await websocket.send(json.dumps({
            "type": "message",
            "content": "Explain quantum computing"
        }))
        
        # Receive streaming response
        async for message in websocket:
            data = json.loads(message)
            
            if data["type"] == "chunk":
                # Streaming content chunk
                print(data["content"], end="", flush=True)
            
            elif data["type"] == "complete":
                # Response complete
                print("\n\nResponse complete")
                print(f"Tokens: {data['tokens']}")
                print(f"Cost: ${data['cost']:.6f}")
                break
            
            elif data["type"] == "error":
                # Error occurred
                print(f"\nError: {data['message']}")
                break

asyncio.run(websocket_chat())
```

### JavaScript WebSocket Example

```javascript
class ZakeraWebSocket {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.ws = null;
    this.messageHandlers = [];
  }
  
  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(
        'wss://api.zakera.app/v1/chat/ws',
        ['zakera-protocol', `Bearer-${this.apiKey}`]
      );
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.messageHandlers.forEach(handler => handler(data));
      };
    });
  }
  
  onMessage(handler) {
    this.messageHandlers.push(handler);
  }
  
  sendMessage(content, options = {}) {
    this.ws.send(JSON.stringify({
      type: 'message',
      content,
      ...options
    }));
  }
  
  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const ws = new ZakeraWebSocket('your-api-key');
await ws.connect();

ws.onMessage((data) => {
  if (data.type === 'chunk') {
    // Append streaming content
    document.getElementById('output').textContent += data.content;
  } else if (data.type === 'complete') {
    console.log('Response complete:', data);
  }
});

ws.sendMessage('What is machine learning?', {
  model: 'gpt-4-turbo',
  temperature: 0.7
});
```

---

## Production Deployment

### Deployment Checklist

- [ ] **Security**
  - [ ] API keys stored in secrets manager (not in code)
  - [ ] HTTPS/WSS only in production
  - [ ] Rate limiting configured
  - [ ] Input validation and sanitization
  - [ ] CORS configured correctly
  
- [ ] **Monitoring**
  - [ ] Health checks configured
  - [ ] Logging aggregation set up
  - [ ] Error tracking (Sentry, etc.)
  - [ ] Performance monitoring (APM)
  - [ ] Cost tracking and alerts
  
- [ ] **Reliability**
  - [ ] Retry logic with exponential backoff
  - [ ] Circuit breaker pattern
  - [ ] Graceful degradation
  - [ ] Fallback models configured
  - [ ] Timeout handling
  
- [ ] **Performance**
  - [ ] Connection pooling
  - [ ] Response caching
  - [ ] CDN for static assets
  - [ ] Database query optimization
  - [ ] Load balancing
  
- [ ] **Testing**
  - [ ] Unit tests (>80% coverage)
  - [ ] Integration tests
  - [ ] Load testing
  - [ ] Chaos engineering tests
  
- [ ] **Documentation**
  - [ ] API documentation
  - [ ] Runbooks for common issues
  - [ ] Incident response procedures
  - [ ] Architecture diagrams

### Production Configuration Example

```python
# config/production.py
import os
from zakera import ZakeraClient

class ProductionConfig:
    # API Configuration
    ZAKERA_API_KEY = os.getenv("ZAKERA_API_KEY")
    ZAKERA_BASE_URL = "https://api.zakera.app/v1"
    
    # Client Configuration
    MAX_RETRIES = 3
    TIMEOUT = 30.0
    MAX_CONNECTIONS = 100
    KEEPALIVE_TIMEOUT = 30.0
    
    # Rate Limiting
    RATE_LIMIT = 60  # requests per minute
    RATE_LIMIT_PERIOD = 60.0  # seconds
    
    # Caching
    CACHE_TTL = 3600  # 1 hour
    REDIS_URL = os.getenv("REDIS_URL")
    
    # Monitoring
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    LOG_LEVEL = "INFO"
    
    # Model Configuration
    DEFAULT_MODEL = "gemini-1.5-flash"  # Cost-effective default
    FALLBACK_MODELS = [
        "gpt-3.5-turbo",
        "claude-3-haiku"
    ]
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATABASE_POOL_SIZE = 20

# Initialize client
client = ZakeraClient(
    api_key=ProductionConfig.ZAKERA_API_KEY,
    base_url=ProductionConfig.ZAKERA_BASE_URL,
    timeout=ProductionConfig.TIMEOUT,
    max_retries=ProductionConfig.MAX_RETRIES,
    max_connections=ProductionConfig.MAX_CONNECTIONS
)
```

---

## Support & Resources

### Documentation
- [API Reference](https://docs.zakera.app/api)
- [SDKs & Libraries](https://docs.zakera.app/sdks)
- [Guides & Tutorials](https://docs.zakera.app/guides)

### Community
- [Discord Server](https://discord.gg/zakera)
- [GitHub Discussions](https://github.com/itsmepraks/zakera/discussions)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/zakera)

### Support
- Email: support@zakera.app
- Status Page: https://status.zakera.app
- Twitter: [@zakera](https://twitter.com/zakera)

### Additional Resources
- [Blog](https://blog.zakera.app)
- [Changelog](https://github.com/itsmepraks/zakera/blob/main/CHANGELOG.md)
- [Examples Repository](https://github.com/itsmepraks/zakera-examples)

---

**Last Updated**: February 2026  
**API Version**: v1  
**Documentation Version**: 1.0
