/**
 * Copy Button Component
 * 
 * Provides copy-to-clipboard functionality with visual feedback.
 * 
 * Usage:
 *   <CopyButton text="Content to copy" />
 */

import React from 'react';
import { useClipboard } from '../hooks/useClipboard';

interface CopyButtonProps {
  text: string;
  className?: string;
  label?: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({ 
  text, 
  className = '', 
  label = 'Copy' 
}) => {
  const { copy, copied } = useClipboard();

  return (
    <button
      className={`copy-button ${className} ${copied ? 'copied' : ''}`}
      onClick={() => copy(text)}
      aria-label={copied ? 'Copied!' : label}
      title={copied ? 'Copied!' : label}
    >
      {copied ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M5 13l4 4L19 7"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="2" />
          <path
            d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"
            stroke="currentColor"
            strokeWidth="2"
          />
        </svg>
      )}
      <span className="copy-button-text">{copied ? 'Copied!' : label}</span>
    </button>
  );
};

export default CopyButton;
