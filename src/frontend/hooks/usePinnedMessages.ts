/**
 * usePinnedMessages
 *
 * Manages pinned-message state for a single conversation.
 * Pins are persisted to localStorage so they survive page refreshes
 * and navigation between conversations.
 *
 * @example
 * ```tsx
 * const { pinnedMessages, togglePin, isPinned } = usePinnedMessages(
 *   conversationId,
 *   allMessages,
 * );
 * ```
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

/** Maximum number of pins per conversation to prevent unbounded storage growth. */
export const MAX_PINS = 20;

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  /** ISO-8601 timestamp */
  timestamp?: string;
  /** Optional metadata blob passed through from the API */
  metadata?: Record<string, unknown>;
}

export interface UsePinnedMessagesReturn {
  /** Ordered set of currently-pinned message IDs. */
  pinnedIds: Set<string>;
  /** Full Message objects for each pinned ID (in pin order). */
  pinnedMessages: Message[];
  /** Pin a message by ID. No-op if already pinned or cap reached. */
  pinMessage: (id: string) => void;
  /** Unpin a message by ID. No-op if not pinned. */
  unpinMessage: (id: string) => void;
  /** Toggle the pin state of a message. */
  togglePin: (id: string) => void;
  /** Remove all pins for this conversation. */
  clearAllPins: () => void;
  /** Returns true if the given message ID is currently pinned. */
  isPinned: (id: string) => boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function storageKey(conversationId: string): string {
  return `zakera:pins:${conversationId}`;
}

function loadPins(conversationId: string): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(storageKey(conversationId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is string => typeof v === 'string');
  } catch {
    return [];
  }
}

function savePins(conversationId: string, ids: string[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(storageKey(conversationId), JSON.stringify(ids));
  } catch {
    // Silently ignore storage quota / private-browsing errors.
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePinnedMessages(
  conversationId: string,
  allMessages: Message[],
): UsePinnedMessagesReturn {
  const [pinnedOrder, setPinnedOrder] = useState<string[]>(() =>
    loadPins(conversationId),
  );

  // Re-load when conversationId changes (user switches to a different chat).
  useEffect(() => {
    setPinnedOrder(loadPins(conversationId));
  }, [conversationId]);

  // Persist whenever the pin list changes.
  useEffect(() => {
    savePins(conversationId, pinnedOrder);
  }, [conversationId, pinnedOrder]);

  const pinnedIds = useMemo(() => new Set(pinnedOrder), [pinnedOrder]);

  const pinnedMessages = useMemo(() => {
    const msgMap = new Map(allMessages.map((m) => [m.id, m]));
    return pinnedOrder
      .map((id) => msgMap.get(id))
      .filter((m): m is Message => m !== undefined);
  }, [pinnedOrder, allMessages]);

  const pinMessage = useCallback(
    (id: string) => {
      setPinnedOrder((prev) => {
        if (prev.includes(id)) return prev;
        if (prev.length >= MAX_PINS) {
          console.warn(
            `[usePinnedMessages] Pin cap (${MAX_PINS}) reached for conversation ` +
              `${conversationId}. Unpin an existing message before adding more.`,
          );
          return prev;
        }
        return [...prev, id];
      });
    },
    [conversationId],
  );

  const unpinMessage = useCallback((id: string) => {
    setPinnedOrder((prev) => prev.filter((pid) => pid !== id));
  }, []);

  const togglePin = useCallback(
    (id: string) => {
      if (pinnedIds.has(id)) {
        unpinMessage(id);
      } else {
        pinMessage(id);
      }
    },
    [pinnedIds, pinMessage, unpinMessage],
  );

  const clearAllPins = useCallback(() => {
    setPinnedOrder([]);
  }, []);

  const isPinned = useCallback(
    (id: string) => pinnedIds.has(id),
    [pinnedIds],
  );

  return {
    pinnedIds,
    pinnedMessages,
    pinMessage,
    unpinMessage,
    togglePin,
    clearAllPins,
    isPinned,
  };
}
