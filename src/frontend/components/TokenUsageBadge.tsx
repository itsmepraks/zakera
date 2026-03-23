/**
 * TokenUsageBadge
 * ================
 * Displays a live token-count and estimated-cost badge for the current
 * conversation.  Click to expand a per-role breakdown popover.
 *
 * Props
 * -----
 * conversationId  – UUID of the conversation to track
 * authToken       – Bearer JWT for the API call
 * refreshInterval – ms between auto-refreshes (default 30 000)
 * className       – optional extra Tailwind classes for the wrapper
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types mirroring the backend response schema
// ---------------------------------------------------------------------------

interface RoleBreakdown {
  role: string;
  message_count: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

interface ProviderBreakdown {
  provider: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
}

interface TokenUsageData {
  conversation_id: string;
  conversation_title: string;
  model_name: string | null;
  total_messages: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  by_role: RoleBreakdown[];
  by_provider: ProviderBreakdown[];
  avg_user_tokens_per_message: number;
  avg_assistant_tokens_per_message: number;
  pricing_info: { prompt_per_1k_usd: number; completion_per_1k_usd: number };
  pricing_provider: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function formatCost(usd: number): string {
  if (usd === 0) return 'free';
  if (usd < 0.001) return `<$0.001`;
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(3)}`;
}

type CostTier = 'free' | 'low' | 'medium' | 'high';

function costTier(usd: number): CostTier {
  if (usd === 0) return 'free';
  if (usd < 0.01) return 'low';
  if (usd < 0.10) return 'medium';
  return 'high';
}

const TIER_BADGE_CLASSES: Record<CostTier, string> = {
  free:   'bg-slate-100 text-slate-500 border-slate-200',
  low:    'bg-emerald-50 text-emerald-700 border-emerald-200',
  medium: 'bg-amber-50  text-amber-700  border-amber-200',
  high:   'bg-red-50    text-red-700    border-red-200',
};

const TIER_DOT_CLASSES: Record<CostTier, string> = {
  free:   'bg-slate-400',
  low:    'bg-emerald-500',
  medium: 'bg-amber-500',
  high:   'bg-red-500',
};

const ROLE_COLORS: Record<string, string> = {
  user:      'text-blue-600',
  assistant: 'text-violet-600',
  system:    'text-slate-500',
  tool:      'text-teal-600',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Skeleton() {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-200 bg-slate-50 animate-pulse">
      <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
      <span className="h-3 w-12 rounded bg-slate-200" />
      <span className="h-3 w-10 rounded bg-slate-200" />
    </div>
  );
}

function ErrorBadge({ onRetry }: { onRetry: () => void }) {
  return (
    <button
      onClick={onRetry}
      title="Failed to load token usage — click to retry"
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-red-200 bg-red-50 text-red-600 text-xs hover:bg-red-100 transition-colors"
    >
      <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
      </svg>
      usage error
    </button>
  );
}

function PopoverBreakdown({ data, onClose }: { data: TokenUsageData; onClose: () => void }) {
  const tier = costTier(data.estimated_cost_usd);
  return (
    <div className="absolute top-full right-0 mt-2 z-50 w-72 rounded-xl shadow-xl border border-slate-200 bg-white p-4 text-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-slate-800 truncate max-w-[180px]" title={data.conversation_title}>
          {data.conversation_title}
        </span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
          <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Model pill */}
      {data.model_name && (
        <div className="mb-3">
          <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5 font-mono">
            {data.model_name}
          </span>
          <span className="ml-1.5 text-xs text-slate-400">
            via {data.pricing_provider}
          </span>
        </div>
      )}

      {/* Totals */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {([
          { label: 'Total tokens', value: formatTokens(data.total_tokens) },
          { label: 'Prompt',       value: formatTokens(data.prompt_tokens) },
          { label: 'Completion',   value: formatTokens(data.completion_tokens) },
        ] as const).map(({ label, value }) => (
          <div key={label} className="text-center">
            <p className="text-base font-semibold text-slate-800">{value}</p>
            <p className="text-[10px] text-slate-400 leading-tight">{label}</p>
          </div>
        ))}
      </div>

      {/* Role breakdown */}
      <table className="w-full text-xs mb-3">
        <thead>
          <tr className="text-slate-400">
            <th className="text-left font-medium pb-1">Role</th>
            <th className="text-right font-medium pb-1">Msgs</th>
            <th className="text-right font-medium pb-1">Tokens</th>
            <th className="text-right font-medium pb-1">Cost</th>
          </tr>
        </thead>
        <tbody>
          {data.by_role.map((row) => (
            <tr key={row.role} className="border-t border-slate-100">
              <td className={`py-1 font-medium capitalize ${ROLE_COLORS[row.role] ?? 'text-slate-600'}`}>
                {row.role}
              </td>
              <td className="py-1 text-right text-slate-500">{row.message_count}</td>
              <td className="py-1 text-right text-slate-500">{formatTokens(row.total_tokens)}</td>
              <td className="py-1 text-right text-slate-500">{formatCost(row.estimated_cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pricing footnote */}
      <p className="text-[10px] text-slate-400 leading-snug">
        Estimated cost at ${data.pricing_info.prompt_per_1k_usd}/1k prompt +
        ${data.pricing_info.completion_per_1k_usd}/1k completion.
        Actual billing may differ.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export interface TokenUsageBadgeProps {
  conversationId: string;
  authToken: string;
  refreshInterval?: number;
  className?: string;
}

export function TokenUsageBadge({
  conversationId,
  authToken,
  refreshInterval = 30_000,
  className = '',
}: TokenUsageBadgeProps) {
  const [data, setData] = useState<TokenUsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchUsage = useCallback(async () => {
    if (!conversationId || !authToken) return;
    try {
      const res = await fetch(
        `/api/v1/conversations/${conversationId}/token-usage`,
        { headers: { Authorization: `Bearer ${authToken}` } },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: TokenUsageData = await res.json();
      setData(json);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [conversationId, authToken]);

  // Initial fetch + periodic refresh
  useEffect(() => {
    setLoading(true);
    fetchUsage();
    intervalRef.current = setInterval(fetchUsage, refreshInterval);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchUsage, refreshInterval]);

  // Close popover on outside click
  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [open]);

  if (loading) return <Skeleton />;
  if (error)   return <ErrorBadge onRetry={fetchUsage} />;
  if (!data)   return null;

  const tier = costTier(data.estimated_cost_usd);

  return (
    <div ref={wrapperRef} className={`relative inline-block ${className}`}>
      {/* Badge button */}
      <button
        onClick={() => setOpen((o) => !o)}
        title={`${data.total_tokens.toLocaleString()} tokens · ${formatCost(data.estimated_cost_usd)} estimated`}
        className={[
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium',
          'transition-colors hover:brightness-95 cursor-pointer select-none',
          TIER_BADGE_CLASSES[tier],
        ].join(' ')}
      >
        {/* Status dot */}
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${TIER_DOT_CLASSES[tier]}`} />

        {/* Token count */}
        <span>{formatTokens(data.total_tokens)} tok</span>

        {/* Separator */}
        <span className="opacity-30">·</span>

        {/* Cost */}
        <span>{formatCost(data.estimated_cost_usd)}</span>

        {/* Caret */}
        <svg
          className={`w-3 h-3 opacity-50 transition-transform ${open ? 'rotate-180' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Expanded popover */}
      {open && <PopoverBreakdown data={data} onClose={() => setOpen(false)} />}
    </div>
  );
}

export default TokenUsageBadge;
