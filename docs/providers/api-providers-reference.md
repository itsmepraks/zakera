# API Providers Reference Guide

Zakera supports **17 AI providers** out of the box. This guide covers
authentication, recommended models, capabilities, and quickstart snippets
for every provider.

---

## Quick-Start Checklist

1. Copy `.env.example` → `.env`
2. Populate the `*_API_KEY` variables for the providers you want to use
3. Set `DEFAULT_PROVIDER=<key>` to choose the default
4. Restart the backend: `make dev` or `docker compose up --build`

---

## Capability Matrix

| Provider | Key | Streaming | FIM | Vision | Function Calling | Web Search | Cost Tier |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Anthropic Claude | `anthropic` | ✅ | ❌ | ✅ | ✅ | ❌ | $$$ |
| Google Gemini 1.5 | `gemini` | ✅ | ❌ | ✅ | ✅ | ❌ | $$ |
| Google Gemini 2.0 | `gemini2` | ✅ | ❌ | ✅ | ✅ | ✅ | $$ |
| Groq (Llama) | `groq` | ✅ | ❌ | ❌ | ✅ | ❌ | $ |
| Mistral AI | `mistral` | ✅ | ❌ | ❌ | ✅ | ❌ | $$ |
| Mistral Codestral | `codestral` | ✅ | ✅ | ❌ | ❌ | ❌ | $ |
| DeepSeek | `deepseek` | ✅ | ❌ | ❌ | ✅ | ❌ | $ |
| Cohere Command R+ | `cohere` | ✅ | ❌ | ❌ | ✅ | ✅ | $$ |
| HuggingFace | `huggingface` | ✅ | ❌ | ❌ | ❌ | ❌ | Free/$ |
| Ollama (remote) | `ollama` | ✅ | ❌ | ✅ | ✅ | ❌ | Free |
| Ollama (local) | `ollama_local` | ✅ | ❌ | ✅ | ✅ | ❌ | Free |
| OpenRouter | `openrouter` | ✅ | ❌ | ✅ | ✅ | ❌ | Varies |
| Together AI | `together` | ✅ | ❌ | ❌ | ❌ | ❌ | $ |
| Perplexity | `perplexity` | ✅ | ❌ | ❌ | ❌ | ✅ | $$ |
| xAI (Grok) | `xai` | ✅ | ❌ | ✅ | ✅ | ✅ | $$ |
| Azure OpenAI | `azure` | ✅ | ❌ | ✅ | ✅ | ❌ | $$$ |

---

## Provider Details

### Anthropic Claude

**Key:** `anthropic`  
**Env var:** `ANTHROPIC_API_KEY`  
**Default model:** `claude-3-5-sonnet-20241022`

Anthropic's Claude models excel at long-context reasoning, nuanced writing,
and safe, instruction-following behaviour. Claude 3.5 Sonnet is the sweet
spot between capability and cost.

```env
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

**Available models:**
- `claude-3-5-sonnet-20241022` — best balance
- `claude-3-5-haiku-20241022` — fastest / cheapest
- `claude-3-opus-20240229` — highest quality

---

### Google Gemini 1.5

**Key:** `gemini`  
**Env var:** `GOOGLE_API_KEY`  
**Default model:** `gemini-1.5-pro`

Gemini 1.5 Pro offers a 1-million-token context window and strong
multimodal capabilities (text + images + video). Good for document Q&A.

```env
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-pro
```

---

### Google Gemini 2.0

**Key:** `gemini2`  
**Env var:** `GOOGLE_API_KEY` (same key)  
**Default model:** `gemini-2.0-flash`

Gemini 2.0 Flash adds native web grounding (real-time search), code
execution, and a 1M-token context. Best for agentic tasks.

```env
GEMINI2_MODEL=gemini-2.0-flash
```

---

### Groq

**Key:** `groq`  
**Env var:** `GROQ_API_KEY`  
**Default model:** `llama-3.3-70b-versatile`

Groq uses custom LPU hardware for ultra-low latency inference. Ideal for
use-cases where time-to-first-token is critical (e.g. live chat, voice).

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```

**Rate limits:** Free tier allows ~30 req/min, 6 000 tokens/min.

---

### Mistral AI

**Key:** `mistral`  
**Env var:** `MISTRAL_API_KEY`  
**Default model:** `mistral-large-latest`

Mistral Large 2 is a top-tier European model with strong multilingual
support and native function-calling.

```env
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-large-latest
```

---

### Mistral Codestral ⭐ New

**Key:** `codestral`  
**Env var:** `MISTRAL_CODESTRAL_API_KEY`  
**Default model:** `codestral-latest`

