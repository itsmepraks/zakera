/**
 * FormattingToolbar Component
 * 
 * Provides a toolbar for markdown formatting with:
 * - Common formatting buttons (bold, italic, code, etc.)
 * - Keyboard shortcuts
 * - Tooltips with hints
 */

import React, { useCallback } from 'react';
import './FormattingToolbar.css';

interface FormattingToolbarProps {
  onFormat: (format: string, value?: string) => void;
  disabled?: boolean;
}

interface FormatButton {
  id: string;
  label: string;
  icon: string;
  tooltip: string;
  shortcut?: string;
  action: () => void;
}

export const FormattingToolbar: React.FC<FormattingToolbarProps> = ({
  onFormat,
  disabled = false
}) => {
  const handleBold = useCallback(() => {
    onFormat('wrap', '**');
  }, [onFormat]);
  
  const handleItalic = useCallback(() => {
    onFormat('wrap', '*');
  }, [onFormat]);
  
  const handleCode = useCallback(() => {
    onFormat('wrap', '`');
  }, [onFormat]);
  
  const handleCodeBlock = useCallback(() => {
    onFormat('block', '```\n', '\n```');
  }, [onFormat]);
  
  const handleLink = useCallback(() => {
    onFormat('link');
  }, [onFormat]);
  
  const handleHeading = useCallback(() => {
    onFormat('prefix', '## ');
  }, [onFormat]);
  
  const handleList = useCallback(() => {
    onFormat('prefix', '- ');
  }, [onFormat]);
  
  const handleNumberedList = useCallback(() => {
    onFormat('prefix', '1. ');
  }, [onFormat]);
  
  const handleQuote = useCallback(() => {
    onFormat('prefix', '> ');
  }, [onFormat]);
  
  const buttons: FormatButton[] = [
    {
      id: 'bold',
      label: 'Bold',
      icon: '🗯',
      tooltip: 'Bold (Ctrl+B)',
      shortcut: 'Ctrl+B',
      action: handleBold,
    },
    {
      id: 'italic',
      label: 'Italic',
      icon: '🦝',
      tooltip: 'Italic (Ctrl+I)',
      shortcut: 'Ctrl+I',
      action: handleItalic,
    },
    {
      id: 'code',
      label: 'Inline Code',
      icon: '👨‍💻',
      tooltip: 'Inline Code (Ctrl+E)',
      shortcut: 'Ctrl+E',
      action: handleCode,
    },
    {
      id: 'codeblock',
      label: 'Code Block',
      icon: '📝',
      tooltip: 'Code Block (Ctrl+Shift+C)',
      shortcut: 'Ctrl+Shift+C',
      action: handleCodeBlock,
    },
    {
      id: 'link',
      label: 'Link',
      icon: '🔗',
      tooltip: 'Insert Link (Ctrl+K)',
      shortcut: 'Ctrl+K',
      action: handleLink,
    },
    {
      id: 'heading',
      label: 'Heading',
      icon: '🅲',
      tooltip: 'Heading (Ctrl+H)',
      shortcut: 'Ctrl+H',
      action: handleHeading,
    },
    {
      id: 'list',
      label: 'Bullet List',
      icon: '📊',
      tooltip: 'Bullet List (Ctrl+L)',
      shortcut: 'Ctrl+L',
      action: handleList,
    },
    {
      id: 'numbered',
      label: 'Numbered List',
      icon: '🔢',
      tooltip: 'Numbered List (Ctrl+Shift+L)',
      shortcut: 'Ctrl+Shift+L',
      action: handleNumberedList,
    },
    {
      id: 'quote',
      label: 'Quote',
      icon: '❝',
      tooltip: 'Quote (Ctrl+Q)',
      shortcut: 'Ctrl+Q',
      action: handleQuote,
    },
  ];
  
  return (
    <div className="formatting-toolbar" role="toolbar" aria-label="Text formatting">
      {buttons.map((button) => (
        <button
          key={button.id}
          className="format-button"
          onClick={button.action}
          disabled={disabled}
          title={button.tooltip}
          aria-label={button.label}
        >
          <span className="format-icon">{button.icon}</span>
        </button>
      ))}
      
      <div className="toolbar-divider" />
      
      <button
        className="format-button help-button"
        onClick={() => window.open('/docs/markdown', '_blank')}
        title="Markdown Help"
        aria-label="Markdown help"
      >
        <span className="format-icon">❔</span>
      </button>
    </div>
  );
};

export default FormattingToolbar;
