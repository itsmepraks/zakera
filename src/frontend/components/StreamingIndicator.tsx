/**
 * StreamingIndicator
 *
 * Displays an animated typing-dots indicator and elapsed time while the
 * AI agent is streaming a response. Renders nothing when not streaming.
 */

import React, { useEffect, useRef, useState } from 'react';
import styles from './StreamingIndicator.module.css';

export interface StreamingIndicatorProps {
  /** Whether the AI is currently streaming a response. */
  isStreaming: boolean;
  /** Optional label shown before the dots (default: "Zakera is thinking"). */
  label?: string;
}

const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({
  isStreaming,
  label = 'Zakera is thinking',
}) => {
  const [elapsedMs, setElapsedMs] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (isStreaming) {
      startRef.current = performance.now();
      setElapsedMs(0);

      const tick = () => {
        setElapsedMs(Math.floor(performance.now() - (startRef.current ?? 0)));
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    } else {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    }

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [isStreaming]);

  if (!isStreaming) return null;

  const seconds = (elapsedMs / 1000).toFixed(1);

  return (
    <div
      className={styles.container}
      role="status"
      aria-live="polite"
      aria-label={`${label} (${seconds}s)`}
    >
      <span className={styles.label}>{label}</span>
      <span className={styles.dots} aria-hidden="true">
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
      </span>
      <span className={styles.elapsed}>{seconds}s</span>
    </div>
  );
};

export default StreamingIndicator;
