/**
 * useModelComparison
 * ------------------
 * React hook that sends the same prompt to multiple AI providers
 * simultaneously and streams their responses in parallel.
 *
 * Usage:
 * ```tsx
 * const { entries, isRunning, run, reset, toggleProvider, selectedProviders } =
 *   useModelComparison(['anthropic', 'gemini', 'groq']);
 *
 * // Fire off a comparison:
 * await run("Explain quantum entanglement in two sentences.");
 * ```
 */

import { useCallback, useRef, useState } from 'react';
import type {
  ComparisonEntry,
  ComparisonMetrics,
  ProviderStatus,
  UseModelComparisonReturn,
} from '../types/comparison';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Claude 3.5 Sonnet',
  gemini: 'Gemini 1.5 Pro',
  gemini2: 'Gemini 2.0 Flash',
  groq: 'Llama 3.3 70B (Groq)',
  mistral: 'Mistral Large',
  codestral: 'Codestral (Code)',
  deepseek: 'DeepSeek Reasoner',
  perplexity: 'Perplexity Sonar',
  xai: 'Grok 2',
  openrouter: 'OpenRouter',
  together: 'Together AI',
  cohere: 'Command R+',
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeEmptyEntry(provider: string): ComparisonEntry {
  return {
    provider,
    label: PROVIDER_LABELS[provider] ?? provider,
    status: 'idle' as ProviderStatus,
    response: '',
    error: null,
    metrics: {
      ttftMs: null,
      totalMs: null,
      inputTokens: null,
      outputTokens: null,
    },
  };
}

function emptyMetrics(): ComparisonMetrics {
  return { ttftMs: null, totalMs: null, inputTokens: null, outputTokens: null };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useModelComparison(
  initialProviders: string[] = ['anthropic', 'gemini', 'groq'],
): UseModelComparisonReturn {
  const [selectedProviders, setSelectedProviders] = useState<string[]>(initialProviders);
  const [entries, setEntries] = useState<ComparisonEntry[]>(
    initialProviders.map(makeEmptyEntry),
  );
  const [isRunning, setIsRunning] = useState(false);
  const abortRefs = useRef<Map<string, AbortController>>(new Map());

  // ---- helpers -----------------------------------------------------------

  const updateEntry = useCallback(
    (provider: string, patch: Partial<ComparisonEntry>) => {
      setEntries((prev) =>
        prev.map((e) => (e.provider === provider ? { ...e, ...patch } : e)),
      );
    },
    [],
  );

  const appendChunk = useCallback((provider: string, chunk: string) => {
    setEntries((prev) =>
      prev.map((e) =>
        e.provider === provider ? { ...e, response: e.response + chunk } : e,
      ),
    );
  }, []);

  // ---- streaming a single provider ---------------------------------------

  const streamProvider = useCallback(
    async (provider: string, prompt: string): Promise<void> => {
      const controller = new AbortController();
      abortRefs.current.set(provider, controller);

      const startTs = performance.now();
      let ttftCaptured = false;
      const metrics = emptyMetrics();

      updateEntry(provider, { status: 'pending', response: '', error: null, metrics });

      try {
        const resp = await fetch(`${API_BASE}/api/v1/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider, message: prompt }),
          signal: controller.signal,
        });

        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        }

        updateEntry(provider, { status: 'streaming' });

        const reader = resp.body!.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });

          // Capture TTFT on first non-empty chunk
          if (!ttftCaptured && text.trim()) {
            metrics.ttftMs = Math.round(performance.now() - startTs);
            ttftCaptured = true;
          }

          // Parse SSE lines
          for (const line of text.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (raw === '[DONE]') break;
            try {
              const payload = JSON.parse(raw);
              if (payload.chunk) appendChunk(provider, payload.chunk);
              if (payload.usage) {
                metrics.inputTokens = payload.usage.input_tokens ?? null;
                metrics.outputTokens = payload.usage.output_tokens ?? null;
              }
            } catch {
              // non-JSON line — skip
            }
          }
        }

        metrics.totalMs = Math.round(performance.now() - startTs);
        updateEntry(provider, { status: 'done', metrics: { ...metrics } });
      } catch (err: unknown) {
        if ((err as Error).name === 'AbortError') return;
        const message = err instanceof Error ? err.message : String(err);
        updateEntry(provider, { status: 'error', error: message });
      } finally {
        abortRefs.current.delete(provider);
      }
    },
    [updateEntry, appendChunk],
  );

  // ---- public API --------------------------------------------------------

  const run = useCallback(
    async (prompt: string): Promise<void> => {
      if (isRunning) return;
      setIsRunning(true);
      try {
        await Promise.allSettled(
          selectedProviders.map((p) => streamProvider(p, prompt)),
        );
      } finally {
        setIsRunning(false);
      }
    },
    [isRunning, selectedProviders, streamProvider],
  );

  const reset = useCallback(() => {
    // Abort any in-flight requests
    abortRefs.current.forEach((ctrl) => ctrl.abort());
    abortRefs.current.clear();
    setIsRunning(false);
    setEntries(selectedProviders.map(makeEmptyEntry));
  }, [selectedProviders]);

  const toggleProvider = useCallback((provider: string) => {
    setSelectedProviders((prev) => {
      const next = prev.includes(provider)
        ? prev.filter((p) => p !== provider)
        : [...prev, provider];
      setEntries(next.map(makeEmptyEntry));
      return next;
    });
  }, []);

  return { entries, isRunning, run, reset, toggleProvider, selectedProviders };
}
