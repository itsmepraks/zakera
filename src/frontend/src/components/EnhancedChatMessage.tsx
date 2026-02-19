import React, { useState, useCallback, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { MessageReactions } from './MessageReactions';
import './EnhancedChatMessage.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  reactions?: any[];
}

interface EnhancedChatMessageProps {
  message: Message;
  onReact?: (messageId: string, emoji: string) => void;
  onRetry?: (messageId: string) => void;
  onCopy?: (content: string) => void;
}

/**
 * Enhanced chat message component with reactions, copy, and animations.
 * Displays messages with rich formatting, code highlighting, and interactions.
 */
export const EnhancedChatMessage: React.FC<EnhancedChatMessageProps> = memo(({
  message,
  onReact,
  onRetry,
  onCopy
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [copied, setCopied] = useState(false);

  const formatTimestamp = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
  };

  const handleCopy = useCallback(() => {
    if (onCopy) {
      onCopy(message.content);
    } else {
      navigator.clipboard.writeText(message.content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content, onCopy]);

  const handleRetry = useCallback(() => {
    if (onRetry) {
      onRetry(message.id);
    }
  }, [message.id, onRetry]);

  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  const isSending = message.status === 'sending';

  return (
    <div
      className={`enhanced-message-container ${
        isUser ? 'user-message' : 'assistant-message'
      } ${isError ? 'error' : ''} ${isSending ? 'sending' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Avatar */}
      <div className="message-avatar">
        <span className="avatar-icon">
          {isUser ? '👤' : '🤖'}
        </span>
        {isSending && (
          <div className="sending-indicator">
            <span className="sending-dot"></span>
          </div>
        )}
      </div>

      {/* Message content */}
      <div className="message-body">
        {/* Header with role and timestamp */}
        <div className="message-header">
          <span className="message-role">
            {isUser ? 'You' : 'AI Assistant'}
          </span>
          <span className="message-timestamp">
            {formatTimestamp(message.timestamp)}
          </span>
          {message.status && (
            <span className={`message-status status-${message.status}`}>
              {message.status === 'sending' && '⏳'}
              {message.status === 'sent' && '✓'}
              {message.status === 'error' && '⚠️'}
            </span>
          )}
        </div>

        {/* Message content with markdown */}
        <div className="message-content">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const language = match ? match[1] : '';
                
                return !inline && match ? (
                  <div className="code-block-wrapper">
                    {language && (
                      <div className="code-block-header">
                        <span className="code-language">{language}</span>
                        <button
                          className="code-copy-btn"
                          onClick={() => {
                            navigator.clipboard.writeText(String(children));
                          }}
                          aria-label="Copy code"
                        >
                          📋 Copy
                        </button>
                      </div>
                    )}
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={language}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  </div>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Error message */}
        {isError && (
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span>Failed to send message</span>
            {onRetry && (
              <button
                className="retry-btn"
                onClick={handleRetry}
                aria-label="Retry sending message"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {/* Action buttons */}
        {isHovered && !isSending && (
          <div className="message-actions">
            <button
              className="action-btn copy-btn"
              onClick={handleCopy}
              aria-label="Copy message"
              title="Copy message"
            >
              {copied ? '✓ Copied' : '📋 Copy'}
            </button>
          </div>
        )}

        {/* Reactions */}
        {!isUser && !isSending && (
          <MessageReactions
            messageId={message.id}
            reactions={message.reactions}
            onReact={onReact}
          />
        )}
      </div>
    </div>
  );
});

EnhancedChatMessage.displayName = 'EnhancedChatMessage';

export default EnhancedChatMessage;