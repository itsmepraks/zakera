import React, { useState } from 'react';
import './MessageReactions.css';

interface Reaction {
  emoji: string;
  count: number;
  users: string[];
  reacted: boolean;
}

interface MessageReactionsProps {
  messageId: string;
  reactions?: Reaction[];
  onReact?: (messageId: string, emoji: string) => void;
}

const AVAILABLE_REACTIONS = ['👍', '❤️', '😂', '🤔', '👎', '🎉'];

/**
 * Message reactions component with emoji support.
 * Allows users to react to messages with quick emoji reactions.
 */
export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions = [],
  onReact
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [hoveredReaction, setHoveredReaction] = useState<string | null>(null);

  const handleReactionClick = (emoji: string) => {
    if (onReact) {
      onReact(messageId, emoji);
    }
    setShowPicker(false);
  };

  const getReactionTooltip = (reaction: Reaction) => {
    if (reaction.users.length === 0) return '';
    if (reaction.users.length === 1) return reaction.users[0];
    if (reaction.users.length === 2) {
      return `${reaction.users[0]} and ${reaction.users[1]}`;
    }
    return `${reaction.users[0]}, ${reaction.users[1]} and ${reaction.users.length - 2} others`;
  };

  return (
    <div className="message-reactions">
      {/* Existing reactions */}
      {reactions.length > 0 && (
        <div className="reactions-list">
          {reactions.map((reaction, index) => (
            <button
              key={`${reaction.emoji}-${index}`}
              className={`reaction-badge ${
                reaction.reacted ? 'reacted' : ''
              }`}
              onClick={() => handleReactionClick(reaction.emoji)}
              onMouseEnter={() => setHoveredReaction(reaction.emoji)}
              onMouseLeave={() => setHoveredReaction(null)}
              title={getReactionTooltip(reaction)}
              aria-label={`React with ${reaction.emoji}`}
            >
              <span className="reaction-emoji">{reaction.emoji}</span>
              <span className="reaction-count">{reaction.count}</span>
              
              {/* Tooltip */}
              {hoveredReaction === reaction.emoji && reaction.users.length > 0 && (
                <div className="reaction-tooltip">
                  {getReactionTooltip(reaction)}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Add reaction button */}
      <div className="reaction-picker-container">
        <button
          className="add-reaction-btn"
          onClick={() => setShowPicker(!showPicker)}
          aria-label="Add reaction"
          aria-expanded={showPicker}
        >
          <span className="plus-icon">+</span>
          <span className="emoji-icon">😊</span>
        </button>

        {/* Reaction picker */}
        {showPicker && (
          <div className="reaction-picker" role="menu">
            {AVAILABLE_REACTIONS.map((emoji) => (
              <button
                key={emoji}
                className="reaction-option"
                onClick={() => handleReactionClick(emoji)}
                role="menuitem"
                aria-label={`React with ${emoji}`}
              >
                {emoji}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageReactions;