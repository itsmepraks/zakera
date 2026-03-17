/**
 * useReactions — custom hook for managing per-message emoji reactions.
 *
 * Design goals
 * ------------
 * 1. Optimistic updates: the local state changes instantly on toggle so
 *    the UI never waits for the server round-trip to feel responsive.
 * 2. Automatic rollback: if the API call fails the optimistic change is
 *    undone and a console warning is emitted (callers can surface this
 *    via the syncStatus map).
 * 3. Conversation-scoped: a single hook instance manages reactions for
 *    every message in one conversation, keyed by messageId.
 * 4. SSR-safe: no direct DOM access; localStorage is only read inside
 *    callbacks, not at module scope.
 *
 * API contract
 * ------------
 * PATCH /api/v1/conversations/{conversationId}/messages/{messageId}/reactions
 * Body:  { emoji: string, action: 'add' | 'remove' }
 * Auth:  Bearer token from localStorage('token')
 * 2xx → success; any other status → rollback optimistic state.
 *
 * Usage
 * -----
 * ```tsx
 * const {
 *   getReactions,
 *   toggleReaction,
 *   addReaction,
 *   syncStatus,
 *   initReactions,
 * } = useReactions(conversationId);
 *
 * // Seed reactions when the conversation loads:
 * useEffect(() => {
 *   initReactions(serverData.messages.map(m => ({ messageId: m.id, reactions: m.reactions })));
 * }, [serverData]);
 *
 * // Inside a message component:
 * <MessageReactions
 *   messageId={message.id}
 *   reactions={getReactions(message.id)}
 *   onReactionToggle={toggleReaction}
 *   onAddReaction={addReaction}
 * />
 * ```
 */

import { useCallback, useReducer, useRef } from 'react';
import type {
  EmojiString,
  ReactionMap,
  ReactionSyncStatus,
  UseReactionsReturn,
} from '../types/reactions';

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

interface ReactionsState {
  /** Per-message reaction maps. Missing key → treat as empty map. */
  reactions: Record<string, ReactionMap>;
  /** Per-message sync status for showing loading / error indicators. */
  syncStatus: Record<string, ReactionSyncStatus>;
}

// ---------------------------------------------------------------------------
// Reducer actions
// ---------------------------------------------------------------------------

type Action =
  | {
      type: 'INIT_REACTIONS';
      payload: Array<{ messageId: string; reactions: ReactionMap }>;
    }
  | {
      type: 'OPTIMISTIC_TOGGLE';
      payload: { messageId: string; emoji: EmojiString };
    }
  | {
      type: 'ROLLBACK_TOGGLE';
      payload: {
        messageId: string;
        previousReactions: ReactionMap;
      };
    }
  | {
      type: 'SET_SYNC_STATUS';
      payload: { messageId: string; status: ReactionSyncStatus };
    };

// ---------------------------------------------------------------------------
// Pure reducer
// ---------------------------------------------------------------------------

function reactionsReducer(
  state: ReactionsState,
  action: Action,
): ReactionsState {
  switch (action.type) {
    case 'INIT_REACTIONS': {
      const next = { ...state.reactions };
      for (const { messageId, reactions } of action.payload) {
        next[messageId] = reactions;
      }
      return { ...state, reactions: next };
    }

    case 'OPTIMISTIC_TOGGLE': {
      const { messageId, emoji } = action.payload;
      const current = state.reactions[messageId] ?? {};
      const entry = current[emoji];

      let updatedMap: ReactionMap;
      if (!entry) {
        // New emoji — add with count 1, userReacted = true
        updatedMap = {
          ...current,
          [emoji]: { count: 1, userReacted: true },
        };
      } else if (entry.userReacted) {
        // User removing their reaction
        const newCount = entry.count - 1;
        if (newCount <= 0) {
          // Drop the key entirely when count hits 0
          const { [emoji]: _removed, ...rest } = current;
          updatedMap = rest;
        } else {
          updatedMap = {
            ...current,
            [emoji]: { count: newCount, userReacted: false },
          };
        }
      } else {
        // Existing emoji, user adding
        updatedMap = {
          ...current,
          [emoji]: { count: entry.count + 1, userReacted: true },
        };
      }

      return {
        ...state,
        reactions: { ...state.reactions, [messageId]: updatedMap },
      };
    }

    case 'ROLLBACK_TOGGLE': {
      const { messageId, previousReactions } = action.payload;
      return {
        ...state,
        reactions: { ...state.reactions, [messageId]: previousReactions },
      };
    }

    case 'SET_SYNC_STATUS': {
      const { messageId, status } = action.payload;
      return {
        ...state,
        syncStatus: { ...state.syncStatus, [messageId]: status },
      };
    }

    default:
      return state;
  }
}

