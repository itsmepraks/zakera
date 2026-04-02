/**
 * ProviderStatusBadge
 *
 * Displays a real-time health indicator for a single AI model provider.
 * Status is fetched from GET /api/v1/health/providers and auto-refreshed
 * every POLL_INTERVAL_MS milliseconds.
 *
 * @example
 * // Full badge with latency display
 * <ProviderStatusBadge provider="anthropic" />
 *
 * @example
 * // Compact dot-only for use inside ModelSelector
 * <ProviderStatusBadge provider="openai" compact />
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import styles from './ProviderStatusBadge.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ProviderStatus = 'healthy' | 'degraded' | 'unavailable' | 'unknown';

export interface ProviderHealthData {
  /** Provider identifier as registered in the backend (e.g. "anthropic"). */
  provider: string;
  /** Current operational status. */
  status: ProviderStatus;
  /** Round-trip latency of the most recent probe, in milliseconds. */
  latency_ms: number | null;
  /** ISO-8601 timestamp of the last completed health check. */
  checked_at: string | null;
  /** Optional human-readable detail about a non-healthy status. */
  detail?: string;
}

export interface ProviderStatusBadgeProps {
  /** Provider identifier to display, e.g. "openai", "anthropic". */
  provider: string;
  /**
   * When true, renders only the status dot without the provider name or
   * latency text.  Useful for embedding inside compact dropdowns.
   * @default false
   */
  compact?: boolean;
  /**
   * Override the polling interval in milliseconds.
   * @default 30000
   */
  pollIntervalMs?: number;
  /** Optional CSS class applied to the outermost element. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEFAULT_POLL_INTERVAL_MS = 30_000;
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';
const HEALTH_ENDPOINT = `${API_BASE}/api/v1/health/providers`;

// Human-readable labels used in aria-label and tooltip.
const STATUS_LABELS: Record<ProviderStatus, string> = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  unavailable: 'Unavailable',
  unknown: 'Unknown',
};

// ---------------------------------------------------------------------------
// Custom hook
// ---------------------------------------------------------------------------

interface UseProviderHealthResult {
  data: ProviderHealthData | null;
  loading: boolean;
  error: string | null;
  /** Imperatively trigger a refresh outside of the poll cycle. */
  refresh: () => void;
}

function useProviderHealth(
  provider: string,
  pollIntervalMs: number
): UseProviderHealthResult {
  const [data, setData] = useState<ProviderHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchHealth = useCallback(async () => {
    // Cancel any in-flight request before firing a new one.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setError(null);
      const res = await fetch(`${HEALTH_ENDPOINT}/${provider}`, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' },
        // Include credentials so auth cookies are forwarded in production.
        credentials: 'include',
      });

      if (!res.ok) {
        throw new Error(`Health endpoint returned HTTP ${res.status}`);
      }

      const json: ProviderHealthData = await res.json();
      setData(json);
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Silently swallow cancellations — the component unmounted or
        // a new request superseded this one.
        return;
      }
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      // Keep stale data visible while in error state so the UI does not
      // blank out on a transient network blip.
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    // Fire immediately, then on interval.
    fetchHealth();
    const timer = setInterval(fetchHealth, pollIntervalMs);
    return () => {
      clearInterval(timer);
      abortRef.current?.abort();
    };
  }, [fetchHealth, pollIntervalMs]);

  return { data, loading, error, refresh: fetchHealth };
}

// ---------------------------------------------------------------------------
// Helper: format latency
// ---------------------------------------------------------------------------

function formatLatency(ms: number | null): string {
  if (ms === null) return '';
  if (ms < 1_000) return `${Math.round(ms)}ms`;
  return `${(ms / 1_000).toFixed(1)}s`;
}

// ---------------------------------------------------------------------------
// Helper: format timestamp for tooltip
// ---------------------------------------------------------------------------

function formatCheckedAt(iso: string | null): string {
  if (!iso) return 'Never checked';
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ProviderStatusBadge: React.FC<ProviderStatusBadgeProps> = React.memo(
  function ProviderStatusBadge({
    provider,
    compact = false,
    pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
    className,
  }) {
    const { data, loading, error, refresh } = useProviderHealth(
      provider,
      pollIntervalMs
    );

    // Derive the visual status: use fetched data, fall back to 'unknown' while
    // loading and 'unavailable' on a hard error.
    const status: ProviderStatus = loading
      ? 'unknown'
      : error
      ? 'unavailable'
      : data?.status ?? 'unknown';

    const latencyText =
      !compact && data ? formatLatency(data.latency_ms) : '';
    const checkedAt = formatCheckedAt(data?.checked_at ?? null);
    const ariaLabel = `${provider} provider: ${STATUS_LABELS[status]}`;
    const tooltipText = error
      ? `Error: ${error}`
      : `Last checked: ${checkedAt}${data?.detail ? ` — ${data.detail}` : ''}`;

    return (
      <div
        className={[
          styles.badge,
          styles[status],
          compact ? styles.compact : '',
          className ?? '',
        ]
          .filter(Boolean)
          .join(' ')}
        aria-label={ariaLabel}
        title={tooltipText}
        role="status"
      >
        {/* Animated status dot */}
        <span
          className={[
            styles.dot,
            status === 'healthy' ? styles.dotPulse : '',
          ]
            .filter(Boolean)
            .join(' ')}
          aria-hidden="true"
        />

        {!compact && (
          <>
            <span className={styles.providerName}>{provider}</span>

            {latencyText && (
              <span className={styles.latency}>{latencyText}</span>
            )}

            {loading && !data && (
              <span className={styles.loadingDots} aria-hidden="true">
                …
              </span>
            )}
          </>
        )}

        {/* Invisible refresh button for keyboard / screen-reader users */}
        <button
          type="button"
          className={styles.refreshButton}
          onClick={refresh}
          aria-label={`Refresh ${provider} status`}
          tabIndex={compact ? -1 : 0}
        >
          ↺
        </button>
      </div>
    );
  }
);

ProviderStatusBadge.displayName = 'ProviderStatusBadge';
export default ProviderStatusBadge;
