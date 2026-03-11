/**
 * useMessageStatus
 * ----------------
 * Tracks the lifecycle of a single chat message from dispatch through
 * streaming completion (or error).  Designed to work alongside the
 * existing useTypingIndicator hook but operating at *message* granularity
 * rather than at conversation granularity.
 *
 * State machine:
 *   idle → sending → streaming → done
 *                  └────────────────→ error
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MessageStatus = 'idle' | 'sending' | 'streaming' | 'done' | 'error';

export type MessageErrorKind =
  | 'network'
  | 'rate_limit'
  | 'context_length'
  | 'server'
  | 'unknown';

export interface MessageStatusState {
  /** Current lifecycle status. */
  status: MessageStatus;
  /** Wall-clock milliseconds since the message was sent (null when idle). */
  elapsedMs: number | null;
  /** Running count of tokens received so far during streaming. */
  streamedTokens: number;
  /** Approximate tokens-per-second during streaming (null before first token). */
  tokensPerSecond: number | null;
  /** Error detail when status === 'error'. */
  error: { kind: MessageErrorKind; message: string } | null;
}

export interface UseMessageStatusReturn extends MessageStatusState {
  /** Call when the user submits the message. */
  onSend: () => void;
  /** Call each time a streaming chunk arrives. Pass the token count in the chunk. */
  onChunk: (tokenDelta?: number) => void;
  /** Call when the stream finishes successfully. */
  onDone: () => void;
  /** Call when an error occurs.  Pass an HTTP status code for auto-classification. */
  onError: (message: string, httpStatus?: number) => void;
  /** Reset back to idle (e.g. when starting a new conversation). */
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function classifyError(message: string, httpStatus?: number): MessageErrorKind {
  if (httpStatus === 429) return 'rate_limit';
  if (httpStatus && httpStatus >= 500) return 'server';
  const lower = message.toLowerCase();
  if (lower.includes('network') || lower.includes('fetch') || lower.includes('econnrefused')) {
    return 'network';
  }
  if (lower.includes('context') || lower.includes('token') || lower.includes('length')) {
    return 'context_length';
  }
  if (httpStatus === 400 || httpStatus === 422) return 'server';
  return 'unknown';
}

const INITIAL_STATE: MessageStatusState = {
  status: 'idle',
  elapsedMs: null,
  streamedTokens: 0,
  tokensPerSecond: null,
  error: null,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * @example
 * ```tsx
 * const { status, elapsedMs, tokensPerSecond, onSend, onChunk, onDone, onError } =
 *   useMessageStatus();
 *
 * // On user submit:
 * onSend();
 * // For each SSE chunk:
 * onChunk(chunk.tokenDelta);
 * // When stream ends:
 * onDone();
 * // On failure:
 * onError(err.message, err.status);
 * ```
 */
export function useMessageStatus(): UseMessageStatusReturn {
  const [state, setState] = useState<MessageStatusState>(INITIAL_STATE);

  // Refs so interval callbacks always have the latest values without
  // re-creating the interval on every render.
  const sendTimeRef = useRef<number | null>(null);
  const firstChunkTimeRef = useRef<number | null>(null);
  const tokenAccRef = useRef<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Tick elapsed time every 100 ms while sending / streaming.
  const startTick = useCallback(() => {
    if (intervalRef.current !== null) return;
    intervalRef.current = setInterval(() => {
      if (sendTimeRef.current === null) return;
      const elapsedMs = Date.now() - sendTimeRef.current;
      const firstChunkTime = firstChunkTimeRef.current;
      const totalTokens = tokenAccRef.current;
      const tokensPerSecond =
        firstChunkTime !== null && totalTokens > 0
          ? Math.round((totalTokens / (Date.now() - firstChunkTime)) * 1_000)
          : null;
      setState((prev) => ({ ...prev, elapsedMs, streamedTokens: totalTokens, tokensPerSecond }));
    }, 100);
  }, []);

  const stopTick = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Clean up on unmount.
  useEffect(() => () => stopTick(), [stopTick]);

  // ------------------------------------------------------------------

  const onSend = useCallback(() => {
    sendTimeRef.current = Date.now();
    firstChunkTimeRef.current = null;
    tokenAccRef.current = 0;
    setState({
      status: 'sending',
      elapsedMs: 0,
      streamedTokens: 0,
      tokensPerSecond: null,
      error: null,
    });
    startTick();
  }, [startTick]);

  const onChunk = useCallback(
    (tokenDelta = 1) => {
      if (firstChunkTimeRef.current === null) {
        firstChunkTimeRef.current = Date.now();
      }
      tokenAccRef.current += tokenDelta;
      setState((prev) => ({
        ...prev,
        status: 'streaming',
        streamedTokens: tokenAccRef.current,
      }));
    },
    [],
  );

  const onDone = useCallback(() => {
    stopTick();
    const finalElapsed =
      sendTimeRef.current !== null ? Date.now() - sendTimeRef.current : null;
    const finalTokens = tokenAccRef.current;
    const firstChunkTime = firstChunkTimeRef.current;
    const tokensPerSecond =
      firstChunkTime !== null && finalTokens > 0
        ? Math.round((finalTokens / (Date.now() - firstChunkTime)) * 1_000)
        : null;
    setState((prev) => ({
      ...prev,
      status: 'done',
      elapsedMs: finalElapsed,
      streamedTokens: finalTokens,
      tokensPerSecond,
    }));
  }, [stopTick]);

  const onError = useCallback(
    (message: string, httpStatus?: number) => {
      stopTick();
      setState((prev) => ({
        ...prev,
        status: 'error',
        error: { kind: classifyError(message, httpStatus), message },
      }));
    },
    [stopTick],
  );

  const reset = useCallback(() => {
    stopTick();
    sendTimeRef.current = null;
    firstChunkTimeRef.current = null;
    tokenAccRef.current = 0;
    setState(INITIAL_STATE);
  }, [stopTick]);

  return { ...state, onSend, onChunk, onDone, onError, reset };
}
