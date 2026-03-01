/**
 * ConversationSorting Component
 * 
 * Advanced sorting and grouping controls for conversations.
 */

import React from 'react';
import { ConversationSort } from '../../types/conversation';
import './ConversationSorting.css';

interface Props {
  sort: ConversationSort;
  onSortChange: (sort: ConversationSort) => void;
  groupBy: 'none' | 'date' | 'model' | 'tag' | 'status';
  onGroupByChange: (groupBy: string) => void;
}

export const ConversationSorting: React.FC<Props> = ({
  sort,
  onSortChange,
  groupBy,
  onGroupByChange,
}) => {
  const sortOptions: Array<{ value: ConversationSort['field']; label: string; icon: string }> = [
    { value: 'lastMessageAt', label: 'Last Activity', icon: '⏰' },
    { value: 'createdAt', label: 'Date Created', icon: '📅' },
    { value: 'updatedAt', label: 'Date Updated', icon: '🔄' },
    { value: 'title', label: 'Title', icon: '🎯' },
    { value: 'messageCount', label: 'Messages', icon: '💬' },
  ];

  const groupOptions = [
    { value: 'none', label: 'No Grouping', icon: '📋' },
    { value: 'date', label: 'Group by Date', icon: '📅' },
    { value: 'model', label: 'Group by Model', icon: '🤖' },
    { value: 'tag', label: 'Group by Tag', icon: '🏷️' },
    { value: 'status', label: 'Group by Status', icon: '🟢' },
  ];

  return (
    <div className="conversation-sorting">
      <div className="sorting-section">
        <label className="section-label">Sort by:</label>
        <div className="sort-options">
          {sortOptions.map(option => (
            <button
              key={option.value}
              onClick={() => onSortChange({ ...sort, field: option.value })}
              className={`sort-option ${sort.field === option.value ? 'active' : ''}`}
              title={option.label}
            >
              <span className="option-icon">{option.icon}</span>
              <span className="option-label">{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="sorting-section">
        <label className="section-label">Direction:</label>
        <div className="direction-toggle">
          <button
            onClick={() => onSortChange({ ...sort, direction: 'desc' })}
            className={`direction-btn ${sort.direction === 'desc' ? 'active' : ''}`}
            aria-label="Sort descending"
          >
            ↓ Desc
          </button>
          <button
            onClick={() => onSortChange({ ...sort, direction: 'asc' })}
            className={`direction-btn ${sort.direction === 'asc' ? 'active' : ''}`}
            aria-label="Sort ascending"
          >
            ↑ Asc
          </button>
        </div>
      </div>

      <div className="sorting-section">
        <label className="section-label">Group by:</label>
        <select
          value={groupBy}
          onChange={(e) => onGroupByChange(e.target.value)}
          className="group-select"
        >
          {groupOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.icon} {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};
