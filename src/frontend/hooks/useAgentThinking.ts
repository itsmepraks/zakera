/**
 * useAgentThinking — manages streamed chain-of-thought steps from the Zakera
 * AI agent backend.  Steps arrive either as WebSocket messages or as
 * server-sent events (SSE), depending on the transport in use.
 *
 * Usage:
 * ```tsx
 * const { steps, status, activeStepIndex, elapsedMs, reset } =
 *   useAgentThinking(conversationId);
 * ```
 */

import { useCallback, useEffect, useReducer, useRef } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ThinkingStepStatus = 'pending' | 'active' | 'done' | 'error';

export interface ThinkingStep {
  /** Unique step identifier returned by the backend */
  id: string;
  /** Human-readable label, e.g. "Searching memory" */
  label: string;
  /** Optional longer explanation / tool output */
  detail?: string;
  /** Step lifecycle state */
  status: ThinkingStepStatus;
  /** Wall-clock ms when this step started */
  startedAt: number;
  /** Wall-clock ms when this step finished (0 while active) */
  finishedAt: number;
  /** Tool name if this step is a tool invocation */
  tool?: string;
  /** Token count consumed by this step, if available */
  tokens?: number;
}

export type AgentThinkingStatus =
  | 'idle'
  | 'thinking'
  | 'streaming'
  | 'done'
  | 'error';

