# Database Persistence System

> [!WARNING]
> **Legacy and unverified.** The inherited migration graph is inconsistent and this page is not the vNext persistence contract. See `docs/VNEXT_PLAN.md` and `docs/vnext/STATUS.md`.

Comprehensive guide to the conversation persistence system in Zakera.

## Overview

Zakera uses a production-ready database persistence system with the following features:

- **SQLAlchemy ORM** for database operations
- **Alembic** for database migrations
- **Soft deletes** for conversation safety
- **Message versioning** and threading
- **Conversation sharing** with tokens
- **Export tracking** for analytics
- **Comprehensive indexing** for performance

## Database Schema

### Core Tables

#### Users Table
- Primary user authentication and profile data
- Relationships: conversations, preferences, sessions

#### User Sessions Table
- Track active user sessions for security
- IP address, user agent, device info
- Session expiration and activity tracking

#### Conversations Table
- Main conversation container
- Supports soft delete, archiving, pinning
- Tracks tokens, cost, message count
- JSON fields for metadata and tags

#### Messages Table
- Individual chat messages
- Support for threading (parent_message_id)
- Version tracking for regenerated responses
- Performance metrics (latency, tokens, cost)

#### Conversation Shares Table
- Share conversations via secure tokens
- Public or private sharing
- Expiration dates and access tracking

#### Conversation Exports Table
- Track export jobs (PDF, Markdown, JSON)
- Status tracking and error handling

## Getting Started

### Initial Setup

1. **Initialize the database**:
```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

2. **Or use the Makefile**:
```bash
make db-init
make db-migrate
```

### Using the API

#### Create a Conversation

```python
POST /api/v1/conversations

{
  "title": "My First Conversation",
  "model_name": "gpt-4-turbo-preview",
  "temperature": 0.7,
  "tags": ["work", "research"]
}
```

#### Add Messages

```python
POST /api/v1/conversations/{conversation_id}/messages

{
  "role": "user",
  "content": "Hello, how are you?",
  "metadata": {"source": "web"}
}
```

#### Search Conversations

```python
GET /api/v1/search/conversations?query=research&tags=work

# Response includes matching conversations with previews
```

#### Get Statistics

```python
GET /api/v1/conversations/stats

# Returns total conversations, tokens, cost, etc.
```

## Integration with Memory System

The `ConversationMemory` class automatically integrates with the database:

```python
from src.model.memory import ConversationMemory
from src.api.database import get_db

# Create memory instance with database persistence
with get_db() as db:
    memory = ConversationMemory.from_conversation_id(
        conversation_id="conv-123",
        db=db,
        max_tokens=4000
    )
    
    # Add messages - automatically saved to database
    memory.add_turn("user", "What's the weather?")
    memory.add_turn("assistant", "It's sunny today!")
    
    # Get messages for API call
    messages = memory.get_messages()
    
    # Update stats
    memory.update_conversation_stats(
        total_tokens=150,
        total_cost=0.003
    )
```

## Advanced Features

### Soft Delete

Conversations are soft-deleted by default:

```python
DELETE /api/v1/conversations/{id}  # Soft delete
DELETE /api/v1/conversations/{id}?hard_delete=true  # Permanent delete
```

Soft-deleted conversations can be restored or permanently deleted later.

### Conversation Sharing

Share conversations securely:

```python
POST /api/v1/conversations/{id}/share

{
  "is_public": true,
  "expires_in_days": 7,
  "can_edit": false
}

# Returns:
{
  "share_token": "abc123...",
  "share_url": "/shared/abc123...",
  "expires_at": "2026-02-21T00:00:00Z"
}
```

### Bulk Operations

Efficiently manage multiple conversations:

```python
POST /api/v1/conversations/bulk/archive
{
  "conversation_ids": ["id1", "id2", "id3"],
  "archive": true
}

POST /api/v1/conversations/bulk/delete
{
  "conversation_ids": ["id1", "id2"],
  "hard_delete": false
}
```

### Message Threading

Support conversation branching:

```python
# Create a new message thread from a previous message
POST /api/v1/conversations/{id}/messages

