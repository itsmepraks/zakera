# Changelog

All notable changes to the Zakera project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned Features (Roadmap)
- Voice input/output support
- Multi-language support
- Plugin marketplace
- Cloud deployment templates (AWS, GCP, Azure)
- Mobile app (React Native)
- Enterprise SSO integration
- Advanced RAG (Retrieval-Augmented Generation)
- Fine-tuning support

---

## [0.9.0] - 2026-03-22

### Added

#### Token Usage & Cost Breakdown (Backend)
- **New endpoint** `GET /api/v1/conversations/{conversation_id}/token-usage` that returns a
  detailed JSON breakdown of every conversation's token consumption and estimated USD cost.
- **Built-in pricing table** covering 30+ models across OpenAI (GPT-4o, o1, o3-mini…),
  Anthropic (Claude 3.5 Sonnet/Haiku, Opus…), Google Gemini (1.5 Pro/Flash, 2.0 Flash),
  Groq, Mistral, DeepSeek, and xAI Grok. Local/Ollama models report zero cost.
- **Response schema** (`TokenUsageResponse`) includes:
  - Aggregate `total_tokens`, `prompt_tokens`, `completion_tokens`, `estimated_cost_usd`
  - `by_role` breakdown (user / assistant / system / tool) with per-role token count and cost
  - `by_provider` breakdown when a conversation uses messages from multiple model providers
  - `message_timeline` — per-message token detail ordered by `created_at`
  - `avg_user_tokens_per_message` and `avg_assistant_tokens_per_message`
  - `pricing_info` snapshot (prompt/completion per-1k USD) and `pricing_provider` used for estimates
- Endpoint is auth-protected (JWT); returns 404 for conversations not owned by the requester
  or soft-deleted conversations.
- Model pricing resolves via exact match → prefix/substring match → zero-cost fallback so
  versioned model aliases (e.g. `gpt-4-turbo-preview-2024-04-09`) resolve correctly.

#### TokenUsageBadge (Frontend)
- **New `<TokenUsageBadge>`** React/TypeScript component (`src/frontend/components/TokenUsageBadge.tsx`)
  that renders a colour-coded pill in the chat header showing live token count and estimated cost.
- Auto-refreshes every 30 s (configurable via `refreshInterval` prop) while the chat is open.
- Expands into a **popover breakdown table** (per-role: user / assistant / system) on click.
- **Three cost tiers** driven by Tailwind CSS:
  - 🟢 Green (< $0.01) — free/very cheap (local models, short conversations)
  - 🟡 Amber ($0.01–$0.10) — moderate spend
  - 🔴 Red (≥ $0.10) — significant spend, prompts user awareness
- Handles loading skeleton, API error state (click-to-retry), and zero-cost local model
  conversations gracefully.
- Props: `conversationId`, `authToken`, optional `refreshInterval`, optional `className`.

#### Testing
- **`tests/test_token_usage.py`** — 10 new pytest test cases covering:
  - Happy path: correct total/prompt/completion token counts and non-zero cost for paid models
  - Multi-model conversation: messages attributed to different providers appear in `by_provider`
  - Zero-cost local/Ollama conversation: `estimated_cost_usd` is exactly 0.0
  - Empty conversation: all numeric fields are 0, no timeline entries
  - 404 for non-existent / soft-deleted / cross-user conversation
  - 401 on missing Authorization header
  - Average tokens per role are computed correctly
  - Pricing helper unit tests: exact match, prefix/alias match, Ollama keyword, unknown model

### Changed
- Version bumped `0.8.0` → `0.9.0`.
- `[Unreleased]` section reset; this sprint's items moved into the `[0.9.0]` entry above.

---

## [0.8.0] - 2026-03-17

### Added

#### Conversation Export
- **Streaming Export API** (`GET /api/v1/export/conversations/{id}`): stream a single conversation in JSON, Markdown, or CSV format as NDJSON with real-time progress events
- **Bulk Export API** (`POST /api/v1/export/conversations/bulk`): export up to 50 conversations in one streamed NDJSON response with per-page progress for the UI progress bar
- **Export Schemas** (`src/api/schemas/export.py`): `ExportFormat`, `ExportOptions`, `BulkExportRequest`, `ExportProgress`, `ExportDataChunk`, `ExportComplete`, `ExportError`, `ExportHistoryItem`
- **Export history and status endpoints**: `GET /api/v1/export/exports/history`, `GET /api/v1/export/conversations/{id}/export/status/{export_id}`
- **gzip compression** support via `compress=true` query parameter
- **Date-range filtering** via `date_from` / `date_to` query parameters
- **Content-Disposition** headers with timestamped filenames for each format
- Streaming metrics recorded via `metrics_collector` for export counts and failures

#### Message Reactions & Chat UI
- **Message reactions system**: users can add emoji reactions (👍 👎 ❤️ 😂 😮) to any chat message
- **Reaction counts**: real-time aggregated reaction counts shown below each message
- **Toggle behaviour**: clicking a reaction the user already added removes it
- **Improved `ChatMessage` component**: cleaner layout, better typography, monospace code blocks with syntax highlighting
- **Assistant message actions**: copy-to-clipboard, regenerate, and reactions toolbar appear on hover
- **User message edit**: inline edit flow for user messages without leaving the conversation
- **Animated message entrance**: subtle fade-in animation for new messages arriving in the stream
- **Streaming cursor indicator**: blinking cursor shown while the assistant is still generating

