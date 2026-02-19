# Troubleshooting Guide

Quick reference for common issues and their solutions in Zakera.

## Common Issues

### Model Provider Issues

#### OpenAI Connection Errors
**Problem**: `OpenAIError: Connection timeout` or `Invalid API key`

**Solutions**:
```bash
# 1. Verify API key is set correctly
echo $OPENAI_API_KEY

# 2. Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. Check for network/firewall issues
ping api.openai.com

# 4. Verify rate limits
make models-health
```

#### Ollama Not Found
**Problem**: `OllamaError: Connection refused at localhost:11434`

**Solutions**:
```bash
# 1. Check if Ollama is running
curl http://localhost:11434/api/tags

# 2. Start Ollama service
make ollama-start
# or manually:
ollama serve

# 3. Verify models are downloaded
ollama list

# 4. Pull missing models
ollama pull llama3:8b
```

### Performance Issues

#### Slow Response Times
**Problem**: Responses taking > 5 seconds

**Solutions**:
1. **Switch to faster models**:
   ```env
   DEFAULT_MODEL=mistral:7b  # Faster than llama3:70b
   ```

2. **Enable streaming**:
   ```python
   # In API calls, use stream=True
   response = client.chat(message, stream=True)
   ```

3. **Check system resources**:
   ```bash
   make health
   # Monitor CPU/Memory usage
   docker stats
   ```

4. **Use local models to avoid network latency**:
   ```env
   DEFAULT_MODEL=llama3:8b
   ENABLE_OLLAMA=true
   ```

#### High Memory Usage
**Problem**: Application consuming > 8GB RAM

**Solutions**:
```bash
# 1. Use smaller models
DEFAULT_MODEL=mistral:7b  # Instead of llama3:70b

# 2. Enable quantization for HuggingFace
HUGGINGFACE_8BIT=true

# 3. Limit conversation history
MAX_CONVERSATION_HISTORY=20  # Default: 50
MAX_CONTEXT_TOKENS=4000      # Default: 8000

# 4. Clear cache periodically
make cache-clear
```

### Database Issues

#### Migration Errors
**Problem**: `alembic.util.exc.CommandError: Can't locate revision`

**Solutions**:
```bash
# 1. Check current revision
alembic current

# 2. View migration history
alembic history

# 3. Stamp to latest (if database manually updated)
alembic stamp head

# 4. Run migrations
alembic upgrade head

# 5. Reset database (⚠️ DELETES DATA)
make db-reset
```

#### Connection Pool Exhausted
**Problem**: `QueuePool limit exceeded`

**Solutions**:
```env
# Increase pool size in .env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### Docker Issues

#### Container Health Check Failing
**Problem**: Container marked as unhealthy

**Solutions**:
```bash
# 1. Check health endpoint
curl http://localhost:8000/api/v1/monitoring/health

# 2. View container logs
docker logs zakera-backend

# 3. Verify all dependencies are running
docker-compose ps

# 4. Restart services
docker-compose restart
```

#### Port Already in Use
**Problem**: `Error: port 8000 already in use`

**Solutions**:
```bash
# 1. Find process using port
lsof -i :8000
# or on Windows:
netstat -ano | findstr :8000

# 2. Kill the process
kill -9 <PID>

# 3. Use different port
API_PORT=8001 make dev
```

### Monitoring Issues

#### Prometheus Not Scraping Metrics
**Problem**: No data showing in Grafana

**Solutions**:
```bash
# 1. Verify metrics endpoint
curl http://localhost:8000/api/v1/monitoring/metrics

# 2. Check Prometheus targets
open http://localhost:9090/targets

# 3. Verify network connectivity
docker-compose exec prometheus ping backend

# 4. Restart monitoring stack
make monitoring-restart
```

#### Grafana Dashboard Not Loading
**Problem**: Dashboard shows "No data"

**Solutions**:
```bash
# 1. Check Prometheus data source
# In Grafana: Configuration > Data Sources > Prometheus

# 2. Verify time range
# Adjust time picker in Grafana

# 3. Check if metrics are being collected
curl http://localhost:9090/api/v1/query?query=up

# 4. Reimport dashboards
make grafana-import
```

### Frontend Issues

#### React Build Failures
**Problem**: `npm run build` fails

**Solutions**:
```bash
# 1. Clear node_modules and reinstall
cd src/frontend
rm -rf node_modules package-lock.json
npm install

# 2. Clear cache
npm cache clean --force

# 3. Use compatible Node version
nvm use 18
# or
nvm install 18
```

#### WebSocket Connection Refused
**Problem**: Real-time chat not working

**Solutions**:
```bash
# 1. Check WebSocket endpoint
wscat -c ws://localhost:8000/api/v1/chat/ws

# 2. Verify CORS settings
ALLOWED_ORIGINS=http://localhost:3000

# 3. Check firewall/proxy settings
# Ensure WebSocket connections are allowed

# 4. Test with direct connection
# Bypass any reverse proxies
```

## Quick Diagnostics

### Run Full System Check
```bash
# Comprehensive health check
make health

# Check all services
make status

# View logs
make logs

# Run diagnostic tests
make test-integration
```

### Get System Information
```bash
# View configuration
make config-show

# Check model availability
make models-list

# Test all providers
make models-health

# View active metrics
make metrics
```

## Getting Help

### Enable Debug Mode
```env
# In .env
DEBUG=true
LOG_LEVEL=debug
ENABLE_SQL_ECHO=true
```

### Collect Diagnostic Information
```bash
# Generate diagnostic report
make diagnostics > diagnostics.txt

# Include:
# - System information
# - Configuration (redacted secrets)
# - Recent logs
# - Health check results
# - Docker status
# - Network connectivity
```

### Report Issues
When reporting issues, include:
1. Zakera version: `grep version README.md`
2. Operating system and version
3. Python version: `python --version`
4. Error messages and full stack traces
5. Steps to reproduce
6. Diagnostic report (if applicable)

**GitHub Issues**: https://github.com/itsmepraks/zakera/issues

## Prevention Tips

1. **Regular Updates**:
   ```bash
   git pull origin main
   make install
   make db-upgrade
   ```

2. **Monitor Resources**:
   ```bash
   # Set up alerts in Grafana
   # Watch for: CPU > 80%, Memory > 90%, Error rate > 5%
   ```

3. **Backup Database**:
   ```bash
   make db-backup
   # Scheduled: cron job for daily backups
   ```

4. **Test Before Deployment**:
   ```bash
   make test
   make test-integration
   make health
   ```

5. **Keep Logs Clean**:
   ```bash
   # Log rotation is automatic, but monitor:
   make logs-rotate
   ```

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_PRODUCTION.md)
- [API Reference](http://localhost:8000/api/docs)
- [Monitoring Guide](MONITORING.md)

---

**Last Updated**: February 18, 2026  
**Version**: 0.5.0
