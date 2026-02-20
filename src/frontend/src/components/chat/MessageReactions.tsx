/**
 * Message Reactions Component
 * Allows users to react to messages with emojis
 */
import React, { useState, useCallback, useMemo } from 'react';
import { Reaction, ReactionType } from '../../types/reactions';
import '../../styles/chat-enhancements.css';

interface MessageReactionsProps {
  /** Message ID */
  messageId: number;
  /** Existing reactions on the message */
  reactions: Reaction[];
  /** Current user ID */
  currentUserId: number;
  /** Callback when user adds/removes a reaction */
  onReactionToggle: (messageId: number, reactionType: ReactionType) => void;
  /** Whether reactions are disabled */
  disabled?: boolean;
}

const AVAILABLE_REACTIONS: { type: ReactionType; emoji: string; label: string }[] = [
  { type: 'thumbs_up', emoji: '👍', label: 'Like' },
  { type: 'heart', emoji: '❤️', label: 'Love' },
  { type: 'laugh', emoji: '😂', label: 'Funny' },
  { type: 'celebrate', emoji: '🎉', label: 'Celebrate' },
  { type: 'thinking', emoji: '🤔', label: 'Thinking' },
  { type: 'thumbs_down', emoji: '👎', label: 'Dislike' },
];

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions,
  currentUserId,
  onReactionToggle,
  disabled = false,
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  // Aggregate reactions by type
  const aggregatedReactions = useMemo(() => {
    const reactionMap = new Map<ReactionType, { count: number; userReacted: boolean }>();

    reactions.forEach((reaction) => {
      const existing = reactionMap.get(reaction.type) || { count: 0, userReacted: false };
      reactionMap.set(reaction.type, {
        count: existing.count + 1,
        userReacted: existing.userReacted || reaction.userId === currentUserId,
      });
    });

    return reactionMap;
  }, [reactions, currentUserId]);

  const handleReactionClick = useCallback(
    (reactionType: ReactionType) => {
      if (disabled) return;

      setIsAnimating(true);
      onReactionToggle(messageId, reactionType);
      setShowPicker(false);

      // Reset animation state
      setTimeout(() => setIsAnimating(false), 300);
    },
    [messageId, onReactionToggle, disabled]
  );

  const togglePicker = useCallback(() => {
    if (!disabled) {
      setShowPicker((prev) => !prev);
    }
  }, [disabled]);

  return (
    <div className="message-reactions-container">
      {/* Display aggregated reactions */}
      {aggregatedReactions.size > 0 && (
        <div className="reactions-display">
          {AVAILABLE_REACTIONS.map(({ type, emoji }) => {
            const reaction = aggregatedReactions.get(type);
            if (!reaction) return null;

            return (
              <button
                key={type}
                className={`reaction-bubble ${
                  reaction.userReacted ? 'user-reacted' : ''
                } ${isAnimating ? 'animating' : ''}`}
                onClick={() => handleReactionClick(type)}
                disabled={disabled}
                aria-label={`${emoji} ${reaction.count}`}
                title={reaction.userReacted ? 'Remove reaction' : 'Add reaction'}
              >
                <span className="reaction-emoji">{emoji}</span>
                <span className="reaction-count">{reaction.count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Reaction picker button */}
      <div className="reaction-picker-wrapper">
        <button
          className={`reaction-add-button ${showPicker ? 'active' : ''}`}
          onClick={togglePicker}
          disabled={disabled}
          aria-label="Add reaction"
          aria-expanded={showPicker}
        >
          <span className="add-icon">😊</span>
          <span className="add-icon-plus">+</span>
        </button>

        {/* Reaction picker popup */}
        {showPicker && (
          <div className="reaction-picker" role="menu">
            {AVAILABLE_REACTIONS.map(({ type, emoji, label }) => (
              <button
                key={type}
                className="reaction-option"
                onClick={() => handleReactionClick(type)}
                role="menuitem"
                aria-label={label}
                title={label}
              >
                <span className="reaction-option-emoji">{emoji}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Click outside to close picker */}
      {showPicker && (
        <div
          className="reaction-picker-backdrop"
          onClick={() => setShowPicker(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

export default MessageReactions;
