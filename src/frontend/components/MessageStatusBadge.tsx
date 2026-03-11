/**
 * MessageStatusBadge
 * ------------------
 * Tiny inline badge that reflects the current message send/stream status.
 * Intended to be placed at the bottom-right of a user message bubble.
 *
 * Status → visual mapping:
 *   sending   — spinning clock icon
 *   streaming — animated arrow / progress dots
 *   done      — single tick (sent) or double tick (acknowledged)
 *   error     — warning triangle with tooltip
 *   idle      — nothing rendered
 */

import React from 'react';
import type { MessageErrorKind, MessageStatus } from '../hooks/useMessageStatus';

export interface MessageStatusBadgeProps {
  status: MessageStatus;
  errorKind?: MessageErrorKind | null;
  errorMessage?: string | null;
  /** Show double-tick style (e.g. once server ACKs storage). */
  acknowledged?: boolean;
  className?: string;
}

const ERROR_LABELS: Record<MessageErrorKind, string> = {
  network:        'Network error — check your connection',
  rate_limit:     'Rate limit reached — please wait a moment',
  context_length: 'Message too long for this model',
  server:         'Server error — please try again',
  unknown:        'Something went wrong',
};

export const MessageStatusBadge: React.FC<MessageStatusBadgeProps> = ({
  status,
  errorKind,
  errorMessage,
  acknowledged = false,
  className = '',
}) => {
  if (status === 'idle') return null;

  const baseClass = `msg-status-badge ${className}`.trim();

  if (status === 'sending') {
    return (
      <span
        className={`${baseClass} msg-status-badge--sending`}
        aria-label="Sending"
        role="img"
      >
        <svg
          className="msg-status-badge__icon msg-status-badge__icon--spin"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeDasharray="24" strokeDashoffset="8" />
        </svg>
      </span>
    );
  }

  if (status === 'streaming') {
    return (
      <span
        className={`${baseClass} msg-status-badge--streaming`}
        aria-label="Streaming response"
        role="img"
      >
        <svg viewBox="0 0 16 16" fill="none" className="msg-status-badge__icon" aria-hidden="true">
          <path d="M2 8h8m0 0-3-3m3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="13" cy="8" r="1.5" fill="currentColor" className="msg-status-badge__pulse" />
        </svg>
      </span>
    );
  }

  if (status === 'done') {
    const label = acknowledged ? 'Delivered' : 'Sent';
    return (
      <span
        className={`${baseClass} msg-status-badge--done`}
        aria-label={label}
        role="img"
      >
        {acknowledged ? (
          /* Double tick */
          <svg viewBox="0 0 20 14" fill="none" className="msg-status-badge__icon" aria-hidden="true">
            <path d="M1 7l4 4L13 1" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M7 11l4 4 8-12" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" opacity="0.6" />
          </svg>
        ) : (
          /* Single tick */
          <svg viewBox="0 0 14 12" fill="none" className="msg-status-badge__icon" aria-hidden="true">
            <path d="M1 6l4 4 8-9" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
    );
  }

  if (status === 'error') {
    const tooltip =
      errorMessage ??
      (errorKind ? ERROR_LABELS[errorKind] : 'Something went wrong');
    return (
      <span
        className={`${baseClass} msg-status-badge--error`}
        aria-label={tooltip}
        title={tooltip}
        role="img"
      >
        <svg viewBox="0 0 16 16" fill="none" className="msg-status-badge__icon" aria-hidden="true">
          <path
            d="M8 1.5L14.5 13H1.5L8 1.5Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path d="M8 6v3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="8" cy="11" r="0.75" fill="currentColor" />
        </svg>
      </span>
    );
  }

  return null;
};

export default MessageStatusBadge;
