/**
 * TypeScript interfaces for the Model Comparison feature.
 *
 * These types are shared between the `useModelComparison` hook and
 * the `ModelComparisonPanel` component.
 */

export type ProviderStatus = 'idle' | 'pending' | 'streaming' | 'done' | 'error';

/** Metrics collected per-provider during a comparison run. */
export interface ComparisonMetrics {
  /** Time-to-first-token in milliseconds. */
  ttftMs: number | null;
  /** Total wall-clock time from request start to completion, ms. */
  totalMs: number | null;
  /** Approximate input token count (if returned by the API). */
  inputTokens: number | null;
  /** Approximate output token count (if returned by the API). */
  outputTokens: number | null;
}

/** State for a single provider slot in the comparison grid. */
export interface ComparisonEntry {
  /** Provider key, e.g. "anthropic", "gemini", "groq". */
  provider: string;
  /** Human-readable display name. */
  label: string;
  /** Current lifecycle status. */
  status: ProviderStatus;
  /** Accumulated response text (grows as chunks arrive). */
  response: string;
  /** Error message if status === "error". */
  error: string | null;
  /** Performance metrics, available once status === "done". */
  metrics: ComparisonMetrics;
}

/** Shape of the object returned by `useModelComparison`. */
export interface UseModelComparisonReturn {
  /** Current entries for every selected provider. */
  entries: ComparisonEntry[];
  /** True while at least one provider is still streaming. */
  isRunning: boolean;
  /** Send the prompt to all selected providers. */
  run: (prompt: string) => Promise<void>;
  /** Reset all entries back to idle. */
  reset: () => void;
  /** Toggle a provider in/out of the active set. */
  toggleProvider: (provider: string) => void;
  /** Currently selected provider keys. */
  selectedProviders: string[];
}
