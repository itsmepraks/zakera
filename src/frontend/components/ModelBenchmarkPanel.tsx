/**
 * ModelBenchmarkPanel
 *
 * Side-by-side AI provider benchmarking component.
 * Lets the user run the same prompt against multiple providers at once
 * and compare responses, latency, and token usage in real time.
 */

'use client';

import React, {
  useState,
  useCallback,
  useRef,
  useEffect,
} from 'react';
import styles from './ModelBenchmarkPanel.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProviderConfig {
  id: string; // local uuid for React keys
  provider_id: string;
  model: string;
  temperature: number;
  max_tokens: number;
}

export interface ProviderResult {
  provider_id: string;
  model: string;
  status: 'success' | 'error' | 'timeout' | 'pending';
  content: string | null;
  error_message: string | null;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  finish_reason: string | null;
}

export interface BenchmarkRunResult {
  run_id: string;
  prompt: string;
  system_prompt: string | null;
  tags: string[];
  results: ProviderResult[];
  created_at: string;
  total_duration_ms: number;
}

export interface CompareResult {
  provider_a: string;
  provider_b: string;
  latency_delta_ms: number;
  token_delta: number;
  content_similarity: number;
  faster_provider: string;
  more_concise_provider: string;
  content_a: string | null;
  content_b: string | null;
}

export interface BenchmarkHistoryItem {
  run_id: string;
  prompt_preview: string;
  provider_ids: string[];
  tags: string[];
  created_at: string;
  total_duration_ms: number;
  success_count: number;
  error_count: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const KNOWN_PROVIDERS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: [
    'claude-3-5-sonnet-20241022',
    'claude-3-opus-20240229',
    'claude-3-haiku-20240307',
  ],
  cohere: ['command-r-plus', 'command-r'],
  gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  groq: ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768'],
  mistral: ['mistral-large-latest', 'mistral-small-latest'],
  xai: ['grok-2', 'grok-2-mini'],
  deepseek: ['deepseek-chat', 'deepseek-coder'],
};

const API_BASE = '/api/v1';

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

function newLocalId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function latencyColor(ms: number): string {
  if (ms < 500) return '#22c55e'; // green
  if (ms < 1500) return '#f59e0b'; // amber
  return '#ef4444'; // red
}

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
}

