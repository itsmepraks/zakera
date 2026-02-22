/**
 * Clipboard Hook
 * 
 * Provides copy-to-clipboard functionality with feedback.
 * 
 * Features:
 * - Copy text to clipboard
 * - Visual feedback (copied state)
 * - Fallback for older browsers
 * - Error handling
 * - Auto-reset after timeout
 * 
 * Usage:
 *   const { copy, copied, error } = useClipboard();
 *   
 *   <button onClick={() => copy(text)}>
 *     {copied ? 'Copied!' : 'Copy'}
 *   </button>
 */

import { useState, useCallback } from 'react';

interface UseClipboardReturn {
  copy: (text: string) => Promise<boolean>;
  copied: boolean;
  error: Error | null;
  reset: () => void;
}

export const useClipboard = (timeout = 2000): UseClipboardReturn => {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      if (!text) {
        setError(new Error('No text provided'));
        return false;
      }

      try {
        // Modern clipboard API
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setError(null);

          setTimeout(() => {
            setCopied(false);
          }, timeout);

          return true;
        } else {
          // Fallback for older browsers
          const textArea = document.createElement('textarea');
          textArea.value = text;
          textArea.style.position = 'fixed';
          textArea.style.left = '-999999px';
          textArea.style.top = '-999999px';
          document.body.appendChild(textArea);
          textArea.focus();
          textArea.select();

          const successful = document.execCommand('copy');
          textArea.remove();

          if (successful) {
            setCopied(true);
            setError(null);

            setTimeout(() => {
              setCopied(false);
            }, timeout);

            return true;
          } else {
            throw new Error('Copy command failed');
          }
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to copy');
        setError(error);
        setCopied(false);
        console.error('Copy failed:', error);
        return false;
      }
    },
    [timeout]
  );

  const reset = useCallback(() => {
    setCopied(false);
    setError(null);
  }, []);

  return { copy, copied, error, reset };
};
