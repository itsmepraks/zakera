# Deployment Guide

This guide covers deploying Zakera AI Chat Agent using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Production Deployment](#production-deployment)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker 20.10 or higher
- Docker Compose 2.0 or higher
- At least 2GB of available RAM
- 10GB of available disk space
- API keys for your chosen AI provider (OpenAI, Anthropic, or Google)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/itsmepraks/zakera.git
cd zakera
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp config/.env.example .env
```

Edit `.env` and set your API keys:

```env
# AI Model Configuration
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4-turbo-preview
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
GOOGLE_API_KEY=your-google-api-key

# Database
POSTGRES_PASSWORD=your-secure-postgres-password

# Redis
REDIS_PASSWORD=your-secure-redis-password

# Security
SECRET_KEY=your-very-secret-key-change-this
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:80

# Optional
DEBUG=false
ENABLE_METRICS=true
```

### 3. Start the Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access the Application

- **Frontend**: http://localhost
- **API**: http://localhost/api
- **API Documentation**: http://localhost/api/docs
- **Health Check**: http://localhost/health
- **Metrics** (if enabled): http://localhost/metrics

## Configuration

### Service Architecture

The Docker Compose setup includes:

1. **PostgreSQL**: Primary database for persistent storage
2. **Redis**: Caching and session management
3. **Backend**: FastAPI application server
4. **Nginx**: Reverse proxy and static file server

### Environment Variables

#### API Configuration

- `API_HOST`: Host to bind the API (default: 0.0.0.0)
- `API_PORT`: Port for the API (default: 8000)
- `DEBUG`: Enable debug mode (default: false)

#### Database Configuration

- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_PASSWORD`: PostgreSQL password

#### Cache Configuration

- `REDIS_URL`: Redis connection string
- `REDIS_PASSWORD`: Redis authentication password

#### AI Model Configuration

- `MODEL_PROVIDER`: AI provider (openai, anthropic, google, local)
- `MODEL_NAME`: Specific model to use
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `GOOGLE_API_KEY`: Google API key

#### Security Configuration

- `SECRET_KEY`: Secret key for JWT tokens and encryption
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)

### Volume Management

Data is persisted in Docker volumes:

```bash
# List volumes
docker volume ls

# Backup database
docker-compose exec postgres pg_dump -U zakera zakera > backup.sql

# Restore database
docker-compose exec -T postgres psql -U zakera zakera < backup.sql
```

## Production Deployment

### 1. Security Hardening

```bash
# Generate strong secrets
openssl rand -hex 32  # For SECRET_KEY
openssl rand -base64 32  # For passwords
```

Update `.env` with production values:

```env
DEBUG=false
SECRET_KEY=<generated-secret-key>
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
ALLOWED_ORIGINS=https://yourdomain.com
```

### 2. SSL/TLS Configuration

Update `config/nginx.conf` to add SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # ... rest of configuration
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. Resource Limits

Update `docker-compose.yml` to add resource limits:

```yaml
services:
  backend:
    # ... existing configuration
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 4. Production Startup

```bash
# Use production compose file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale backend services
docker-compose up -d --scale backend=3
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check all services
docker-compose ps

# Check individual service health
curl http://localhost/health
```

### Logs

```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100
```

### Database Maintenance

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U zakera

# Clean up expired sessions
docker-compose exec postgres psql -U zakera zakera -c "SELECT cleanup_expired_sessions();"

# Vacuum database
docker-compose exec postgres vacuumdb -U zakera -d zakera -z
```

### Redis Maintenance

```bash
# Access Redis CLI
docker-compose exec redis redis-cli -a <your-redis-password>

# Check memory usage
docker-compose exec redis redis-cli -a <your-redis-password> INFO memory

# Flush all cache (use with caution)
docker-compose exec redis redis-cli -a <your-redis-password> FLUSHALL
```

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Service Won't Start

```bash
# Check service logs
docker-compose logs <service-name>

# Check Docker events
docker events

# Verify configuration
docker-compose config
```

### Database Connection Issues

```bash
# Test database connectivity
docker-compose exec backend python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://zakera:password@postgres:5432/zakera'); print('Connected!' if engine.connect() else 'Failed')"

# Check PostgreSQL logs
docker-compose logs postgres
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Limit container resources (see Production Deployment section)
```

### API Response Errors

```bash
# Check backend logs
docker-compose logs backend

# Verify environment variables
docker-compose exec backend env | grep API

# Test API endpoint
curl -v http://localhost/api/health
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose exec redis redis-cli -a <password> ping

# Check Redis logs
docker-compose logs redis
```

## Advanced Configuration

### Using Google Gemini

```env
MODEL_PROVIDER=google
MODEL_NAME=gemini-pro
GOOGLE_API_KEY=your-google-api-key
```

### Using Local Models (Ollama)

```yaml
# Add to docker-compose.yml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: zakera-ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    networks:
      - zakera-network

volumes:
  ollama_data:
```

```env
MODEL_PROVIDER=local
MODEL_NAME=llama2
LOCAL_MODEL_URL=http://ollama:11434
```

### Horizontal Scaling

```bash
# Scale backend to 3 instances
docker-compose up -d --scale backend=3

# Add load balancer configuration to nginx.conf
```

## Support

For issues and questions:

- GitHub Issues: https://github.com/itsmepraks/zakera/issues
- Documentation: https://github.com/itsmepraks/zakera/tree/main/docs
