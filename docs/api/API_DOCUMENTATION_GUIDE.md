# API Documentation Guide

Comprehensive guide for maintaining and extending Zakera's API documentation.

## Overview

Zakera's API is documented using **OpenAPI 3.0** (formerly Swagger) specification. The documentation is automatically generated from Python code using FastAPI's built-in support and enhanced with custom configurations.

## Documentation Structure

```
docs/api/
├── openapi.json              # Generated OpenAPI specification
├── openapi-validator.py      # Validation tool
├── API_DOCUMENTATION_GUIDE.md # This file
├── examples/                 # API usage examples
│   ├── python/              # Python client examples
│   ├── javascript/          # JavaScript client examples
│   ├── curl/                # cURL examples
│   └── postman/             # Postman collection
└── schemas/                  # Custom schema definitions
```

## Accessing Documentation

### Interactive Documentation

**Swagger UI** (Interactive):
- URL: `http://localhost:8000/api/docs`
- Features: Try out API calls, explore schemas, view examples

**ReDoc** (Clean Reference):
- URL: `http://localhost:8000/api/redoc`
- Features: Beautiful, readable documentation

### OpenAPI Specification

**JSON Format**:
- URL: `http://localhost:8000/api/openapi.json`
- Download: `curl http://localhost:8000/api/openapi.json > openapi.json`

## Generating Documentation

### Automatic Generation

FastAPI automatically generates OpenAPI documentation from your code:

```python
from fastapi import FastAPI, Path, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="Zakera AI Chat Agent",
    description="Production-ready AI chat agent API",
    version="0.8.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str = Field(..., description="User message", min_length=1)
    model: str = Field("gpt-3.5-turbo", description="AI model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Randomness")

class ChatResponse(BaseModel):
    """Chat response."""
    response: str = Field(..., description="AI response")
    model: str = Field(..., description="Model used")
    tokens: int = Field(..., description="Tokens consumed")

@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Send chat message",
    description="Send a message to the AI and get a response.",
    responses={
        200: {"description": "Successful response"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Server error"},
    }
)
async def chat(
    request: ChatRequest,
    conversation_id: str = Query(..., description="Conversation ID"),
) -> ChatResponse:
    """Process chat message and return AI response."""
    # Implementation
    pass
```

### Customizing Documentation

#### Add Examples

```python
class ChatRequest(BaseModel):
    message: str = Field(..., example="Explain quantum computing")
    model: str = Field("gpt-3.5-turbo", example="gpt-4")
    
    class Config:
        schema_extra = {
            "examples": [
                {
                    "message": "What is machine learning?",
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.7
                },
                {
                    "message": "Write a Python function",
                    "model": "gpt-4",
                    "temperature": 0.2
                }
            ]
        }
```

#### Add Response Examples

```python
@app.post(
    "/api/v1/chat",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Quantum computing uses quantum mechanics...",
                        "model": "gpt-4",
                        "tokens": 245
                    }
                }
            }
        }
    }
)
```

#### Group Endpoints with Tags

```python
tags_metadata = [
    {
        "name": "Chat",
        "description": "Chat and conversation endpoints",
    },
    {
        "name": "Users",
        "description": "User management operations",
    },
    {
        "name": "Admin",
        "description": "Administrative endpoints",
        "externalDocs": {
            "description": "Admin guide",
            "url": "https://docs.zakera.ai/admin",
        },
    },
]

app = FastAPI(openapi_tags=tags_metadata)
```

## Validation

### Automated Validation

Use the provided validator:

```bash
# Validate OpenAPI specification
python docs/api/openapi-validator.py docs/api/openapi.json

# Output:
# ✓ No errors found!
# ⚠ 3 warnings
# ℹ 15 paths, 45 operations
```

### CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Validate OpenAPI Schema
  run: |
    python docs/api/openapi-validator.py docs/api/openapi.json
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python docs/api/openapi-validator.py docs/api/openapi.json
if [ $? -ne 0 ]; then
    echo "OpenAPI validation failed!"
    exit 1
