/**
 * Enhanced ChatMessage Component
 * 
 * Displays a single chat message with animations, reactions, and actions.
 * Supports markdown rendering, code highlighting, and rich media.
 */

import React, { useState } from 'react';
import MessageReactions from './MessageReactions';
import './ChatMessage.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  reactions?: Array<{
    emoji: string;
    count: number;
    users: string[];
    userReacted: boolean;
  }>;
  isStreaming?: boolean;
  metadata?: {
    model?: string;
    tokens?: number;
    cost?: number;
  };
}

interface ChatMessageProps {
  message: Message;
  onReact?: (messageId: string, emoji: string) => void;
  onRemoveReaction?: (messageId: string, emoji: string) => void;
  onCopy?: (content: string) => void;
  onEdit?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  showActions?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onReact,
  onRemoveReaction,
  onCopy,
  onEdit,
  onDelete,
  showActions = true
}) => {
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const [copied, setCopied] = useState(false);

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  };

  const handleCopy = () => {
    if (onCopy) {
      onCopy(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div 
      className={`chat-message ${message.role}-message ${
        message.isStreaming ? 'streaming' : ''
      }`}
      data-message-id={message.id}
    >
      {!isSystem && (
        <div className="message-avatar">
          {isUser ? (
            <span className="avatar-user">👤</span>
          ) : (
            <span className="avatar-ai">🤖</span>
          )}
        </div>
      )}
      
      <div className="message-content-wrapper">
        <div 
          className="message-bubble"
          onMouseEnter={() => setShowActionsMenu(true)}
          onMouseLeave={() => setShowActionsMenu(false)}
        >
          <div className="message-header">
            <span className="message-role">
              {isUser ? 'You' : isSystem ? 'System' : 'AI Assistant'}
            </span>
            <span className="message-timestamp">
              {formatTimestamp(message.timestamp)}
            </span>
          </div>
          
          <div className="message-text">
            {message.content}
            {message.isStreaming && (
              <span className="streaming-cursor" aria-label="Generating response">|</span>
            )}
          </div>
          
          {message.metadata && (
            <div className="message-metadata">
              {message.metadata.model && (
                <span className="metadata-item" title="Model">
                  🧠 {message.metadata.model}
                </span>
              )}
              {message.metadata.tokens && (
                <span className="metadata-item" title="Tokens">
                  📊 {message.metadata.tokens}
                </span>
              )}
              {message.metadata.cost && (
                <span className="metadata-item" title="Cost">
                  💰 ${message.metadata.cost.toFixed(4)}
                </span>
              )}
            </div>
          )}
          
          {/* Message Actions */}
          {showActions && showActionsMenu && !message.isStreaming && (
            <div className="message-actions">
              <button 
                className="action-btn"
                onClick={handleCopy}
                aria-label="Copy message"
                title="Copy"
              >
                {copied ? '✅' : '📋'}
              </button>
              {isUser && onEdit && (
                <button 
                  className="action-btn"
                  onClick={() => onEdit(message.id)}
                  aria-label="Edit message"
                  title="Edit"
                >
                  ✏️
                </button>
              )}
              {onDelete && (
                <button 
                  className="action-btn"
                  onClick={() => onDelete(message.id)}
                  aria-label="Delete message"
                  title="Delete"
                >
                  🗑️
                </button>
              )}
            </div>
          )}
        </div>
        
        {/* Reactions */}
        {!isSystem && (
          <MessageReactions
            messageId={message.id}
            reactions={message.reactions}
            onReact={(emoji) => onReact?.(message.id, emoji)}
            onRemoveReaction={(emoji) => onRemoveReaction?.(message.id, emoji)}
          />
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
