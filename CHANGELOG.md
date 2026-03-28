# Changelog

All notable changes to Zakera are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added

#### Backend — Meta Llama 3 Provider (`src/model/providers_llama3.py`)
- New `LlamaProvider` class that routes Llama 3 requests through the
  **Groq inference API**, consistent with the existing
  `providers_groq.py` / `providers_deepseek.py` architecture.
- Supports three model variants:
  | Model ID | Context | Notes |
  |---|---|---|
  | `llama3-8b-8192` | 8 192 tokens | Fast, low-cost |
  | `llama3-70b-8192` | 8 192 tokens | High-capability |
  | `llama-3.1-405b-reasoning` | 131 072 tokens | State-of-the-art reasoning |
- Async `chat()` method returns a typed `LlamaResponse` dataclass
  with content, usage stats, tool calls, latency, and estimated cost.
- Async `stream()` generator yields content deltas via SSE,
  terminating cleanly on `[DONE]`.
- **Function / tool calling** support via OpenAI-compatible tool
  definitions (matches Groq API schema).
- Exponential back-off retry (3 attempts by default) on 429 and 5xx
  responses; 4xx client errors raise immediately.
- `create_llama_provider()` factory wired into the provider registry.

#### Frontend — SettingsPanel Component (`src/frontend/components/`)
- New **`SettingsPanel.tsx`** slide-in drawer for user preferences:
  - **Appearance** — light / dark / system theme toggle.
  - **Model Defaults** — temperature slider (0–2), max tokens input,
    top-p slider, streaming on/off toggle.
  - **Memory & Context** — context window size slider, FAISS vector
    search toggle, auto-summarise threshold, include-summary toggle.
  - **API & Providers** — active provider badge with colour coding,
    masked API key preview.
  - **Danger Zone** — two-step confirmation for "Clear history" and
    "Reset settings" to prevent accidental data loss.
- Fully **accessible**: `role="dialog"`, `aria-modal`, focus-trap,
  Esc-to-close, visible focus rings on all interactive elements.
- All state lifted via `onSettingsChange` callback so parents can
  persist prefs to `localStorage` or `POST /api/v1/settings`.
- Typed exports: `ZakeraSettings`, `ModelSettings`, `MemorySettings`,
  `Theme`, `DEFAULT_SETTINGS` for easy integration.
- New **`SettingsPanel.module.css`**:
  - CSS custom properties aligned with existing Tailwind colour palette.
  - Smooth 300 ms `cubic-bezier` slide animation.
  - Responsive: full-screen on mobile (≤ 640 px), fixed 480 px on desktop.
  - Dark-mode via `prefers-color-scheme` **and** `.dark` class.

#### Tests — Llama 3 Provider Suite (`tests/test_providers_llama3.py`)
- **35 + test cases** covering:
  - Provider instantiation guards (empty key, unknown model).
  - `list_models()` and `get_model_info()` catalogue validation.
  - Successful non-streaming chat (mocked `httpx`).
  - Temperature, max-tokens, top-p, system-prompt, stop-sequence
    passthrough verification.
  - Token usage extraction and cost estimation accuracy.
  - Latency field population.
  - Streaming SSE delta accumulation, `[DONE]` termination, and
    malformed-chunk resilience.
  - Tool / function call response parsing.
  - Tools payload forwarding including `tool_choice`.
  - Retry on 429 → eventual success.
  - RuntimeError after max-retry exhaustion.
  - Immediate raise on 4xx client errors (no retry).
  - `close()` lifecycle method.
  - `create_llama_provider()` factory.
- Mirrors the structure of `test_providers_groq.py` and
  `test_deepseek_provider.py` for navigation consistency.

---

## Previous releases

> See `COMPLETE_MARCH_2026_RELEASES.md`, `MARCH_2026_FEATURE_RELEASES.md`,
> and `MARCH_2026_PROGRESS.md` for the full history of March 2026 releases
> covering conversation templates, enhanced memory, vector search, security
> hardening, CI/CD pipelines, and multi-provider benchmarking.
