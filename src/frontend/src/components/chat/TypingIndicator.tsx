/**
 * TypingIndicator Component
 * 
 * Displays an animated typing indicator showing when the AI is generating a response.
 * Features smooth animations and customizable styling.
 */

import React from 'react';
import './TypingIndicator.css';

interface TypingIndicatorProps {
  isTyping?: boolean;
  message?: string;
  className?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isTyping = true,
  message = 'AI is thinking',
  className = ''
}) => {
  if (!isTyping) return null;

  return (
    <div className={`typing-indicator ${className}`} role="status" aria-live="polite">
      <div className="typing-indicator-content">
        <div className="typing-indicator-avatar">
          <span className="avatar-icon">🤖</span>
        </div>
        <div className="typing-indicator-bubble">
          <span className="typing-text" aria-label={message}>{message}</span>
          <div className="typing-dots">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
