# Zakera Test Suite

Comprehensive test suite for the Zakera AI Chat Agent project, providing extensive coverage across all layers of the application.

## 📊 Test Coverage

The test suite includes **250+ test cases** covering:

- ✅ **API Integration Tests**: Conversations, Messages, User Management
- ✅ **WebSocket Tests**: Real-time messaging and streaming
- ✅ **Database Tests**: Models, queries, transactions, integrity
- ✅ **Authentication Tests**: JWT, login, registration, permissions
- ✅ **AI Provider Tests**: OpenAI, Anthropic, Gemini integration
- ✅ **Memory Management Tests**: Context handling and optimization
- ✅ **Security Tests**: Input validation, SQL injection prevention
- ✅ **Edge Cases**: Unicode, large payloads, concurrent operations

## 🗂️ Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # pytest configuration
├── fixtures.py                  # Shared test fixtures
├── test_auth.py                 # Authentication tests
├── test_api_conversations.py    # Conversation API tests (40+ tests)
├── test_api_messages.py         # Message API tests (50+ tests)
├── test_api_users.py            # User management tests (60+ tests)
├── test_websocket.py            # WebSocket tests (50+ tests)
├── test_database.py             # Database tests (60+ tests)
├── test_gemini_provider.py      # Gemini provider tests
└── test_memory.py               # Memory management tests
```

## 🚀 Running Tests

### Run All Tests

```bash
# Basic run
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Parallel execution for speed
pytest -n auto
```

### Run Specific Test Files

```bash
# API tests
pytest tests/test_api_conversations.py
pytest tests/test_api_messages.py
pytest tests/test_api_users.py

# WebSocket tests
pytest tests/test_websocket.py

# Database tests
pytest tests/test_database.py

# Authentication tests
pytest tests/test_auth.py
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/test_api_conversations.py::TestConversationCreation

# Run specific test
pytest tests/test_api_conversations.py::TestConversationCreation::test_create_conversation_success

# Run tests matching pattern
pytest -k "test_create"
pytest -k "websocket"
```

### Run Tests with Different Verbosity

```bash
# Quiet mode (minimal output)
pytest -q

# Verbose mode
pytest -v

# Extra verbose (show all output)
pytest -vv

# Show print statements
pytest -s
```

### Run Tests with Coverage

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Generate terminal coverage report
pytest --cov=src --cov-report=term-missing

# Generate XML coverage for CI/CD
pytest --cov=src --cov-report=xml

# Set minimum coverage threshold
pytest --cov=src --cov-fail-under=80
```

## 🎯 Test Categories

### API Integration Tests

Test HTTP endpoints with various scenarios:

```bash
# All API tests
pytest tests/test_api_*.py

# Conversation endpoints
pytest tests/test_api_conversations.py -v

# Message endpoints with AI provider mocking
pytest tests/test_api_messages.py -v

# User management and authentication
pytest tests/test_api_users.py -v
```

**Coverage includes:**
- CRUD operations
- Validation and error handling
- Authentication and authorization
- Pagination and filtering
- Search functionality
- Bulk operations
- Edge cases and security

### WebSocket Tests

Test real-time communication:

```bash
pytest tests/test_websocket.py -v
```

**Coverage includes:**
- Connection establishment
- Authentication via token
- Message streaming
- Event handling (typing indicators, ping/pong)
- Error recovery
- Multiple connections
- Reconnection scenarios

### Database Tests

Test database layer operations:

```bash
pytest tests/test_database.py -v
```

**Coverage includes:**
- Model CRUD operations
- Foreign key constraints
- Unique constraints
- Cascade deletions
- Complex queries and joins
- Transactions and rollbacks
- Query optimization
- Data integrity

### Authentication Tests

Test security and authentication:

```bash
pytest tests/test_auth.py -v
```

**Coverage includes:**
- User registration
- Login/logout
- JWT token generation and validation
- Password hashing
- Token expiration
- Access control

## 🔧 Test Configuration

### Environment Variables

Tests use environment variables from `.env.test`:

```bash
# Create test environment file
cat > .env.test << EOF
DATABASE_URL=sqlite:///:memory:
SECRET_KEY=test-secret-key
OPENAI_API_KEY=test-key
ANTHROPIC_API_KEY=test-key
GOOGLE_API_KEY=test-key
DEBUG=true
ENVIRONMENT=test
EOF
```

### Database Setup

Tests use in-memory SQLite for speed and isolation:

- Each test function gets a fresh database
- No cleanup required between tests
- Fast execution (no disk I/O)
- Complete isolation

### Mocking AI Providers

AI provider responses are mocked to:

- Avoid API costs during testing
- Ensure consistent test results
- Enable offline testing
- Speed up test execution

```python
@patch('src.model.providers.OpenAIProvider.generate')
def test_with_mock(mock_generate):
    mock_generate.return_value = {"content": "Mocked response"}
    # Test code here
```

