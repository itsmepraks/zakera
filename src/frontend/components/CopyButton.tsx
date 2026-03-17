/**
 * CopyButton — copy-to-clipboard pill, used inside MessageCard's action toolbar.
 *
 * Changes in this revision
 * ------------------------
 * - Added optional `onCopy` callback (fires after a successful copy).
 * - Added optional `className` forwarding so MessageCard can pass
 *   `message-card__action-btn` to inherit the shared pill style.
 * - Kept the SVG check / clipboard icons from the original.
 */

import React from 'react';
import { useClipboard } from '../hooks/useClipboard';

export interface CopyButtonProps {
  /** Text to write to the clipboard. */
  text: string;
  /** Extra class names forwarded to the root <button>. */
  className?: string;
  /** Accessible label for the button (default: "Copy"). */
  label?: string;
  /** Optional callback invoked after a successful copy. */
  onCopy?: () => void;
}

export const CopyButton: React.FC<CopyButtonProps> = ({
  text,
  className = '',
  label = 'Copy',
  onCopy,
}) => {
  const { copy, copied } = useClipboard();

  const handleClick = async () => {
    const ok = await copy(text);
    if (ok) onCopy?.();
  };

  return (
    <button
      type="button"
      className={`copy-button ${className} ${copied ? 'copied' : ''}`.trim()}
      onClick={handleClick}
      aria-label={copied ? 'Copied!' : label}
      title={copied ? 'Copied!' : label}
    >
      {copied ? (
        /* Check-mark icon */
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M5 13l4 4L19 7"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        /* Clipboard icon */
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
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
