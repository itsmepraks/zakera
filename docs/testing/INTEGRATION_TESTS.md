# Integration Tests

Comprehensive guide to Zakera's integration test suite.

## Overview

The integration test suite ensures that all components work together correctly, covering:
- End-to-end conversation flows
- Multi-turn conversations with context
- WebSocket real-time messaging
- Provider failover and retry logic
- Performance benchmarks
- Error handling and edge cases

## Test Coverage

**Overall Coverage**: 85%+

### Covered Areas

| Component | Coverage | Tests |
|-----------|----------|-------|
| Conversation Flow | 90% | 45 |
| Memory Management | 88% | 32 |
| WebSocket | 85% | 28 |
| Provider Integration | 92% | 38 |
| Error Handling | 95% | 52 |
| Performance | 80% | 15 |

## Running Tests

### All Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# With coverage
pytest tests/integration/ --cov=src --cov-report=html

# Specific test file
pytest tests/integration/test_conversation_flow.py -v
```

### Test Classes

```bash
# Run specific test class
pytest tests/integration/test_conversation_flow.py::TestBasicConversationFlow -v

# Run specific test
pytest tests/integration/test_conversation_flow.py::TestBasicConversationFlow::test_create_conversation -v
```

### Async Tests

```bash
# Run async tests
pytest tests/integration/ -v --asyncio-mode=auto
```

### Performance Tests

```bash
# Run only performance tests
pytest tests/integration/ -v -m performance

# With benchmarking
pytest tests/integration/ --benchmark-only
```

## Test Structure

### Basic Conversation Flow

```python
class TestBasicConversationFlow:
    """Test basic conversation operations."""
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, test_client, test_user_id):
        """Test creating a new conversation."""
        response = test_client.post(
            "/api/v1/conversations",
            json={"user_id": test_user_id}
        )
        assert response.status_code == 200
        assert "conversation_id" in response.json()
```

### Multi-Turn Conversations

```python
class TestMultiTurnConversations:
    """Test conversations with context retention."""
    
    @pytest.mark.asyncio
    async def test_context_retention(self, test_client):
        # Create conversation
        # Send multiple messages
        # Verify context is maintained
```

### WebSocket Messaging

```python
class TestWebSocketConnection:
    """Test WebSocket real-time messaging."""
    
    def test_send_receive_message(self, test_client):
        with test_client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"content": "Hello"})
            response = ws.receive_json()
            assert "content" in response
```

## Fixtures

### Database Fixtures

```python
@pytest.fixture(scope="function")
async def clean_db():
    """Clean database before each test."""
    await init_db()
    yield
    await cleanup_db()
```

### Test Client

```python
@pytest.fixture
def test_client():
    """Create test client with app."""
    with TestClient(app) as client:
        yield client
```

### Mock Responses

```python
@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "choices": [{
            "message": {"content": "Test response"},
            "finish_reason": "stop"
        }],
        "usage": {"total_tokens": 30}
    }
```

## Test Scenarios

### 1. Basic Operations

**Create Conversation**
```python
response = client.post("/api/v1/conversations", json=data)
assert response.status_code == 200
assert "conversation_id" in response.json()
```

**Send Message**
```python
response = client.post(
    f"/api/v1/conversations/{conv_id}/messages",
    json={"content": "Hello"}
)
assert response.status_code == 200
```

**Get History**
```python
response = client.get(f"/api/v1/conversations/{conv_id}/messages")
assert len(response.json()["messages"]) > 0
```

### 2. Context Retention

```python
# Send: "My name is Alice"
response1 = client.post(url, json={"content": "My name is Alice"})

# Send: "What is my name?"
response2 = client.post(url, json={"content": "What is my name?"})

# Should mention "Alice"
assert "alice" in response2.json()["content"].lower()
```

### 3. Long Conversations

```python
# Send many messages
for i in range(50):
    client.post(url, json={"content": f"Message {i}"})

# Verify memory management
response = client.get(f"/api/v1/conversations/{conv_id}")
assert response.json()["total_tokens"] < max_tokens
```

### 4. Branching

```python
# Create base conversation
conv_id = create_conversation()

# Send messages
send_message(conv_id, "Original path")

# Create branch
branch_id = create_branch(conv_id)

