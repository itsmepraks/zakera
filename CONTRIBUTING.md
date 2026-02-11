# Contributing to Zakera AI Chat Agent

Thank you for your interest in contributing to Zakera! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Pull Request Process](#pull-request-process)
8. [Release Process](#release-process)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Unacceptable behavior includes:**
- Harassment, trolling, or derogatory comments
- Public or private harassment
- Publishing others' private information
- Other unethical or unprofessional conduct

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- Git
- Docker (for integration testing)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/zakera.git
   cd zakera
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/itsmepraks/zakera.git
   ```

## Development Setup

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head
```

### Frontend Setup

```bash
cd src/frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Frontend tests
cd src/frontend
npm test
```

## Making Changes

### Branching Strategy

We use Git Flow:

- `main` - Production-ready code
- `develop` - Latest development changes
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Emergency fixes for production

### Creating a Feature Branch

```bash
# Update develop branch
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/your-feature-name
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add conversation export endpoint

Implement CSV and JSON export formats for conversations
with optional date range filtering.

Closes #123
```

```
fix(frontend): resolve message scroll issue

Fix auto-scroll behavior when new messages arrive
while user is scrolled up.

Fixes #456
```

## Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/)
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for all public functions/classes

**Example:**

```python
from typing import List, Optional

def get_conversations(
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Conversation]:
    """
    Retrieve conversations for a user.
    
    Args:
        user_id: The user's unique identifier
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List of Conversation objects
        
    Raises:
        ValueError: If limit is negative
    """
    if limit < 0:
        raise ValueError("Limit must be non-negative")
    
    # Implementation
    pass
```

### JavaScript/TypeScript

- Use ESLint configuration
- Use TypeScript for new code
- Follow React best practices
- Use functional components with hooks

**Example:**

```typescript
interface MessageProps {
  content: string;
  timestamp: Date;
  author: string;
}

export const Message: React.FC<MessageProps> = ({
  content,
  timestamp,
  author
}) => {
  return (
    <div className="message">
      <span className="author">{author}</span>
      <p>{content}</p>
      <time>{timestamp.toLocaleString()}</time>
    </div>
  );
};
```

### Code Formatting

**Python:**
```bash
# Format with black
black src/

# Sort imports
isort src/

# Lint
flake8 src/
mypy src/
```

**JavaScript:**
```bash
# Format with Prettier
npm run format

# Lint
npm run lint
```

## Testing

### Writing Tests

**Backend (pytest):**

```python
import pytest
from src.api import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    return app.test_client()

def test_create_conversation(client):
    response = client.post(
        '/conversations',
        json={'title': 'Test Conversation'}
    )
    assert response.status_code == 201
    assert 'id' in response.json
```

**Frontend (Jest/React Testing Library):**

```typescript
import { render, screen } from '@testing-library/react';
import { Message } from './Message';

test('renders message content', () => {
  render(
    <Message
      content="Hello, world!"
      timestamp={new Date()}
      author="Test User"
    />
  );
  
  expect(screen.getByText('Hello, world!')).toBeInTheDocument();
});
```

### Test Coverage

Maintain minimum 80% test coverage:

```bash
# Generate coverage report
pytest --cov=src --cov-report=html tests/

# View report
open htmlcov/index.html
```

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No merge conflicts with develop
- [ ] Added/updated tests for changes

### Submitting PR

1. Push your branch:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create pull request on GitHub

3. Fill out PR template:
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   Describe testing done
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Comments added to complex code
   - [ ] Documentation updated
   - [ ] Tests added/updated
   - [ ] All tests pass
   ```

4. Request review from maintainers

### Review Process

- At least one approval required
- All CI checks must pass
- No unresolved conversations
- Maintainer will merge when ready

### After Merge

```bash
# Update your local repository
git checkout develop
git pull upstream develop

# Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

## Documentation

### API Documentation

Update `docs/api-reference.md` for API changes.

### Code Documentation

- Add docstrings to all public functions/classes
- Include examples in docstrings when helpful
- Update README.md for significant changes

### Architecture Documentation

For architectural changes, update `docs/architecture.md`.

## Release Process

(For maintainers only)

1. Create release branch from develop
2. Update version numbers
3. Update CHANGELOG.md
4. Create release PR to main
5. After merge, tag release
6. Merge main back to develop

## Questions?

- Check existing issues and discussions
- Join our Discord server: [link]
- Email: contribute@zakera.ai

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Zakera! 🚀
