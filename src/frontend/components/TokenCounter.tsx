/**
 * TokenCounter
 *
 * Displays real-time token usage: prompt tokens, completion tokens, and a
 * colour-coded progress bar showing how much of the model's context window
 * has been consumed.
 */

import React, { useMemo } from 'react';
import styles from './TokenCounter.module.css';

export interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

export interface TokenCounterProps {
  usage: TokenUsage;
  /** Maximum context window size for the active model (default: 128 000). */
  contextWindow?: number;
  /** Whether to show the detailed breakdown tooltip on hover. */
  showBreakdown?: boolean;
}

const FORMAT = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

const TokenCounter: React.FC<TokenCounterProps> = ({
  usage,
  contextWindow = 128_000,
  showBreakdown = true,
}) => {
  const { promptTokens, completionTokens, totalTokens } = usage;
  const usedPct = useMemo(
    () => Math.min(100, (totalTokens / contextWindow) * 100),
    [totalTokens, contextWindow],
  );

  const barClass =
    usedPct >= 90
      ? styles.barCritical
      : usedPct >= 70
      ? styles.barWarning
      : styles.barNormal;

  const tooltipText = showBreakdown
    ? `Prompt: ${promptTokens.toLocaleString()} tokens\nCompletion: ${completionTokens.toLocaleString()} tokens\nTotal: ${totalTokens.toLocaleString()} / ${contextWindow.toLocaleString()}`
    : undefined;

  return (
    <div
      className={styles.container}
      title={tooltipText}
      aria-label={`Token usage: ${totalTokens} of ${contextWindow}`}
    >
      <span className={styles.count}>{FORMAT.format(totalTokens)}</span>
      <span className={styles.separator}>/</span>
      <span className={styles.limit}>{FORMAT.format(contextWindow)}</span>

      <div className={styles.barTrack} role="progressbar" aria-valuenow={usedPct} aria-valuemin={0} aria-valuemax={100}>
        <div className={`${styles.barFill} ${barClass}`} style={{ width: `${usedPct}%` }} />
      </div>
    </div>
  );
};

export default TokenCounter;
