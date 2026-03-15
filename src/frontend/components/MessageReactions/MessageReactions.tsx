import React, {
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import type { ReactionMap, EmojiString } from '../../types/reactions';
import styles from './MessageReactions.module.css';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Curated emoji palette shown in the picker popover. */
const EMOJI_PALETTE: EmojiString[] = [
  '\u{1F44D}', // 👍
  '\u{1F44E}', // 👎
  '\u2764\uFE0F', // ❤️
  '\u{1F602}', // 😂
  '\u{1F62E}', // 😮
  '\u{1F622}', // 😢
  '\u{1F525}', // 🔥
  '\u{1F389}', // 🎉
  '\u{1F914}', // 🤔
  '\u{1F4AF}', // 💯
  '\u{1F440}', // 👀
  '\u2705',   // ✅
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MessageReactionsProps {
  /** ID of the message these reactions belong to. */
  messageId: string;
  /** Current reaction state keyed by emoji. */
  reactions: ReactionMap;
  /** Called when the user toggles an existing reaction chip. */
  onReactionToggle: (messageId: string, emoji: EmojiString) => void;
  /** Called when the user picks a new emoji from the popover. */
  onAddReaction: (messageId: string, emoji: EmojiString) => void;
  /** Disable all interaction (e.g. while the AI is typing). */
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const MessageReactions = memo(function MessageReactions({
  messageId,
  reactions,
  onReactionToggle,
  onAddReaction,
  disabled = false,
}: MessageReactionsProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);
  const addButtonRef = useRef<HTMLButtonElement>(null);

  // Close picker on outside click
  useEffect(() => {
    if (!pickerOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(event.target as Node) &&
        addButtonRef.current &&
        !addButtonRef.current.contains(event.target as Node)
      ) {
        setPickerOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [pickerOpen]);

  // Close picker on Escape
  useEffect(() => {
    if (!pickerOpen) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setPickerOpen(false);
        addButtonRef.current?.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [pickerOpen]);

  const handleChipClick = useCallback(
    (emoji: EmojiString) => {
      if (!disabled) onReactionToggle(messageId, emoji);
    },
    [disabled, messageId, onReactionToggle],
  );

  const handleChipKeyDown = useCallback(
    (event: React.KeyboardEvent, emoji: EmojiString) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleChipClick(emoji);
      }
    },
    [handleChipClick],
  );

  const handleEmojiPick = useCallback(
    (emoji: EmojiString) => {
      onAddReaction(messageId, emoji);
      setPickerOpen(false);
    },
    [messageId, onAddReaction],
  );

  const reactionEntries = Object.entries(reactions);

  return (
    <div className={styles.reactionTray} data-testid="reaction-tray">
      {/* Existing reaction chips */}
      {reactionEntries.map(([emoji, entry]) => (
        <button
          key={emoji}
          type="button"
          className={[
            styles.reactionChip,
            entry.userReacted ? styles.reactionChipActive : '',
          ]
            .filter(Boolean)
            .join(' ')}
          onClick={() => handleChipClick(emoji)}
          onKeyDown={(e) => handleChipKeyDown(e, emoji)}
          disabled={disabled}
          aria-label={`React with ${emoji}, ${entry.count} reaction${
            entry.count !== 1 ? 's' : ''
          }${entry.userReacted ? ', you reacted' : ''}`}
          aria-pressed={entry.userReacted}
          data-testid={`reaction-chip-${emoji}`}
        >
          <span className={styles.emojiSymbol}>{emoji}</span>
          <span className={styles.countBadge}>{entry.count}</span>
        </button>
      ))}

      {/* Add reaction button + picker */}
      {!disabled && (
        <div className={styles.addWrapper}>
          <button
            ref={addButtonRef}
            type="button"
            className={styles.addButton}
            onClick={() => setPickerOpen((prev) => !prev)}
            aria-label="Add reaction"
            aria-expanded={pickerOpen}
            aria-haspopup="true"
            data-testid="add-reaction-button"
          >
            + Add
          </button>

          {pickerOpen && (
            <div
              ref={pickerRef}
              className={styles.emojiPickerPopover}
              role="dialog"
              aria-label="Emoji picker"
              data-testid="emoji-picker"
            >
              {EMOJI_PALETTE.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  className={styles.emojiOption}
                  onClick={() => handleEmojiPick(emoji)}
                  aria-label={`Pick ${emoji}`}
                  data-testid={`emoji-option-${emoji}`}
                >
                  {emoji}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default MessageReactions;
