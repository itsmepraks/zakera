
# Conversation Templates API

## Overview

The Conversation Templates API provides a comprehensive system for managing predefined conversation starters, system prompts, and templates that users can use to quickly begin conversations with specific contexts and behaviors.

**Base URL:** `/api/v1/conversation-templates`

## Features

- ✅ **Full CRUD Operations** - Create, read, update, and delete templates
- ✅ **Advanced Filtering** - Filter by category, difficulty, tags, and search
- ✅ **Usage Analytics** - Track template usage and popularity
- ✅ **Bulk Import** - Import multiple templates at once
- ✅ **Categorization** - Organized by category and difficulty level
- ✅ **Model Recommendations** - Suggest optimal AI models for each template
- ✅ **Public/Private** - Control template visibility
- ✅ **Soft Delete** - Preserve templates while marking inactive

## Template Categories

- `code_review` - Code review and analysis templates
- `technical` - Technical discussions and system design
- `creative` - Creative writing and content generation
- `problem_solving` - Problem-solving and debugging
- `learning` - Educational and learning-focused templates
- `brainstorming` - Ideation and brainstorming sessions
- `analysis` - Code and system analysis
- `general` - General-purpose templates

## Difficulty Levels

- `beginner` - Suitable for beginners
- `intermediate` - Intermediate skill level
- `advanced` - Advanced users
- `expert` - Expert-level templates

## Endpoints

### List Templates

**GET** `/api/v1/conversation-templates/`

Retrieve a paginated list of conversation templates with optional filtering.

**Query Parameters:**
- `skip` (int, default: 0) - Number of records to skip for pagination
- `limit` (int, default: 50, max: 100) - Maximum records to return
- `category` (string) - Filter by category
- `difficulty` (string) - Filter by difficulty level
- `tags` (array) - Filter by tags (any match)
- `search` (string) - Search in title and description
- `is_public` (boolean) - Filter public/private templates
- `is_active` (boolean, default: true) - Filter active/inactive
- `sort_by` (string) - Sort field (created_at, updated_at, usage_count, title)
- `sort_order` (string) - Sort order (asc, desc)

**Response:**
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "templates": [
    {
      "id": 1,
      "title": "Python Code Review",
      "description": "Comprehensive Python code review...",
      "category": "code_review",
      "difficulty": "intermediate",
      "system_prompt": "You are an expert Python developer...",
      "starter_message": "Hello! I'm your Python code review assistant...",
      "suggested_questions": [
        "Is this code PEP 8 compliant?",
        "Are there any potential bugs?"
      ],
      "tags": ["python", "code-review", "pep8"],
      "model_recommendations": ["gpt-4-turbo", "claude-3-opus"],
      "is_public": true,
      "is_active": true,
      "usage_count": 125,
      "created_by": null,
      "created_at": "2026-03-08T00:00:00Z",
      "updated_at": "2026-03-08T00:00:00Z"
    }
  ]
}
```

**Example Requests:**
```bash
# Get all templates
curl "http://localhost:8000/api/v1/conversation-templates/"

# Filter by category
curl "http://localhost:8000/api/v1/conversation-templates/?category=code_review"

# Search templates
curl "http://localhost:8000/api/v1/conversation-templates/?search=python"

# Filter by difficulty and tags
curl "http://localhost:8000/api/v1/conversation-templates/?difficulty=beginner&tags=learning"

# Sort by popularity
curl "http://localhost:8000/api/v1/conversation-templates/?sort_by=usage_count&sort_order=desc"
```

### Create Template

**POST** `/api/v1/conversation-templates/`

Create a new conversation template.

**Request Body:**
```json
{
  "title": "React Component Review",
  "description": "Review React components for best practices and performance",
  "category": "code_review",
  "difficulty": "intermediate",
  "system_prompt": "You are an expert React developer. Review components for hooks usage, performance, and best practices.",
  "starter_message": "Share your React component and I'll review it.",
  "suggested_questions": [
    "Are my hooks optimized?",
    "Is this component performant?",
    "Should I split this component?"
  ],
  "tags": ["react", "javascript", "components"],
  "model_recommendations": ["gpt-4-turbo", "claude-3-sonnet"],
  "is_public": true,
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "id": 15,
  "title": "React Component Review",
  ...
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/conversation-templates/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "React Component Review",
    "description": "Review React components",
    "category": "code_review",
    "system_prompt": "You are a React expert...",
    "tags": ["react", "javascript"]
  }'
```

### Get Template

**GET** `/api/v1/conversation-templates/{id}`

Retrieve a specific template by ID.

**Path Parameters:**
- `id` (int) - Template ID

**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "Python Code Review",
  ...
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/conversation-templates/1"
```

### Update Template

**PUT** `/api/v1/conversation-templates/{id}`

Update an existing template. All fields are optional - only provided fields will be updated.

