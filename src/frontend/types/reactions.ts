/**
 * Shared TypeScript types for the MessageReactions system.
 *
 * Consumed by:
 *   - src/frontend/hooks/useReactions.ts
 *   - src/frontend/components/MessageReactions/MessageReactions.tsx
 *   - src/frontend/components/MessageCard.tsx
 */

// ---------------------------------------------------------------------------
// Core domain types
// ---------------------------------------------------------------------------

/** A single emoji character string, e.g. "👍" or "❤️" */
export type EmojiString = string;

/** Reaction state for one emoji on one message. */
export interface ReactionEntry {
  /** Total number of users who have reacted with this emoji. */
  count: number;
  /** Whether the authenticated user has already reacted. */
  userReacted: boolean;
}

/**
 * Full reaction map for a single message.
 * Keys are emoji characters; values are ReactionEntry objects.
 *
 * @example
 * const reactions: ReactionMap = {
 *   "👍": { count: 3, userReacted: true },
 *   "❤️": { count: 1, userReacted: false },
 * };
 */
export type ReactionMap = Record<EmojiString, ReactionEntry>;

/** Callback signature for toggling / adding a reaction. */
export type ReactionToggleHandler = (
  messageId: string,
  emoji: EmojiString,
) => void;

// ---------------------------------------------------------------------------
// Sync / network status
// ---------------------------------------------------------------------------

/**
 * Tracks the in-flight state of a reaction PATCH for one message.
 *
 * - idle    → no pending request
 * - syncing → PATCH in flight (optimistic update applied)
 * - error   → last PATCH failed; optimistic update was rolled back
 */
export type ReactionSyncStatus = 'idle' | 'syncing' | 'error';

// ---------------------------------------------------------------------------
// API contract
// ---------------------------------------------------------------------------

/** Body sent to PATCH /api/v1/conversations/{id}/messages/{msgId}/reactions */
export interface ReactionApiPayload {
  emoji: EmojiString;
  action: 'add' | 'remove';
}

// ---------------------------------------------------------------------------
// Hook return type
// ---------------------------------------------------------------------------

/**
 * Return shape of the useReactions hook.
 *
 * @see src/frontend/hooks/useReactions.ts
 */
export interface UseReactionsReturn {
  /**
   * Returns the current ReactionMap for a given message.
   * Returns an empty object for messages that have no reactions yet.
   */
  getReactions: (messageId: string) => ReactionMap;

  /**
   * Toggle the authenticated user's reaction to an emoji.
   * Applies an optimistic update immediately and syncs with the API
   * in the background; rolls back on failure.
   */
  toggleReaction: ReactionToggleHandler;

  /**
   * Add a new emoji reaction selected from the picker.
   * No-op if the user has already reacted with this emoji.
   */
  addReaction: ReactionToggleHandler;

  /**
   * Per-message sync status map.
   * Keys are messageIds; values are ReactionSyncStatus.
   * Missing key ↔ 'idle'.
   */
  syncStatus: Record<string, ReactionSyncStatus>;

  /**
   * Seed initial reaction state from server data (call once on load).
   * Accepts an array so all messages can be initialised in one dispatch.
   */
  initReactions: (
    entries: Array<{ messageId: string; reactions: ReactionMap }>,
  ) => void;
}
