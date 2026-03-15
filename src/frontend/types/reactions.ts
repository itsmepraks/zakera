/**
 * Shared TypeScript types for the MessageReactions system.
 */

/** A single emoji character, e.g. "👍" */
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
