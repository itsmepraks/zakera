/**
 * ConversationPinPanel
 *
 * A collapsible sidebar panel listing all messages the user has pinned for
 * the currently-open conversation.  Clicking a pin entry calls
 * `onScrollToMessage` so the host component can scroll the message into view.
 *
 * @example
 * ```tsx
 * <ConversationPinPanel
 *   conversationId={conversation.id}
 *   pinnedMessages={pinnedMessages}
 *   onUnpin={unpinMessage}
 *   onClearAll={clearAllPins}
 *   onScrollToMessage={(id) => messageRefs.current[id]?.scrollIntoView()}
 * />
 * ```
 */

import React, { useCallback, useId, useRef, useState } from 'react';
import styles from './ConversationPinPanel.module.css';
import type { Message } from '../hooks/usePinnedMessages';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function roleLabel(role: Message['role']): string {
  if (role === 'assistant') return 'AI';
  if (role === 'user') return 'You';
  return 'Sys';
}

function roleClassName(role: Message['role']): string {
  if (role === 'assistant') return styles.roleAI;
  if (role === 'user') return styles.roleUser;
  return styles.roleSystem;
}

// ---------------------------------------------------------------------------
// PinEntry sub-component
// ---------------------------------------------------------------------------

interface PinEntryProps {
  message: Message;
  onUnpin: (id: string) => void;
  onNavigate: (id: string) => void;
}

const PinEntry: React.FC<PinEntryProps> = ({ message, onUnpin, onNavigate }) => {
  const handleUnpinClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onUnpin(message.id);
    },
    [message.id, onUnpin],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onNavigate(message.id);
      }
    },
    [message.id, onNavigate],
  );

  return (
    <div
      className={styles.pinEntry}
      role="button"
      tabIndex={0}
      aria-label={`Go to pinned ${roleLabel(message.role)} message`}
      onClick={() => onNavigate(message.id)}
      onKeyDown={handleKeyDown}
    >
      <div className={styles.pinEntryHeader}>
        <span
          className={`${styles.roleChip} ${roleClassName(message.role)}`}
          aria-hidden="true"
        >
          {roleLabel(message.role)}
        </span>
        {message.timestamp && (
          <span className={styles.timestamp}>
            {formatTimestamp(message.timestamp)}
          </span>
        )}
        <button
          className={styles.unpinBtn}
          onClick={handleUnpinClick}
          aria-label="Unpin this message"
          title="Unpin"
          type="button"
        >
          {String.fromCodePoint(0x1f4cc)}
        </button>
      </div>
      <p className={styles.pinPreview}>{message.content}</p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// ConversationPinPanel
// ---------------------------------------------------------------------------

export interface ConversationPinPanelProps {
  /** The ID of the conversation whose pins are displayed. */
  conversationId: string;
  /** Ordered list of pinned Message objects. */
  pinnedMessages: Message[];
  /** Called when the user unpins a single message. */
  onUnpin: (id: string) => void;
  /** Called when the user confirms clearing all pins. */
  onClearAll: () => void;
  /**
   * Called when the user clicks a pin entry to navigate to that message.
   * The host component is responsible for scrolling the message into view.
   */
  onScrollToMessage: (id: string) => void;
  /** Initial open/closed state. Defaults to `true`. */
  defaultOpen?: boolean;
  /** Additional CSS class(es) for the root element. */
  className?: string;
}

const ConversationPinPanel: React.FC<ConversationPinPanelProps> = ({
  conversationId,
  pinnedMessages,
  onUnpin,
  onClearAll,
  onScrollToMessage,
  defaultOpen = true,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  /**
   * Two-click confirmation guard: first click shows "Confirm?",
   * second click within 3 s actually clears all pins.
   */
  const [clearConfirm, setClearConfirm] = useState(false);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const headingId = useId();
  const panelId = useId();

  const handleToggle = useCallback(() => {
    setIsOpen((prev) => !prev);
    setClearConfirm(false);
    if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
  }, []);

  const handleClearAll = useCallback(() => {
    if (!clearConfirm) {
      setClearConfirm(true);
      clearTimerRef.current = setTimeout(() => setClearConfirm(false), 3000);
      return;
    }
    if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    setClearConfirm(false);
    onClearAll();
  }, [clearConfirm, onClearAll]);

  const pinCount = pinnedMessages.length;

  return (
    <aside
      className={[styles.panel, className].filter(Boolean).join(' ')}
      role="complementary"
      aria-label="Pinned messages"
      data-conversation-id={conversationId}
    >
      {/* ---- Header / toggle button ---- */}
      <div className={styles.panelHeader}>
        <button
          className={styles.toggleBtn}
          onClick={handleToggle}
          aria-expanded={isOpen}
          aria-controls={panelId}
          type="button"
          aria-label="Pinned messages"
        >
          <span className={styles.pinIcon} aria-hidden="true">
            {String.fromCodePoint(0x1f4cc)}
          </span>
          <span id={headingId} className={styles.panelTitle}>
            Pinned
            {pinCount > 0 && (
              <span
                className={styles.badge}
                aria-label={`${pinCount} pinned`}
              >
                {pinCount}
              </span>
            )}
          </span>
          <span
            className={[
              styles.chevron,
              isOpen ? styles.chevronOpen : '',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-hidden="true"
          >
            &rsaquo;
          </span>
        </button>

        {isOpen && pinCount > 0 && (
          <button
            className={[
              styles.clearBtn,
              clearConfirm ? styles.clearBtnConfirm : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onClick={handleClearAll}
            type="button"
            title={clearConfirm ? 'Click again to confirm' : 'Clear all pins'}
            aria-label={
              clearConfirm ? 'Confirm clear all pins' : 'Clear all pins'
            }
          >
            {clearConfirm ? 'Confirm?' : 'Clear all'}
          </button>
        )}
      </div>

      {/* ---- Collapsible body ---- */}
      <div
        id={panelId}
        className={[styles.panelBody, isOpen ? styles.panelBodyOpen : '']
          .filter(Boolean)
          .join(' ')}
        aria-labelledby={headingId}
        role="list"
      >
        {pinCount === 0 ? (
          <div className={styles.emptyState} role="listitem">
            <span className={styles.emptyIcon} aria-hidden="true">
              {String.fromCodePoint(0x1f4ce)}
            </span>
            <p className={styles.emptyText}>
              No pinned messages yet.
              <br />
              <span className={styles.emptyHint}>
                Click {String.fromCodePoint(0x1f4cc)} on any message to pin it here.
              </span>
            </p>
          </div>
        ) : (
          pinnedMessages.map((msg) => (
            <div key={msg.id} role="listitem">
              <PinEntry
                message={msg}
                onUnpin={onUnpin}
                onNavigate={onScrollToMessage}
              />
            </div>
          ))
        )}
      </div>
    </aside>
  );
};

export default ConversationPinPanel;
