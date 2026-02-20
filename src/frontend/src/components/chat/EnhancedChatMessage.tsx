/**
 * Enhanced Chat Message Component
 * Displays messages with improved styling, animations, and interactions
 */
import React, { useState, useEffect } from 'react';
import MessageReactions from './MessageReactions';
import { MessageStatus, ChatMessage } from '../../types/chat';
import { Reaction, ReactionType } from '../../types/reactions';
import '../../styles/chat-enhancements.css';

interface EnhancedChatMessageProps {
  /** Message data */
  message: ChatMessage;
  /** Current user ID */
  currentUserId: number;
  /** Whether this is the user's own message */
  isOwnMessage: boolean;
  /** Callback for reaction toggle */
  onReactionToggle: (messageId: number, reactionType: ReactionType) => void;
  /** Whether to show reactions */
  showReactions?: boolean;
  /** Whether to show timestamp */
  showTimestamp?: boolean;
}

export const EnhancedChatMessage: React.FC<EnhancedChatMessageProps> = ({
  message,
  currentUserId,
  isOwnMessage,
  onReactionToggle,
  showReactions = true,
  showTimestamp = true,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  // Fade in animation on mount
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  const handleCopyMessage = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  const formatTimestamp = (timestamp: Date): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusIcon = (status?: MessageStatus): string => {
    switch (status) {
      case 'sending':
        return '⏳';
      case 'sent':
        return '✓';
      case 'delivered':
        return '✓✓';
      case 'error':
        return '❌';
      default:
        return '';
    }
  };

  const getRoleIcon = (role: string): string => {
    switch (role) {
      case 'assistant':
        return '🤖';
      case 'user':
        return '👤';
      case 'system':
        return '⚙️';
      default:
        return '💬';
    }
  };

  return (
    <div
      className={`
        enhanced-message
        ${isOwnMessage ? 'own-message' : 'other-message'}
        ${isVisible ? 'visible' : ''}
        ${message.status === 'error' ? 'error-message' : ''}
      `}
      data-message-id={message.id}
    >
      {/* Message avatar */}
      {!isOwnMessage && (
        <div className="message-avatar" aria-hidden="true">
          <span className="avatar-icon">{getRoleIcon(message.role)}</span>
        </div>
      )}

      <div className="message-wrapper">
        {/* Message header */}
        <div className="message-header">
          <span className="message-sender">
            {isOwnMessage ? 'You' : message.role === 'assistant' ? 'AI Assistant' : 'System'}
          </span>
          {showTimestamp && (
            <span className="message-timestamp">
              {formatTimestamp(message.timestamp)}
            </span>
          )}
        </div>

        {/* Message content */}
        <div className="message-content-wrapper">
          <div className="message-content">{message.content}</div>

          {/* Message actions */}
          <div className="message-actions">
            <button
              className="message-action-button"
              onClick={handleCopyMessage}
              aria-label="Copy message"
              title={copied ? 'Copied!' : 'Copy message'}
            >
              {copied ? '✓' : '📋'}
            </button>
          </div>
        </div>

        {/* Message metadata */}
        <div className="message-metadata">
          {/* Status indicator */}
          {message.status && (
            <span
              className={`message-status status-${message.status}`}
              aria-label={`Status: ${message.status}`}
            >
              {getStatusIcon(message.status)}
            </span>
          )}

          {/* Token count (if available) */}
          {message.tokens && (
            <span className="message-tokens" title="Token count">
              🎫 {message.tokens}
            </span>
          )}

          {/* Model name (if available) */}
          {message.model && (
            <span className="message-model" title="Model used">
              🤖 {message.model}
            </span>
          )}
        </div>

        {/* Reactions */}
        {showReactions && (
          <MessageReactions
            messageId={message.id}
            reactions={message.reactions || []}
            currentUserId={currentUserId}
            onReactionToggle={onReactionToggle}
          />
        )}
      </div>

      {/* Avatar for own messages */}
      {isOwnMessage && (
        <div className="message-avatar" aria-hidden="true">
          <span className="avatar-icon">{getRoleIcon('user')}</span>
        </div>
      )}
    </div>
  );
};

export default EnhancedChatMessage;
