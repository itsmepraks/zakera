/**
 * MessageReactionBar
 *
 * Renders a compact row of action buttons attached to an AI chat message:
 *   - 👍 Thumbs-up  (positive feedback)
 *   - 👎 Thumbs-down (negative feedback)
 *   - 📋 Copy-to-clipboard (flips to ✓ for 2 s on success)
 *
 * Usage:
 * ```tsx
 * <MessageReactionBar
 *   messageId={msg.id}
 *   content={msg.content}
 *   onReaction={(id, reaction) => trackFeedback(id, reaction)}
 *   onCopy={(id) => trackCopy(id)}
 * />
 * ```
 */

import React from 'react';
import { useMessageActions, Reaction } from '../hooks/useMessageActions';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MessageReactionBarProps {
  /** Unique identifier for the message (used in callbacks). */
  messageId: string;
  /** Full text content of the message — used for clipboard copy. */
  content: string;
  /** Called when the user clicks a reaction button. */
  onReaction?: (messageId: string, reaction: Reaction | null) => void;
  /** Called when the user successfully copies the message. */
  onCopy?: (messageId: string) => void;
  /** When true, all buttons are rendered but non-interactive. */
  disabled?: boolean;
  /** Extra CSS classes applied to the container. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Subcomponent: icon button
// ---------------------------------------------------------------------------

interface IconButtonProps {
  onClick: () => void;
  label: string;
  active?: boolean;
  disabled?: boolean;
  title?: string;
  children: React.ReactNode;
  testId?: string;
}

const IconButton: React.FC<IconButtonProps> = ({
  onClick,
  label,
  active = false,
  disabled = false,
  title,
  children,
  testId,
}) => (
  <button
    type="button"
    aria-label={label}
    aria-pressed={active}
    title={title ?? label}
    onClick={disabled ? undefined : onClick}
    disabled={disabled}
    data-testid={testId}
    className={[
      'inline-flex items-center justify-center rounded-md p-1 text-sm transition-colors duration-150',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-blue-500',
      disabled
        ? 'cursor-not-allowed opacity-40'
        : 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700',
      active
        ? 'text-blue-600 dark:text-blue-400'
        : 'text-gray-400 hover:text-gray-700 dark:hover:text-gray-200',
    ]
      .filter(Boolean)
      .join(' ')}
  >
    {children}
  </button>
);

// ---------------------------------------------------------------------------
// SVG icons (inline, no external dependency)
// ---------------------------------------------------------------------------

const ThumbUpIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M2 20h2a1 1 0 0 0 1-1v-7a1 1 0 0 0-1-1H2v9zm19.83-7.12A2 2 0 0 0 20 10h-5.36l.77-3.85A1.5 1.5 0 0 0 14 4.5L8 10.5V20h10.5a2 2 0 0 0 1.96-1.61l1.34-6a2 2 0 0 0-.97-2.51z" />
  </svg>
);

const ThumbDownIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M22 4H20a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h2V4zm-19.83 7.12A2 2 0 0 0 4 14h5.36l-.77 3.85A1.5 1.5 0 0 0 10 19.5L16 13.5V4H5.5a2 2 0 0 0-1.96 1.61l-1.34 6a2 2 0 0 0 .97 2.51z" />
  </svg>
);

const CopyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const MessageReactionBar: React.FC<MessageReactionBarProps> = ({
  messageId,
  content,
  onReaction,
  onCopy,
  disabled = false,
  className = '',
}) => {
  const { reaction, copied, handleLike, handleDislike, handleCopy } =
    useMessageActions({ messageId, content, onReaction, onCopy });

  return (
    <div
      role="group"
      aria-label="Message actions"
      className={`flex items-center gap-0.5 ${className}`}
    >
      <IconButton
        onClick={handleLike}
        label={reaction === 'like' ? 'Remove like' : 'Like this response'}
        active={reaction === 'like'}
        disabled={disabled}
        testId="reaction-like"
      >
        <ThumbUpIcon />
      </IconButton>

      <IconButton
        onClick={handleDislike}
        label={reaction === 'dislike' ? 'Remove dislike' : 'Dislike this response'}
        active={reaction === 'dislike'}
        disabled={disabled}
        testId="reaction-dislike"
      >
        <ThumbDownIcon />
      </IconButton>

      <div className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-600" aria-hidden="true" />

      <IconButton
        onClick={handleCopy}
        label={copied ? 'Copied!' : 'Copy message'}
        active={copied}
        disabled={disabled}
        testId="copy-button"
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </IconButton>
    </div>
  );
};

export default MessageReactionBar;
