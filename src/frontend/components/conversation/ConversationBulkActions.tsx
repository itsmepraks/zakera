/**
 * ConversationBulkActions Component
 * 
 * Provides bulk operations on multiple selected conversations.
 * Features multi-select, keyboard shortcuts, and batch operations.
 */

import React, { useState, useCallback } from 'react';
import { Conversation } from '../../types/conversation';
import { useConversationBulkSelect } from '../../hooks/useConversationBulkSelect';
import './ConversationBulkActions.css';

interface Props {
  conversations: Conversation[];
  selectedIds: Set<string>;
  onSelectionChange: (selectedIds: Set<string>) => void;
  onBulkDelete: (ids: string[]) => Promise<void>;
  onBulkArchive: (ids: string[]) => Promise<void>;
  onBulkExport: (ids: string[], format: 'json' | 'markdown' | 'pdf' | 'csv') => Promise<void>;
  onBulkTag: (ids: string[], tags: string[]) => Promise<void>;
}

export const ConversationBulkActions: React.FC<Props> = ({
  conversations,
  selectedIds,
  onSelectionChange,
  onBulkDelete,
  onBulkArchive,
  onBulkExport,
  onBulkTag,
}) => {
  const {
    selectAll,
    deselectAll,
    toggleSelection,
    selectRange,
    isAllSelected,
    hasSelection,
  } = useConversationBulkSelect(conversations, selectedIds, onSelectionChange);

  const [showActions, setShowActions] = useState(false);
  const [showTagDialog, setShowTagDialog] = useState(false);
  const [newTags, setNewTags] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const selectedCount = selectedIds.size;
  const selectedConversations = conversations.filter(c => selectedIds.has(c.id));

  const handleBulkOperation = useCallback(async (
    operation: () => Promise<void>,
    successMessage: string
  ) => {
    setIsProcessing(true);
    try {
      await operation();
      deselectAll();
      // Show toast notification
      console.log(successMessage);
    } catch (error) {
      console.error('Bulk operation failed:', error);
      // Show error toast
    } finally {
      setIsProcessing(false);
    }
  }, [deselectAll]);

  const handleDelete = () => {
    if (confirm(`Delete ${selectedCount} conversation(s)?`)) {
      handleBulkOperation(
        () => onBulkDelete(Array.from(selectedIds)),
        `Deleted ${selectedCount} conversations`
      );
    }
  };

  const handleArchive = () => {
    handleBulkOperation(
      () => onBulkArchive(Array.from(selectedIds)),
      `Archived ${selectedCount} conversations`
    );
  };

  const handleExport = (format: 'json' | 'markdown' | 'pdf' | 'csv') => {
    handleBulkOperation(
      () => onBulkExport(Array.from(selectedIds), format),
      `Exported ${selectedCount} conversations as ${format.toUpperCase()}`
    );
  };

  const handleTag = async () => {
    if (!newTags.trim()) return;
    
    const tags = newTags.split(',').map(t => t.trim()).filter(Boolean);
    await handleBulkOperation(
      () => onBulkTag(Array.from(selectedIds), tags),
      `Tagged ${selectedCount} conversations`
    );
    
    setNewTags('');
    setShowTagDialog(false);
  };

  if (!hasSelection) {
    return null;
  }

  return (
    <div className="conversation-bulk-actions">
      <div className="bulk-actions-bar">
        <div className="selection-info">
          <button
            onClick={() => isAllSelected ? deselectAll() : selectAll()}
            className="checkbox-btn"
            title={isAllSelected ? 'Deselect all' : 'Select all'}
          >
            {isAllSelected ? '☑' : '☐'}
          </button>
          <span className="selected-count">
            {selectedCount} selected
          </span>
        </div>

        <div className="bulk-actions">
          <button
            onClick={() => setShowTagDialog(true)}
            disabled={isProcessing}
            className="action-btn"
            title="Add tags"
          >
            🏷️ Tag
          </button>

          <button
            onClick={handleArchive}
            disabled={isProcessing}
            className="action-btn"
            title="Archive selected"
          >
            📦 Archive
          </button>

          <div className="action-dropdown">
            <button
              onClick={() => setShowActions(!showActions)}
              disabled={isProcessing}
              className="action-btn"
            >
              📤 Export ▾
            </button>
            {showActions && (
              <div className="dropdown-menu">
                <button onClick={() => handleExport('json')}>Export as JSON</button>
                <button onClick={() => handleExport('markdown')}>Export as Markdown</button>
                <button onClick={() => handleExport('pdf')}>Export as PDF</button>
                <button onClick={() => handleExport('csv')}>Export as CSV</button>
              </div>
            )}
          </div>

          <button
            onClick={handleDelete}
            disabled={isProcessing}
            className="action-btn action-btn-danger"
            title="Delete selected"
          >
            🗑️ Delete
          </button>

          <button
            onClick={deselectAll}
            disabled={isProcessing}
            className="action-btn action-btn-ghost"
            title="Clear selection"
          >
            ✕
          </button>
        </div>
      </div>

      {isProcessing && (
        <div className="processing-overlay">
          <div className="spinner" />
          <span>Processing {selectedCount} conversations...</span>
        </div>
      )}

      {/* Tag Dialog */}
      {showTagDialog && (
        <div className="dialog-overlay" onClick={() => setShowTagDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Add Tags to {selectedCount} Conversations</h3>
            <input
              type="text"
              value={newTags}
              onChange={(e) => setNewTags(e.target.value)}
              placeholder="Enter tags (comma-separated)"
              onKeyDown={(e) => e.key === 'Enter' && handleTag()}
              autoFocus
            />
            <p className="hint">Example: important, work, review</p>
            <div className="dialog-actions">
              <button onClick={() => setShowTagDialog(false)} className="btn">Cancel</button>
              <button onClick={handleTag} className="btn btn-primary">Add Tags</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
