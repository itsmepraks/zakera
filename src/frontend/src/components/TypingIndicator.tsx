import React from 'react';
import './TypingIndicator.css';

interface TypingIndicatorProps {
  model?: 'gpt-4' | 'gemini' | 'claude' | 'ollama' | string;
  show?: boolean;
  size?: 'small' | 'medium' | 'large';
  customText?: string;
}

/**
 * Typing indicator with model-specific animations.
 * 
 * Displays an animated indicator when the AI is generating a response.
 * Animation style varies based on the model provider.
 * 
 * @example
 * <TypingIndicator model="gpt-4" show={isTyping} />
 */
export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  model = 'gpt-4',
  show = true,
  size = 'medium',
  customText,
}) => {
  if (!show) return null;

  const getModelInfo = () => {
    const modelLower = model.toLowerCase();
    
    if (modelLower.includes('gpt')) {
      return {
        name: 'GPT',
        color: '#10a37f',
        animation: 'wave',
        text: customText || 'ChatGPT is thinking...',
      };
    }
    
    if (modelLower.includes('gemini')) {
      return {
        name: 'Gemini',
        color: '#8e44ad',
        animation: 'pulse',
        text: customText || 'Gemini is processing...',
      };
    }
    
    if (modelLower.includes('claude')) {
      return {
        name: 'Claude',
        color: '#cc9263',
        animation: 'fade',
        text: customText || 'Claude is composing...',
      };
    }
    
    if (modelLower.includes('ollama') || modelLower.includes('llama')) {
      return {
        name: 'Ollama',
        color: '#2ecc71',
        animation: 'bounce',
        text: customText || 'Ollama is generating...',
      };
    }
    
    return {
      name: 'AI',
      color: '#3498db',
      animation: 'wave',
      text: customText || 'AI is typing...',
    };
  };

  const modelInfo = getModelInfo();

  return (
    <div className={`typing-indicator typing-indicator--${size}`}>
      <div className="typing-indicator__container">
        <div 
          className={`typing-indicator__dots typing-indicator__dots--${modelInfo.animation}`}
          style={{ '--dot-color': modelInfo.color } as React.CSSProperties}
        >
          <span className="typing-indicator__dot"></span>
          <span className="typing-indicator__dot"></span>
          <span className="typing-indicator__dot"></span>
        </div>
        <span className="typing-indicator__text">
          {modelInfo.text}
        </span>
      </div>
    </div>
  );
};

export default TypingIndicator;
