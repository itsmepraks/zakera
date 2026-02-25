# Troubleshooting Guide

## Common Issues

### Installation Issues

#### Python Dependencies Fail to Install

**Problem**: `pip install` fails with compilation errors

**Solution**:
```bash
# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Install build dependencies (Ubuntu/Debian)
sudo apt-get install python3-dev build-essential

# Install build dependencies (macOS)
brew install python@3.9

# Retry installation
make install
```

### Runtime Issues

#### API Server Won't Start

**Problem**: Server fails to start with port binding error

**Solution**:
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill the process using the port
kill -9 <PID>

# Or use a different port
export PORT=8001
make dev
```

#### Database Connection Errors

**Problem**: Cannot connect to database

**Solution**:
```bash
# Reset database
make db-reset

# Run migrations
make db-migrate

# Check database file permissions
ls -la zakera.db
```

### Model Provider Issues

#### OpenAI API Errors

**Problem**: Invalid API key or quota exceeded

**Solution**:
1. Verify API key in `.env`
2. Check API key validity at https://platform.openai.com/api-keys
3. Verify quota and billing at https://platform.openai.com/usage
4. Try using a different provider as fallback

### More Issues?

See the full troubleshooting guide or [open an issue](https://github.com/itsmepraks/zakera/issues).
