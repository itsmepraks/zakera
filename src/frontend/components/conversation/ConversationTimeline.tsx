/**
 * ConversationTimeline Component
 * 
 * Interactive timeline visualization of conversation history.
 * Features scrubbing, branching visualization, and time-travel preview.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Message, Branch } from '../../types/conversation';
import './ConversationTimeline.css';

interface Props {
  messages: Message[];
  branches: Branch[];
  currentBranchId: string;
  selectedMessageId?: string;
  onMessageSelect: (messageId: string) => void;
  onBranchSwitch: (branchId: string) => void;
}

export const ConversationTimeline: React.FC<Props> = ({
  messages,
  branches,
  currentBranchId,
  selectedMessageId,
  onMessageSelect,
  onBranchSwitch,
}) => {
  const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);
  const [scrubPosition, setScrubPosition] = useState<number>(messages.length - 1);

  // Group messages by date
  const groupedMessages = useMemo(() => {
    const groups: Record<string, Message[]> = {};
    
    messages.forEach(message => {
      const date = new Date(message.timestamp).toLocaleDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(message);
    });

    return groups;
  }, [messages]);

  // Calculate branch points
  const branchPoints = useMemo(() => {
    const points = new Set<string>();
    messages.forEach(msg => {
      if (msg.metadata?.branchPoint) {
        points.add(msg.id);
      }
    });
    return points;
  }, [messages]);

  const handleScrub = useCallback((position: number) => {
    setScrubPosition(Math.max(0, Math.min(messages.length - 1, position)));
    if (messages[position]) {
      onMessageSelect(messages[position].id);
    }
  }, [messages, onMessageSelect]);

  const getBranchColor = (branchId: string): string => {
    const branch = branches.find(b => b.id === branchId);
    return branch?.metadata?.color || '#3b82f6';
  };

  return (
    <div className="conversation-timeline">
      <div className="timeline-header">
        <h3>Timeline</h3>
        <div className="timeline-info">
          {messages.length} messages across {branches.length} branches
        </div>
      </div>

      <div className="timeline-scrubber">
        <input
          type="range"
          min="0"
          max={messages.length - 1}
          value={scrubPosition}
          onChange={(e) => handleScrub(parseInt(e.target.value))}
          className="scrubber-slider"
        />
        <div className="scrubber-label">
          Message {scrubPosition + 1} of {messages.length}
        </div>
      </div>

      <div className="timeline-content">
        {Object.entries(groupedMessages).map(([date, dateMessages]) => (
          <div key={date} className="timeline-group">
            <div className="group-date">{date}</div>
            
            <div className="timeline-messages">
              {dateMessages.map((message, idx) => {
                const isSelected = message.id === selectedMessageId;
                const isHovered = message.id === hoveredMessageId;
                const isBranchPoint = branchPoints.has(message.id);
                const timestamp = new Date(message.timestamp).toLocaleTimeString();

                return (
                  <div
                    key={message.id}
                    className={`timeline-message ${
                      isSelected ? 'selected' : ''
                    } ${isHovered ? 'hovered' : ''} ${
                      isBranchPoint ? 'branch-point' : ''
                    }`}
                    onClick={() => onMessageSelect(message.id)}
                    onMouseEnter={() => setHoveredMessageId(message.id)}
                    onMouseLeave={() => setHoveredMessageId(null)}
                  >
                    <div className="message-marker">
                      <div 
                        className="marker-dot"
                        style={{ background: message.role === 'user' ? '#3b82f6' : '#10b981' }}
                      />
                      {isBranchPoint && (
                        <div className="branch-indicator" title="Branch point">
                          🌳
                        </div>
                      )}
                    </div>

                    <div className="message-content">
                      <div className="message-header">
                        <span className="message-role">
                          {message.role === 'user' ? '👤 You' : '🤖 Assistant'}
                        </span>
                        <span className="message-time">{timestamp}</span>
                      </div>
                      
                      <div className="message-preview">
                        {message.content.slice(0, 100)}
                        {message.content.length > 100 ? '...' : ''}
                      </div>

                      {message.model && (
                        <div className="message-meta">
                          Model: {message.model}
                          {message.tokens && (
                            <> • {message.tokens.total} tokens</>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Branch switcher */}
      {branches.length > 1 && (
        <div className="timeline-branches">
          <div className="branches-label">Branches:</div>
          <div className="branch-pills">
            {branches.map(branch => (
              <button
                key={branch.id}
                className={`branch-pill ${branch.id === currentBranchId ? 'active' : ''}`}
                style={{
                  borderColor: getBranchColor(branch.id),
                  background: branch.id === currentBranchId 
                    ? getBranchColor(branch.id) 
                    : 'transparent',
                }}
                onClick={() => onBranchSwitch(branch.id)}
                title={`${branch.messageCount} messages`}
              >
                {branch.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
