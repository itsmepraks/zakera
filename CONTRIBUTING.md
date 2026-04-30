# Contributing to Zakera

Thanks for wanting to help. Here's what you need to know.

## What we're working on

Zakera is evolving from a multi-provider LLM wrapper into a personal AI orchestrator that learns habits and acts proactively. The areas that need the most help right now:

- **Habit learning** — Building the system that tracks user patterns across sessions and surfaces proactive suggestions
- **Intent classification** — Better routing of user requests to the right provider and tools
- **Tool integrations** — New tools beyond the built-in set (web search, calculator, code execution, etc.)
- **Frontend** — React/Next.js UI for managing background tasks and viewing orchestration status
- **Provider fixes** — Some provider implementations have broken imports or untested code paths

## Setting up for development

```bash
git clone https://github.com/itsmepraks/zakera.git
cd zakera
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# add at least one API key

mkdir -p data logs
make dev
```

The API runs at http://localhost:8000 and Swagger docs at http://localhost:8000/api/docs.

## Making changes

1. Fork the repo and create a branch from `main`
2. Make your changes
3. If you added something that should be tested, add tests
4. Make sure existing tests pass: `make test`
5. Open a PR with a clear description of what you changed and why

## Code style

- Python: we use `black` for formatting, `flake8` for linting, `isort` for imports
- Run `make format` before committing
- Keep changes focused — one PR per feature or fix

## Reporting bugs

Open an issue. Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## Suggesting features

Open an issue with the "feature" label. Describe what you'd want and why it would be useful. Even rough ideas are welcome — we can figure out implementation together.

## Questions?

Open an issue or start a discussion. There are no dumb questions.
