# Environment Variables Reference

Complete reference for all environment variables used in Zakera.

## Table of Contents

- [Core Configuration](#core-configuration)
- [Model Providers](#model-providers)
- [Database](#database)
- [Security](#security)
- [Monitoring](#monitoring)
- [Server](#server)
- [Features](#features)
- [Development](#development)

## Core Configuration

### `DEFAULT_MODEL`
- **Type**: String
- **Default**: `gpt-3.5-turbo`
- **Required**: No
- **Description**: Primary model to use for chat completions
- **Examples**: 
  - `gpt-4-turbo` - OpenAI GPT-4 Turbo
  - `claude-3-sonnet` - Anthropic Claude 3 Sonnet
  - `gemini-1.5-pro` - Google Gemini 1.5 Pro
  - `llama3:8b` - Ollama Llama 3 8B
- **Notes**: Must be a valid model identifier from one of your enabled providers

### `FALLBACK_STRATEGY`
- **Type**: String (enum)
- **Default**: `none`
- **Options**: `none`, `sequential`, `parallel`, `smart`
- **Description**: Strategy for falling back when primary model fails
  - `none`: No fallback, fail immediately
  - `sequential`: Try providers one by one
  - `parallel`: Try multiple providers simultaneously
  - `smart`: Intelligent routing based on capabilities

### `ENABLE_MODEL_FALLBACK`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable automatic fallback to alternative models
- **Example**: `true`

## Model Providers

### OpenAI

#### `OPENAI_API_KEY`
- **Type**: String
- **Required**: Yes (if using OpenAI)
- **Description**: Your OpenAI API key
- **Format**: `sk-...`
- **Get Key**: https://platform.openai.com/api-keys
- **Security**: Never commit this to version control!

#### `OPENAI_BASE_URL`
- **Type**: String (URL)
- **Default**: `https://api.openai.com/v1`
- **Description**: Base URL for OpenAI API (useful for proxies)
- **Example**: `https://your-proxy.com/v1`

#### `OPENAI_ORGANIZATION`
- **Type**: String
- **Optional**: Yes
- **Description**: OpenAI organization ID for team accounts
- **Format**: `org-...`

#### `OPENAI_MAX_RETRIES`
- **Type**: Integer
- **Default**: `3`
- **Range**: 0-10
- **Description**: Maximum retry attempts for failed requests

#### `OPENAI_TIMEOUT`
- **Type**: Float
- **Default**: `60.0`
- **Unit**: Seconds
- **Description**: Request timeout for OpenAI API calls

#### `ENABLE_OPENAI`
- **Type**: Boolean
- **Default**: `true` (if API key present)
- **Description**: Enable/disable OpenAI provider

### Anthropic (Claude)

#### `ANTHROPIC_API_KEY`
- **Type**: String
- **Required**: Yes (if using Anthropic)
- **Description**: Your Anthropic API key
- **Format**: `sk-ant-...`
- **Get Key**: https://console.anthropic.com/

#### `ANTHROPIC_BASE_URL`
- **Type**: String (URL)
- **Default**: `https://api.anthropic.com/v1`
- **Description**: Base URL for Anthropic API

#### `ENABLE_ANTHROPIC`
- **Type**: Boolean
- **Default**: `true` (if API key present)
- **Description**: Enable/disable Anthropic provider

### Google Gemini

#### `GOOGLE_API_KEY`
- **Type**: String
- **Required**: Yes (if using Gemini)
- **Description**: Your Google AI API key
- **Format**: `AIza...`
- **Get Key**: https://makersuite.google.com/app/apikey

#### `GEMINI_BASE_URL`
- **Type**: String (URL)
- **Default**: `https://generativelanguage.googleapis.com/v1beta`
- **Description**: Base URL for Gemini API

#### `ENABLE_GEMINI`
- **Type**: Boolean
- **Default**: `true` (if API key present)
- **Description**: Enable/disable Gemini provider

### Ollama (Local Models)

#### `OLLAMA_BASE_URL`
- **Type**: String (URL)
- **Default**: `http://localhost:11434`
- **Description**: Ollama server endpoint
- **Examples**: 
  - `http://localhost:11434` - Local installation
  - `http://ollama-server:11434` - Docker network

#### `ENABLE_OLLAMA`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable Ollama provider for local models
- **Requires**: Ollama installed and running

#### `OLLAMA_NUM_GPU`
- **Type**: Integer
- **Default**: `1`
- **Description**: Number of GPUs to use for Ollama
- **Note**: Set to `0` for CPU-only mode

#### `OLLAMA_TIMEOUT`
- **Type**: Integer
- **Default**: `120`
- **Unit**: Seconds
- **Description**: Timeout for Ollama requests (longer for large models)

### HuggingFace

#### `HUGGINGFACE_MODEL`
- **Type**: String
- **Default**: None
- **Description**: HuggingFace model identifier
- **Examples**:
  - `mistralai/Mistral-7B-Instruct-v0.2`
  - `meta-llama/Llama-2-7b-chat-hf`

#### `HUGGINGFACE_DEVICE`
- **Type**: String (enum)
- **Default**: `cuda` (if available), else `cpu`
- **Options**: `cuda`, `cpu`, `mps`
- **Description**: Device to run model on

#### `HUGGINGFACE_8BIT`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable 8-bit quantization (reduces memory)
- **Note**: Requires `bitsandbytes` package

#### `HUGGINGFACE_CACHE_DIR`
- **Type**: String (path)
- **Default**: `~/.cache/huggingface`
- **Description**: Directory to cache downloaded models

#### `ENABLE_HUGGINGFACE`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable HuggingFace Transformers provider

## Database

### `DATABASE_URL`
- **Type**: String (URL)
- **Default**: `sqlite:///./data/zakera.db`
- **Description**: Database connection string
- **Formats**:
  - SQLite: `sqlite:///path/to/db.db`
  - PostgreSQL: `postgresql://user:pass@host:5432/db`
  - MySQL: `mysql://user:pass@host:3306/db`

### `DB_POOL_SIZE`
- **Type**: Integer
- **Default**: `5`
- **Description**: Database connection pool size

### `DB_MAX_OVERFLOW`
- **Type**: Integer
- **Default**: `10`
- **Description**: Maximum overflow connections

### `DB_POOL_TIMEOUT`
- **Type**: Float
- **Default**: `30.0`
- **Unit**: Seconds
- **Description**: Connection pool timeout

## Security

### `SECRET_KEY`
- **Type**: String
- **Required**: Yes
- **Description**: Secret key for JWT token generation
- **Generation**: `python -c "import secrets; print(secrets.token_hex(32))"`
- **Security**: MUST be changed in production!

### `ALLOWED_ORIGINS`
- **Type**: String (comma-separated)
- **Default**: `http://localhost:3000`
- **Description**: CORS allowed origins
- **Example**: `http://localhost:3000,https://app.example.com`

### `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- **Type**: Integer
- **Default**: `30`
- **Description**: JWT token expiration time

### `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- **Type**: Integer
- **Default**: `7`
- **Description**: Refresh token expiration time

### `ENABLE_AUTH`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable authentication requirement

### `RATE_LIMIT_PER_MINUTE`
- **Type**: Integer
- **Default**: `60`
- **Description**: API requests per minute per user

## Monitoring

### `ENABLE_METRICS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable Prometheus metrics collection

### `METRICS_PORT`
- **Type**: Integer
- **Default**: `8000` (same as API)
- **Description**: Port to expose metrics endpoint

### `LOG_LEVEL`
- **Type**: String (enum)
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging level

### `LOG_FILE`
- **Type**: String (path)
- **Default**: `logs/zakera.log`
- **Description**: Log file path

### `JSON_LOGS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Output logs in JSON format

### `ENABLE_ALERTS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable alert system

### `ALERT_EMAIL`
- **Type**: String (email)
- **Optional**: Yes
- **Description**: Email for alert notifications

### `SLACK_WEBHOOK_URL`
- **Type**: String (URL)
- **Optional**: Yes
- **Description**: Slack webhook for alerts

### `DISCORD_WEBHOOK_URL`
- **Type**: String (URL)
- **Optional**: Yes
- **Description**: Discord webhook for alerts

## Server

### `API_HOST`
- **Type**: String (IP)
- **Default**: `0.0.0.0`
- **Description**: Host to bind the API server
- **Production**: `0.0.0.0`
- **Development**: `127.0.0.1`

### `API_PORT`
- **Type**: Integer
- **Default**: `8000`
- **Description**: Port for the API server

### `DEBUG`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable debug mode
- **Warning**: Never enable in production!

### `WORKERS`
- **Type**: Integer
- **Default**: `4`
- **Description**: Number of worker processes
- **Recommendation**: `(2 * CPU_cores) + 1`

## Features

### `ENABLE_TOOLS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable tool execution system

### `ENABLE_WEBSOCKET`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable WebSocket endpoints

### `ENABLE_ANALYTICS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable usage analytics

### `ENABLE_CACHING`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable response caching

### `CACHE_TTL`
- **Type**: Integer
- **Default**: `3600`
- **Unit**: Seconds
- **Description**: Cache time-to-live

### `MAX_CONVERSATION_LENGTH`
- **Type**: Integer
- **Default**: `50`
- **Description**: Maximum messages per conversation

### `MAX_CONTEXT_TOKENS`
- **Type**: Integer
- **Default**: `4096`
- **Description**: Maximum tokens to send as context

## Development

### `ENVIRONMENT`
- **Type**: String (enum)
- **Default**: `production`
- **Options**: `development`, `staging`, `production`
- **Description**: Environment identifier

### `RELOAD`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable auto-reload on code changes
- **Use**: Development only

### `PROFILING`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable performance profiling

### `TEST_MODE`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Enable test mode (uses mock responses)

## Configuration Profiles

### Minimal Configuration (Development)
```env
OPENAI_API_KEY=sk-...
DEFAULT_MODEL=gpt-3.5-turbo
DEBUG=true
LOG_LEVEL=DEBUG
```

### Local-Only (Privacy)
```env
ENABLE_OLLAMA=true
DEFAULT_MODEL=llama3:8b
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_OPENAI=false
ENABLE_ANTHROPIC=false
ENABLE_GEMINI=false
```

### Production (High Availability)
```env
DEFAULT_MODEL=gpt-4-turbo
FALLBACK_STRATEGY=sequential
ENABLE_MODEL_FALLBACK=true

OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

DATABASE_URL=postgresql://user:pass@db:5432/zakera
SECRET_KEY=<generated-secret>

ENABLE_METRICS=true
ENABLE_ALERTS=true
LOG_LEVEL=INFO
JSON_LOGS=true

ALERT_EMAIL=admin@example.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Cost-Optimized
```env
DEFAULT_MODEL=llama3:8b
ENABLE_OLLAMA=true
FALLBACK_STRATEGY=sequential

# Only use API when local fails
OPENAI_API_KEY=sk-...
ENABLE_OPENAI=true

# Optimize settings
MAX_TOKENS=1024
ENABLE_CACHING=true
CACHE_TTL=7200
```

## Environment File Example

Complete `.env` file template is available as `.env.example` in the repository root.

## Security Best Practices

1. **Never commit `.env` to version control**
   - Add `.env` to `.gitignore`
   - Use `.env.example` as template

2. **Rotate secrets regularly**
   - Change `SECRET_KEY` periodically
   - Rotate API keys every 90 days

3. **Use strong secrets**
   ```bash
   # Generate strong secret
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Limit permissions**
   - Use read-only API keys when possible
   - Set rate limits appropriately

5. **Monitor usage**
   - Enable alerts for unusual activity
   - Track API key usage

## Validation

Zakera validates environment variables on startup:

```bash
# Check configuration
python -m src.api.main --check-config

# This will:
# - Verify required variables are set
# - Check API key formats
# - Test provider connections
# - Validate database URL
# - Check model availability
```

## Troubleshooting

### Variables Not Loading
```bash
# Ensure .env is in project root
ls -la .env

# Check for BOM or encoding issues
file .env

# Verify no trailing spaces
cat -A .env | grep ' $'
```

### Override via Shell
```bash
# Temporarily override for testing
DEFAULT_MODEL=gpt-4 python -m uvicorn src.api.main:app

# Set for session
export DEFAULT_MODEL=gpt-4
python -m uvicorn src.api.main:app
```

### Docker Environment
```yaml
# docker-compose.yml
services:
  zakera:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEFAULT_MODEL=gpt-3.5-turbo
    env_file:
      - .env
```

## References

- [Configuration Guide](configuration.md)
- [Security Best Practices](../SECURITY.md)
- [Deployment Guide](deployment.md)
- [Model Providers](../README.md#model-providers)