function similarityLabel(score: number): string {
  if (score >= 0.8) return 'Very similar';
  if (score >= 0.5) return 'Moderately similar';
  if (score >= 0.2) return 'Somewhat different';
  return 'Very different';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ProviderCardProps {
  result: ProviderResult;
  isSelected: boolean;
  onSelect: () => void;
  rank: number | null; // 1 = fastest
}

const ProviderCard: React.FC<ProviderCardProps> = ({
  result,
  isSelected,
  onSelect,
  rank,
}) => {
  const isPending = result.status === 'pending';
  const isError = result.status === 'error' || result.status === 'timeout';

  return (
    <article
      className={[
        styles.providerCard,
        isSelected ? styles.providerCardSelected : '',
        isPending ? styles.providerCardPending : '',
        isError ? styles.providerCardError : '',
      ]
        .filter(Boolean)
        .join(' ')}
      aria-label={`Result from ${result.provider_id} ${result.model}`}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onSelect()}
    >
      {/* Header */}
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>
          <span className={styles.providerBadge}>{result.provider_id}</span>
          <span className={styles.modelName}>{result.model}</span>
        </div>
        <div className={styles.cardMeta}>
          {rank === 1 && (
            <span className={styles.fastestBadge} aria-label="Fastest response">
              ⚡ Fastest
            </span>
          )}
          {!isPending && (
            <span
              className={styles.latencyBadge}
              style={{ color: latencyColor(result.latency_ms) }}
              aria-label={`Latency: ${formatLatency(result.latency_ms)}`}
            >
              {formatLatency(result.latency_ms)}
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className={styles.cardBody}>
        {isPending && (
          <div className={styles.pendingPulse} role="status" aria-label="Waiting for response">
            <span />
            <span />
            <span />
          </div>
        )}
        {isError && (
          <p className={styles.errorText} role="alert">
            {result.status === 'timeout'
              ? 'Request timed out'
              : result.error_message || 'An error occurred'}
          </p>
        )}
        {result.status === 'success' && (
          <p className={styles.responseText}>{result.content}</p>
        )}
      </div>

      {/* Footer: token stats */}
      {result.status === 'success' && (
        <footer className={styles.cardFooter}>
          <span
            className={styles.tokenStat}
            title="Input tokens"
            aria-label={`${result.input_tokens} input tokens`}
          >
            ↑ {result.input_tokens}
          </span>
          <span
            className={styles.tokenStat}
            title="Output tokens"
            aria-label={`${result.output_tokens} output tokens`}
          >
            ↓ {result.output_tokens}
          </span>
          <span
            className={styles.tokenStat}
            title="Total tokens"
            aria-label={`${result.total_tokens} total tokens`}
          >
            Σ {result.total_tokens}
          </span>
          {result.finish_reason && (
            <span className={styles.finishReason}>{result.finish_reason}</span>
          )}
        </footer>
      )}
    </article>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface ModelBenchmarkPanelProps {
  /** Called when a benchmark completes so parents can persist the result */
  onRunComplete?: (run: BenchmarkRunResult) => void;
  /** Initial prompt to pre-fill */
  initialPrompt?: string;
  /** API base URL override for testing */
  apiBase?: string;
}

const ModelBenchmarkPanel: React.FC<ModelBenchmarkPanelProps> = ({
  onRunComplete,
  initialPrompt = '',
  apiBase = API_BASE,
}) => {
  // Form state
  const [prompt, setPrompt] = useState(initialPrompt);
  const [systemPrompt, setSystemPrompt] = useState('');
  const [tags, setTags] = useState('');
  const [providers, setProviders] = useState<ProviderConfig[]>([
    { id: newLocalId(), provider_id: 'openai', model: 'gpt-4o', temperature: 0.7, max_tokens: 1024 },
    { id: newLocalId(), provider_id: 'anthropic', model: 'claude-3-5-sonnet-20241022', temperature: 0.7, max_tokens: 1024 },
  ]);

  // Run state
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<ProviderResult[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [totalDurationMs, setTotalDurationMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Compare state
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]); // provider_id:model
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  // History drawer
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<BenchmarkHistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  // ---------------------------------------------------------------------------
  // Provider config management
  // ---------------------------------------------------------------------------

  const addProvider = useCallback(() => {
    if (providers.length >= 8) return;
    setProviders((prev) => [
      ...prev,
      { id: newLocalId(), provider_id: 'gemini', model: 'gemini-2.0-flash', temperature: 0.7, max_tokens: 1024 },
    ]);
  }, [providers.length]);

  const removeProvider = useCallback((localId: string) => {
    setProviders((prev) => prev.filter((p) => p.id !== localId));
  }, []);

  const updateProvider = useCallback(
    (localId: string, updates: Partial<Omit<ProviderConfig, 'id'>>) => {
      setProviders((prev) =>
        prev.map((p) => (p.id === localId ? { ...p, ...updates } : p))
      );
    },
    []
  );

  // ---------------------------------------------------------------------------
  // Run benchmark
  // ---------------------------------------------------------------------------

  const handleRun = useCallback(async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt before running the benchmark.');
      return;
    }
    if (providers.length < 2) {
      setError('Add at least 2 providers to run a benchmark.');
      return;
    }

    setError(null);
    setIsRunning(true);
    setCompareResult(null);
    setSelectedForCompare([]);
    setCurrentRunId(null);
    setTotalDurationMs(null);

    // Seed pending results immediately for instant UI feedback
    const pendingResults: ProviderResult[] = providers.map((p) => ({
      provider_id: p.provider_id,
      model: p.model,
      status: 'pending',
      content: null,
      error_message: null,
      latency_ms: 0,
      input_tokens: 0,
      output_tokens: 0,
      total_tokens: 0,
      finish_reason: null,
    }));
    setResults(pendingResults);

    abortRef.current = new AbortController();

    const body = {
      prompt: prompt.trim(),
      system_prompt: systemPrompt.trim() || null,
      tags: tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      providers: providers.map((p) => ({
        provider_id: p.provider_id,
        model: p.model,
        temperature: p.temperature,
        max_tokens: p.max_tokens,
      })),
    };

    try {
      const resp = await fetch(`${apiBase}/benchmark/run/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortRef.current.signal,
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Server error ${resp.status}: ${errText}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error('No response body reader available.');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const event = JSON.parse(line) as {
              event: string;
              data: ProviderResult | BenchmarkRunResult;
            };

            if (event.event === 'provider_result') {
              const pr = event.data as ProviderResult;
              setResults((prev) =>
                prev.map((r) =>
                  r.provider_id === pr.provider_id && r.model === pr.model
                    ? pr
                    : r
                )
              );
            } else if (event.event === 'run_complete') {
              const run = event.data as BenchmarkRunResult;
              setCurrentRunId(run.run_id);
              setTotalDurationMs(run.total_duration_ms);
              setResults(run.results);
              onRunComplete?.(run);
            }
          } catch {
            // Ignore malformed NDJSON lines
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
        setResults([]);
      }
    } finally {
      setIsRunning(false);
    }
  }, [prompt, systemPrompt, tags, providers, apiBase, onRunComplete]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
  }, []);

  // ---------------------------------------------------------------------------
  // Compare
  // ---------------------------------------------------------------------------

  const toggleCompareSelection = useCallback((key: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(key)) return prev.filter((k) => k !== key);
      if (prev.length >= 2) return [prev[1], key]; // slide window
      return [...prev, key];
    });
    setCompareResult(null);
  }, []);

  const handleCompare = useCallback(async () => {
    if (!currentRunId || selectedForCompare.length !== 2) return;
    setIsComparing(true);
    setCompareResult(null);
    try {
      const resp = await fetch(`${apiBase}/benchmark/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: currentRunId,
          provider_a: selectedForCompare[0],
          provider_b: selectedForCompare[1],
        }),
      });
      if (!resp.ok) throw new Error(`Compare failed: ${resp.status}`);
      const data: CompareResult = await resp.json();
      setCompareResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Compare failed');
    } finally {
      setIsComparing(false);
    }
  }, [currentRunId, selectedForCompare, apiBase]);

  // ---------------------------------------------------------------------------
  // History
  // ---------------------------------------------------------------------------

  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const resp = await fetch(`${apiBase}/benchmark/history?per_page=20`);
      if (!resp.ok) throw new Error('Failed to load history');
      const data: BenchmarkHistoryItem[] = await resp.json();
      setHistory(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'History load failed');
    } finally {
      setIsLoadingHistory(false);
    }
  }, [apiBase]);

  useEffect(() => {
    if (showHistory) loadHistory();
  }, [showHistory, loadHistory]);

  // ---------------------------------------------------------------------------
  // Derived state
  // ---------------------------------------------------------------------------

  const successResults = results.filter((r) => r.status === 'success');
  const fastestMs = successResults.length
    ? Math.min(...successResults.map((r) => r.latency_ms))
    : null;

  const getRank = (r: ProviderResult): number | null =>
    r.status === 'success' && r.latency_ms === fastestMs ? 1 : null;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <section className={styles.panel} aria-label="Model Benchmark Panel">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className={styles.panelHeader}>
        <h2 className={styles.panelTitle}>Model Benchmark</h2>
        <button
          className={styles.historyBtn}
          onClick={() => setShowHistory((v) => !v)}
          aria-expanded={showHistory}
          aria-controls="benchmark-history-drawer"
        >
          {showHistory ? 'Hide History' : 'View History'}
        </button>
      </header>

      {/* ── History Drawer ─────────────────────────────────────────────── */}
      {showHistory && (
        <aside
          id="benchmark-history-drawer"
          className={styles.historyDrawer}
          aria-label="Benchmark run history"
        >
          <h3 className={styles.historyTitle}>Recent Runs</h3>
          {isLoadingHistory && <p className={styles.loadingText}>Loading…</p>}
          {!isLoadingHistory && history.length === 0 && (
            <p className={styles.emptyText}>No previous benchmark runs found.</p>
          )}
          <ul className={styles.historyList} role="list">
            {history.map((item) => (
              <li key={item.run_id} className={styles.historyItem}>
                <p className={styles.historyPrompt}>{item.prompt_preview}</p>
                <div className={styles.historyMeta}>
                  <span>{item.provider_ids.join(', ')}</span>
                  <span>{formatLatency(item.total_duration_ms)}</span>
                  <span className={styles.successCount}>
                    {item.success_count} OK
                  </span>
                  {item.error_count > 0 && (
                    <span className={styles.errorCount}>{item.error_count} ERR</span>
                  )}
                </div>
                <time className={styles.historyDate}>
                  {new Date(item.created_at).toLocaleString()}
                </time>
              </li>
            ))}
          </ul>
        </aside>
      )}

      {/* ── Config Form ────────────────────────────────────────────────── */}
      <div className={styles.configSection}>
        <label className={styles.fieldLabel} htmlFor="benchmark-prompt">
          Prompt
        </label>
        <textarea
          id="benchmark-prompt"
          className={styles.promptInput}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter the prompt to benchmark across providers…"
          rows={3}
          disabled={isRunning}
          aria-required="true"
        />

        <label className={styles.fieldLabel} htmlFor="benchmark-system">
          System Prompt{' '}
          <span className={styles.optional}>(optional)</span>
        </label>
        <textarea
          id="benchmark-system"
          className={styles.systemInput}
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          placeholder="Optional system-level instructions…"
          rows={2}
          disabled={isRunning}
        />

        <label className={styles.fieldLabel} htmlFor="benchmark-tags">
          Tags{' '}
          <span className={styles.optional}>(comma-separated)</span>
        </label>
        <input
          id="benchmark-tags"
          className={styles.tagsInput}
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="e.g. production, geography, v2"
          disabled={isRunning}
        />

        {/* Provider configuration rows */}
        <div className={styles.providersSection}>
          <div className={styles.providersSectionHeader}>
            <span className={styles.fieldLabel}>Providers</span>
            <button
              className={styles.addProviderBtn}
              onClick={addProvider}
              disabled={isRunning || providers.length >= 8}
              aria-label="Add another provider"
            >
              + Add Provider
            </button>
          </div>

          {providers.map((p) => (
            <div key={p.id} className={styles.providerRow}>
              <select
                className={styles.providerSelect}
                value={p.provider_id}
                onChange={(e) =>
                  updateProvider(p.id, {
                    provider_id: e.target.value,
                    model: KNOWN_PROVIDERS[e.target.value]?.[0] ?? '',
                  })
                }
                disabled={isRunning}
                aria-label="Provider"
              >
                {Object.keys(KNOWN_PROVIDERS).map((pid) => (
                  <option key={pid} value={pid}>
                    {pid}
                  </option>
                ))}
              </select>

              <select
                className={styles.modelSelect}
                value={p.model}
                onChange={(e) => updateProvider(p.id, { model: e.target.value })}
                disabled={isRunning}
                aria-label="Model"
              >
                {(KNOWN_PROVIDERS[p.provider_id] ?? [p.model]).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>

              <label className={styles.sliderLabel}>
                <span>Temp</span>
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={0.1}
                  value={p.temperature}
                  onChange={(e) =>
                    updateProvider(p.id, { temperature: parseFloat(e.target.value) })
                  }
                  disabled={isRunning}
                  aria-label={`Temperature for ${p.provider_id} ${p.model}`}
                />
                <span className={styles.sliderValue}>{p.temperature.toFixed(1)}</span>
              </label>

              <label className={styles.sliderLabel}>
                <span>Tokens</span>
                <input
                  type="range"
                  min={64}
                  max={4096}
                  step={64}
                  value={p.max_tokens}
                  onChange={(e) =>
                    updateProvider(p.id, { max_tokens: parseInt(e.target.value, 10) })
                  }
                  disabled={isRunning}
                  aria-label={`Max tokens for ${p.provider_id} ${p.model}`}
                />
                <span className={styles.sliderValue}>{p.max_tokens}</span>
              </label>

              <button
                className={styles.removeProviderBtn}
                onClick={() => removeProvider(p.id)}
                disabled={isRunning || providers.length <= 2}
                aria-label={`Remove ${p.provider_id} ${p.model}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className={styles.actions}>
          {!isRunning ? (
            <button
              className={styles.runBtn}
              onClick={handleRun}
              disabled={providers.length < 2 || !prompt.trim()}
            >
              ▶ Run Benchmark
            </button>
          ) : (
            <button className={styles.cancelBtn} onClick={handleCancel}>
              ⏹ Cancel
            </button>
          )}

          {selectedForCompare.length === 2 && currentRunId && (
            <button
              className={styles.compareBtn}
              onClick={handleCompare}
              disabled={isComparing}
              aria-label="Compare selected providers"
            >
              {isComparing ? 'Comparing…' : '🔍 Compare Selected'}
            </button>
          )}
        </div>

        {error && (
          <p className={styles.globalError} role="alert">
            {error}
          </p>
        )}
      </div>

      {/* ── Results Grid ───────────────────────────────────────────────── */}
      {results.length > 0 && (
        <div className={styles.resultsSection}>
          <div className={styles.resultsHeader}>
            <h3 className={styles.resultsTitle}>
              Results
              {totalDurationMs !== null && (
                <span className={styles.totalTime}>
                  {' '}(total: {formatLatency(totalDurationMs)})
                </span>
              )}
            </h3>
            {selectedForCompare.length > 0 && (
              <p className={styles.selectHint}>
                {selectedForCompare.length}/2 providers selected for comparison
              </p>
            )}
          </div>

          <div
            className={styles.resultsGrid}
            style={{
              gridTemplateColumns: `repeat(${Math.min(results.length, 4)}, 1fr)`,
            }}
          >
            {results.map((r) => {
              const key = `${r.provider_id}:${r.model}`;
              return (
                <ProviderCard
                  key={key}
                  result={r}
                  isSelected={selectedForCompare.includes(key)}
                  onSelect={() => toggleCompareSelection(key)}
                  rank={getRank(r)}
                />
              );
            })}
          </div>

          {/* Summary bar */}
          {successResults.length >= 2 && (
            <div className={styles.summaryBar}>
              <span>
                <strong>⚡ Fastest:</strong>{' '}
                {successResults
                  .filter((r) => r.latency_ms === fastestMs)
                  .map((r) => `${r.provider_id} / ${r.model}`)
                  .join(', ')}
              </span>
              <span>
                <strong>📊 Most efficient:</strong>{' '}
                {successResults
                  .reduce((a, b) =>
                    a.total_tokens <= b.total_tokens ? a : b
                  )
                  .provider_id}
              </span>
            </div>
          )}
        </div>
      )}

      {/* ── Compare Panel ──────────────────────────────────────────────── */}
      {compareResult && (
        <section
          className={styles.comparePanel}
          aria-label="Provider comparison results"
        >
          <h3 className={styles.compareTitle}>
            Comparison:{' '}
            <em>{compareResult.provider_a}</em> vs{' '}
            <em>{compareResult.provider_b}</em>
          </h3>

          <dl className={styles.compareStats}>
            <div className={styles.compareStat}>
              <dt>Latency Δ</dt>
              <dd
                style={{
                  color:
                    compareResult.latency_delta_ms < 0 ? '#22c55e' : '#ef4444',
                }}
              >
                {compareResult.latency_delta_ms > 0 ? '+' : ''}
                {compareResult.latency_delta_ms.toFixed(0)}ms
              </dd>
            </div>

            <div className={styles.compareStat}>
              <dt>Token Δ</dt>
              <dd>
                {compareResult.token_delta > 0 ? '+' : ''}
                {compareResult.token_delta} tokens
              </dd>
            </div>

            <div className={styles.compareStat}>
              <dt>Content Similarity</dt>
              <dd>
                {(compareResult.content_similarity * 100).toFixed(1)}%{' '}
                <span className={styles.similarityLabel}>
                  ({similarityLabel(compareResult.content_similarity)})
                </span>
              </dd>
            </div>

            <div className={styles.compareStat}>
              <dt>Faster</dt>
              <dd className={styles.winnerBadge}>
                {compareResult.faster_provider}
              </dd>
            </div>

            <div className={styles.compareStat}>
              <dt>More Concise</dt>
              <dd className={styles.winnerBadge}>
                {compareResult.more_concise_provider}
              </dd>
            </div>
          </dl>
        </section>
      )}
    </section>
  );
};

export default ModelBenchmarkPanel;
