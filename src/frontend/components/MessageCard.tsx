/**
 * MessageCard — individual chat message with full action toolbar.
 *
 * What changed in this revision
 * ------------------------------
 * - Removed inline clipboard code; delegates to <CopyButton> which
 *   uses the shared useClipboard hook (avoids duplicating the
 *   navigator.clipboard / execCommand fallback logic).
 * - Replaced the inline formatTimestamp helper with <MessageTimestamp>
 *   which auto-refreshes every minute and shows absolute time on hover.
 * - Added a "Regenerate" action button for assistant messages that calls
 *   the optional `onRegenerate` prop; shows a spinning SVG while in
 *   progress and is hidden while the message is streaming.
 * - Wired up <MessageReactions> below the message body. Reactions are
 *   only rendered when a `messageId` is supplied and the message is not
 *   actively streaming. The caller must provide onReactionToggle and
 *   onAddReaction (typically from the useReactions hook).
 * - Added `messageId` to props (required for reaction forwarding).
 */

import React, { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { CopyButton } from './CopyButton';
import MessageTimestamp from './MessageTimestamp';
import { MessageReactions } from './MessageReactions';
import type { ReactionMap, ReactionToggleHandler } from '../types/reactions';
import './MessageCard.css';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MessageCardProps {
  /** Unique message ID — required to forward to MessageReactions. */
  messageId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date | string;
  /** Model name shown as a badge on assistant messages. */
  model?: string;
  /** Whether the AI response is still streaming in. */
  isStreaming?: boolean;
  /**
   * Called when the user clicks the Regenerate button.
   * Only shown on assistant messages when this prop is provided.
   */
  onRegenerate?: (messageId: string) => Promise<void>;
  /** Copy action callback (optional — CopyButton handles its own state). */
  onCopy?: () => void;
  // ----- Reactions props (all optional; omit to hide the tray) ------------
  reactions?: ReactionMap;
  onReactionToggle?: ReactionToggleHandler;
  onAddReaction?: ReactionToggleHandler;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ROLE_AVATAR: Record<MessageCardProps['role'], string> = {
  user: '\u{1F9D1}',      // 🧑
  assistant: '\u{1F916}', // 🤖
  system: '\u2699\uFE0F', // ⚙️
};

const ROLE_LABEL: Record<MessageCardProps['role'], string> = {
  user: 'You',
  assistant: 'AI Assistant',
  system: 'System',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const MessageCard: React.FC<MessageCardProps> = ({
  messageId,
  role,
  content,
  timestamp,
  model,
  isStreaming = false,
  onRegenerate,
  onCopy,
  reactions = {},
  onReactionToggle,
  onAddReaction,
}) => {
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleRegenerate = useCallback(async () => {
    if (!onRegenerate || isRegenerating) return;
    setIsRegenerating(true);
    try {
      await onRegenerate(messageId);
    } finally {
      setIsRegenerating(false);
    }
  }, [onRegenerate, isRegenerating, messageId]);

  /** Only show the reactions tray when we have a valid message ID and
   *  the necessary callbacks are wired up. */
  const showReactions =
    !isStreaming &&
    onReactionToggle !== undefined &&
    onAddReaction !== undefined;

  return (
    <div
      className={[
        'message-card',
        `message-card--${role}`,
        isStreaming ? 'message-card--streaming' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      role="article"
      aria-label={`${role} message`}
    >
      {/* Avatar */}
      <div className="message-card__avatar">
        <span className="message-card__avatar-icon" aria-hidden="true">
          {ROLE_AVATAR[role]}
        </span>
      </div>

      {/* Main content area */}
      <div className="message-card__content">
        {/* Header row: role label, model badge, timestamp */}
        <div className="message-card__header">
          <span className="message-card__role">{ROLE_LABEL[role]}</span>

          {model && role === 'assistant' && (
            <span className="message-card__model" title={`Model: ${model}`}>
              {model}
            </span>
          )}

          {timestamp && (
            <MessageTimestamp
              timestamp={timestamp}
              format="relative"
              className="message-card__timestamp"
            />
          )}
        </div>

        {/* Message body */}
        <div className="message-card__body">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>

          {/* Streaming indicator */}
          {isStreaming && (
            <span
              className="message-card__streaming-indicator"
              aria-live="polite"
              aria-label="AI is typing"
            >
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
          )}
        </div>

        {/* Action toolbar — hidden while streaming */}
        {!isStreaming && (
          <div className="message-card__actions">
            {/* Copy button — delegates to CopyButton → useClipboard */}
            <CopyButton
              text={content}
              label="Copy"
              className="message-card__action-btn"
              onCopy={onCopy}
            />

            {/* Regenerate button — assistant messages only */}
            {role === 'assistant' && onRegenerate && (
              <button
                className={[
                  'message-card__action-btn',
                  'message-card__regenerate-btn',
                  isRegenerating
                    ? 'message-card__regenerate-btn--loading'
                    : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onClick={handleRegenerate}
                disabled={isRegenerating}
                aria-label="Regenerate response"
                title="Regenerate response"
              >
                {/* Refresh SVG — rotates continuously while loading */}
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                  className="message-card__regenerate-icon"
                >
                  <path
                    d="M21 12a9 9 0 11-2.636-6.364"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                  <polyline
                    points="21 3 21 9 15 9"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="sr-only">
                  {isRegenerating ? 'Regenerating\u2026' : 'Regenerate'}
                </span>
              </button>
            )}
          </div>
        )}

        {/* Reactions tray */}
        {showReactions && (
          <div className="message-card__reactions-row">
            <MessageReactions
              messageId={messageId}
              reactions={reactions}
              onReactionToggle={onReactionToggle!}
              onAddReaction={onAddReaction!}
              disabled={isStreaming}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageCard;