**Path Parameters:**
- `id` (int) - Template ID

**Request Body:**
```json
{
  "title": "Updated Title",
  "tags": ["python", "code-review", "advanced"],
  "is_active": false
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "Updated Title",
  ...
}
```

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/v1/conversation-templates/1" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title", "tags": ["python", "advanced"]}'
```

### Delete Template

**DELETE** `/api/v1/conversation-templates/{id}`

Delete a template (soft delete by default).

**Path Parameters:**
- `id` (int) - Template ID

**Query Parameters:**
- `hard_delete` (boolean, default: false) - Permanently delete vs soft delete

**Response:** `204 No Content`

**Example:**
```bash
# Soft delete (set is_active=false)
curl -X DELETE "http://localhost:8000/api/v1/conversation-templates/1"

# Hard delete (permanent)
curl -X DELETE "http://localhost:8000/api/v1/conversation-templates/1?hard_delete=true"
```

### Get Popular Templates

**GET** `/api/v1/conversation-templates/popular/top`

Get most popular templates by usage count.

**Query Parameters:**
- `limit` (int, default: 10, max: 50) - Number of templates
- `category` (string) - Optional category filter

**Response:** `200 OK`
```json
[
  {
    "id": 5,
    "title": "Technical Problem Solving",
    "usage_count": 450,
    ...
  }
]
```

**Example:**
```bash
# Get top 10 popular templates
curl "http://localhost:8000/api/v1/conversation-templates/popular/top"

