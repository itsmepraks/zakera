# Changelog

All notable changes to Zakera are documented here.

## Unreleased

- Rewrote README around the project's actual vision (habit-based AI orchestration)
- Deleted ~11,000 lines of dead code (unused memory implementations, unused provider files, unused cache layer)
- Fixed monitoring — metrics middleware and system metrics collector now actually record data
- Wired OpenTelemetry tracing into app startup
- Fixed broken imports across multiple provider files
- Cleaned up requirements.txt (removed unused heavy ML deps, fixed typos, loosened version pins)
- Fixed SQLAlchemy reserved attribute name collision on `metadata` column
- Added LICENSE, SECURITY.md, CODE_OF_CONDUCT.md
- Rewrote CONTRIBUTING.md to reflect actual project state

## Earlier work

The initial codebase was scaffolded with AI assistance and includes:
- FastAPI backend with JWT auth, MFA, and conversation management
- 21+ LLM provider integrations with failover
- Tool framework (web search, code execution, calculator, file I/O)
- React + TypeScript frontend
- Docker, Kubernetes, Helm, and Terraform configs
- Prometheus, Grafana, and Jaeger monitoring setup
