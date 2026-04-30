# Caching

Zakera uses caching at two levels: in-memory tool result caching and conversation memory trimming. There is no Redis dependency at this time.

## Tool result caching

The `ToolManager` in `src/tools/manager.py` caches tool execution results in memory with a configurable TTL (default: 5 minutes). If the same tool is called with the same parameters within the TTL window, the cached result is returned without re-executing.

Cache keys are generated from the tool name and a hash of the parameters.

## Conversation memory

`ConversationMemory` keeps the most recent turns in the context window and trims older messages when the token budget is exceeded. This isn't caching in the traditional sense, but it serves the same purpose — keeping frequently needed data close and discarding what's less relevant.

## What's not implemented yet

- **Redis-backed caching** — the docker-compose file includes Redis but no Python code uses it. This is a good area for contribution if you want to add response caching or shared state across workers.
- **Model response caching** — caching LLM responses for identical prompts could reduce API costs significantly. Needs careful key design since small prompt changes produce different outputs.
- **Embedding cache** — if semantic search is added, caching embeddings would avoid redundant API calls.

## Adding Redis caching

If you want to wire up Redis:

1. The Redis service is already in `docker-compose.yml`
2. Environment variables for Redis config are in `.env.example`
3. You'd add a cache client in `src/utils/` and integrate it with the tool manager or model providers
4. Consider cache invalidation carefully — LLM responses are non-deterministic, so caching needs to account for temperature and other generation parameters