Codestral is Mistral's dedicated code model. It supports both standard chat
completions and **Fill-in-the-Middle (FIM)** completions — invaluable for
inline code suggestions (similar to GitHub Copilot's core capability).

```env
# Note: Codestral uses a SEPARATE key from the standard Mistral key.
# Get yours at: https://console.mistral.ai/codestral
MISTRAL_CODESTRAL_API_KEY=...
CODESTRAL_MODEL=codestral-latest
```

**FIM example (Python):**
```python
from src.model.providers_mistral_codestral import (
    MistralCodestralProvider, FIMRequest
)
import asyncio, os

async def main():
    p = MistralCodestralProvider(api_key=os.environ["MISTRAL_CODESTRAL_API_KEY"])
    result = await p.complete_fim(FIMRequest(
        prompt="def fibonacci(n: int) -> int:\n    if n <= 1:\n        ",
        suffix="\n    return a",
    ))
    print(result)

asyncio.run(main())
```

---

### DeepSeek

**Key:** `deepseek`  
**Env var:** `DEEPSEEK_API_KEY`  
**Default model:** `deepseek-reasoner`

DeepSeek R1 is an open-weight reasoning model competitive with o1 on math
and coding benchmarks at a fraction of the cost.

```env
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-reasoner
```

---

### Cohere Command R+

**Key:** `cohere`  
**Env var:** `COHERE_API_KEY`  
**Default model:** `command-r-plus`

Command R+ is optimised for RAG (Retrieval-Augmented Generation) and has
native grounding / citation support. Also supports web search.

```env
COHERE_API_KEY=...
COHERE_MODEL=command-r-plus
```

---

### HuggingFace Inference API

**Key:** `huggingface`  
**Env var:** `HUGGINGFACE_API_KEY`  
**Default model:** `meta-llama/Meta-Llama-3-8B-Instruct`

Access thousands of open-source models via HuggingFace's serverless
Inference API. Free tier available with rate limits.

```env
HUGGINGFACE_API_KEY=hf_...
HUGGINGFACE_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
```

---

### Ollama (Remote)

**Key:** `ollama`  
**Env var:** `OLLAMA_BASE_URL` (no API key needed)  
**Default model:** `llama3.2`

Connect to a remote Ollama server. Useful for self-hosted deployments on a
GPU machine accessible over the network.

```env
OLLAMA_BASE_URL=http://my-gpu-server:11434
OLLAMA_MODEL=llama3.2
```

---

### Ollama (Local)

**Key:** `ollama_local`  
**Env var:** `OLLAMA_LOCAL_BASE_URL` (default: `http://localhost:11434`)  
**Default model:** `llama3.2`

Runs entirely on your machine — zero API cost, full privacy. Requires
[Ollama](https://ollama.ai) to be installed and the model to be pulled.

```bash
# Pull a model locally
ollama pull llama3.2
ollama pull codellama:13b
```

---

### OpenRouter

**Key:** `openrouter`  
**Env var:** `OPENROUTER_API_KEY`  
**Default model:** `anthropic/claude-3.5-sonnet`

OpenRouter is an aggregation API that provides unified access to 100+
models from all major providers under a single key and billing account.

```env
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

---

### Together AI

**Key:** `together`  
**Env var:** `TOGETHER_API_KEY`  
**Default model:** `meta-llama/Llama-3-70b-chat-hf`

Together AI hosts popular open-weight models at competitive prices with
good throughput for batch workloads.

```env
TOGETHER_API_KEY=...
TOGETHER_MODEL=meta-llama/Llama-3-70b-chat-hf
```

---

### Perplexity

**Key:** `perplexity`  
**Env var:** `PERPLEXITY_API_KEY`  
**Default model:** `llama-3.1-sonar-large-128k-online`

Perplexity's Sonar models add real-time web search to LLM responses,
citing sources inline. Ideal for research and fact-checking use-cases.

```env
PERPLEXITY_API_KEY=pplx-...
PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online
```

---

### xAI (Grok)

**Key:** `xai`  
**Env var:** `XAI_API_KEY`  
**Default model:** `grok-2-latest`

xAI's Grok 2 features real-time X/Twitter data, vision input, and function
calling. Grok-2 Vision is particularly strong at diagram interpretation.

```env
XAI_API_KEY=xai-...
XAI_MODEL=grok-2-latest
```

---

### Azure OpenAI

**Key:** `azure`  
**Env vars:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`

For enterprise deployments with data residency, VNet integration, and
compliance requirements. Uses the same models as OpenAI but through a
dedicated Azure resource.

```env
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21
```

---

## Switching Provider at Runtime

You can switch the provider per-request via the API:

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "Explain quantum computing in one paragraph.",
    "provider": "groq",
    "model": "llama-3.3-70b-versatile"
  }'
```

Or select from the **Settings → Model** panel in the frontend UI.

---

## Adding a New Provider

1. Create `src/model/providers_<name>.py` implementing the standard
   `stream_chat()` / `chat()` interface (see `providers_mistral_codestral.py`
   for a clean reference implementation).
2. Register it in `src/model/model_manager.py` inside `_build_provider()`.
3. Add the API key env var to `src/model/config.py` and `.env.example`.
4. Write tests in `tests/test_providers_<name>.py`.
5. Update this reference guide.

---

*Last updated: March 2026*
