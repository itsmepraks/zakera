/**
 * ConversationComparison Component
 * 
 * Side-by-side comparison of two conversation branches.
 * Shows differences, common messages, and branch points.
 */

import React, { useMemo } from 'react';
import { Branch, Message } from '../../types/conversation';
import './ConversationComparison.css';

interface Props {
  leftBranch: Branch;
  rightBranch: Branch;
  onClose: () => void;
}

export const ConversationComparison: React.FC<Props> = ({
  leftBranch,
  rightBranch,
  onClose,
}) => {
  // Find common ancestor messages
  const { commonMessages, leftOnly, rightOnly, divergePoint } = useMemo(() => {
    const leftMsgs = leftBranch.messages;
    const rightMsgs = rightBranch.messages;
    
    let divergeIndex = 0;
    while (
      divergeIndex < leftMsgs.length &&
      divergeIndex < rightMsgs.length &&
      leftMsgs[divergeIndex].id === rightMsgs[divergeIndex].id
    ) {
      divergeIndex++;
    }

    return {
      commonMessages: leftMsgs.slice(0, divergeIndex),
      leftOnly: leftMsgs.slice(divergeIndex),
      rightOnly: rightMsgs.slice(divergeIndex),
      divergePoint: divergeIndex,
    };
  }, [leftBranch, rightBranch]);

  return (
    <div className="conversation-comparison">
      <div className="comparison-header">
        <h2>Branch Comparison</h2>
        <button onClick={onClose} className="close-btn" aria-label="Close">
          ✕
        </button>
      </div>

      <div className="comparison-info">
        <div className="branch-card left">
          <h3>{leftBranch.name}</h3>
          <div className="branch-stats">
            <span>{leftBranch.messageCount} messages</span>
            <span>{leftOnly.length} unique</span>
          </div>
        </div>

        <div className="vs-indicator">
          <span>VS</span>
        </div>

        <div className="branch-card right">
          <h3>{rightBranch.name}</h3>
          <div className="branch-stats">
            <span>{rightBranch.messageCount} messages</span>
            <span>{rightOnly.length} unique</span>
          </div>
        </div>
      </div>

      <div className="comparison-content">
        {/* Common messages */}
        {commonMessages.length > 0 && (
          <div className="common-section">
            <div className="section-header">
              🔗 Common History ({commonMessages.length} messages)
            </div>
            <div className="message-preview">
              Last common message: {commonMessages[commonMessages.length - 1]?.content.slice(0, 100)}...
            </div>
          </div>
        )}

        {/* Divergence point */}
        {divergePoint > 0 && (
          <div className="diverge-indicator">
            <div className="diverge-line" />
            <div className="diverge-label">
              🌳 Branches diverge here (at message {divergePoint})
            </div>
            <div className="diverge-line" />
          </div>
        )}

        {/* Side-by-side diff */}
        <div className="diff-view">
          <div className="diff-column left">
            <div className="column-header">
              {leftBranch.name} ({leftOnly.length})
            </div>
            <div className="message-list">
              {leftOnly.map((msg, idx) => (
                <div key={msg.id} className="message-item left-only">
                  <div className="message-number">{divergePoint + idx + 1}</div>
                  <div className="message-content">
                    <div className="message-role">
                      {msg.role === 'user' ? '👤' : '🤖'} {msg.role}
                    </div>
                    <div className="message-text">{msg.content}</div>
                    {msg.model && (
                      <div className="message-meta">Model: {msg.model}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="diff-column right">
            <div className="column-header">
              {rightBranch.name} ({rightOnly.length})
            </div>
            <div className="message-list">
              {rightOnly.map((msg, idx) => (
                <div key={msg.id} className="message-item right-only">
                  <div className="message-number">{divergePoint + idx + 1}</div>
                  <div className="message-content">
                    <div className="message-role">
                      {msg.role === 'user' ? '👤' : '🤖'} {msg.role}
                    </div>
                    <div className="message-text">{msg.content}</div>
                    {msg.model && (
                      <div className="message-meta">Model: {msg.model}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="comparison-footer">
        <div className="diff-summary">
          <span className="stat">
            <span className="stat-label">Common:</span>
            <span className="stat-value">{commonMessages.length}</span>
          </span>
          <span className="stat left-stat">
            <span className="stat-label">{leftBranch.name}:</span>
            <span className="stat-value">+{leftOnly.length}</span>
          </span>
          <span className="stat right-stat">
            <span className="stat-label">{rightBranch.name}:</span>
            <span className="stat-value">+{rightOnly.length}</span>
          </span>
        </div>
      </div>
    </div>
  );
};
