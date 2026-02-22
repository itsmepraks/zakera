/**
 * Typing Indicator Component
 * 
 * Shows an animated typing indicator when the AI is generating a response.
 * Displays different animations based on the model being used.
 * 
 * Features:
 * - Model-specific animations
 * - Smooth fade-in/fade-out
 * - Pulsing dots animation
 * - Shows current model name
 * - Estimated time remaining
 * - Accessible with ARIA labels
 * 
 * Usage:
 *   <TypingIndicator 
 *     isVisible={isTyping} 
 *     model="gpt-4"
 *     estimatedTime={5}
 *   />
 */

import React, { useEffect, useState } from 'react';

interface TypingIndicatorProps {
  isVisible: boolean;
  model?: string;
  estimatedTime?: number; // in seconds
  onCancel?: () => void;
}

const modelDisplayNames: Record<string, string> = {
  'gpt-4': 'GPT-4',
  'gpt-4-turbo': 'GPT-4 Turbo',
  'gpt-3.5-turbo': 'GPT-3.5 Turbo',
  'claude-3-opus': 'Claude 3 Opus',
  'claude-3-sonnet': 'Claude 3 Sonnet',
  'claude-3-haiku': 'Claude 3 Haiku',
  'gemini-1.5-pro': 'Gemini 1.5 Pro',
  'gemini-1.5-flash': 'Gemini 1.5 Flash',
  'llama3:8b': 'Llama 3 8B',
  'mistral:7b': 'Mistral 7B',
};

const modelColors: Record<string, string> = {
  'gpt-4': '#10a37f',
  'gpt-3.5-turbo': '#19c37d',
  'claude-3-opus': '#cc785c',
  'claude-3-sonnet': '#d97757',
  'gemini-1.5-pro': '#4285f4',
  'gemini-1.5-flash': '#669df6',
  'llama3:8b': '#8b5cf6',
  'mistral:7b': '#f97316',
};

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isVisible,
  model = 'unknown',
  estimatedTime,
  onCancel,
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isVisible) {
      setElapsed(0);
      return;
    }

    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  const displayName = modelDisplayNames[model] || model;
  const color = modelColors[model] || '#6b7280';
  const progress = estimatedTime ? Math.min((elapsed / estimatedTime) * 100, 95) : undefined;

  return (
    <div 
      className="typing-indicator"
      role="status"
      aria-live="polite"
      aria-label={`${displayName} is typing`}
    >
      <div className="typing-indicator-content">
        <div className="typing-avatar" style={{ backgroundColor: color }}>
          <span className="typing-avatar-icon">🤖</span>
        </div>

        <div className="typing-bubble">
          <div className="typing-info">
            <span className="typing-model" style={{ color }}>
              {displayName}
            </span>
            <span className="typing-status">is thinking...</span>
          </div>

          <div className="typing-dots">
            <span className="dot" style={{ backgroundColor: color }} />
            <span className="dot" style={{ backgroundColor: color }} />
            <span className="dot" style={{ backgroundColor: color }} />
          </div>

          {progress !== undefined && (
            <div className="typing-progress">
              <div 
                className="typing-progress-bar" 
                style={{ width: `${progress}%`, backgroundColor: color }}
              />
            </div>
          )}
        </div>

        {onCancel && (
          <button
            className="typing-cancel"
            onClick={onCancel}
            aria-label="Cancel generation"
            title="Cancel"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M6 6l12 12M6 18L18 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

export default TypingIndicator;