{
  "role": "assistant",
  "content": "Alternative response",
  "parent_message_id": "msg-456",
  "version": 2
}
```

### Tags and Search

Organize conversations with tags:

```python
# Get all tags
GET /api/v1/search/tags
# Returns: ["work", "personal", "research", ...]

# Search by tags
GET /api/v1/conversations?tags=work,research

# Advanced search
GET /api/v1/search/all?query=machine+learning
```

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add user preferences"

# Create empty migration for custom changes
alembic revision -m "Add custom indexes"
```

### Applying Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade one version
alembic upgrade +1

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>
```

### Migration History

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --verbose
```

## Performance Optimization

### Indexes

The schema includes comprehensive indexes for common queries:

- User + conversation lookups
- Conversation + date ranges
- Message + conversation + creation time
- Tag-based filtering
- Archive status queries

### Query Optimization Tips

1. **Use pagination** for large result sets
2. **Filter archived** conversations when listing
3. **Include message limits** when fetching conversation details
4. **Use bulk operations** for multiple updates
5. **Cache tag lists** for autocomplete

### Monitoring

Track database performance:

```python
# Get conversation statistics
GET /api/v1/conversations/stats

# Monitor message counts
GET /api/v1/conversations?sort_by=message_count&order=desc
```

## Backup and Recovery

### Export Conversations

```bash
# Export specific conversation
GET /api/v1/conversations/{id}?include_messages=true

# Export all conversations
GET /api/v1/conversations?limit=1000
```

### Database Backup

```bash
# SQLite backup
sqlite3 data/zakera.db ".backup data/zakera_backup.db"

# PostgreSQL backup
pg_dump zakera > zakera_backup.sql
```

## Error Handling

The API includes comprehensive error handling:

- **404**: Conversation not found or access denied
- **400**: Invalid input data
- **409**: Conflict (e.g., duplicate share token)
- **500**: Database errors (with rollback)

All database operations include:
- Transaction management
- Automatic rollback on errors
- Detailed error messages
- Proper HTTP status codes

## Testing

Run database tests:

```bash
# All database tests
pytest tests/test_database.py -v

# Conversation persistence tests
pytest tests/test_conversations.py -v

# Integration tests
pytest tests/test_integration.py -v
```

## Best Practices

1. **Always use transactions** for multiple operations
2. **Soft delete** conversations by default
3. **Update conversation stats** after message operations
4. **Use indexes** for frequently queried fields
5. **Paginate** large result sets
6. **Validate user ownership** before operations
7. **Handle concurrent access** with proper locking
8. **Monitor database size** and clean old data

## Migration Checklist

When deploying migrations to production:

- [ ] Test migration on development database
- [ ] Backup production database
- [ ] Review migration SQL
- [ ] Check for breaking changes
- [ ] Plan rollback strategy
- [ ] Schedule maintenance window if needed
- [ ] Apply migration
- [ ] Verify data integrity
- [ ] Update application code if needed
- [ ] Monitor for errors

## Troubleshooting

### Common Issues

**Migration conflicts:**
```bash
# Resolve with:
alembic stamp head
alembic revision --autogenerate -m "Resolve conflicts"
```

**Database locked (SQLite):**
```bash
# Close all connections and retry
# Or switch to PostgreSQL for production
```

**Missing columns:**
```bash
# Run pending migrations:
alembic upgrade head
```

## Production Considerations

### PostgreSQL Recommended

For production deployments, use PostgreSQL:

```python
# Update .env
DATABASE_URL=postgresql://user:pass@localhost/zakera

# Or with connection pooling
DATABASE_URL=postgresql+psycopg2://user:pass@localhost/zakera?pool_size=20
```

### Connection Pooling

Configure connection pooling for better performance:

```python
# src/api/database.py
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Regular Maintenance

Schedule regular maintenance tasks:

```bash
# Vacuum database (PostgreSQL)
VACUUM ANALYZE;

# Clean old soft-deleted conversations
DELETE FROM conversations 
WHERE is_deleted = true 
AND deleted_at < NOW() - INTERVAL '90 days';

# Archive old conversations
UPDATE conversations 
SET is_archived = true 
WHERE updated_at < NOW() - INTERVAL '180 days';
```

## Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Database Guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
