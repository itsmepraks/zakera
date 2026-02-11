import React, { useState } from 'react';
import { MessageReactions } from './MessageReactions';
import './MessageBubble.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  reactions?: Array<{
    emoji: string;
    count: number;
    userReacted: boolean;
  }>;
}

interface MessageBubbleProps {
  message: Message;
  onReactionToggle: (messageId: string, emoji: string) => void;
  onCopy?: (content: string) => void;
  onEdit?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  showActions?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onReactionToggle,
  onCopy,
  onEdit,
  onDelete,
  showActions = true,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    if (onCopy) onCopy(message.content);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const isUser = message.role === 'user';

  return (
    <div className={`message-bubble-container ${isUser ? 'user-message' : 'assistant-message'}`}>
      {!isUser && (
        <div className="message-avatar">
          <span className="avatar-icon">AI</span>
        </div>
      )}

      <div className="message-content-wrapper">
        <div className="message-bubble">
          <div className="message-text">
            {message.content}
          </div>
          
          {showActions && (
            <div className="message-actions">
              <button
                className="action-button"
                onClick={handleCopy}
                aria-label="Copy message"
                title="Copy"
              >
                {copied ? (
                  <span className="icon">✓</span>
                ) : (
                  <span className="icon">📋</span>
                )}
              </button>
              
              {isUser && onEdit && (
                <button
                  className="action-button"
                  onClick={() => onEdit(message.id)}
                  aria-label="Edit message"
                  title="Edit"
                >
                  <span className="icon">✏️</span>
                </button>
              )}
              
              {onDelete && (
                <button
                  className="action-button delete-button"
                  onClick={() => onDelete(message.id)}
                  aria-label="Delete message"
                  title="Delete"
                >
                  <span className="icon">🗑️</span>
                </button>
              )}
            </div>
          )}
        </div>

        <div className="message-footer">
          <span className="message-time">{formatTime(message.timestamp)}</span>
          
          {message.reactions && message.reactions.length > 0 && (
            <MessageReactions
              messageId={message.id}
              reactions={message.reactions}
              onReactionToggle={onReactionToggle}
            />
          )}
        </div>
      </div>

      {isUser && (
        <div className="message-avatar user-avatar">
          <span className="avatar-icon">You</span>
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
