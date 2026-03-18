/**
 * useTokenCounter
 *
 * Subscribes to the active chat session's token-usage SSE stream and
 * accumulates prompt/completion/total token counts in real time.
 *
 * Usage:
 *
 *   const { usage, reset } = useTokenCounter(sessionId, contextWindow);
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { TokenUsage } from '../components/TokenCounter';

const INITIAL_USAGE: TokenUsage = {
  promptTokens: 0,
  completionTokens: 0,
  totalTokens: 0,
};

interface UseTokenCounterResult {
  usage: TokenUsage;
  /** Reset counters to zero (e.g. on new conversation). */
  reset: () => void;
}

export function useTokenCounter(
  sessionId: string | null,
  contextWindow: number = 128_000,
): UseTokenCounterResult {
  const [usage, setUsage] = useState<TokenUsage>(INITIAL_USAGE);
  const esRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => setUsage(INITIAL_USAGE), []);

  useEffect(() => {
    if (!sessionId) {
      reset();
      return;
    }

    // Close any previous connection
    esRef.current?.close();

    const es = new EventSource(`/api/v1/sessions/${sessionId}/token-stream`);
    esRef.current = es;

    es.addEventListener('token_usage', (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data) as {
          prompt_tokens?: number;
          completion_tokens?: number;
          total_tokens?: number;
          delta_prompt?: number;
          delta_completion?: number;
        };

        setUsage((prev) => {
          const promptTokens =
            data.prompt_tokens ?? prev.promptTokens + (data.delta_prompt ?? 0);
          const completionTokens =
            data.completion_tokens ?? prev.completionTokens + (data.delta_completion ?? 0);
          const totalTokens =
            data.total_tokens ?? promptTokens + completionTokens;

          return { promptTokens, completionTokens, totalTokens };
        });
      } catch (err) {
        console.warn('[useTokenCounter] Failed to parse token_usage event:', err);
      }
    });

    es.addEventListener('error', () => {
      console.warn('[useTokenCounter] SSE connection error for session', sessionId);
    });

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [sessionId, contextWindow, reset]);

  return { usage, reset };
}
