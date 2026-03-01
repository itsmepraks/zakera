/**
 * ConversationListEnhanced Component
 * 
 * Feature-rich conversation list with all management capabilities.
 * Integrates searching, filtering, sorting, grouping, bulk actions, and branching.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Conversation, ConversationFilter, ConversationSort } from '../../types/conversation';
import { ConversationBulkActions } from './ConversationBulkActions';
import { ConversationSorting } from './ConversationSorting';
import { QuickActionsMenu } from './QuickActionsMenu';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import { matchesFilter, sortConversations, groupConversations } from '../../utils/conversationUtils';
import './ConversationListEnhanced.css';

interface Props {
  conversations: Conversation[];
  onConversationSelect: (conversation: Conversation) => void;
  onConversationAction: (action: string, conversation: Conversation) => void;
  filter?: ConversationFilter;
  onFilterChange?: (filter: ConversationFilter) => void;
}

export const ConversationListEnhanced: React.FC<Props> = ({
  conversations,
  onConversationSelect,
  onConversationAction,
  filter = {},
  onFilterChange,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [sort, setSort] = useState<ConversationSort>({
    field: 'lastMessageAt',
    direction: 'desc',
  });
  const [groupBy, setGroupBy] = useState<string>('none');
  const [showQuickActions, setShowQuickActions] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Filter conversations
  const filteredConversations = useMemo(
    () => conversations.filter(c => matchesFilter(c, filter)),
    [conversations, filter]
  );

  // Sort conversations
  const sortedConversations = useMemo(
    () => sortConversations(filteredConversations, sort),
    [filteredConversations, sort]
  );

  // Group conversations
  const groupedConversations = useMemo(
    () => groupBy === 'none' 
      ? new Map([['All Conversations', sortedConversations]])
      : groupConversations(sortedConversations, groupBy),
    [sortedConversations, groupBy]
  );

  // Quick actions
  const quickActions = useMemo(() => [
    {
      id: 'new-conversation',
      label: 'New Conversation',
      description: 'Start a new chat',
      icon: '➕',
      category: 'Conversations',
      shortcut: '⌘N',
      handler: () => onConversationAction('create', {} as Conversation),
      keywords: ['create', 'start', 'new'],
    },
    {
      id: 'search',
      label: 'Search',
      description: 'Find conversations',
      icon: '🔍',
      category: 'Navigation',
      shortcut: '⌘F',
      handler: () => document.getElementById('search-input')?.focus(),
      keywords: ['find', 'filter'],
    },
    {
      id: 'toggle-branches',
      label: 'Toggle Branches',
      description: 'Show/hide branch tree',
      icon: '🌳',
      category: 'View',
      shortcut: '⌘B',
      handler: () => console.log('Toggle branches'),
      keywords: ['branch', 'tree'],
    },
  ], [onConversationAction]);

  // Keyboard shortcuts
  const shortcuts = useMemo(() => [
    {
      key: 'k',
      metaKey: true,
      description: 'Quick actions',
      handler: () => setShowQuickActions(true),
      enabled: true,
    },
    {
      key: 'a',
      metaKey: true,
      description: 'Select all',
      handler: () => {
        const allIds = new Set(filteredConversations.map(c => c.id));
        setSelectedIds(allIds);
      },
      enabled: true,
    },
    {
      key: 'Escape',
      description: 'Clear selection',
      handler: () => setSelectedIds(new Set()),
      enabled: selectedIds.size > 0,
    },
  ], [filteredConversations, selectedIds.size]);

  useKeyboardShortcuts(shortcuts);

  const toggleGroup = (groupKey: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
    } else {
      newExpanded.add(groupKey);
    }
    setExpandedGroups(newExpanded);
  };

  // Bulk operation handlers
  const handleBulkDelete = async (ids: string[]) => {
    for (const id of ids) {
      const conv = conversations.find(c => c.id === id);
      if (conv) await onConversationAction('delete', conv);
    }
  };

  const handleBulkArchive = async (ids: string[]) => {
    for (const id of ids) {
      const conv = conversations.find(c => c.id === id);
      if (conv) await onConversationAction('archive', conv);
    }
  };

  const handleBulkExport = async (ids: string[], format: string) => {
    console.log(`Exporting ${ids.length} conversations as ${format}`);
  };

  const handleBulkTag = async (ids: string[], tags: string[]) => {
    for (const id of ids) {
      const conv = conversations.find(c => c.id === id);
      if (conv) {
        await onConversationAction('tag', { ...conv, tags: [...conv.tags, ...tags] });
      }
    }
  };

  return (
    <div className="conversation-list-enhanced">
      {/* Quick Actions Menu */}
      <QuickActionsMenu
        actions={quickActions}
        isOpen={showQuickActions}
        onClose={() => setShowQuickActions(false)}
      />

      {/* Bulk Actions Bar */}
      {selectedIds.size > 0 && (
        <ConversationBulkActions
          conversations={filteredConversations}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onBulkDelete={handleBulkDelete}
          onBulkArchive={handleBulkArchive}
          onBulkExport={handleBulkExport}
          onBulkTag={handleBulkTag}
        />
      )}

      {/* Sorting Controls */}
      <ConversationSorting
        sort={sort}
        onSortChange={setSort}
        groupBy={groupBy}
        onGroupByChange={setGroupBy}
      />

      {/* Conversation Groups */}
      <div className="conversation-groups">
        {Array.from(groupedConversations.entries()).map(([groupKey, groupConvs]) => {
          const isExpanded = expandedGroups.has(groupKey) || groupBy === 'none';

          return (
            <div key={groupKey} className="conversation-group">
              {groupBy !== 'none' && (
                <button
                  className="group-header"
                  onClick={() => toggleGroup(groupKey)}
                >
                  <span className="expand-icon">
                    {isExpanded ? '▼' : '▶'}
                  </span>
                  <span className="group-name">{groupKey}</span>
                  <span className="group-count">{groupConvs.length}</span>
                </button>
              )}

              {isExpanded && (
                <div className="conversation-items">
                  {groupConvs.map((conversation, index) => {
                    const isSelected = selectedIds.has(conversation.id);

                    return (
                      <div
                        key={conversation.id}
                        className={`conversation-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => onConversationSelect(conversation)}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {
                            const newSelected = new Set(selectedIds);
                            if (newSelected.has(conversation.id)) {
                              newSelected.delete(conversation.id);
                            } else {
                              newSelected.add(conversation.id);
                            }
                            setSelectedIds(newSelected);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="conversation-checkbox"
                        />

                        <div className="conversation-content">
                          <div className="conversation-header">
                            <h4 className="conversation-title">{conversation.title}</h4>
                            {conversation.metadata?.pinned && <span>📌</span>}
                            {conversation.metadata?.starred && <span>⭐</span>}
                          </div>

                          <div className="conversation-meta">
                            <span>{conversation.messageCount} messages</span>
                            <span>•</span>
                            <span>{conversation.branches.length} branches</span>
                            <span>•</span>
                            <span>
                              {new Date(conversation.updatedAt).toLocaleDateString()}
                            </span>
                          </div>

                          {conversation.tags.length > 0 && (
                            <div className="conversation-tags">
                              {conversation.tags.map(tag => (
                                <span key={tag} className="tag">{tag}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filteredConversations.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">💭</div>
          <h3>No conversations found</h3>
          <p>Try adjusting your filters or create a new conversation</p>
          <button
            onClick={() => onConversationAction('create', {} as Conversation)}
            className="btn btn-primary"
          >
            + New Conversation
          </button>
        </div>
      )}
    </div>
  );
};
