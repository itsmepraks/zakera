/**
 * useTypingIndicator
 *
 * A React hook that tracks typing presence for a conversation over WebSocket.
 *
 * Features:
 *  - Listens for "typing_start" and "typing_stop" events from the server.
 *  - Exposes `sendTypingEvent(isTyping)` so the local user can broadcast
 *    their own typing status.
 *  - Automatically sends a "typing_stop" event after 2 000 ms of inactivity
 *    (debounced via useEffect cleanup).
 *  - Cleans up listeners and pending timers on unmount or conversation change.
 *
 * Usage:
 *   const { isTyping, typingUsers, sendTypingEvent } = useTypingIndicator(
 *     wsRef,
 *     conversationId,
 *   );
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Shape of a WebSocket typing event sent/received over the wire. */
interface TypingEvent {
  type: 'typing_start' | 'typing_stop';
  conversationId: string;
  userId: string;
  username?: string;
}

/** Return value of the hook. */
export interface UseTypingIndicatorReturn {
  /** True when at least one remote user is currently typing. */
  isTyping: boolean;
  /** Display names (or user IDs) of everyone currently typing. */
  typingUsers: string[];
  /**
   * Call with `true` when the local user starts typing and `false` when they
   * stop.  The hook debounces the stop event internally so callers can simply
   * invoke this on every keystroke.
   */
  sendTypingEvent: (typing: boolean) => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Milliseconds to wait before auto-sending a "typing_stop" event. */
const STOP_DEBOUNCE_MS = 2_000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Manage real-time typing indicators for a single conversation.
 *
 * @param wsRef          - A React ref whose `.current` holds the active
 *                         `WebSocket` instance (or `null` when disconnected).
 * @param conversationId - The ID of the conversation to scope events to.
 *                         The hook re-initialises whenever this changes.
 * @param currentUserId  - The local user's ID, used to filter out self-echo.
 *                         Defaults to an empty string (no filtering).
 */
export function useTypingIndicator(
  wsRef: React.RefObject<WebSocket | null>,
  conversationId: string,
  currentUserId = '',
): UseTypingIndicatorReturn {
  // Set of user identifiers currently typing (userId → display label).
  const [typingUsers, setTypingUsers] = useState<string[]>([]);

  // Derived convenience flag.
  const isTyping = typingUsers.length > 0;

  // Ref for the debounce timer so we can cancel it across renders.
  const stopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track whether we have already sent a "typing_start" to avoid redundant
  // messages on every single keystroke.
  const isBroadcastingRef = useRef(false);

  // -------------------------------------------------------------------------
  // Helper — send a raw event over the WebSocket if it is open.
  // -------------------------------------------------------------------------
  const sendRaw = useCallback(
    (eventType: TypingEvent['type']) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;

      const payload: TypingEvent = {
        type: eventType,
        conversationId,
        userId: currentUserId,
      };

      ws.send(JSON.stringify(payload));
    },
    [wsRef, conversationId, currentUserId],
  );

  // -------------------------------------------------------------------------
  // Public API — sendTypingEvent
  // -------------------------------------------------------------------------
  const sendTypingEvent = useCallback(
    (typing: boolean) => {
      if (typing) {
        // Only broadcast "typing_start" if we are not already flagged as typing.
        if (!isBroadcastingRef.current) {
          sendRaw('typing_start');
          isBroadcastingRef.current = true;
        }

        // Reset the auto-stop debounce timer on every keystroke.
        if (stopTimerRef.current !== null) {
          clearTimeout(stopTimerRef.current);
        }

        stopTimerRef.current = setTimeout(() => {
          sendRaw('typing_stop');
          isBroadcastingRef.current = false;
          stopTimerRef.current = null;
        }, STOP_DEBOUNCE_MS);
      } else {
        // Explicit stop — cancel any pending debounce and send immediately.
        if (stopTimerRef.current !== null) {
          clearTimeout(stopTimerRef.current);
          stopTimerRef.current = null;
        }

        if (isBroadcastingRef.current) {
          sendRaw('typing_stop');
          isBroadcastingRef.current = false;
        }
      }
    },
    [sendRaw],
  );

  // -------------------------------------------------------------------------
  // WebSocket message listener
  // -------------------------------------------------------------------------
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;

    const handleMessage = (event: MessageEvent) => {
      let data: unknown;

      try {
        data = JSON.parse(event.data as string);
      } catch {
        // Not JSON — ignore.
        return;
      }

      const payload = data as Partial<TypingEvent>;

      // Only handle typing events for the current conversation.
      if (
        payload.conversationId !== conversationId ||
        (payload.type !== 'typing_start' && payload.type !== 'typing_stop')
      ) {
        return;
      }

      const senderId = payload.userId ?? '';

      // Filter out events echoed back from the local user.
      if (currentUserId && senderId === currentUserId) return;

      const displayName = payload.username ?? senderId;

      if (payload.type === 'typing_start') {
        setTypingUsers((prev) =>
          prev.includes(displayName) ? prev : [...prev, displayName],
        );
      } else {
        setTypingUsers((prev) => prev.filter((u) => u !== displayName));
      }
    };

    ws.addEventListener('message', handleMessage);

    return () => {
      ws.removeEventListener('message', handleMessage);
    };
  }, [wsRef, conversationId, currentUserId]);

  // -------------------------------------------------------------------------
  // Reset state when the active conversation changes.
  // -------------------------------------------------------------------------
  useEffect(() => {
    setTypingUsers([]);
    isBroadcastingRef.current = false;

    // Cancel any pending stop timer from the previous conversation.
    if (stopTimerRef.current !== null) {
      clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }

    // Send an explicit stop in case we were mid-broadcast when the user
    // switched conversations.
    sendRaw('typing_stop');
  }, [conversationId, sendRaw]);

  // -------------------------------------------------------------------------
  // Cleanup on unmount.
  // -------------------------------------------------------------------------
  useEffect(() => {
    return () => {
      if (stopTimerRef.current !== null) {
        clearTimeout(stopTimerRef.current);
      }
      if (isBroadcastingRef.current) {
        sendRaw('typing_stop');
        isBroadcastingRef.current = false;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { isTyping, typingUsers, sendTypingEvent };
}