fi
```

## Best Practices

### 1. Comprehensive Descriptions

✅ **Good**:
```python
@app.post(
    "/api/v1/chat",
    summary="Send chat message to AI",
    description="""
    Send a message to the AI model and receive a response.
    
    The conversation context is maintained using the conversation_id.
    Different models can be selected, each with different capabilities
    and costs.
    
    **Rate Limit**: 60 requests per minute
    **Authentication**: Required (Bearer token)
    """,
)
```

❌ **Bad**:
```python
@app.post("/api/v1/chat")  # No description
```

### 2. Clear Response Documentation

✅ **Good**:
```python
responses={
    200: {
        "description": "Message processed successfully",
        "content": {"application/json": {"example": {...}}}
    },
    400: {"description": "Invalid request (missing required fields)"},
    401: {"description": "Unauthorized (invalid or missing token)"},
    429: {"description": "Rate limit exceeded"},
    500: {"description": "Server error (model unavailable)"},
}
```

### 3. Detailed Parameter Descriptions

✅ **Good**:
```python
conversation_id: str = Query(
    ...,
    description="Unique conversation identifier (UUID format)",
    example="550e8400-e29b-41d4-a716-446655440000",
    regex=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
```

### 4. Use Pydantic Models

✅ **Good**:
```python
class UserProfile(BaseModel):
    """User profile information."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    name: str = Field(..., description="Display name")
    created_at: datetime = Field(..., description="Account creation time")
```

### 5. Include Examples

Every request/response should have examples:

```python
class Config:
    schema_extra = {
        "examples": [
            {
                "message": "Explain photosynthesis",
                "model": "gpt-4",
                "temperature": 0.7
            }
        ]
    }
```

## Testing API Documentation

### Manual Testing

1. **Start development environment**:
   ```bash
   make dev
   ```

2. **Open Swagger UI**:
   ```bash
   make api-docs
   # Or visit: http://localhost:8000/api/docs
   ```

3. **Try endpoints**:
   - Click "Try it out"
   - Fill in parameters
   - Execute request
   - View response

### Automated Testing

```python
import pytest
import requests

def test_openapi_spec():
    """Test that OpenAPI spec is valid."""
    response = requests.get("http://localhost:8000/api/openapi.json")
    assert response.status_code == 200
    
    spec = response.json()
    assert spec['openapi'].startswith('3.')
    assert 'paths' in spec
    assert len(spec['paths']) > 0

def test_all_endpoints_documented():
    """Test that all endpoints have descriptions."""
    response = requests.get("http://localhost:8000/api/openapi.json")
    spec = response.json()
    
    for path, methods in spec['paths'].items():
        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                assert 'summary' in operation, f"{method.upper()} {path} missing summary"
                assert 'description' in operation, f"{method.upper()} {path} missing description"
```

## Code Examples

### Python Client

```python
import requests

class ZakeraClient:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def chat(self, message: str, conversation_id: str, model: str = "gpt-3.5-turbo"):
        response = requests.post(
            f"{self.base_url}/api/v1/chat",
            json={
                "message": message,
                "model": model,
            },
            params={"conversation_id": conversation_id},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = ZakeraClient(api_key="your-api-key")
result = client.chat(
    message="Hello, AI!",
    conversation_id="conv-123",
    model="gpt-4"
)
print(result['response'])
```

### JavaScript/TypeScript Client

```typescript
class ZakeraClient {
  constructor(
    private apiKey: string,
    private baseUrl: string = 'http://localhost:8000'
  ) {}

  async chat(params: {
    message: string;
    conversationId: string;
    model?: string;
  }): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        message: params.message,
        model: params.model || 'gpt-3.5-turbo',
      }),
      params: {
        conversation_id: params.conversationId,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }
}

// Usage
const client = new ZakeraClient('your-api-key');
const result = await client.chat({
  message: 'Hello, AI!',
  conversationId: 'conv-123',
  model: 'gpt-4',
});
console.log(result.response);
```

### cURL Examples

```bash
# Send chat message
curl -X POST "http://localhost:8000/api/v1/chat?conversation_id=conv-123" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Explain quantum computing",
    "model": "gpt-4",
    "temperature": 0.7
  }'

# Get conversations
curl -X GET "http://localhost:8000/api/v1/conversations" \\
  -H "Authorization: Bearer YOUR_API_KEY"

# Create branch
curl -X POST "http://localhost:8000/api/v1/conversations/conv-123/branches" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "experiment",
    "parentId": "main"
  }'
```

## Maintaining Documentation

### When Adding New Endpoints

1. **Add proper docstrings**:
   ```python
   @app.post("/api/v1/endpoint")
   async def endpoint():
       """Clear, concise description of what this does."""
       pass
   ```

2. **Use Pydantic models** for request/response:
   ```python
   class RequestModel(BaseModel):
       """Request model description."""
       field: str = Field(..., description="Field description")
   ```

3. **Add tags** for grouping:
   ```python
   @app.post("/api/v1/endpoint", tags=["Category"])
   ```

4. **Document responses**:
   ```python
   responses={
       200: {"description": "Success"},
       400: {"description": "Bad request"},
   }
   ```

5. **Validate** documentation:
   ```bash
   python docs/api/openapi-validator.py docs/api/openapi.json
   ```

### Updating Existing Documentation

1. Update Python code (docstrings, Field descriptions)
2. Restart API server
3. Download updated spec: `make api-openapi`
4. Validate: `python docs/api/openapi-validator.py docs/api/openapi.json`
5. Commit changes

## OpenAPI Validator

### Usage

```bash
python docs/api/openapi-validator.py docs/api/openapi.json
```

### Validation Checks

**Errors** (must fix):
- Missing required fields (openapi, info, paths)
- Invalid structure
- Missing response definitions
- Undefined path parameters
- Invalid version format

**Warnings** (should fix):
- Missing descriptions
- Missing examples
- Missing security definitions
- Missing tags
- No error responses defined

**Info** (statistics):
- Total paths and operations
- Operations by method
- Schema count
- Security schemes present

### Output Example

```
======================================================================
OpenAPI Specification Validation Report
======================================================================

Specification: docs/api/openapi.json
OpenAPI Version: 3.0.2
API Title: Zakera AI Chat Agent
API Version: 0.8.0

ℹ Info:
  • Found 45 API paths
  • Found 78 schema definitions
  • Found 5 security schemes

⚠ Warnings (3):
  • POST /api/v1/chat: Missing example in request body
  • GET /api/v1/conversations: Missing description
  • Schema 'UserProfile': Missing description

✓ No errors found!

======================================================================
Validation PASSED with 3 warning(s)
======================================================================

Specification Statistics:
  Total Paths: 45
  Total Operations: 78
  Operations by Method: {'get': 32, 'post': 25, 'put': 8, 'patch': 7, 'delete': 6}
  Total Schemas: 78
  Has Security: True
  Has Tags: True
  Has Servers: True
```

## Client Code Generation

### Generate Python Client

```bash
# Using openapi-generator
openapi-generator-cli generate \\
  -i http://localhost:8000/api/openapi.json \\
  -g python \\
  -o clients/python \\
  --additional-properties=packageName=zakera_client
```

### Generate TypeScript Client

```bash
openapi-generator-cli generate \\
  -i http://localhost:8000/api/openapi.json \\
  -g typescript-axios \\
  -o clients/typescript
```

### Generate Other Clients

Supported generators:
- Java
- Go
- Ruby
- PHP
- C#
- And 50+ more

See: https://openapi-generator.tech/docs/generators

## Postman Collection

### Export to Postman

1. Open: http://localhost:8000/api/openapi.json
2. Copy JSON
3. In Postman: Import → Raw Text → Paste → Import

### Or Use Converter

```bash
# Install converter
npm install -g openapi-to-postmanv2

# Convert
openapi2postmanv2 \\
  -s docs/api/openapi.json \\
  -o docs/api/postman-collection.json
```

## Versioning

### API Versioning Strategy

Zakera uses URL-based versioning:

```
/api/v1/chat     # Version 1
/api/v2/chat     # Version 2 (breaking changes)
```

### Documenting Multiple Versions

```python
# v1
from fastapi import APIRouter
router_v1 = APIRouter(prefix="/api/v1")

@router_v1.post("/chat")
async def chat_v1():
    """Version 1 of chat endpoint."""
    pass

# v2
router_v2 = APIRouter(prefix="/api/v2")

@router_v2.post("/chat")
async def chat_v2():
    """Version 2 with enhanced features."""
    pass
```

## Troubleshooting

### Documentation Not Updating

**Problem**: Changes not reflected in Swagger UI

**Solutions**:
1. Restart API server
2. Clear browser cache
3. Check for syntax errors in code
4. Verify changes in openapi.json

### Validation Errors

**Problem**: Validator reports errors

**Solutions**:
1. Review error messages
2. Check FastAPI code for issues
3. Ensure all required fields present
4. Verify Pydantic models are complete

### Missing Schemas

**Problem**: Schemas not appearing in docs

**Solutions**:
1. Use `response_model` parameter
2. Reference model in type hints
3. Add to `components.schemas` manually if needed

## Resources

### Official Documentation
- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.0)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Tools
- [Swagger Editor](https://editor.swagger.io/)
- [OpenAPI Generator](https://openapi-generator.tech/)
- [Postman](https://www.postman.com/)
- [Insomnia](https://insomnia.rest/)

### Zakera Resources
- API Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI JSON: http://localhost:8000/api/openapi.json

---

**Last Updated**: February 2026  
**OpenAPI Version**: 3.0.2  
**Validator Version**: 1.0.0
