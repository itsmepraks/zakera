/**
 * ConversationActions Component
 * 
 * Comprehensive action menu for individual conversations.
 */

import React, { useState } from 'react';
import { Conversation, ConversationAction } from '../../types/conversation';
import './ConversationActions.css';

interface Props {
  conversation: Conversation;
  actions: ConversationAction[];
  onAction: (action: ConversationAction) => void;
}

export const ConversationActions: React.FC<Props> = ({
  conversation,
  actions,
  onAction,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAction = async (action: ConversationAction) => {
    if (action.disabled?.(conversation)) return;
    
    if (action.dangerous) {
      if (!confirm(`Are you sure you want to ${action.label.toLowerCase()}?`)) {
        return;
      }
    }

    setIsProcessing(true);
    try {
      await onAction(action);
      setShowMenu(false);
    } catch (error) {
      console.error(`Action failed: ${action.label}`, error);
    } finally {
      setIsProcessing(false);
    }
  };

  const groupedActions = actions.reduce((groups, action) => {
    const category = action.dangerous ? 'Danger Zone' : 'Actions';
    if (!groups[category]) groups[category] = [];
    groups[category].push(action);
    return groups;
  }, {} as Record<string, ConversationAction[]>);

  return (
    <div className="conversation-actions">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="actions-trigger"
        aria-label="More actions"
        aria-expanded={showMenu}
        disabled={isProcessing}
      >
        ⋮
      </button>

      {showMenu && (
        <>
          <div className="actions-overlay" onClick={() => setShowMenu(false)} />
          <div className="actions-menu">
            {Object.entries(groupedActions).map(([category, categoryActions]) => (
              <div key={category} className="action-group">
                {category !== 'Actions' && (
                  <div className="group-label">{category}</div>
                )}
                {categoryActions.map(action => {
                  const disabled = action.disabled?.(conversation) || isProcessing;
                  
                  return (
                    <button
                      key={action.id}
                      onClick={() => handleAction(action)}
                      disabled={disabled}
                      className={`action-item ${
                        action.dangerous ? 'dangerous' : ''
                      } ${disabled ? 'disabled' : ''}`}
                      aria-label={action.label}
                    >
                      <span className="action-icon">{action.icon}</span>
                      <span className="action-label">{action.label}</span>
                      {action.shortcut && (
                        <kbd className="action-shortcut">{action.shortcut}</kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
