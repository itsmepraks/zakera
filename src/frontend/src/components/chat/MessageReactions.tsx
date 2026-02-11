import React, { useState } from 'react';
import './MessageReactions.css';

interface Reaction {
  emoji: string;
  count: number;
  userReacted: boolean;
}

interface MessageReactionsProps {
  messageId: string;
  reactions: Reaction[];
  onReactionToggle: (messageId: string, emoji: string) => void;
  onReactionAdd?: (messageId: string) => void;
}

const QUICK_REACTIONS = ['👍', '❤️', '😂', '🎉', '🤔', '👏'];

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions,
  onReactionToggle,
  onReactionAdd,
}) => {
  const [showPicker, setShowPicker] = useState(false);

  const handleReactionClick = (emoji: string) => {
    onReactionToggle(messageId, emoji);
  };

  const handleAddClick = () => {
    setShowPicker(!showPicker);
  };

  return (
    <div className="message-reactions">
      <div className="reactions-list">
        {reactions.map((reaction, index) => (
          <button
            key={`${reaction.emoji}-${index}`}
            className={`reaction-badge ${
              reaction.userReacted ? 'user-reacted' : ''
            }`}
            onClick={() => handleReactionClick(reaction.emoji)}
            aria-label={`React with ${reaction.emoji}`}
          >
            <span className="reaction-emoji">{reaction.emoji}</span>
            {reaction.count > 1 && (
              <span className="reaction-count">{reaction.count}</span>
            )}
          </button>
        ))}
        
        <button
          className="reaction-add-button"
          onClick={handleAddClick}
          aria-label="Add reaction"
        >
          <span className="add-icon">+</span>
        </button>
      </div>

      {showPicker && (
        <div className="reaction-picker">
          {QUICK_REACTIONS.map((emoji) => (
            <button
              key={emoji}
              className="picker-emoji"
              onClick={() => {
                handleReactionClick(emoji);
                setShowPicker(false);
              }}
              aria-label={`React with ${emoji}`}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default MessageReactions;
