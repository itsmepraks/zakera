# Debugging Guide

## VS Code Debugging

### FastAPI Application

**Launch Configuration** (already configured in `.vscode/launch.json`):

```json
{
  "name": "Python: FastAPI",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": [
    "src.api.main:app",
    "--reload",
    "--host", "0.0.0.0",
    "--port", "8000"
  ]
}
```

**Usage**:
1. Set breakpoints in your code (click left of line number)
2. Press F5 or select "Python: FastAPI" from debug menu
3. Application starts with debugger attached
4. Make API requests to hit breakpoints

### Running Tests

**Debug Current Test File**:
1. Open test file
2. Set breakpoints
3. Select "Python: Pytest" from debug menu
4. Press F5

**Debug Specific Test**:
```bash
# Using pytest
pytest -v -s tests/test_specific.py::test_function_name

# With debugger
python -m pdb -m pytest tests/test_specific.py::test_function_name
```

## Python Debugger (pdb)

### Basic Usage

```python
import pdb; pdb.set_trace()
# Execution stops here
```

### Common Commands

```
n (next)     - Execute next line
s (step)     - Step into function
c (continue) - Continue execution
l (list)     - Show code context
p variable   - Print variable value
pp variable  - Pretty print
w (where)    - Show stack trace
u (up)       - Go up stack frame
d (down)     - Go down stack frame
q (quit)     - Exit debugger
```

## Debugging Common Issues

### Database Issues

```python
# Add logging to see SQL queries
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### API Request Issues

```python
# Log request details
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    return response
```

### Model Provider Issues

```python
# Enable debug logging for model providers
import logging
logger = logging.getLogger("model_provider")
logger.setLevel(logging.DEBUG)

# Log API calls
logger.debug(f"Calling {provider} with prompt: {prompt[:100]}...")
```

## Performance Debugging

### Profiling

```python
import cProfile
import pstats

# Profile a function
def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    result = slow_function()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 slowest
    
    return result
```

### Memory Debugging

```python
import tracemalloc

tracemalloc.start()

# Your code
result = memory_intensive_function()

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")

tracemalloc.stop()
```

## Docker Debugging

### Attach to Running Container

```bash
# Get container ID
docker ps

# Attach to container
docker exec -it <container_id> /bin/bash

# View logs
docker logs -f <container_id>

# View logs for specific service
docker-compose logs -f api
```

### Debug in Container

Add to `docker-compose.yml`:

```yaml
services:
  api:
    environment:
      - DEBUGPY_ENABLE=true
    ports:
      - "5678:5678"  # Debugger port
```

In your code:
```python
import debugpy
if os.getenv("DEBUGPY_ENABLE"):
    debugpy.listen(("0.0.0.0", 5678))
    debugpy.wait_for_client()
```

## Logging Best Practices

### Structured Logging

```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured log entry
logger.info(json.dumps({
    "event": "api_request",
    "method": "POST",
    "path": "/api/chat",
    "user_id": user_id,
    "duration_ms": 123,
    "status": 200
}))
```

### Log Levels

```python
logger.debug("Detailed diagnostic info")
logger.info("General informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
logger.critical("Critical issues")
```

## Frontend Debugging

### React DevTools

1. Install React DevTools browser extension
2. Open browser developer tools
3. Select "Components" tab
4. Inspect component props and state

### Console Debugging

```javascript
// Debug log
console.log('Variable value:', variable);

// Table view
console.table(arrayOfObjects);

// Timing
console.time('operation');
// ... code ...
console.timeEnd('operation');

// Group logs
console.group('API Call');
console.log('Request:', request);
console.log('Response:', response);
console.groupEnd();
```

## Network Debugging

### curl Commands

```bash
# Basic request
curl http://localhost:8000/api/health

# With headers
curl -H "Authorization: Bearer token" \
     http://localhost:8000/api/chat

# POST request
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"message": "test"}' \
     http://localhost:8000/api/chat

# Verbose output
curl -v http://localhost:8000/api/health
```

### httpie (Alternative)

```bash
# Install
pip install httpie

# Usage
http GET http://localhost:8000/api/health
http POST http://localhost:8000/api/chat message="test"
```

## Tips and Tricks

1. **Use breakpoints instead of print()**: More powerful and cleaner
2. **Check logs first**: Often provides clues
3. **Reproduce minimal case**: Isolate the issue
4. **Use git bisect**: Find which commit introduced bug
5. **Enable debug mode**: `DEBUG=true` in .env
6. **Check stack traces**: Read from bottom up
7. **Verify environment**: Check .env and configs
8. **Test in isolation**: Unit tests help isolate issues

---

**Last Updated**: February 2026
