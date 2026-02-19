import React from 'react';
import './TypingIndicator.css';

interface TypingIndicatorProps {
  userName?: string;
}

/**
 * Animated typing indicator component.
 * Shows when the AI is generating a response.
 */
export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  userName = 'AI'
}) => {
  return (
    <div className="typing-indicator-container">
      <div className="typing-indicator">
        <div className="typing-avatar">
          <span className="avatar-icon">🤖</span>
        </div>
        <div className="typing-content">
          <span className="typing-name">{userName}</span>
          <div className="typing-dots">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;