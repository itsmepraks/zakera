# Zakera

Zakera is an orchestrator for AI agents. It handles the stuff most people skip when they're just wrapping an LLM API — memory management, provider failover, tool execution, and observability.

Instead of wiring up each provider individually, you get a single interface across 21+ LLMs (OpenAI, Anthropic, Gemini, DeepSeek, Groq, Cerebras, Mistral, Cohere, Perplexity, xAI, Ollama, and more). The system manages conversation context across turns, supports tool calling, and tracks what's actually happening in production.

Built with FastAPI, React, and PostgreSQL.

## What it does

**Unified provider layer** — One API surface for 21+ models. Swap between GPT-4, Claude, Gemini, DeepSeek R1, Llama (via Groq/Cerebras/Ollama), and others without changing your application code. Includes automatic failover if a provider goes down.

**Memory system** — Three tiers: basic conversation memory with token counting, enhanced memory with hierarchical summarization and importance scoring, and vector memory (FAISS + sentence transformers) for semantic retrieval. Keeps agents from losing context mid-conversation.

**Tool use** — Built-in tools for web search, code execution, calculations, file reading, datetime, and weather. Extensible base class for custom tools. The tool manager handles caching, rate limiting, retries, and parallel execution.

**Monitoring** — OpenTelemetry tracing (Jaeger), Prometheus metrics (50+), structured logging, and alerting to Slack/Discord/email. Kubernetes-ready health probes.

**Auth** — JWT authentication with MFA (TOTP) and OAuth2 support.

## Providers

Anthropic, OpenAI, Google Gemini, DeepSeek, Groq, Cerebras, Mistral, Cohere, Perplexity, xAI (Grok), Together AI, OpenRouter, HuggingFace, Ollama, AWS Bedrock, Google Vertex, Azure OpenAI, and Llama 3 (dedicated). Each has its own provider file under `src/model/`.

Running locally with Ollama is supported if you don't want to use external APIs.

## Setup

```bash
git clone https://github.com/itsmepraks/zakera.git
cd zakera
make install

cp .env.example .env
# add your API keys to .env

make dev
# API runs at http://localhost:8000
# Swagger docs at http://localhost:8000/api/docs
```

For the full stack (Postgres, Redis, Jaeger, Prometheus, Grafana):

```bash
docker-compose up
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for details.

## Project structure

```
src/
  api/           FastAPI backend, routes, middleware, auth
  model/         Provider implementations, memory system, model manager
  tools/         Tool framework and built-in tools
  monitoring/    Tracing, metrics, logging, alerts
  security/      Auth, JWT, MFA
  frontend/      React + TypeScript UI
docs/            Architecture, deployment, monitoring guides
kubernetes/      K8s manifests
helm/            Helm charts
terraform/       AWS infrastructure (EKS, RDS, ElastiCache)
monitoring/      Prometheus, Grafana, AlertManager config
tests/           Test suites
```

## Docs

- [Architecture](docs/ARCHITECTURE.md) — system design overview
- [Quick Start](docs/QUICKSTART.md) — setup walkthrough
- [Monitoring](docs/MONITORING.md) — Prometheus, Grafana, tracing setup
- [Deployment](docs/DEPLOYMENT.md) — production deployment
- [Security](docs/SECURITY.md) — auth and security details
- [Tool System](docs/tools.md) — built-in and custom tools
- [Memory System](docs/MEMORY_SYSTEM.md) — how context management works
- [API Guide](docs/api-integration-guide.md) — endpoint reference

## License

MIT