export interface AgentThinkingState {
  status: AgentThinkingStatus;
  steps: ThinkingStep[];
  activeStepIndex: number;
  elapsedMs: number;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

type Action =
  | { type: 'START' }
  | { type: 'STEP_BEGIN'; payload: Omit<ThinkingStep, 'status' | 'finishedAt'> }
  | { type: 'STEP_UPDATE'; id: string; detail: string }
  | { type: 'STEP_DONE'; id: string; tokens?: number }
  | { type: 'STEP_ERROR'; id: string; error: string }
  | { type: 'AGENT_DONE' }
  | { type: 'AGENT_STREAMING' }
  | { type: 'AGENT_ERROR'; error: string }
  | { type: 'TICK'; elapsedMs: number }
  | { type: 'RESET' };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

const initialState: AgentThinkingState = {
  status: 'idle',
  steps: [],
  activeStepIndex: -1,
  elapsedMs: 0,
  error: null,
};

function reducer(
  state: AgentThinkingState,
  action: Action
): AgentThinkingState {
  switch (action.type) {
    case 'START':
      return { ...initialState, status: 'thinking' };

    case 'STEP_BEGIN': {
      const newStep: ThinkingStep = {
        ...action.payload,
        status: 'active',
        finishedAt: 0,
      };
      // Mark previous active step as done if it was still active
      const steps = state.steps.map((s) =>
        s.status === 'active' ? { ...s, status: 'done' as ThinkingStepStatus, finishedAt: Date.now() } : s
      );
      return {
        ...state,
        steps: [...steps, newStep],
        activeStepIndex: steps.length,
        status: 'thinking',
      };
    }

    case 'STEP_UPDATE': {
      const steps = state.steps.map((s) =>
        s.id === action.id ? { ...s, detail: (s.detail ?? '') + action.detail } : s
      );
      return { ...state, steps };
    }

    case 'STEP_DONE': {
      const steps = state.steps.map((s) =>
        s.id === action.id
          ? {
              ...s,
              status: 'done' as ThinkingStepStatus,
              finishedAt: Date.now(),
              tokens: action.tokens ?? s.tokens,
            }
          : s
      );
      return { ...state, steps };
    }

    case 'STEP_ERROR': {
      const steps = state.steps.map((s) =>
        s.id === action.id
          ? {
              ...s,
              status: 'error' as ThinkingStepStatus,
              finishedAt: Date.now(),
              detail: action.error,
            }
          : s
      );
      return { ...state, steps, status: 'error', error: action.error };
    }

    case 'AGENT_STREAMING':
      return { ...state, status: 'streaming' };

    case 'AGENT_DONE':
      return {
        ...state,
        status: 'done',
        steps: state.steps.map((s) =>
          s.status === 'active'
            ? { ...s, status: 'done' as ThinkingStepStatus, finishedAt: Date.now() }
            : s
        ),
        activeStepIndex: -1,
      };

    case 'AGENT_ERROR':
      return { ...state, status: 'error', error: action.error };

    case 'TICK':
      return { ...state, elapsedMs: action.elapsedMs };

    case 'RESET':
      return { ...initialState };

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseAgentThinkingOptions {
  /** Base URL for the API (defaults to empty string = same origin) */
  apiBase?: string;
  /** WebSocket protocol to use, defaults to detecting from window.location */
  wsProtocol?: 'ws' | 'wss';
  /** Called whenever the final response text chunk arrives */
  onResponseChunk?: (chunk: string) => void;
  /** Called when thinking is fully complete */
  onComplete?: (steps: ThinkingStep[]) => void;
  /** Called on error */
  onError?: (error: string) => void;
}

export interface UseAgentThinkingReturn extends AgentThinkingState {
  /** Start a new agent reasoning session for the given message */
  startThinking: (conversationId: string, message: string) => void;
  /** Cancel the current thinking session */
  cancel: () => void;
  /** Reset to idle state */
  reset: () => void;
  /** Formatted elapsed time string e.g. "1.23s" */
  elapsedLabel: string;
}

export function useAgentThinking(
  options: UseAgentThinkingOptions = {}
): UseAgentThinkingReturn {
  const {
    apiBase = '',
    wsProtocol,
    onResponseChunk,
    onComplete,
    onError,
  } = options;

  const [state, dispatch] = useReducer(reducer, initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const startTimeRef = useRef<number>(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ------------------------------------------------------------------
  // Elapsed timer
  // ------------------------------------------------------------------

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    tickRef.current = setInterval(() => {
      dispatch({
        type: 'TICK',
        elapsedMs: Date.now() - startTimeRef.current,
      });
    }, 100);
  }, []);

  const stopTimer = useCallback(() => {
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  // ------------------------------------------------------------------
  // Cleanup on unmount
  // ------------------------------------------------------------------

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      stopTimer();
    };
  }, [stopTimer]);

  // ------------------------------------------------------------------
  // WebSocket message handler
  // ------------------------------------------------------------------

  const handleMessage = useCallback(
    (raw: string) => {
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(raw);
      } catch {
        return; // ignore malformed frames
      }

      const evtType = event['type'] as string;

      switch (evtType) {
        case 'agent.step.begin':
          dispatch({
            type: 'STEP_BEGIN',
            payload: {
              id: event['step_id'] as string,
              label: event['label'] as string,
              detail: event['detail'] as string | undefined,
              tool: event['tool'] as string | undefined,
              tokens: event['tokens'] as number | undefined,
              startedAt: Date.now(),
            },
          });
          break;

        case 'agent.step.update':
          dispatch({
            type: 'STEP_UPDATE',
            id: event['step_id'] as string,
            detail: event['detail'] as string,
          });
          break;

        case 'agent.step.done':
          dispatch({
            type: 'STEP_DONE',
            id: event['step_id'] as string,
            tokens: event['tokens'] as number | undefined,
          });
          break;

        case 'agent.step.error':
          dispatch({
            type: 'STEP_ERROR',
            id: event['step_id'] as string,
            error: event['error'] as string,
          });
          onError?.(event['error'] as string);
          stopTimer();
          break;

        case 'agent.response.chunk':
          dispatch({ type: 'AGENT_STREAMING' });
          onResponseChunk?.(event['chunk'] as string);
          break;

        case 'agent.done':
          dispatch({ type: 'AGENT_DONE' });
          stopTimer();
          onComplete?.(state.steps);
          wsRef.current?.close();
          break;

        case 'agent.error':
          dispatch({ type: 'AGENT_ERROR', error: event['error'] as string });
          onError?.(event['error'] as string);
          stopTimer();
          wsRef.current?.close();
          break;

        default:
          // Unknown event type — silently ignore for forward compatibility
          break;
      }
    },
    [onComplete, onError, onResponseChunk, state.steps, stopTimer]
  );

  // ------------------------------------------------------------------
  // Public API
  // ------------------------------------------------------------------

  const startThinking = useCallback(
    (conversationId: string, message: string) => {
      // Close any existing connection
      wsRef.current?.close();
      dispatch({ type: 'START' });
      startTimer();

      const protocol =
        wsProtocol ??
        (typeof window !== 'undefined' && window.location.protocol === 'https:'
          ? 'wss'
          : 'ws');

      const host =
        typeof window !== 'undefined'
          ? window.location.host
          : 'localhost:8000';

      const wsUrl = `${protocol}://${host}${apiBase}/ws/agent/${conversationId}/think`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify({ type: 'agent.message', content: message }));
        };

        ws.onmessage = (evt) => handleMessage(evt.data);

        ws.onerror = () => {
          dispatch({ type: 'AGENT_ERROR', error: 'WebSocket connection error' });
          stopTimer();
          onError?.('WebSocket connection error');
        };

        ws.onclose = (evt) => {
          if (!evt.wasClean && state.status === 'thinking') {
            dispatch({
              type: 'AGENT_ERROR',
              error: 'Connection closed unexpectedly',
            });
            stopTimer();
          }
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'WebSocket init failed';
        dispatch({ type: 'AGENT_ERROR', error: msg });
        stopTimer();
        onError?.(msg);
      }
    },
    [apiBase, handleMessage, onError, startTimer, state.status, stopTimer, wsProtocol]
  );

  const cancel = useCallback(() => {
    wsRef.current?.close();
    dispatch({ type: 'AGENT_DONE' });
    stopTimer();
  }, [stopTimer]);

  const reset = useCallback(() => {
    wsRef.current?.close();
    stopTimer();
    dispatch({ type: 'RESET' });
  }, [stopTimer]);

  const elapsedLabel =
    state.elapsedMs >= 1000
      ? `${(state.elapsedMs / 1000).toFixed(2)}s`
      : `${state.elapsedMs}ms`;

  return { ...state, startThinking, cancel, reset, elapsedLabel };
}
