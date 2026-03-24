/**
 * useMessageActions
 *
 * Encapsulates the stateful logic for MessageReactionBar:
 *   - Togglable like / dislike with mutual exclusivity
 *   - Clipboard copy with a 2-second "copied" confirmation flash
 *   - Optional callbacks for persistence / analytics
 */

import { useState, useCallback, useRef } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Reaction = 'like' | 'dislike';

export interface UseMessageActionsOptions {
  /** Unique message id passed through to callbacks. */
  messageId: string;
  /** The text to be copied to the clipboard. */
  content: string;
  /**
   * Called whenever the active reaction changes.
   * Receives `null` when a reaction is toggled off.
   */
  onReaction?: (messageId: string, reaction: Reaction | null) => void;
  /** Called after a successful clipboard copy. */
  onCopy?: (messageId: string) => void;
  /** Duration (ms) to show the "copied" confirmation. Defaults to 2000. */
  copyConfirmDurationMs?: number;
}

export interface UseMessageActionsReturn {
  /** The currently active reaction, or null if none. */
  reaction: Reaction | null;
  /** True during the post-copy confirmation window. */
  copied: boolean;
  handleLike: () => void;
  handleDislike: () => void;
  handleCopy: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMessageActions({
  messageId,
  content,
  onReaction,
  onCopy,
  copyConfirmDurationMs = 2000,
}: UseMessageActionsOptions): UseMessageActionsReturn {
  const [reaction, setReaction] = useState<Reaction | null>(null);
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // -------------------------------------------------------------------------
  // Reaction handlers
  // -------------------------------------------------------------------------

  const handleLike = useCallback(() => {
    setReaction((prev) => {
      const next = prev === 'like' ? null : 'like';
      onReaction?.(messageId, next);
      return next;
    });
  }, [messageId, onReaction]);

  const handleDislike = useCallback(() => {
    setReaction((prev) => {
      const next = prev === 'dislike' ? null : 'dislike';
      onReaction?.(messageId, next);
      return next;
    });
  }, [messageId, onReaction]);

  // -------------------------------------------------------------------------
  // Copy handler
  // -------------------------------------------------------------------------

  const handleCopy = useCallback(async () => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(content);
      } else {
        // Fallback for older browsers / non-HTTPS contexts
        const textarea = document.createElement('textarea');
        textarea.value = content;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }

      setCopied(true);
      onCopy?.(messageId);

      // Clear any previous timer before setting a new one
      if (copyTimerRef.current !== null) {
        clearTimeout(copyTimerRef.current);
      }
      copyTimerRef.current = setTimeout(() => {
        setCopied(false);
        copyTimerRef.current = null;
      }, copyConfirmDurationMs);
    } catch (err) {
      console.error('[useMessageActions] Clipboard write failed:', err);
    }
  }, [content, messageId, onCopy, copyConfirmDurationMs]);

  return { reaction, copied, handleLike, handleDislike, handleCopy };
}
