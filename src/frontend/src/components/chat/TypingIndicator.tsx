/**
 * Typing Indicator Component
 * Shows animated dots when AI is generating a response
 */
import React from 'react';
import '../../styles/chat-enhancements.css';

interface TypingIndicatorProps {
  /** Whether to show the typing indicator */
  isTyping: boolean;
  /** Name/role of who is typing */
  typingEntity?: string;
  /** Custom class name */
  className?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isTyping,
  typingEntity = 'AI Assistant',
  className = '',
}) => {
  if (!isTyping) return null;

  return (
    <div 
      className={`typing-indicator-container ${className}`}
      role="status"
      aria-live="polite"
      aria-label={`${typingEntity} is typing`}
    >
      <div className="typing-indicator">
        <div className="typing-avatar">
          <span className="avatar-icon">🤖</span>
        </div>
        <div className="typing-content">
          <span className="typing-text">{typingEntity} is typing</span>
          <div className="typing-dots">
            <span className="dot dot-1"></span>
            <span className="dot dot-2"></span>
            <span className="dot dot-3"></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
