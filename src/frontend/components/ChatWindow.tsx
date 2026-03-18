/**
 * ChatWindow
 *
 * Main chat interface component. Renders the message history, the composer
 * input, the streaming indicator while the AI is responding, and the token
 * counter in the header bar.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import StreamingIndicator from './StreamingIndicator';
import TokenCounter from './TokenCounter';
import { useTokenCounter } from '../hooks/useTokenCounter';
import styles from './ChatWindow.module.css';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: Date;
}

export interface ChatWindowProps {
  sessionId: string;
  modelName?: string;
  contextWindow?: number;
  onSendMessage: (content: string) => Promise<void>;
  messages: Message[];
  isStreaming: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  sessionId,
  modelName = 'Zakera AI',
  contextWindow = 1_048_576, // Gemini 2.0 Flash default
  onSendMessage,
  messages,
  isStreaming,
}) => {
  const [draft, setDraft] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const { usage, reset: resetTokens } = useTokenCounter(sessionId, contextWindow);

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = draft.trim();
      if (!trimmed || isStreaming) return;
      setDraft('');
      await onSendMessage(trimmed);
    },
    [draft, isStreaming, onSendMessage],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void handleSubmit(e as unknown as React.FormEvent);
      }
    },
    [handleSubmit],
  );

  return (
    <div className={styles.window}>
      {/* ── Header ─────────────────────────────────────────── */}
      <div className={styles.header}>
        <span className={styles.modelBadge}>{modelName}</span>
        <TokenCounter
          usage={usage}
          contextWindow={contextWindow}
          showBreakdown
        />
      </div>

      {/* ── Message list ───────────────────────────────────── */}
      <div className={styles.messages} role="log" aria-label="Chat history" aria-live="polite">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`${styles.message} ${
              msg.role === 'user' ? styles.user : styles.assistant
            }`}
          >
            <div className={styles.bubble}>{msg.content}</div>
            <time className={styles.timestamp} dateTime={msg.createdAt.toISOString()}>
              {msg.createdAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </time>
          </div>
        ))}

        {/* Streaming indicator sits after the last message */}
        {isStreaming && (
          <div className={`${styles.message} ${styles.assistant}`}>
            <StreamingIndicator isStreaming={isStreaming} />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Composer ───────────────────────────────────────── */}
      <form className={styles.composer} onSubmit={handleSubmit}>
        <textarea
          className={styles.textarea}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Zakera… (Shift+Enter for newline)"
          disabled={isStreaming}
          rows={1}
          aria-label="Message input"
        />
        <button
          type="submit"
          className={styles.sendButton}
          disabled={!draft.trim() || isStreaming}
          aria-label="Send message"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatWindow;
