# Zakera

An open-source AI orchestrator that moves beyond prompt-and-response toward something more useful — an assistant that learns your habits, routes tasks across tools, and works proactively in the background.

Most AI tools wait for you to type something. Zakera is built around a different idea: what if your assistant already knew what you needed?

## Why this exists

The gap between "I can use ChatGPT" and "I have AI automating my workflows" is massive. It requires wiring together providers, managing context across sessions, handling auth for dozens of APIs, and building interfaces that don't get in the way.

Zakera bridges that gap. It's an orchestration layer that handles intent classification, smart routing across 21+ LLM providers, and persistent memory — so you can focus on what you want done, not how to wire it up.

This is open source because the tools that make AI accessible shouldn't be locked behind enterprise paywalls.

## How it works

```
┌─────────────────────────────────────────────────┐
│                   Interface                      │
│              React / Next.js frontend            │
│         Background task management UI            │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                 Orchestrator                     │
│            Intent classification                 │
│         Smart routing across providers           │
│           Tool selection & execution             │
└───────┬──────────────┬──────────────┬───────────┘
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌────▼───────────┐
│  Providers   │ │   Tools    │ │ Memory & State  │
│  21+ LLMs   │ │ Web search │ │   Persistent    │
│  Unified API │ │ Code exec  │ │   context that  │
│  Failover    │ │ Calculator │ │   tracks habits │
│              │ │ File I/O   │ │   across        │
│              │ │ + custom   │ │   sessions      │
└──────────────┘ └────────────┘ └─────────────────┘
```

**Orchestrator** (Python/FastAPI) — Classifies what you're trying to do and routes it to the right provider and tools. Handles failover automatically if a provider goes down.

**Provider layer** — Single interface across OpenAI, Anthropic, Gemini, DeepSeek, Groq, Cerebras, Mistral, Cohere, Perplexity, xAI, Together AI, OpenRouter, Ollama, and more. Add an API key, use the model.

**Memory** — Conversation context that persists across sessions. Token-aware trimming so the model doesn't lose track of what you were doing.

**Tools** — Built-in web search, code execution, calculator, file operations, datetime, weather. Extensible — write a tool class, register it, done.

**Monitoring** — Request metrics (Prometheus), distributed tracing (OpenTelemetry/Jaeger), structured logging, health probes. Know what's happening in production.

## Quick start

```bash
git clone https://github.com/itsmepraks/zakera.git
cd zakera
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# add at least one provider API key

mkdir -p data logs
make dev
```

API: http://localhost:8000
Docs: http://localhost:8000/api/docs

For the full monitoring stack (Postgres, Jaeger, Prometheus, Grafana):
```bash
docker-compose up
```

## Project structure

```
src/
  api/           FastAPI app, routes, auth, middleware
  model/         Provider implementations, memory, model manager
  tools/         Tool framework and built-in tools
  monitoring/    Metrics, tracing, logging, alerts
  security/      JWT auth, MFA, OAuth2
  frontend/      React + TypeScript UI
```

## Supported providers

Anthropic · OpenAI · Google Gemini · DeepSeek · Groq · Cerebras · Mistral · Cohere · Perplexity · xAI · Together AI · OpenRouter · HuggingFace · Ollama · AWS Bedrock · Google Vertex · Azure OpenAI · Fireworks

Each provider lives in its own file under `src/model/`. Ollama is supported for fully local inference.

## Contributing

This project is early and actively evolving. If you're interested in:
- Habit learning and proactive task scheduling
- Better intent classification
- New tool integrations
- Frontend/UX for background task management

Open an issue or PR. No contribution is too small.

## License

MIT