const INITIAL_STATE: ReactionsState = { reactions: {}, syncStatus: {} };

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Manages emoji reaction state for all messages in a single conversation.
 *
 * @param conversationId - UUID of the conversation; used to build API paths.
 */
export function useReactions(conversationId: string): UseReactionsReturn {
  const [state, dispatch] = useReducer(reactionsReducer, INITIAL_STATE);

  /**
   * Keep a ref to the current reactions so async rollback callbacks can
   * read the *pre-optimistic* snapshot without closing over stale state.
   */
  const reactionsRef = useRef(state.reactions);
  reactionsRef.current = state.reactions;

  // -------------------------------------------------------------------------
  // getReactions
  // -------------------------------------------------------------------------

  const getReactions = useCallback(
    (messageId: string): ReactionMap =>
      reactionsRef.current[messageId] ?? {},
    [],
  );

  // -------------------------------------------------------------------------
  // initReactions  (called once when conversation data loads)
  // -------------------------------------------------------------------------

  const initReactions = useCallback(
    (entries: Array<{ messageId: string; reactions: ReactionMap }>) => {
      dispatch({ type: 'INIT_REACTIONS', payload: entries });
    },
    [],
  );

  // -------------------------------------------------------------------------
  // _syncReaction  (shared async logic for toggle + add)
  // -------------------------------------------------------------------------

  const _syncReaction = useCallback(
    async (
      messageId: string,
      emoji: EmojiString,
      action: 'add' | 'remove',
      snapshotBeforeOptimistic: ReactionMap,
    ): Promise<void> => {
      dispatch({
        type: 'SET_SYNC_STATUS',
        payload: { messageId, status: 'syncing' },
      });

      try {
        const token =
          typeof window !== 'undefined'
            ? window.localStorage.getItem('token')
            : null;

        const res = await fetch(
          `/api/v1/conversations/${conversationId}/messages/${messageId}/reactions`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ emoji, action }),
          },
        );

        if (!res.ok) {
          throw new Error(`Reaction sync failed: HTTP ${res.status}`);
        }

        dispatch({
          type: 'SET_SYNC_STATUS',
          payload: { messageId, status: 'idle' },
        });
      } catch (err) {
        console.warn('[useReactions] Rolling back optimistic update:', err);

        // Revert to the snapshot taken before the optimistic update
        dispatch({
          type: 'ROLLBACK_TOGGLE',
          payload: { messageId, previousReactions: snapshotBeforeOptimistic },
        });
        dispatch({
          type: 'SET_SYNC_STATUS',
          payload: { messageId, status: 'error' },
        });
      }
    },
    [conversationId],
  );

  // -------------------------------------------------------------------------
  // toggleReaction  (flip existing reaction on/off)
  // -------------------------------------------------------------------------

  const toggleReaction = useCallback(
    (messageId: string, emoji: EmojiString): void => {
      // Snapshot the pre-optimistic state for potential rollback
      const snapshot = reactionsRef.current[messageId] ?? {};
      const wasReacted = snapshot[emoji]?.userReacted ?? false;
      const apiAction: 'add' | 'remove' = wasReacted ? 'remove' : 'add';

      // Optimistic update — fires synchronously, makes UI instant
      dispatch({ type: 'OPTIMISTIC_TOGGLE', payload: { messageId, emoji } });

      // Async sync — may roll back if it fails
      _syncReaction(messageId, emoji, apiAction, snapshot).catch(() => {
        // Errors are already handled inside _syncReaction; this catches
        // any unexpected promise rejection to prevent unhandled rejections.
      });
    },
    [_syncReaction],
  );

  // -------------------------------------------------------------------------
  // addReaction  (add a *new* emoji from the picker; always action='add')
  // -------------------------------------------------------------------------

  const addReaction = useCallback(
    (messageId: string, emoji: EmojiString): void => {
      const snapshot = reactionsRef.current[messageId] ?? {};

      // If the user already reacted with this emoji treat it as a no-op
      // (the picker shouldn't show already-reacted emojis as selectable,
      //  but guard defensively here).
      if (snapshot[emoji]?.userReacted) return;

      dispatch({ type: 'OPTIMISTIC_TOGGLE', payload: { messageId, emoji } });

      _syncReaction(messageId, emoji, 'add', snapshot).catch(() => {});
    },
    [_syncReaction],
  );

  // -------------------------------------------------------------------------
  // Return value
  // -------------------------------------------------------------------------

  return {
    getReactions,
    toggleReaction,
    addReaction,
    syncStatus: state.syncStatus,
    initReactions,
  };
}

export default useReactions;