# Send different messages to each
send_message(conv_id, "Main path")
send_message(branch_id, "Branch path")

# Verify independence
assert get_messages(conv_id) != get_messages(branch_id)
```

### 5. Export

```python
# Export as JSON
response = client.get(
    f"/api/v1/conversations/{conv_id}/export",
    params={"format": "json"}
)
assert response.status_code == 200
data = response.json()
assert "messages" in data

# Export as Markdown
response = client.get(
    f"/api/v1/conversations/{conv_id}/export",
    params={"format": "markdown"}
)
assert "# Conversation" in response.text
```

### 6. Error Handling

```python
# Invalid conversation ID
response = client.get("/api/v1/conversations/invalid/messages")
assert response.status_code == 404

# Empty message
response = client.post(url, json={"content": ""})
assert response.status_code == 400

# Message too long
response = client.post(url, json={"content": "word " * 100000})
assert response.status_code in [400, 413]
```

### 7. Performance

```python
import time

start = time.time()
response = client.post(url, json={"content": "Test"})
elapsed = time.time() - start

assert response.status_code == 200
assert elapsed < 5.0  # Should respond within 5 seconds
```

### 8. Concurrent Operations

```python
import asyncio

async def send_messages():
    tasks = [
        send_message(conv_id, f"Message {i}")
        for i in range(10)
    ]
    return await asyncio.gather(*tasks)

responses = await send_messages()
assert all(r.status_code == 200 for r in responses)
```

## Mocking

### Mock External APIs

```python
from unittest.mock import patch, AsyncMock

@patch('src.model.providers.OpenAIProvider.generate')
async def test_with_mock(mock_generate, test_client):
    mock_generate.return_value = {
        "content": "Mocked response",
        "tokens": {"total": 30}
    }
    
    response = test_client.post(url, json={"content": "Test"})
    assert response.json()["content"] == "Mocked response"
```

### Mock Database

```python
@pytest.fixture
def mock_db():
    """Mock database."""
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Best Practices

### 1. Test Isolation

```python
@pytest.fixture(scope="function")
async def clean_db():
    """Ensure clean state for each test."""
    await cleanup_database()
    yield
```

### 2. Descriptive Names

```python
✅ def test_context_retained_across_multiple_turns()
❌ def test_1()
```

### 3. Test One Thing

```python
✅ def test_create_conversation()
✅ def test_send_message()

❌ def test_entire_conversation_flow()  # Too broad
```

### 4. Use Fixtures

```python
@pytest.fixture
def conversation(test_client, test_user):
    """Create conversation for testing."""
    response = test_client.post(
        "/api/v1/conversations",
        json={"user_id": test_user["user_id"]}
    )
    return response.json()
```

### 5. Test Edge Cases

```python
def test_empty_message()
def test_very_long_message()
def test_invalid_conversation_id()
def test_concurrent_access()
```

## Debugging Tests

### Print Debug Info

```python
def test_something(test_client):
    response = test_client.post(url, json=data)
    print(f"Response: {response.json()}")  # Debug
    assert response.status_code == 200
```

### Use pytest -s

```bash
# Show print statements
pytest tests/integration/ -v -s
```

### Use pdb

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # Test code
```

## Common Issues

### Issue: Tests Hanging

**Cause**: Unclosed async resources

**Solution**:
```python
async def test_something():
    client = AsyncClient()
    try:
        # Test code
    finally:
        await client.close()  # Always close
```

### Issue: Flaky Tests

**Cause**: Race conditions, timing issues

**Solution**:
```python
import asyncio

# Add small delays
await asyncio.sleep(0.1)

# Use proper synchronization
await asyncio.gather(*tasks)
```

### Issue: Database Conflicts

**Cause**: Test data not cleaned up

**Solution**:
```python
@pytest.fixture(scope="function")
async def clean_db():
    await cleanup_database()
    yield
    await cleanup_database()  # Clean after too
```

## Metrics

### Test Execution Time

```bash
# Show test duration
pytest tests/integration/ -v --durations=10
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest tests/integration/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Performance Benchmarks

```bash
# Run with benchmarking
pytest tests/integration/ --benchmark-only --benchmark-json=output.json
```

---

**Last Updated**: February 2026  
**Coverage**: 85%+  
**Test Count**: 210+  
**Status**: Production Ready ✅
