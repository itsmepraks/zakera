/**
 * Enhanced Message Card Component
 * 
 * A modern, feature-rich message card for displaying chat messages with:
 * - Role-based styling (user vs assistant)
 * - Markdown rendering with syntax highlighting
 * - Copy-to-clipboard functionality
 * - Timestamp with relative time display
 * - Smooth animations and transitions
 * - Responsive design
 */

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './MessageCard.css';

interface MessageCardProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date | string;
  model?: string;
  onCopy?: () => void;
  isStreaming?: boolean;
}

export const MessageCard: React.FC<MessageCardProps> = ({
  role,
  content,
  timestamp,
  model,
  onCopy,
  isStreaming = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      onCopy?.();
      
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const formatTimestamp = (ts?: Date | string) => {
    if (!ts) return '';
    
    const date = typeof ts === 'string' ? new Date(ts) : ts;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
  };

  const getAvatarIcon = () => {
    switch (role) {
      case 'user':
        return '👤';
      case 'assistant':
        return '🤖';
      case 'system':
        return '⚙️';
      default:
        return '💬';
    }
  };

  return (
    <div 
      className={`message-card message-card--${role} ${isStreaming ? 'message-card--streaming' : ''}`}
      role="article"
      aria-label={`${role} message`}
    >
      <div className="message-card__avatar">
        <span className="message-card__avatar-icon" aria-hidden="true">
          {getAvatarIcon()}
        </span>
      </div>
      
      <div className="message-card__content">
        <div className="message-card__header">
          <span className="message-card__role">
            {role === 'assistant' ? 'AI Assistant' : 'You'}
          </span>
          {model && role === 'assistant' && (
            <span className="message-card__model" title={`Model: ${model}`}>
              {model}
            </span>
          )}
          {timestamp && (
            <span className="message-card__timestamp">
              {formatTimestamp(timestamp)}
            </span>
          )}
        </div>
        
        <div className="message-card__body">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
          
          {isStreaming && (
            <span className="message-card__streaming-indicator" aria-live="polite">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </span>
          )}
        </div>
        
        {!isStreaming && (
          <div className="message-card__actions">
            <button
              className={`message-card__action-btn ${copied ? 'message-card__action-btn--success' : ''}`}
              onClick={handleCopy}
              aria-label="Copy message"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <span aria-hidden="true">✓</span>
                  <span className="sr-only">Copied</span>
                </>
              ) : (
                <>
                  <span aria-hidden="true">📋</span>
                  <span className="sr-only">Copy</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageCard;
