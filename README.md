# Zakera - AI Chat Agent

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Monitoring](https://img.shields.io/badge/monitoring-Prometheus-orange.svg)](https://prometheus.io/)

A modern, production-ready AI chat agent with conversational memory, multi-provider LLM support, comprehensive tool integration, and enterprise-grade monitoring. Built for developers who need a robust foundation for context-aware chatbot applications.

## ✨ Features

### Core Capabilities
- **🧠 Conversation Memory**: Context-aware multi-turn conversations with efficient memory management
- **🤖 Multi-Provider LLM Support**: OpenAI, Anthropic, Google Gemini, Ollama, HuggingFace
- **🏠 Local Model Support**: Run Llama, Mistral, CodeLlama locally - no API costs!
- **🛠️ Tool Integration**: Extensible tool system with built-in tools and custom tool support
- **⚡ Smart Fallback**: Automatic fallback between providers for reliability
- **🔌 Flexible API**: RESTful and WebSocket endpoints for all integration scenarios
- **💾 Persistent Storage**: SQLAlchemy-backed conversation history and user preferences
- **🎨 Modern UI**: React + TypeScript frontend with tool system integration

### Enterprise Features
- **📊 Prometheus Metrics**: 50+ metrics for comprehensive monitoring
- **📝 Structured Logging**: JSON logs with correlation IDs and log rotation
- **💚 Health Checks**: Kubernetes-ready liveness and readiness probes
- **🚨 Alert System**: Email, Slack, and Discord notifications
- **📈 Grafana Dashboards**: Pre-built visualization dashboards
- **🔒 Authentication**: JWT-based secure authentication
- **⏱️ Performance Tracking**: Execution time monitoring and profiling
- **🎯 Rate Limiting**: Configurable rate limits per user and endpoint

### Advanced Features
- Conversation branching and versioning
- Real-time streaming responses from all providers
- Model cost tracking and optimization
- Tool caching and parallel execution
- Custom prompt templates
- Analytics and usage tracking
- WebSocket support with authentication

## 🏗️ Architecture

```
zakera/
├── src/
│   ├── model/          # Multi-provider LLM system
│   │   ├── providers.py           # Base providers (OpenAI, Anthropic, Gemini)
│   │   ├── providers_ollama.py    # Ollama local models
│   │   ├── providers_huggingface.py  # HuggingFace Transformers
│   │   ├── model_manager.py       # Fallback and routing
│   │   └── config.py              # Model configuration
│   ├── api/            # FastAPI backend
│   │   ├── routes/     # API endpoints
│   │   ├── main.py     # Application entry
│   │   └── ...         # Auth, database, config
│   ├── frontend/       # React + TypeScript UI
│   │   ├── src/
│   │   │   ├── components/tools/  # Tool system UI
│   │   │   ├── types/             # TypeScript types
│   │   │   └── services/          # API clients
│   │   └── package.json
│   ├── tools/          # Tool system
│   │   ├── base.py     # Base tool classes
│   │   ├── manager.py  # Tool execution manager
│   │   ├── registry.py # Tool registry
│   │   └── builtin/    # Built-in tools
│   └── monitoring/     # Observability system
│       ├── metrics.py      # Prometheus metrics
│       ├── logging.py      # Structured logging
│       ├── health.py       # Health checks
│       ├── performance.py  # Performance tracking
│       └── alerts.py       # Alert management
├── monitoring/         # Monitoring stack
│   ├── prometheus.yml       # Prometheus config
│   ├── alertmanager.yml     # Alert routing
│   ├── alerts.yml           # Alert rules
│   ├── docker-compose.yml   # Monitoring stack
│   └── grafana/             # Dashboards
├── config/             # Configuration files
├── docs/               # Comprehensive documentation
├── tests/              # Test suites (50+ tests)
└── Makefile            # Build automation
```

## 🚀 Quick Start

### Option 1: Quick Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/itsmepraks/zakera.git
cd zakera

# Install dependencies
make install

# Setup local models (optional but recommended)
make ollama-install
make ollama-pull

# Start monitoring stack
make monitoring-start

# Start development server
make dev

# Access:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/api/docs
# - Grafana: http://localhost:3001 (admin/admin)
# - Prometheus: http://localhost:9090
```

### Option 2: Manual Setup

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the backend
python -m uvicorn src.api.main:app --reload
```

#### Frontend Setup

```bash
# Navigate to frontend
cd src/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

#### Monitoring Setup

```bash
# Start monitoring stack
cd monitoring
docker-compose up -d

# Verify services
docker-compose ps
```

## 🤖 Model Providers

### API-Based Providers

#### OpenAI (GPT-4, GPT-3.5)
```env
OPENAI_API_KEY=sk-...
DEFAULT_MODEL=gpt-4-turbo
```

#### Anthropic (Claude 3)
```env
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=claude-3-sonnet
```

#### Google Gemini
```env
GOOGLE_API_KEY=AIza...
DEFAULT_MODEL=gemini-1.5-pro
```

### Local Providers (No API Costs!)

#### Ollama (Recommended)
```bash
# Install Ollama
make ollama-install

# Pull models
ollama pull llama3:8b      # General chat (4.7GB)
ollama pull mistral:7b     # Fast responses (4.1GB)
ollama pull codellama:13b  # Code generation (7.4GB)

# Configure
DEFAULT_MODEL=llama3:8b
ENABLE_OLLAMA=true
```

#### HuggingFace Transformers
```env
HUGGINGFACE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
HUGGINGFACE_DEVICE=cuda  # or cpu
HUGGINGFACE_8BIT=true  # Enable quantization
```

**See [docs/LOCAL_MODELS.md](docs/LOCAL_MODELS.md) for detailed setup**

## 📊 Monitoring & Observability

### Metrics Dashboard

Access comprehensive metrics via Grafana:
- API performance and latency
- Model usage and costs
- Tool execution statistics
- System resources (CPU, memory, disk)
- Database performance
- Error rates and status codes

### Health Checks

```bash
# Detailed health check
curl http://localhost:8000/api/v1/monitoring/health?detailed=true

# Quick health check
make health
```

### Alerts

Automatic alerts for:
- High error rates (>5%)
- Slow response times
- Model provider failures
- System resource exhaustion
- Database issues

**Configure in `monitoring/alertmanager.yml`**

### Logging

Structured JSON logs with:
- Correlation IDs for request tracking
- Performance metrics per request
- Error context and stack traces
- Automatic log rotation

**See [docs/MONITORING.md](docs/MONITORING.md) for complete guide**

## 📚 Documentation

### Setup Guides
- [Local Models Setup](docs/LOCAL_MODELS.md) - Ollama and HuggingFace configuration
- [Monitoring Guide](docs/MONITORING.md) - Observability setup
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Tool Development](docs/tools.md) - Creating custom tools
- [Configuration Guide](docs/configuration.md) - Environment setup
- [Deployment Guide](docs/deployment.md) - Production deployment

### Summary Documents
- [Tool System Summary](TOOL_SYSTEM_SUMMARY.md) - Tool implementation details
- [Model System Summary](MODEL_SYSTEM_SUMMARY.md) - Multi-provider setup
- [Monitoring Summary](MONITORING_SYSTEM_SUMMARY.md) - Observability features
- [CI/CD Summary](CI_CD_SUMMARY.md) - Pipeline configuration

## 🛠️ Development

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
mypy src/
```

### Using Make Commands

```bash
# View all available commands
make help

# Development
make dev              # Start dev server
make test             # Run tests
make format           # Format code

# Monitoring
make monitoring-start # Start Prometheus, Grafana, AlertManager
make health           # Check application health
make metrics          # View current metrics
make alerts           # View active alerts

# Models
make ollama-install   # Install Ollama
make ollama-pull      # Download models
make models-list      # List available models
make models-health    # Check provider health
```

## 🔧 Configuration

Key configuration in `.env`:

```env
# Model Configuration
DEFAULT_MODEL=llama3:8b  # or gpt-4-turbo, claude-3-sonnet
FALLBACK_STRATEGY=sequential
ENABLE_MODEL_FALLBACK=true

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_OLLAMA=true

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO
ENABLE_ALERTS=true

# Database
DATABASE_URL=sqlite:///./data/zakera.db

# Security
SECRET_KEY=your_secret_key_change_in_production
ALLOWED_ORIGINS=http://localhost:3000
```

## 📈 Monitoring Stack

### Access Points

- **Grafana Dashboard**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093
- **API Metrics**: http://localhost:8000/api/v1/monitoring/metrics
- **Health Check**: http://localhost:8000/api/v1/monitoring/health

### Key Metrics

- **API Performance**: Request rate, latency, error rate
- **Model Usage**: Requests by provider, token usage, costs
- **Tool Executions**: Success rate, cache hits, execution time
- **System Resources**: CPU, memory, disk usage
- **Database**: Query performance, connection pool status

## 🎯 Use Cases

### 1. Cost-Optimized Chat
```bash
# Use free local models for most requests
DEFAULT_MODEL=llama3:8b
FALLBACK_STRATEGY=none

# Only use API models when explicitly requested
```

### 2. High-Quality Production
```bash
# Use best models with fallback
DEFAULT_MODEL=gpt-4-turbo
FALLBACK_STRATEGY=sequential

# Falls back to: gpt-4 → claude-3-sonnet → gpt-3.5 → llama3:8b
```

### 3. Privacy-First Local
```bash
# All processing stays local
DEFAULT_MODEL=llama3:70b
ENABLE_OLLAMA=true
ENABLE_OPENAI=false
ENABLE_ANTHROPIC=false
```

### 4. Development with Monitoring
```bash
# Full stack with observability
make monitoring-start
make dev

# Access Grafana for real-time metrics
open http://localhost:3001
```

## 🚀 Production Deployment

### Docker

```bash
# Build image
make docker-build

# Run container
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e DEFAULT_MODEL=gpt-3.5-turbo \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  zakera:latest
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zakera
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: zakera
        image: zakera:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/v1/monitoring/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/monitoring/health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: zakera-secrets
              key: openai-api-key
```

## 📚 API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

**Chat & Conversations:**
- `POST /api/v1/chat/send` - Send chat message
- `GET /api/v1/conversations` - List conversations
- `WebSocket /api/v1/chat/ws` - Real-time chat

**Models:**
- `GET /api/v1/models/` - List available models
- `POST /api/v1/models/generate` - Generate with any model
- `GET /api/v1/models/health` - Provider health status

**Tools:**
- `GET /api/v1/tools/` - List available tools
- `POST /api/v1/tools/execute` - Execute tool
- `GET /api/v1/tools/history` - Execution history

**Monitoring:**
- `GET /api/v1/monitoring/metrics` - Prometheus metrics
- `GET /api/v1/monitoring/health` - Health check
- `GET /api/v1/monitoring/alerts` - Active alerts
- `GET /api/v1/monitoring/performance` - Performance stats

## 🧪 Testing

```bash
# Run all tests (50+ test cases)
make test

# Run with coverage report
make test-cov

# Run specific test file
pytest tests/test_tools.py -v

# Run tests with markers
pytest -m "not slow"
pytest -m integration
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

### Development Workflow

```bash
# 1. Format code
make format

# 2. Run linters
make lint

# 3. Run tests
make test-cov

# 4. Check monitoring
make health

# 5. Commit and push
```

## 📊 Performance

### Benchmarks (Local M1 Mac)

| Model | Provider | Tokens/sec | Latency (p95) | Cost/1K tokens |
|-------|----------|------------|---------------|----------------|
| GPT-4 Turbo | OpenAI | ~40 | 2.5s | $0.04 |
| Claude 3 Sonnet | Anthropic | ~35 | 2.8s | $0.018 |
| Llama 3 8B | Ollama | ~25 | 1.2s | **FREE** |
| Mistral 7B | Ollama | ~30 | 0.9s | **FREE** |
| GPT-3.5 | OpenAI | ~60 | 0.8s | $0.002 |

*Results may vary based on hardware and configuration*

## 🔒 Security

- JWT-based authentication
- API key encryption
- Rate limiting per user
- CORS configuration
- SQL injection protection
- Input validation
- Secure password hashing

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by modern conversational AI systems
- Built with FastAPI, React, Prometheus, and modern AI technologies
- Community contributions and feedback
- Open source LLM community (Ollama, HuggingFace)

## 📧 Contact

Prakriti Bista - [https://praks.me](https://praks.me)

Project Link: [https://github.com/itsmepraks/zakera](https://github.com/itsmepraks/zakera)

## 🎯 Roadmap

- [ ] Voice input/output support
- [ ] Multi-language support
- [ ] Plugin marketplace
- [ ] Cloud deployment templates (AWS, GCP, Azure)
- [ ] Mobile app (React Native)
- [ ] Enterprise SSO integration
- [ ] Advanced RAG (Retrieval-Augmented Generation)
- [ ] Fine-tuning support

---

**Version**: 0.5.0  
**Status**: Production-Ready 🚀  
**Last Updated**: February 2026

**Quick Links:**
- [🚀 Quick Start](#quick-start)
- [📚 Documentation](docs/)
- [🤖 Model Setup](docs/LOCAL_MODELS.md)
- [📊 Monitoring](docs/MONITORING.md)
- [🛠️ API Docs](http://localhost:8000/api/docs)