## 📈 Writing New Tests

### Test Structure

Follow this pattern for new tests:

```python
"""
Module docstring describing what is tested.
"""

import pytest
from tests.fixtures import client, auth_headers, test_user

class TestFeatureName:
    """Test class for related functionality."""
    
    def test_specific_behavior(self, client, auth_headers):
        """Test description in imperative mood."""
        # Arrange
        data = {"key": "value"}
        
        # Act
        response = client.post("/endpoint", json=data, headers=auth_headers)
        
        # Assert
        assert response.status_code == 200
        assert "expected" in response.json()
```

### Best Practices

1. **Use Descriptive Names**: Test names should clearly describe what is being tested
2. **One Assertion Per Concept**: Focus each test on a single behavior
3. **Arrange-Act-Assert**: Structure tests in three clear phases
4. **Use Fixtures**: Leverage shared fixtures for common setup
5. **Mock External Services**: Don't depend on external APIs
6. **Test Edge Cases**: Include boundary conditions and error scenarios
7. **Keep Tests Independent**: Tests should not depend on each other
8. **Use Parametrize**: Test multiple inputs efficiently

### Example: Parametrized Test

```python
@pytest.mark.parametrize("role,expected_status", [
    ("user", 200),
    ("assistant", 403),
    ("system", 403),
])
def test_message_creation_by_role(client, auth_headers, role, expected_status):
    response = client.post(
        "/api/messages",
        json={"role": role, "content": "test"},
        headers=auth_headers
    )
    assert response.status_code == expected_status
```

## 🐛 Debugging Tests

### Run Tests in Debug Mode

```bash
# Show all print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on error
pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### View Test Output

```bash
# Show local variables on failure
pytest -l

# Show full diff on assertion failure
pytest -vv

# Capture output for failed tests only
pytest --tb=short
```

### Markers for Selective Testing

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit
```

## 📊 Continuous Integration

Tests run automatically on:

- Every push to `main` and `develop` branches
- Every pull request
- Manual workflow dispatch

### CI Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs:

1. **Backend Tests**: pytest with multiple Python versions
2. **Frontend Tests**: Jest test suite
3. **Linting**: flake8, black, isort, mypy
4. **Security Scanning**: bandit, safety, Trivy
5. **Code Coverage**: Reports uploaded to Codecov

### Coverage Reports

- **Codecov**: View coverage reports at codecov.io
- **Artifacts**: Download HTML reports from GitHub Actions
- **PR Comments**: Coverage changes posted on pull requests

## 🎨 Test Fixtures

Common fixtures available in `fixtures.py`:

```python
# Database fixtures
test_db_session    # Test database session
test_db_engine     # Database engine

# User fixtures
test_user          # Single test user
test_user_token    # JWT token for test user
auth_headers       # Authorization headers
multiple_test_users # List of test users

# Conversation fixtures
test_conversation  # Single conversation
test_conversations # List of conversations with different states

# Message fixtures
test_messages      # List of messages
test_message_data  # Sample message data

# Mock fixtures
mock_openai_response      # Mocked OpenAI response
mock_streaming_response   # Mocked streaming chunks
```

## 🔍 Test Metrics

Current test coverage:

- **Total Tests**: 250+
- **API Tests**: 150+
- **WebSocket Tests**: 50+
- **Database Tests**: 60+
- **Coverage Target**: 80%+

## 📝 Contributing Tests

When adding new features:

1. Write tests first (TDD approach)
2. Ensure new code has 80%+ coverage
3. Include both positive and negative test cases
4. Test edge cases and error conditions
5. Update this README if adding new test categories

### Test Checklist

- [ ] Tests cover happy path
- [ ] Tests cover error conditions
- [ ] Tests cover edge cases
- [ ] Tests use appropriate fixtures
- [ ] Tests are independent
- [ ] Tests have clear descriptions
- [ ] Mocks are used for external services
- [ ] Coverage meets minimum threshold

## 🚨 Troubleshooting

### Common Issues

**Issue**: Tests failing with database errors
```bash
# Solution: Clear test database
rm -rf test.db
pytest
```

**Issue**: Tests hanging or timing out
```bash
# Solution: Run with timeout
pytest --timeout=30
```

**Issue**: Import errors
```bash
# Solution: Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-timeout
```

**Issue**: WebSocket tests failing
```bash
# Solution: Check if test client supports WebSocket
pip install httpx websockets
```

## 📚 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)

## 🤝 Support

For issues or questions about tests:

1. Check the test output for specific error messages
2. Review test documentation and comments
3. Check existing test examples
4. Open an issue on GitHub
5. Contact the development team

---

**Happy Testing! 🎉**

Remember: Good tests make good code. Write tests that you'd want to debug.
