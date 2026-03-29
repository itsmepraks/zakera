import { useCallback, useEffect, useRef, useState } from "react";

interface TypingEvent {
  type: "typing_start" | "typing_stop";
  conversationId: string;
  userId: string;
  userName?: string;
}

interface UseTypingIndicatorOptions {
  /** Milliseconds of inactivity before a "typing_stop" is auto-sent. */
  debounceMs?: number;
}

interface UseTypingIndicatorReturn {
  /** Whether any remote participant is currently typing. */
  isTyping: boolean;
  /** Display names / IDs of users currently typing. */
  typingUsers: string[];
  /**
   * Call this whenever the local user's input changes.
   * Pass `true` when they start typing, `false` when they stop.
   */
  sendTypingEvent: (typing: boolean) => void;
}

/**
 * useTypingIndicator
 *
 * Manages real-time typing presence over an existing WebSocket connection.
 * Listens for `typing_start` / `typing_stop` events from remote participants
 * and broadcasts the local user's own typing status with automatic debouncing.
 *
 * @example
 * ```tsx
 * const wsRef = useRef<WebSocket | null>(null);
 * const { isTyping, typingUsers, sendTypingEvent } = useTypingIndicator(wsRef, conversationId);
 *
 * <input onChange={() => sendTypingEvent(true)} onBlur={() => sendTypingEvent(false)} />
 * {isTyping && <TypingBubble users={typingUsers} />}
 * ```
 */
export function useTypingIndicator(
  wsRef: React.RefObject<WebSocket | null>,
  conversationId: string,
  { debounceMs = 2000 }: UseTypingIndicatorOptions = {}
): UseTypingIndicatorReturn {
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isLocallyTyping = useRef(false);

  // ── Handle incoming WebSocket messages ─────────────────────────────────────
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws) return;

    const handleMessage = (event: MessageEvent) => {
      let data: TypingEvent;
      try {
        data = JSON.parse(event.data as string) as TypingEvent;
      } catch {
        return;
      }

      if (data.conversationId !== conversationId) return;
      if (data.type !== "typing_start" && data.type !== "typing_stop") return;

      const identifier = data.userName ?? data.userId;

      setTypingUsers((prev) => {
        if (data.type === "typing_start") {
          return prev.includes(identifier) ? prev : [...prev, identifier];
        }
        // typing_stop
        return prev.filter((u) => u !== identifier);
      });
    };

    ws.addEventListener("message", handleMessage);
    return () => ws.removeEventListener("message", handleMessage);
  }, [wsRef, conversationId]);

  // ── Send local typing events ────────────────────────────────────────────────
  const sendTypingEvent = useCallback(
    (typing: boolean) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;

      // Clear any pending auto-stop timer.
      if (debounceTimer.current !== null) {
        clearTimeout(debounceTimer.current);
        debounceTimer.current = null;
      }

      if (typing) {
        if (!isLocallyTyping.current) {
          isLocallyTyping.current = true;
          ws.send(
            JSON.stringify({ type: "typing_start", conversationId })
          );
        }

        // Auto-stop after debounceMs of no further calls.
        debounceTimer.current = setTimeout(() => {
          isLocallyTyping.current = false;
          ws?.send(
            JSON.stringify({ type: "typing_stop", conversationId })
          );
        }, debounceMs);
      } else {
        if (isLocallyTyping.current) {
          isLocallyTyping.current = false;
          ws.send(
            JSON.stringify({ type: "typing_stop", conversationId })
          );
        }
      }
    },
    [wsRef, conversationId, debounceMs]
  );

  // ── Cleanup on unmount ──────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (debounceTimer.current !== null) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, []);

  return {
    isTyping: typingUsers.length > 0,
    typingUsers,
    sendTypingEvent,
  };
}

export default useTypingIndicator;
