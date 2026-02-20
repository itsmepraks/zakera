/**
 * MessageReactions Component
 * 
 * Allows users to react to messages with emoji reactions.
 * Shows reaction counts and provides an emoji picker.
 */

import React, { useState, useRef, useEffect } from 'react';
import './MessageReactions.css';

interface Reaction {
  emoji: string;
  count: number;
  users: string[];
  userReacted: boolean;
}

interface MessageReactionsProps {
  messageId: string;
  reactions?: Reaction[];
  onReact?: (emoji: string) => void;
  onRemoveReaction?: (emoji: string) => void;
  className?: string;
}

const POPULAR_EMOJIS = ['👍', '❤️', '😄', '😮', '👎', '🎉', '😍', '🤔'];

export const MessageReactions: React.FC<MessageReactionsProps> = ({
  messageId,
  reactions = [],
  onReact,
  onRemoveReaction,
  className = ''
}) => {
  const [showPicker, setShowPicker] = useState(false);
  const [hoveredReaction, setHoveredReaction] = useState<string | null>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  // Close picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowPicker(false);
      }
    };

    if (showPicker) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showPicker]);

  const handleReactionClick = (emoji: string, userReacted: boolean) => {
    if (userReacted && onRemoveReaction) {
      onRemoveReaction(emoji);
    } else if (!userReacted && onReact) {
      onReact(emoji);
    }
    setShowPicker(false);
  };

  const handleAddReactionClick = (emoji: string) => {
    if (onReact) {
      onReact(emoji);
    }
    setShowPicker(false);
  };

  return (
    <div className={`message-reactions ${className}`}>
      {/* Existing Reactions */}
      <div className="reactions-list">
        {reactions.map((reaction) => (
          <button
            key={reaction.emoji}
            className={`reaction-bubble ${
              reaction.userReacted ? 'user-reacted' : ''
            }`}
            onClick={() => handleReactionClick(reaction.emoji, reaction.userReacted)}
            onMouseEnter={() => setHoveredReaction(reaction.emoji)}
            onMouseLeave={() => setHoveredReaction(null)}
            aria-label={`${reaction.emoji} reaction, ${reaction.count} ${reaction.count === 1 ? 'person' : 'people'}`}
          >
            <span className="reaction-emoji">{reaction.emoji}</span>
            <span className="reaction-count">{reaction.count}</span>
            
            {/* Tooltip */}
            {hoveredReaction === reaction.emoji && (
              <div className="reaction-tooltip">
                {reaction.users.slice(0, 3).join(', ')}
                {reaction.users.length > 3 && ` and ${reaction.users.length - 3} more`}
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Add Reaction Button */}
      <div className="add-reaction-container" ref={pickerRef}>
        <button
          className="add-reaction-btn"
          onClick={() => setShowPicker(!showPicker)}
          aria-label="Add reaction"
          aria-expanded={showPicker}
        >
          <span className="add-icon">➕</span>
          <span className="add-emoji">😊</span>
        </button>

        {/* Emoji Picker */}
        {showPicker && (
          <div className="emoji-picker" role="dialog" aria-label="Emoji picker">
            <div className="emoji-picker-header">
              <span>React with an emoji</span>
            </div>
            <div className="emoji-picker-grid">
              {POPULAR_EMOJIS.map((emoji) => (
                <button
                  key={emoji}
                  className="emoji-option"
                  onClick={() => handleAddReactionClick(emoji)}
                  aria-label={`React with ${emoji}`}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageReactions;
