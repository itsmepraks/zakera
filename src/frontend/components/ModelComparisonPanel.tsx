/**
 * ModelComparisonPanel
 * --------------------
 * A responsive UI panel that lets users send a single prompt to multiple
 * AI providers side-by-side and compare their streamed responses in real-time.
 *
 * Props:
 *   availableProviders  – list of provider keys to show in the selector
 *   defaultProviders    – which providers are pre-selected on mount
 */

import React, { useRef, useState } from 'react';
import { useModelComparison } from '../hooks/useModelComparison';
import type { ComparisonEntry } from '../types/comparison';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: ComparisonEntry['status'] }) {
  const map: Record<string, string> = {
    idle: 'bg-gray-100 text-gray-600',
    pending: 'bg-yellow-100 text-yellow-700 animate-pulse',
    streaming: 'bg-blue-100 text-blue-700 animate-pulse',
    done: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${
        map[status] ?? map.idle
      }`}
    >
      {status}
    </span>
  );
}

function MetricsFooter({ entry }: { entry: ComparisonEntry }) {
  const { metrics, status } = entry;
  if (status === 'idle' || status === 'pending') return null;

  return (
    <div className="mt-2 flex flex-wrap gap-3 border-t border-gray-100 pt-2 text-xs text-gray-500">
      {metrics.ttftMs !== null && (
        <span>⚡ TTFT: <strong>{metrics.ttftMs} ms</strong></span>
      )}
      {metrics.totalMs !== null && (
        <span>🕑 Total: <strong>{metrics.totalMs} ms</strong></span>
      )}
      {metrics.outputTokens !== null && (
        <span>🔢 Tokens out: <strong>{metrics.outputTokens}</strong></span>
      )}
    </div>
  );
}

function ProviderCard({ entry }: { entry: ComparisonEntry }) {
  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="font-semibold text-gray-800 text-sm">{entry.label}</h3>
        <StatusBadge status={entry.status} />
      </div>

      {/* Response body */}
      <div className="flex-1 overflow-y-auto px-4 py-3 text-sm text-gray-700 whitespace-pre-wrap min-h-[160px] max-h-[400px] font-mono">
        {entry.error ? (
          <span className="text-red-600">Error: {entry.error}</span>
        ) : entry.response ? (
          entry.response
        ) : (
          <span className="text-gray-400 italic">
            {entry.status === 'idle' ? 'Waiting for prompt…' : 'Generating…'}
          </span>
        )}
      </div>

      {/* Metrics */}
      <div className="px-4 pb-3">
        <MetricsFooter entry={entry} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const ALL_PROVIDERS = [
  'anthropic',
  'gemini',
  'gemini2',
  'groq',
  'mistral',
  'codestral',
  'deepseek',
  'perplexity',
  'xai',
  'openrouter',
  'together',
  'cohere',
] as const;

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Claude 3.5',
  gemini: 'Gemini 1.5',
  gemini2: 'Gemini 2.0',
  groq: 'Groq',
  mistral: 'Mistral',
  codestral: 'Codestral',
  deepseek: 'DeepSeek',
  perplexity: 'Perplexity',
  xai: 'Grok',
  openrouter: 'OpenRouter',
  together: 'Together',
  cohere: 'Cohere',
};

interface ModelComparisonPanelProps {
  availableProviders?: readonly string[];
  defaultProviders?: string[];
}

export function ModelComparisonPanel({
  availableProviders = ALL_PROVIDERS,
  defaultProviders = ['anthropic', 'gemini', 'groq'],
}: ModelComparisonPanelProps) {
  const [prompt, setPrompt] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { entries, isRunning, run, reset, toggleProvider, selectedProviders } =
    useModelComparison(defaultProviders);

  const handleRun = async () => {
    const trimmed = prompt.trim();
    if (!trimmed || isRunning) return;
    await run(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleRun();
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* ---- Provider selector ---- */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Select providers to compare
        </p>
        <div className="flex flex-wrap gap-2">
          {availableProviders.map((p) => {
            const selected = selectedProviders.includes(p);
            return (
              <button
                key={p}
                onClick={() => toggleProvider(p)}
                disabled={isRunning}
                className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                  selected
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-300 bg-white text-gray-600 hover:border-gray-400'
                } disabled:opacity-50`}
              >
                {PROVIDER_LABELS[p] ?? p}
              </button>
            );
          })}
        </div>
      </div>

      {/* ---- Prompt input ---- */}
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-700">
          Prompt
          <span className="ml-1 text-xs text-gray-400">(Cmd/Ctrl + Enter to run)</span>
        </label>
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
          rows={4}
          placeholder="Enter your prompt here…"
          className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50"
        />
        <div className="flex justify-end gap-3">
          <button
            onClick={reset}
            disabled={isRunning}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Reset
          </button>
          <button
            onClick={handleRun}
            disabled={isRunning || !prompt.trim() || selectedProviders.length === 0}
            className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isRunning ? 'Running…' : `Compare (${selectedProviders.length})`}
          </button>
        </div>
      </div>

      {/* ---- Response grid ---- */}
      {entries.length > 0 && (
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: `repeat(auto-fill, minmax(min(100%, 380px), 1fr))`,
          }}
        >
          {entries.map((entry) => (
            <ProviderCard key={entry.provider} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}

export default ModelComparisonPanel;
