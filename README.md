# Zakera - AI Chat Agent

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg)](https://github.com/itsmepraks/zakera/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Monitoring](https://img.shields.io/badge/monitoring-Prometheus-orange.svg)](https://prometheus.io/)
[![Tracing](https://img.shields.io/badge/tracing-OpenTelemetry-blueviolet.svg)](https://opentelemetry.io/)

A modern, production-ready AI chat agent with conversational memory, multi-provider LLM support, comprehensive tool integration, and enterprise-grade observability. Built for developers who need a robust foundation for context-aware chatbot applications.

## ✨ Features

### Core Capabilities
- **🧠 Conversation Memory**: Context-aware multi-turn conversations with efficient memory management
- **🤖 Multi-Provider LLM Support**: OpenAI, Anthropic, **Google Gemini**, Ollama, HuggingFace, Cohere, Groq, Mistral
- **🏠 Local Model Support**: Run Llama, Mistral, CodeLlama locally - no API costs!
- **🛠️ Tool Integration**: Extensible tool system with built-in tools and custom tool support
- **⚡ Smart Fallback**: Automatic fallback between providers for reliability
- **🔌 Flexible API**: RESTful and WebSocket endpoints for all integration scenarios
- **💾 Persistent Storage**: SQLAlchemy-backed conversation history and user preferences
- **🎨 Modern UI**: React + TypeScript frontend with tool system integration

### Enterprise Features
- **🔄 CI/CD Pipeline**: Automated testing, security scanning, and deployment with GitHub Actions
- **🔍 Distributed Tracing**: **OpenTelemetry + Jaeger** for end-to-end request visibility **(NEW!)**
- **📊 Prometheus Metrics**: 50+ metrics for comprehensive monitoring
- **📍d Structured Logging**: JSON logs with correlation IDs and log rotation
- **💚 Health Checks**: Kubernetes-ready liveness and readiness probes
- **🚨 Alert System**: Email, Slack, and Discord notifications
- **📈 Grafana Dashboards**: Pre-built visualization dashboards
- **🔒 Authentication**: JWT-based secure authentication with MFA support
- **⏱️ Performance Tracking**: Execution time monitoring and profiling
- **🎯 Rate Limiting**: Configurable rate limits per user and endpoint
- **🔐 Security Scanning**: Automated vulnerability detection with Trivy, Bandit, CodeQL

### Advanced Features
- Conversation branching and versioning
- Real-time streaming responses from all providers
- Model cost tracking and optimization
- Tool caching and parallel execution
- Custom prompt templates
- Analytics and usage tracking
- WebSocket support with authentication
- **📥 Conversation Export**: Stream exports in JSON, Markdown, Text, CSV formats with progress updates

## 🆕 What's New

### Latest Updates (February 2026)

- 🔍 **Distributed Tracing**: Production-ready OpenTelemetry integration with Jaeger visualization **(NEW!)**
- ✨ **Google Gemini Integration**: Added support for Gemini 1.5 Pro (2M context) and Flash models
- 🔄 **CI/CD Pipeline**: Production-ready GitHub Actions workflow with matrix builds and security scanning
- 📚 **API Integration Guide**: Comprehensive documentation with code examples in multiple languages
- 🤖 **8 Model Providers**: Now supporting OpenAI, Anthropic, Gemini, Ollama, HuggingFace, Cohere, Groq, and Mistral
- 🔐 **Enhanced Security**: Automated dependency scanning, secret detection, and vulnerability alerts
- 📊 **Better Monitoring**: Improved metrics, dashboards, and alerting capabilities

## 🔍 Distributed Tracing

### Overview

Zakera now includes production-ready distributed tracing with **OpenTelemetry** and **Jaeger**, providing complete visibility into every request:

```
GET /api/v1/chat/send                      [245ms]
├── auth.validate_token                    [8ms]
├── conversation.get                       [15ms]
│   └── db.query.conversations             [12ms]
├── model.openai.gpt-4                     [200ms]
│   ├── cache.check                        [3ms]
│   ├── http.post                          [190ms]
│   └── cache.set                          [5ms]
└── conversation.update                    [22ms]
    └── db.query.update                    [18ms]
```

### What Gets Traced?

✅ **All API Requests** - Automatic FastAPI instrumentation  
✅ **Model Provider Calls** - OpenAI, Anthropic, Gemini, Ollama, etc.  
✅ **Conversation Flows** - Message creation, retrieval, updates  
✅ **Tool Executions** - Built-in and custom tools  
✅ **Database Queries** - Automatic SQLAlchemy instrumentation  
✅ **HTTP Requests** - Outgoing API calls to external services  
✅ **Cache Operations** - Redis and in-memory cache access  
✅ **WebSocket Connections** - Real-time messaging flows  

### Quick Start with Tracing

```bash
# Enable tracing
export ENABLE_TRACING=true
export TRACE_SAMPLING_RATE=1.0  # 100% for development

# Start with Jaeger
docker-compose up -d

# View traces at http://localhost:16686
```

### Benefits

- 🐛 **Faster Debugging**: Identify bottlenecks and errors in seconds
- 📊 **Performance Optimization**: See exactly where time is spent
- 💰 **Cost Tracking**: Monitor model usage and costs per user/conversation
- 🔗 **Service Dependencies**: Understand how components interact
- 🎯 **SLA Monitoring**: Ensure response times meet requirements

### Custom Tracing

```python
from monitoring.trace_decorators import trace_model_call, trace_conversation

@trace_model_call(provider="openai", model="gpt-4")
async def call_gpt4(prompt: str):
    response = await openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response
    # Trace includes: tokens, cost, latency, errors

@trace_conversation()
async def process_message(conversation_id: str, message: str):
    # Automatically traced with conversation context
    response = await generate_response(conversation_id, message)
    return response
```

**See [docs/DISTRIBUTED_TRACING.md](docs/DISTRIBUTED_TRACING.md) for complete guide**

## 🏗️ Architecture

```
zakera/
├── .github/workflows/      # CI/CD pipelines
│   ├── ci.yml             # Comprehensive CI pipeline
│   ├── security.yml       # Security scanning
│   ├── deploy-staging.yml # Staging deployment
│   └── deploy-production.yml # Production deployment
├── src/
│   ├── model/             # Multi-provider LLM system
│   │   ├── providers.py           # Base providers (OpenAI, Anthropic)
│   │   ├── providers_gemini.py    # Google Gemini
│   │   ├── providers_ollama.py    # Ollama local models
│   │   ├── providers_huggingface.py  # HuggingFace Transformers
│   │   ├── providers_cohere.py    # Cohere integration
│   │   ├── providers_groq.py      # Groq integration
│   │   ├── providers_mistral.py   # Mistral AI
│   │   ├── model_manager.py       # Fallback and routing
│   │   └── config.py              # Model configuration
│   ├── api/               # FastAPI backend
│   ├── frontend/          # React + TypeScript UI
│   ├── tools/             # Tool system
│   ├── monitoring/        # Observability system
│   │   ├── tracing.py             # OpenTelemetry setup (NEW!)
│   │   ├── trace_decorators.py    # Tracing decorators (NEW!)
│   │   ├── instrumentation.py     # Auto-instrumentation (NEW!)
│   │   └── metrics.py             # Prometheus metrics
│   ├── security/          # Auth & security
│   └── utils/             # Utilities
├── docs/                  # Documentation
│   ├── DISTRIBUTED_TRACING.md  # Tracing guide (NEW!)
│   ├── api-integration-guide.md  # Complete API guide
│   ├── quickstart.md             # Quick start guide
│   ├── gemini-provider.md        # Gemini docs
│   └── ...
├── tests/                 # Test suites (75%+ coverage)
├── monitoring/            # Monitoring stack
├── kubernetes/            # K8s deployment
├── helm/                  # Helm charts
├── terraform/             # Infrastructure as Code
└── Makefile              # Build automation
```

## 🚀 Quick Start

### 5-Minute Setup

```bash
# Clone and install
git clone https://github.com/itsmepraks/zakera.git
cd zakera
make install

# Configure (edit .env with your API keys)
cp .env.example .env

# Start services (includes Jaeger for tracing)
make dev

# Access:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/api/docs
# - Jaeger UI: http://localhost:16686
# - Grafana: http://localhost:3001
```

### First API Call

```python
from zakera import ZakeraClient

client = ZakeraClient(api_key="your-api-key")

response = await client.chat.send(
    message="Explain quantum computing simply",
    model="gemini-1.5-flash"  # Fast and affordable!
)

print(response.content)
print(f"Cost: ${response.cost:.6f}")
```

**See [docs/quickstart.md](docs/quickstart.md) for detailed setup**

## 🤖 Model Providers

### Supported Providers (8 Total)

| Provider | Models | Context | Cost/1K (Input) | Best For |
|----------|--------|---------|-----------------|----------|
| **Google Gemini** 🆕 | 1.5 Pro, Flash | 2M / 1M | $0.00125 / $0.000125 | Large context, cost-effective |
| OpenAI | GPT-4, 3.5 | 128K | $0.01 | High quality, reliable |
| Anthropic | Claude 3 | 200K | $0.003 | Long context, analysis |
| Ollama | Llama, Mistral | 32K | **FREE** | Local, private, no cost |
| HuggingFace | Various | Varies | **FREE** | Custom models, research |
| Cohere | Command | 128K | $0.0015 | Multilingual, embeddings |
| Groq | Llama, Mixtral | 32K | $0.00027 | Ultra-fast inference |
| Mistral | Mistral, Mixtral | 32K | $0.00065 | European alternative |

## 📊 Monitoring & Observability

### Complete Observability Stack

- **🔍 Distributed Tracing**: OpenTelemetry + Jaeger - http://localhost:16686
- **📈 Grafana**: Metrics visualization - http://localhost:3001
- **📊 Prometheus**: Metrics collection - http://localhost:9090
- **🚨 AlertManager**: Alert routing - http://localhost:9093
- **💚 Health Check**: API health - http://localhost:8000/api/v1/monitoring/health

### Key Capabilities

**Distributed Tracing**:
- End-to-end request visibility
- Model provider call tracking
- Database query profiling
- Tool execution monitoring
- Error tracking and debugging
- Performance bottleneck identification

**Metrics**:
- API performance (latency, throughput, error rate)
- Model usage by provider (requests, tokens, costs)
- Tool executions (success rate, cache hits, duration)
- System resources (CPU, memory, disk, network)
- Database performance (query time, connection pool)

**Alerts**:
Automatic notifications for:
- High error rates (>5%)
- Slow response times (>5s p95)
- Model provider failures
- Resource exhaustion
- Security incidents

## 📚 Documentation

### Quick Links
- 🔍 **[Distributed Tracing Guide](docs/DISTRIBUTED_TRACING.md)** - **Complete OpenTelemetry guide (NEW!)**
- 📚 [API Integration Guide](docs/api-integration-guide.md) - **Complete guide with code examples**
- 🚀 [Quick Start](docs/quickstart.md) - **Get started in 5 minutes**
- 🤖 [Gemini Provider](docs/gemini-provider.md) - **Google Gemini setup**
- 🔄 [CI/CD Pipeline](.github/workflows/ci.yml) - **Automated testing and deployment**
- 📊 [Monitoring Guide](docs/MONITORING.md) - Observability setup
- 📥 [Conversation Export](docs/CONVERSATION_EXPORT.md) - Export in multiple formats
- 🔒 [Authentication Guide](docs/authentication.md) - Auth setup
- 🛠️ [Tool Development](docs/tools.md) - Creating custom tools

### API Documentation
- **Swagger UI**: http://localhost:8000/api/docs (Interactive)
- **ReDoc**: http://localhost:8000/api/redoc (Clean reference)
- **Postman Collection**: Available in [docs/postman/](docs/postman/)

## 🎯 Roadmap

### Completed ✅
- [x] Multi-provider support (8 providers)
- [x] Google Gemini integration
- [x] **Distributed tracing with OpenTelemetry + Jaeger** ✨
- [x] Conversation export (streaming)
- [x] Production CI/CD pipeline
- [x] Comprehensive API documentation
- [x] Security scanning automation
- [x] Monitoring and alerting
- [x] Docker and Kubernetes support

### In Progress 🚧
- [ ] Voice input/output support
- [ ] Advanced RAG (Retrieval-Augmented Generation)
- [ ] Plugin marketplace
- [ ] Mobile app (React Native)

### Planned 📋
- [ ] Multi-language UI support
- [ ] Enterprise SSO integration
- [ ] Cloud deployment templates (AWS, GCP, Azure)
- [ ] Fine-tuning support
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework

---

**Version**: 0.7.0  
**Status**: Production-Ready 🚀  
**Last Updated**: February 2026

**⭐ If you find this project useful, please star it on GitHub!**

**Quick Navigation:**
- [🚀 Quick Start](#quick-start)
- [🔍 Distributed Tracing](#distributed-tracing)
- [📚 API Integration Guide](docs/api-integration-guide.md)
- [🤖 Model Providers](#model-providers)
- [🔄 CI/CD Pipeline](#cicd-pipeline)
- [📊 Monitoring](#monitoring--observability)
- [🛠️ Development](#development)
- [🚀 Deployment](#production-deployment)
- [🤝 Contributing](#contributing)
