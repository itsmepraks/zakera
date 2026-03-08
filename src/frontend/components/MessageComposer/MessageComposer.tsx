/**
 * Enhanced Message Composer Component
 * 
 * Advanced message input with formatting tools, auto-save, and rich features
 */

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { useDraftAutosave } from '../../hooks/useDraftAutosave';
import './MessageComposer.css';

interface MessageComposerProps {
  onSendMessage: (message: string) => void;
  conversationId: string;
  placeholder?: string;
  disabled?: boolean;
  showTemplateButton?: boolean;
  onOpenTemplates?: () => void;
  maxLength?: number;
}

type FormatAction = 'bold' | 'italic' | 'code' | 'code_block' | 'link' | 'list';

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  conversationId,
  placeholder = 'Type your message...',
  disabled = false,
  showTemplateButton = true,
  onOpenTemplates,
  maxLength = 5000,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showFormatting, setShowFormatting] = useState(false);
  const [charCount, setCharCount] = useState(0);

  // Use draft autosave hook
  const {
    draft,
    setDraft,
    clearDraft,
    hasDraft,
    lastSaved,
    isSaving,
  } = useDraftAutosave({
    conversationId,
    autosaveDelay: 2000,
  });

  // Update char count
  useEffect(() => {
    setCharCount(draft.length);
  }, [draft]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 300)}px`;
    }
  }, [draft]);

  // Handle send
  const handleSend = () => {
    const message = draft.trim();
    if (message && !disabled) {
      onSendMessage(message);
      clearDraft();
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.focus();
      }
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Ctrl/Cmd + Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }

    // Bold: Ctrl/Cmd + B
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      applyFormat('bold');
    }

    // Italic: Ctrl/Cmd + I
    if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
      e.preventDefault();
      applyFormat('italic');
    }

    // Code: Ctrl/Cmd + K
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      applyFormat('code');
    }
  };

  // Apply formatting
  const applyFormat = (action: FormatAction) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = draft.substring(start, end);
    const beforeText = draft.substring(0, start);
    const afterText = draft.substring(end);

    let formattedText = '';
    let newCursorPos = start;

    switch (action) {
      case 'bold':
        formattedText = `**${selectedText || 'bold text'}**`;
        newCursorPos = selectedText ? end + 4 : start + 2;
        break;

      case 'italic':
        formattedText = `*${selectedText || 'italic text'}*`;
        newCursorPos = selectedText ? end + 2 : start + 1;
        break;

      case 'code':
        formattedText = `\`${selectedText || 'code'}\``;
        newCursorPos = selectedText ? end + 2 : start + 1;
        break;

      case 'code_block':
        formattedText = `\`\`\`\n${selectedText || 'code here'}\n\`\`\``;
        newCursorPos = selectedText ? end + 8 : start + 4;
        break;

      case 'link':
        formattedText = `[${selectedText || 'link text'}](url)`;
        newCursorPos = selectedText ? end + 3 : start + 1;
        break;

      case 'list':
        const lines = (selectedText || 'List item').split('\n');
        formattedText = lines.map((line) => `- ${line}`).join('\n');
        newCursorPos = end + lines.length * 2;
        break;
    }

    const newText = beforeText + formattedText + afterText;
    setDraft(newText);

    // Restore cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  // Insert template text
  const insertTemplate = (text: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const beforeText = draft.substring(0, start);
    const afterText = draft.substring(start);

    const newText = beforeText + text + afterText;
    setDraft(newText);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + text.length, start + text.length);
    }, 0);
  };

  return (
    <div className="message-composer-container">
      {/* Draft indicator */}
      {hasDraft && (
        <div className="draft-indicator">
          <span className="draft-icon">💾</span>
          <span className="draft-text">
            {isSaving ? 'Saving...' : `Draft saved${lastSaved ? ` at ${lastSaved.toLocaleTimeString()}` : ''}`}
          </span>
        </div>
      )}

      {/* Formatting toolbar */}
      <div className={`formatting-toolbar ${showFormatting ? 'visible' : ''}`}>
        <div className="toolbar-group">
          <button
            className="format-btn"
            onClick={() => applyFormat('bold')}
            title="Bold (Ctrl+B)"
            disabled={disabled}
          >
            <strong>B</strong>
          </button>
          <button
            className="format-btn"
            onClick={() => applyFormat('italic')}
            title="Italic (Ctrl+I)"
            disabled={disabled}
          >
            <em>I</em>
          </button>
          <button
            className="format-btn"
            onClick={() => applyFormat('code')}
            title="Inline Code (Ctrl+K)"
            disabled={disabled}
          >
            {'</>'}
          </button>
          <button
            className="format-btn"
            onClick={() => applyFormat('code_block')}
            title="Code Block"
            disabled={disabled}
          >
            {'{ }'}
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-group">
          <button
            className="format-btn"
            onClick={() => applyFormat('link')}
            title="Insert Link"
            disabled={disabled}
          >
            🔗
          </button>
          <button
            className="format-btn"
            onClick={() => applyFormat('list')}
            title="Bullet List"
            disabled={disabled}
          >
            ☰
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-group">
          <button
            className="format-btn"
            onClick={() => insertTemplate('```python\n\n```')}
            title="Python Code Block"
            disabled={disabled}
          >
            🐍
          </button>
          <button
            className="format-btn"
            onClick={() => insertTemplate('```javascript\n\n```')}
            title="JavaScript Code Block"
            disabled={disabled}
          >
            JS
          </button>
        </div>
      </div>

      {/* Main composer area */}
      <div className="composer-main">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          className="message-textarea"
          placeholder={placeholder}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          maxLength={maxLength}
          aria-label="Message input"
        />

        {/* Action buttons */}
        <div className="composer-actions">
          <div className="left-actions">
            {/* Template selector button */}
            {showTemplateButton && onOpenTemplates && (
              <button
                className="action-icon-btn"
                onClick={onOpenTemplates}
                title="Choose template"
                disabled={disabled}
              >
                📚
              </button>
            )}

            {/* Formatting toggle */}
            <button
              className={`action-icon-btn ${showFormatting ? 'active' : ''}`}
              onClick={() => setShowFormatting(!showFormatting)}
              title="Toggle formatting toolbar"
              disabled={disabled}
            >
              ✏️
            </button>

            {/* Character count */}
            <span className={`char-counter ${charCount > maxLength * 0.9 ? 'warning' : ''}`}>
              {charCount}/{maxLength}
            </span>
          </div>

          <div className="right-actions">
            {/* Clear draft */}
            {hasDraft && (
              <button
                className="action-text-btn clear-btn"
                onClick={clearDraft}
                title="Clear draft"
                disabled={disabled}
              >
                Clear
              </button>
            )}

            {/* Send button */}
            <button
              className="send-button"
              onClick={handleSend}
              disabled={disabled || !draft.trim()}
              title="Send message (Ctrl+Enter)"
            >
              <span className="send-icon">✈️</span>
              <span className="send-text">Send</span>
            </button>
          </div>
        </div>
      </div>

      {/* Help text */}
      <div className="composer-help">
        <span className="help-text">
          Press <kbd>Ctrl+Enter</kbd> to send • <kbd>Ctrl+B</kbd> bold •{' '}
          <kbd>Ctrl+I</kbd> italic • <kbd>Ctrl+K</kbd> code
        </span>
      </div>
    </div>
  );
};

export default MessageComposer;