#### Testing
- **Integration test suite for Export API** (`tests/integration/test_export_api.py`): 30+ test cases covering:
  - Authentication and authorization (unauthenticated, wrong-user cross-access)
  - All three export formats (JSON, Markdown, CSV) for both single and bulk endpoints
  - Response header assertions (Content-Disposition, X-Export-Format, Cache-Control)
  - Compressed export (`.gz` filename)
  - Bulk export response headers and stream event shape (`bulk_complete`)
  - Rate-limit enforcement and window-reset behaviour
  - Edge cases: soft-deleted conversation, non-existent ID, empty conversation, long conversation progress events, mid-stream service errors, >50 IDs rejection, duplicate ID deduplication

### Changed
- `[Unreleased]` section cleaned up; routine maintenance notes moved into versioned release entry
- Version bumped from `0.7.0` → `0.8.0` to reflect the new features shipped in this sprint

### Fixed
- Export rate-limit log now correctly prunes timestamps older than the rolling window before evaluating the limit, preventing false positives after idle periods

---

## [0.5.0] - 2026-02-14

### Project Status
Current release is production-ready with comprehensive features for AI chat agents, enterprise monitoring, and multi-provider LLM support.

### Added
- **Multi-Provider LLM Support**: OpenAI, Anthropic, Google Gemini, Ollama, HuggingFace integration
- **Local Model Support**: Run Llama 3, Mistral, CodeLlama locally with zero API costs
- **Conversation Memory System**: Context-aware multi-turn conversations with efficient memory management
- **Tool Integration System**: Extensible tool framework with built-in tools and custom tool support
- **Enterprise Monitoring Stack**:
  - 50+ Prometheus metrics for comprehensive observability
  - Grafana dashboards for visualization
  - Structured JSON logging with correlation IDs
  - Alert system (Email, Slack, Discord notifications)
- **RESTful & WebSocket APIs**: FastAPI-based endpoints for all integration scenarios
- **Modern React Frontend**: TypeScript-based UI with tool system integration
- **Authentication**: JWT-based secure authentication system
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Rate Limiting**: Configurable limits per user and endpoint
- **Database Integration**: SQLAlchemy-backed persistent storage for conversations and preferences
- **Docker Support**: Containerization with Docker and docker-compose configurations
- **Comprehensive Testing**: 50+ test cases covering all major components
- **CI/CD Pipeline**: GitHub Actions workflows for automated testing and deployment
- **Make Commands**: Build automation with extensive Makefile targets
- **Documentation**:
  - API documentation with Swagger UI and ReDoc
  - Local models setup guide
  - Monitoring and observability guide
  - Tool development guide
  - Configuration and deployment guides
  - Multiple comprehensive summary documents

### Features Highlights
- **Smart Fallback**: Automatic fallback between providers for enhanced reliability
- **Performance Tracking**: Execution time monitoring and profiling
- **Real-time Streaming**: Streaming responses from all LLM providers
- **Model Cost Tracking**: Track and optimize model usage costs
- **Tool Caching**: Parallel execution with intelligent caching
- **Custom Prompts**: Flexible prompt template system
- **Analytics**: Usage tracking and insights
- **Conversation Branching**: Version control for conversation flows

### Infrastructure
- **Monitoring Stack**: Prometheus, Grafana, AlertManager integration
- **Database**: SQLite/PostgreSQL support with Alembic migrations
- **Deployment**: Kubernetes manifests and Terraform configurations
- **Development Tools**: Comprehensive linting (flake8), formatting, and type checking (mypy)

### Documentation
- README with quick start and comprehensive guides
- API reference documentation
- Local models setup instructions
- Monitoring and observability guide
- Contributing guidelines
- Multiple implementation summaries
- Test coverage reports

### Performance Benchmarks
- GPT-4 Turbo: ~40 tokens/sec, 2.5s p95 latency
- Claude 3 Sonnet: ~35 tokens/sec, 2.8s p95 latency
- Llama 3 8B (Local): ~25 tokens/sec, 1.2s p95 latency
- Mistral 7B (Local): ~30 tokens/sec, 0.9s p95 latency

### Security
- JWT authentication
- API key encryption
- Rate limiting
- CORS configuration
- SQL injection protection
- Input validation
- Secure password hashing

---

## Version History Summary

### 0.9.0 (Current) - Token Usage & Cost Breakdown
New `GET /api/v1/conversations/{id}/token-usage` endpoint, `TokenUsageBadge` frontend component,
and 10 new pytest test cases. Pricing table covers 30+ models across 8 providers.

### 0.8.0 - Export, Reactions & Test Coverage
Streaming conversation export (JSON/CSV/Markdown), message reactions UI, improved chat components, comprehensive integration test suite for the export API.

### 0.5.0 - Production-Ready Release
Complete AI chat agent system with enterprise features, monitoring, and multi-provider support.

---

## Contributing

When making changes to this project, please:
1. Update the [Unreleased] section with your changes
2. Categorize changes under appropriate headers:
   - `Added` for new features
   - `Changed` for changes in existing functionality
   - `Deprecated` for soon-to-be removed features
   - `Removed` for now removed features
   - `Fixed` for any bug fixes
   - `Security` for vulnerability fixes

## Links
- [Project Repository](https://github.com/itsmepraks/zakera)
- [Documentation](docs/)
- [Contributing Guidelines](CONTRIBUTING.md)
- [License](LICENSE)

---

**Maintained by**: Prakriti Bista  
**Website**: https://praks.me  
**License**: MIT
