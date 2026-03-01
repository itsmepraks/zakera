/**
 * QuickActionsMenu Component
 * 
 * Keyboard-accessible quick actions menu (Cmd+K style).
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import './QuickActionsMenu.css';

interface Action {
  id: string;
  label: string;
  description?: string;
  icon: string;
  shortcut?: string;
  category: string;
  handler: () => void | Promise<void>;
  keywords?: string[];
}

interface Props {
  actions: Action[];
  isOpen: boolean;
  onClose: () => void;
}

export const QuickActionsMenu: React.FC<Props> = ({ actions, isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Filter actions based on query
  const filteredActions = useCallback(() => {
    if (!query.trim()) return actions;

    const lowerQuery = query.toLowerCase();
    return actions.filter(action => {
      const matchLabel = action.label.toLowerCase().includes(lowerQuery);
      const matchDesc = action.description?.toLowerCase().includes(lowerQuery);
      const matchKeywords = action.keywords?.some(k => k.toLowerCase().includes(lowerQuery));
      return matchLabel || matchDesc || matchKeywords;
    });
  }, [query, actions]);

  const filtered = filteredActions();

  // Group actions by category
  const groupedActions = useCallback(() => {
    const groups: Record<string, Action[]> = {};
    filtered.forEach(action => {
      if (!groups[action.category]) {
        groups[action.category] = [];
      }
      groups[action.category].push(action);
    });
    return groups;
  }, [filtered]);

  const groups = groupedActions();

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, filtered.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filtered[selectedIndex]) {
            filtered[selectedIndex].handler();
            onClose();
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filtered, onClose]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="quick-actions-overlay" onClick={onClose}>
      <div className="quick-actions-menu" onClick={(e) => e.stopPropagation()}>
        <div className="quick-actions-search">
          <span className="search-icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or search..."
            className="search-input"
          />
          <kbd className="shortcut-hint">ESC</kbd>
        </div>

        <div className="quick-actions-list">
          {Object.keys(groups).length === 0 ? (
            <div className="no-results">No actions found</div>
          ) : (
            Object.entries(groups).map(([category, categoryActions]) => (
              <div key={category} className="action-group">
                <div className="group-label">{category}</div>
                {categoryActions.map((action, idx) => {
                  const globalIndex = filtered.indexOf(action);
                  const isSelected = globalIndex === selectedIndex;

                  return (
                    <button
                      key={action.id}
                      className={`action-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => {
                        action.handler();
                        onClose();
                      }}
                      onMouseEnter={() => setSelectedIndex(globalIndex)}
                    >
                      <span className="action-icon">{action.icon}</span>
                      <div className="action-content">
                        <span className="action-label">{action.label}</span>
                        {action.description && (
                          <span className="action-description">{action.description}</span>
                        )}
                      </div>
                      {action.shortcut && (
                        <kbd className="action-shortcut">{action.shortcut}</kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="quick-actions-footer">
          <span>Navigate with ↑ ↓</span>
          <span>Select with ⏎</span>
        </div>
      </div>
    </div>
  );
};
