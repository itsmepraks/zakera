/**
 * TypeScript type definitions for message reactions and feedback
 */

export type ReactionType =
  | 'thumbs_up'
  | 'thumbs_down'
  | 'heart'
  | 'fire'
  | 'thinking'
  | 'check'
  | 'star'
  | 'celebrate';

export interface Reaction {
  id: string;
  message_id: string;
  user_id: string;
  reaction_type: ReactionType;
  created_at: string;
}

export interface ReactionCount {
  type: ReactionType;
  count: number;
  user_reacted: boolean;
}

export interface MessageFeedback {
  id: string;
  message_id: string;
  user_id: string;
  feedback_type: 'positive' | 'negative';
  feedback_text?: string;
  created_at: string;
}

export const REACTION_EMOJIS: Record<ReactionType, string> = {
  thumbs_up: '👍',
  thumbs_down: '👎',
  heart: '❤️',
  fire: '🔥',
  thinking: '🤔',
  check: '✅',
  star: '⭐',
  celebrate: '🎉',
};

export const REACTION_LABELS: Record<ReactionType, string> = {
  thumbs_up: 'Helpful',
  thumbs_down: 'Not Helpful',
  heart: 'Love it',
  fire: 'Amazing',
  thinking: 'Interesting',
  check: 'Correct',
  star: 'Favorite',
  celebrate: 'Excellent',
};

export const REACTION_COLORS: Record<ReactionType, string> = {
  thumbs_up: '#22c55e',
  thumbs_down: '#ef4444',
  heart: '#ec4899',
  fire: '#f97316',
  thinking: '#8b5cf6',
  check: '#10b981',
  star: '#eab308',
  celebrate: '#06b6d4',
};
