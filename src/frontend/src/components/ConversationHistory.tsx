import React, { useState, useEffect, useCallback, useRef } from "react";
import "./ConversationHistory.css";

interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messageCount: number;
  tokenCount?: number;
  cost?: number;
  isPinned?: boolean;
  isArchived?: boolean;
}

interface ConversationHistoryProps {
  conversations: Conversation[];
  currentConversationId?: string;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation?: (id: string) => void;
  onPinConversation?: (id: string) => void;
  onArchiveConversation?: (id: string) => void;
}

const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onPinConversation,
  onArchiveConversation,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut for search (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === "Escape" && isSearchFocused) {
        searchInputRef.current?.blur();
        setSearchQuery("");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSearchFocused]);

  const getRelativeTime = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const groupConversationsByDate = (
    conversations: Conversation[]
  ): Record<string, Conversation[]> => {
    const now = new Date();
    const groups: Record<string, Conversation[]> = {
      Pinned: [],
      Today: [],
      Yesterday: [],
      "Last 7 Days": [],
      "Last 30 Days": [],
      Older: [],
    };

    conversations.forEach((conv) => {
      if (conv.isPinned) {
        groups.Pinned.push(conv);
        return;
      }

      const diffMs = now.getTime() - conv.timestamp.getTime();
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffDays === 0) {
        groups.Today.push(conv);
      } else if (diffDays === 1) {
        groups.Yesterday.push(conv);
      } else if (diffDays < 7) {
        groups["Last 7 Days"].push(conv);
      } else if (diffDays < 30) {
        groups["Last 30 Days"].push(conv);
      } else {
        groups.Older.push(conv);
      }
    });

    // Remove empty groups
    Object.keys(groups).forEach((key) => {
      if (groups[key].length === 0) {
        delete groups[key];
      }
    });

    return groups;
  };

  const filteredConversations = conversations.filter((conv) => {
    if (!showArchived && conv.isArchived) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        conv.title.toLowerCase().includes(query) ||
        conv.lastMessage.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const groupedConversations = groupConversationsByDate(filteredConversations);

  const handleConversationAction = (
    e: React.MouseEvent,
    action: () => void
  ) => {
    e.stopPropagation();
    action();
  };

  return (
    <div
      className={`conversation-history ${isCollapsed ? "collapsed" : ""}`}
      role="navigation"
      aria-label="Conversation history"
    >
      <div className="conversation-history-header">
        <button
          className="new-conversation-btn"
          onClick={onNewConversation}
          aria-label="Start new conversation"
        >
          <span className="icon">+</span>
          {!isCollapsed && <span>New Chat</span>}
        </button>
        <button
          className="collapse-btn"
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <span className="icon">{isCollapsed ? "→" : "←"}</span>
        </button>
      </div>

      {!isCollapsed && (
        <>
          <div className="search-container">
            <input
              ref={searchInputRef}
              type="text"
              className="search-input"
              placeholder="Search conversations... (⌘K)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setIsSearchFocused(false)}
              aria-label="Search conversations"
            />
            <span className="search-icon">🔍</span>
          </div>

          <div className="filter-controls">
            <button
              className={`filter-btn ${showArchived ? "active" : ""}`}
              onClick={() => setShowArchived(!showArchived)}
            >
              {showArchived ? "Hide" : "Show"} Archived
            </button>
          </div>

          <div className="conversations-list" role="list">
            {Object.keys(groupedConversations).length === 0 ? (
              <div className="empty-state">
                <p>No conversations found</p>
                {searchQuery && (
                  <button onClick={() => setSearchQuery("")}>Clear search</button>
                )}
              </div>
            ) : (
              Object.entries(groupedConversations).map(([group, convs]) => (
                <div key={group} className="conversation-group">
                  <h3 className="group-header">{group}</h3>
                  {convs.map((conv) => (
                    <div
                      key={conv.id}
                      className={`conversation-item ${
                        conv.id === currentConversationId ? "active" : ""
                      } ${conv.isPinned ? "pinned" : ""} ${
                        conv.isArchived ? "archived" : ""
                      }`}
                      onClick={() => onSelectConversation(conv.id)}
                      role="listitem"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onSelectConversation(conv.id);
                        }
                      }}
                    >
                      <div className="conversation-content">
                        <div className="conversation-header">
                          <h4 className="conversation-title">{conv.title}</h4>
                          {conv.isPinned && <span className="pin-badge">📌</span>}
                        </div>
                        <p className="conversation-preview">{conv.lastMessage}</p>
                        <div className="conversation-meta">
                          <span className="timestamp">
                            {getRelativeTime(conv.timestamp)}
                          </span>
                          <span className="message-count">
                            {conv.messageCount} messages
                          </span>
                          {conv.tokenCount !== undefined && (
                            <span className="token-count">
                              {conv.tokenCount.toLocaleString()} tokens
                            </span>
                          )}
                          {conv.cost !== undefined && conv.cost > 0 && (
                            <span className="cost">${conv.cost.toFixed(4)}</span>
                          )}
                        </div>
                      </div>
                      <div className="conversation-actions">
                        {onPinConversation && (
                          <button
                            className="action-btn"
                            onClick={(e) =>
                              handleConversationAction(e, () =>
                                onPinConversation(conv.id)
                              )
                            }
                            aria-label={conv.isPinned ? "Unpin" : "Pin"}
                            title={conv.isPinned ? "Unpin" : "Pin"}
                          >
                            {conv.isPinned ? "📌" : "📍"}
                          </button>
                        )}
                        {onArchiveConversation && (
                          <button
                            className="action-btn"
                            onClick={(e) =>
                              handleConversationAction(e, () =>
                                onArchiveConversation(conv.id)
                              )
                            }
                            aria-label={conv.isArchived ? "Unarchive" : "Archive"}
                            title={conv.isArchived ? "Unarchive" : "Archive"}
                          >
                            📦
                          </button>
                        )}
                        {onDeleteConversation && (
                          <button
                            className="action-btn delete"
                            onClick={(e) =>
                              handleConversationAction(e, () =>
                                onDeleteConversation(conv.id)
                              )
                            }
                            aria-label="Delete conversation"
                            title="Delete"
                          >
                            🗑️
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ConversationHistory;
