import React from 'react';
import './TypingIndicator.css';

interface TypingIndicatorProps {
  userName?: string;
  show: boolean;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ userName = 'AI', show }) => {
  if (!show) return null;

  return (
    <div className="typing-indicator-container" role="status" aria-live="polite">
      <div className="typing-indicator-avatar">
        <span className="avatar-icon">{userName.charAt(0).toUpperCase()}</span>
      </div>
      <div className="typing-indicator-bubble">
        <div className="typing-indicator">
          <span className="dot"></span>
          <span className="dot"></span>
          <span className="dot"></span>
        </div>
        <span className="typing-text">{userName} is typing...</span>
      </div>
    </div>
  );
};

export default TypingIndicator;
