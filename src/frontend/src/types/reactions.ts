/**
 * Type definitions for message reactions
 */

export type ReactionType =
  | 'thumbs_up'
  | 'thumbs_down'
  | 'heart'
  | 'laugh'
  | 'celebrate'
  | 'thinking';

export interface Reaction {
  /** Unique reaction ID */
  id: number;
  /** Message ID this reaction belongs to */
  messageId: number;
  /** User ID who created the reaction */
  userId: number;
  /** Type of reaction */
  type: ReactionType;
  /** When the reaction was created */
  createdAt: Date;
}

export interface ReactionCount {
  /** Reaction type */
  type: ReactionType;
  /** Number of users who reacted with this type */
  count: number;
  /** Whether the current user has this reaction */
  userReacted: boolean;
}

export interface ReactionUpdate {
  /** Message ID */
  messageId: number;
  /** Reaction type */
  type: ReactionType;
  /** Whether to add or remove the reaction */
  action: 'add' | 'remove';
}
