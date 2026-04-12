# Zakera - AI Chat Agent

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg)](https://github.com/itsmepraks/zakera/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Monitoring](https://img.shields.io/badge/monitoring-Prometheus-orange.svg)](https://prometheus.io/)
[![Tracing](https://img.shields.io/badge/tracing-OpenTelemetry-blueviolet.svg)](https://opentelemetry.io/)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-brightgreen.svg)](docs/)

A modern, production-ready AI chat agent with conversational memory, multi-provider LLM and embedding support, comprehensive tool integration, and enterprise-grade observability. Built for developers who need a robust foundation for context-aware chatbot applications.

## ✨ Features

### Core Capabilities
- **🧠 Conversation Memory**: Context-aware multi-turn conversations with efficient memory management
- **🤖 Multi-Provider AI Support**: OpenAI, Anthropic, Google Gemini, Groq, Mistral, Cohere, xAI, DeepSeek, Fireworks, Together AI, Perplexity, OpenRouter, Azure, Vertex AI, Cerebras, DeepInfra, HuggingFace, Ollama, and Jina AI embeddings
- **🏠 Local Model Support**: Run Llama, Mistral, CodeLlama locally - no API costs!
- **🛠️ Tool Integration**: Extensible tool system with built-in tools and custom tool support
- **⭐ User Message Feedback Loop**: Database-backed positive/negative feedback system for AI responses
- **⚡ Smart Fallback**: Automatic fallback between providers for reliability
- **🔌 Flexible API**: RESTful and WebSocket endpoints for all integration scenarios
- **💾 Persistent Storage**: SQLAlchemy-backed conversation history and user preferences
- **🎨 Modern UI**: React + TypeScript frontend with tool system integration

### Enterprise Features
- **🔄 CI/CD Pipeline**: Automated testing, security scanning, and deployment with GitHub Actions
- **🔍 Distributed Tracing**: **OpenTelemetry + Jaeger** for end-to-end request visibility
- **📊 Prometheus Metrics**: 50+ metrics for comprehensive monitoring
- **📝 Structured Logging**: JSON logs with correlation IDs and log rotation
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

- 📚 **Documentation Reorganization**: Clean, organized docs structure with comprehensive navigation
- 🔍 **Distributed Tracing**: Production-ready OpenTelemetry integration with Jaeger visualization
- ✨ **Google Gemini Integration**: Added support for Gemini 1.5 Pro (2M context) and Flash models
- ⚡ **Groq LPU Support**: Ultra-high-speed inference via Groq's API for Llama 3 and Mixtral models
- ⭐ **Feedback System**: Integrated a user feedback loop to track response quality and improve model performance
- 🔄 **CI/CD Pipeline**: Production-ready GitHub Actions workflow with matrix builds and security scanning
- 📚 **API Integration Guide**: Comprehensive documentation with code examples in multiple languages
- 🤖 **19 AI Providers**: Now supporting OpenAI, Anthropic, Gemini, Groq, Mistral, Cohere, xAI, DeepSeek, Fireworks, Together AI, Perplexity, OpenRouter, Azure, Vertex AI, Cerebras, DeepInfra, HuggingFace, Ollama, and Jina AI embeddings
- 🔐 **Enhanced Security**: Automated dependency scanning, secret detection, and vulnerability alerts
- 📊 **Better Monitoring**: Improved metrics, dashboards, and alerting capabilities

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

**📖 For detailed setup instructions, see [Quick Start Guide](docs/QUICKSTART.md)**

## 🤖 Model Providers

### Supported Providers (19 Total)

| Provider | Example models / service | Notes |
|----------|--------------------------|-------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo | High-quality general chat and tool calling |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3.7 Sonnet, Claude 3 Haiku | Long-context reasoning and vision |
| **Google Gemini** | Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.0 Flash | Large context, fast multimodal |
| **Groq** | Llama 3, Mixtral | Ultra-fast inference |
| **Mistral** | Mistral, Mixtral, Codestral | Strong European/open models |
| **Cohere** | Command R+, Command R, Command Light | Retrieval-augmented chat |
| **xAI** | Grok | Up-to-date conversational models |
| **DeepSeek** | DeepSeek-V3, DeepSeek-R1 | General and reasoning models |
| **Fireworks** | Llama 3.1, Mistral, Qwen, DeepSeek distills | Open-model inference API |
| **Together AI** | Llama 3.3 / 3.1, Mistral, Qwen, DeepSeek, Gemma | Large catalog of hosted OSS models |
| **Perplexity** | Sonar | Search-grounded answers |
| **OpenRouter** | Many vendor-hosted models | Unified API across providers |
| **Azure** | Azure OpenAI deployments | Enterprise OpenAI compatibility |
| **Vertex AI** | Gemini models on Google Cloud | Managed Google AI platform |
| **Cerebras** | Llama 3.1, Qwen, and other hosted models | High-throughput inference |
| **DeepInfra** | Open-source chat and code models | Low-friction hosted inference |
| **HuggingFace** | Hosted inference models | Flexible research and custom models |
| **Ollama** | Local Llama, Mistral, CodeLlama, etc. | Private on-device inference |
| **Jina AI** | jina-embeddings-v3 | Embeddings for semantic search and vector memory |

> **Note:** Provider availability and exact model names depend on your API keys, account access, and configured deployments.

**📖 See [Provider Documentation](docs/providers/) for setup guides**

## 📚 Documentation

### 📖 [Complete Documentation Hub](docs/)

Our documentation is organized for easy navigation:

#### Getting Started
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 5 minutes
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and components
- **[Environment Variables](docs/ENVIRONMENT_VARIABLES.md)** - Configuration reference

#### Core Features
- **[Distributed Tracing](docs/DISTRIBUTED_TRACING.md)** 🔥 - OpenTelemetry + Jaeger guide
- **[API Integration Guide](docs/api-integration-guide.md)** - Complete API reference with examples
- **[Tool System](docs/tools.md)** - Built-in and custom tools
- **[Memory System](docs/MEMORY_SYSTEM.md)** - Conversation context management
- **[Conversation Export](docs/CONVERSATION_EXPORT.md)** - Export in multiple formats

#### Development
- **[Testing Guide](docs/TESTING.md)** - Unit, integration, and E2E tests
- **[CI/CD Setup](docs/ci-cd-setup.md)** - GitHub Actions workflows
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

#### Deployment & Operations
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)** - Production best practices
- **[Kubernetes Setup](docs/DEPLOYMENT_PRODUCTION.md)** - K8s deployment guide
- **[Monitoring Guide](docs/MONITORING.md)** - Prometheus & Grafana setup
- **[Security Guide](docs/SECURITY.md)** - Security best practices
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues & solutions

#### API Documentation
- **Swagger UI**: http://localhost:8000/api/docs (Interactive)
- **ReDoc**: http://localhost:8000/api/redoc (Clean reference)

**💡 Tip**: See [docs/README.md](docs/README.md) for the complete documentation index with search tips and quick navigation.

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

**📖 See [Monitoring Guide](docs/MONITORING.md) for setup instructions**

## 🏗️ Architecture

```
zakera/
├── .github/workflows/      # CI/CD pipelines
├── src/
│   ├── model/             # Multi-provider LLM system
│   ├── api/               # FastAPI backend
│   ├── frontend/          # React + TypeScript UI
│   ├── tools/             # Tool system
│   ├── monitoring/        # Observability (tracing, metrics)
│   ├── security/          # Auth & security
│   └── utils/             # Utilities
├── docs/                  # 📚 Comprehensive documentation
│   ├── README.md         # Documentation hub
│   ├── archive/          # Historical documentation
│   └── ...               # Organized guides
├── tests/                 # Test suites (75%+ coverage)
├── monitoring/            # Monitoring stack configuration
├── kubernetes/            # K8s deployment manifests
├── helm/                  # Helm charts
├── terraform/             # Infrastructure as Code
└── Makefile              # Build automation
```

**📖 See [Architecture Guide](docs/ARCHITECTURE.md) for detailed system design**

### 📄 Architecture Decision Records (ADR)
- **ADR 001: Feedback Loop Implementation**: We chose a database-backed feedback system (PostgreSQL/SQLite) using a dedicated `MessageFeedback` model. This allows for qualitative (comments) and quantitative (is_positive) analysis of AI responses to improve prompt engineering and RAG strategies.

## 🎯 Roadmap

### Completed ✅
- [x] Multi-provider support (9 providers including Groq)
- [x] Google Gemini integration
- [x] **User Feedback System**: Integrated database loop for quality tracking
- [x] Distributed tracing with OpenTelemetry + Jaeger
- [x] Conversation export (streaming)
- [x] Production CI/CD pipeline
- [x] Comprehensive API documentation
- [x] Security scanning automation
- [x] Monitoring and alerting
- [x] Docker and Kubernetes support
- [x] Documentation organization

### In Progress 🚧
- [ ] Voice input/output support
- [ ] Advanced RAG (Retrieval-Augmented Generation)
- [ ] Plugin marketplace
- [ ] Mobile app (React Native)

### Planned 📋
- [ ] Multi-language UI support
- [ ] Enterprise SSO integration
- [ ] Cloud deployment templates (AWS, GCP, Azure)
- [ ] Fine-tuning support based on user feedback data
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for:
- Code of Conduct
- Development setup
- Coding standards
- Pull request process
- Testing requirements

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), and [OpenTelemetry](https://opentelemetry.io/)
- Monitoring powered by [Prometheus](https://prometheus.io/) and [Grafana](https://grafana.com/)
- Distributed tracing by [Jaeger](https://www.jaegertracing.io/)

---

**Version**: 0.7.0  
**Status**: Production-Ready 🚀  
**Last Updated**: April 2026

**⭐ If you find this project useful, please star it on GitHub!**

**📚 [View Complete Documentation](docs/) | 🐛 [Report Issues](https://github.com/itsmepraks/zakera/issues) | 💬 [Discussions](https://github.com/itsmepraks/zakera/discussions)**