# Get top 5 code review templates
curl "http://localhost:8000/api/v1/conversation-templates/popular/top?limit=5&category=code_review"
```

### Get Template Statistics

**GET** `/api/v1/conversation-templates/{id}/stats`

Get detailed usage statistics for a template.

**Path Parameters:**
- `id` (int) - Template ID

**Response:** `200 OK`
```json
{
  "template_id": 1,
  "title": "Python Code Review",
  "total_uses": 125,
  "unique_users": 45,
  "last_used": "2026-03-07T15:30:00Z",
  "model_distribution": {
    "gpt-4-turbo": 75,
    "claude-3-opus": 40,
    "gemini-1.5-pro": 10
  },
  "created_at": "2026-03-01T00:00:00Z",
  "is_public": true,
  "is_active": true
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/conversation-templates/1/stats"
```

### Log Template Usage

**POST** `/api/v1/conversation-templates/{id}/use`

Record template usage for analytics.

**Path Parameters:**
- `id` (int) - Template ID

**Query Parameters:**
- `conversation_id` (int) - Associated conversation ID
- `model_used` (string) - Model provider used

**Response:** `200 OK`
```json
{
  "message": "Usage logged successfully"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/conversation-templates/1/use?conversation_id=123&model_used=gpt-4-turbo"
```

### Bulk Import Templates

**POST** `/api/v1/conversation-templates/bulk-import`

Import multiple templates at once.

**Request Body:**
```json
{
  "templates": [
    {
      "title": "Template 1",
      "description": "First template",
      "category": "code_review",
      "system_prompt": "You are an expert..."
    },
    {
      "title": "Template 2",
      "description": "Second template",
      "category": "learning",
      "system_prompt": "You are a teacher..."
    }
  ],
  "skip_duplicates": true
}
```

**Response:** `201 Created`
```json
{
  "total_attempted": 2,
  "successful": 2,
  "failed": 0,
  "skipped": 0,
  "imported_ids": [16, 17],
  "errors": []
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/conversation-templates/bulk-import" \
  -H "Content-Type: application/json" \
  -d @templates.json
```

### List Categories

**GET** `/api/v1/conversation-templates/categories/list`

Get all available template categories.

**Response:** `200 OK`
```json
[
  "code_review",
  "technical",
  "creative",
  "problem_solving",
  "learning",
  "brainstorming",
  "analysis",
  "general"
]
```

### List Difficulty Levels

**GET** `/api/v1/conversation-templates/difficulties/list`

Get all available difficulty levels.

**Response:** `200 OK`
```json
[
  "beginner",
  "intermediate",
  "advanced",
  "expert"
]
```

## Predefined Templates

The system comes with 12 predefined templates:

### Code Review
1. **Python Code Review** - PEP 8, best practices, security
2. **JavaScript/TypeScript Code Review** - Modern ES6+, React, Node.js
3. **Code Architecture Review** - System design, scalability, patterns

### Problem Solving
4. **Technical Problem Solving** - Structured problem-solving approach
5. **Debugging Assistant** - Systematic debugging help

### Technical
6. **System Design Discussion** - Scalable system architecture

### Learning
7. **Concept Explainer** - Clear technical concept explanations
8. **Learning Path Advisor** - Personalized learning roadmaps

### Creative
9. **Technical Writing Assistant** - Documentation and blog posts
10. **Brainstorming Partner** - Creative ideation and innovation

### Analysis
11. **Performance Optimization Advisor** - Code and system optimization
12. **Security Audit Assistant** - Vulnerability assessment and hardening

## Setup and Initialization

### 1. Run Database Migration

```bash
alembic upgrade head
```

### 2. Seed Default Templates

```bash
# Import all default templates
python scripts/seed_templates.py

# Force re-import
python scripts/seed_templates.py --force

# List existing templates
python scripts/seed_templates.py --list

# Create tables and seed
python scripts/seed_templates.py --create-tables
```

### 3. Verify Installation

```bash
# Check templates endpoint
curl "http://localhost:8000/api/v1/conversation-templates/"

# View API documentation
open "http://localhost:8000/api/docs#/Conversation%20Templates"
```

## Integration Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Get all code review templates
response = requests.get(
    f"{BASE_URL}/conversation-templates/",
    params={
        "category": "code_review",
        "limit": 10
    }
)
templates = response.json()["templates"]

# Use a template
template_id = templates[0]["id"]
system_prompt = templates[0]["system_prompt"]
starter_message = templates[0]["starter_message"]

# Log usage
requests.post(
    f"{BASE_URL}/conversation-templates/{template_id}/use",
    params={"model_used": "gpt-4-turbo"}
)
```

### JavaScript/TypeScript Client

```typescript
const BASE_URL = "http://localhost:8000/api/v1";

// Get popular templates
const response = await fetch(
  `${BASE_URL}/conversation-templates/popular/top?limit=5`
);
const popularTemplates = await response.json();

// Create a new template
const newTemplate = {
  title: "My Custom Template",
  description: "A specialized template",
  category: "code_review",
  system_prompt: "You are an expert in...",
  tags: ["custom", "specialized"]
};

const createResponse = await fetch(
  `${BASE_URL}/conversation-templates/`,
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(newTemplate)
  }
);
const created = await createResponse.json();
```

### cURL Examples

```bash
# Search for Python-related templates
curl "http://localhost:8000/api/v1/conversation-templates/?search=python&limit=5"

# Get beginner templates
curl "http://localhost:8000/api/v1/conversation-templates/?difficulty=beginner"

# Create and use a template
TEMPLATE_ID=$(curl -X POST "http://localhost:8000/api/v1/conversation-templates/" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","category":"general","system_prompt":"Test prompt","description":"Test desc"}' \
  | jq -r '.id')

curl -X POST "http://localhost:8000/api/v1/conversation-templates/$TEMPLATE_ID/use"

# Get statistics
curl "http://localhost:8000/api/v1/conversation-templates/$TEMPLATE_ID/stats"
```

## Best Practices

### Creating Templates

1. **Clear Titles** - Use descriptive, searchable titles
2. **Detailed System Prompts** - Provide specific instructions for AI behavior
3. **Helpful Starters** - Include welcoming starter messages
4. **Actionable Questions** - Add relevant suggested questions
5. **Accurate Tags** - Use consistent, lowercase tags
6. **Model Recommendations** - Suggest appropriate AI models

### Using Templates

1. **Log Usage** - Always log template usage for analytics
2. **Track Conversations** - Link templates to created conversations
3. **Monitor Statistics** - Review popular templates and usage patterns
4. **Update Regularly** - Keep templates current and relevant
5. **Categorize Properly** - Use correct categories and difficulty levels

### Performance

1. **Use Pagination** - Don't fetch all templates at once
2. **Cache Popular Templates** - Cache frequently used templates
3. **Index Tags** - Ensure proper database indexing
4. **Soft Delete** - Use soft delete to preserve analytics

## Error Handling

### Common Error Responses

```json
// 404 Not Found
{
  "detail": "Template with ID 999 not found"
}

// 400 Bad Request
{
  "detail": "Validation error: title must be at least 3 characters"
}

// 500 Internal Server Error
{
  "detail": "Failed to create template: database error"
}
```

### Error Codes

- `400` - Bad Request (validation errors)
- `404` - Template not found
- `500` - Internal server error

## Security Considerations

- **Authentication** - Requires authentication (when auth is enabled)
- **Authorization** - Users can only modify their own templates
- **Input Validation** - All inputs are validated via Pydantic
- **SQL Injection** - Protected by SQLAlchemy ORM
- **Rate Limiting** - API rate limiting applies

## Future Enhancements

- [ ] Template versioning
- [ ] Template sharing and forking
- [ ] Template ratings and reviews
- [ ] AI-powered template suggestions
- [ ] Template marketplace
- [ ] Template analytics dashboard
- [ ] Custom template variables
- [ ] Template A/B testing

## Support

For issues or questions:
- GitHub Issues: https://github.com/itsmepraks/zakera/issues
- API Documentation: http://localhost:8000/api/docs
- Main Documentation: /docs/README.md

---

**Version:** 1.0.0  
**Last Updated:** March 8, 2026  
**API Version:** v1
