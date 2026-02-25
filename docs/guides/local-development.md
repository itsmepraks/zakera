# Local Development Guide

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Git

## Quick Setup

```bash
# Clone repository
git clone https://github.com/itsmepraks/zakera.git
cd zakera

# Install dependencies
make install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start development server
make dev
```

## Environment Configuration

See [.env.example](../../.env.example) for all configuration options.

## Development Workflow

1. Create feature branch
2. Make changes
3. Run tests: `make test`
4. Format code: `make format`
5. Lint code: `make lint`
6. Commit and push
7. Create pull request

For more details, see [troubleshooting.md](troubleshooting.md).
