/**
 * Conversation Search Component
 * 
 * Provides real-time search functionality with text highlighting.
 * Supports searching through conversation history with debouncing.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { debounce } from 'lodash';
import './ConversationSearch.css';

export interface SearchResult {
  conversationId: string;
  messageId: string;
  content: string;
  timestamp: Date;
  role: 'user' | 'assistant';
  highlightedContent?: string;
}

interface ConversationSearchProps {
  conversations: any[];
  onResultClick: (result: SearchResult) => void;
  onClose?: () => void;
  placeholder?: string;
}

export const ConversationSearch: React.FC<ConversationSearchProps> = ({
  conversations,
  onResultClick,
  onClose,
  placeholder = 'Search conversations...',
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Highlight matching text
  const highlightMatch = (text: string, query: string): string => {
    if (!query.trim()) return text;
    
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  };

  // Escape special regex characters
  const escapeRegex = (str: string): string => {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  };

  // Search through conversations
  const performSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    
    const searchResults: SearchResult[] = [];
    const lowerQuery = searchQuery.toLowerCase();

    conversations.forEach((conversation) => {
      conversation.messages?.forEach((message: any) => {
        const content = message.content || '';
        const lowerContent = content.toLowerCase();
        
        if (lowerContent.includes(lowerQuery)) {
          searchResults.push({
            conversationId: conversation.id,
            messageId: message.id,
            content,
            timestamp: new Date(message.timestamp),
            role: message.role,
            highlightedContent: highlightMatch(content, searchQuery),
          });
        }
      });
    });

    // Sort by relevance and recency
    searchResults.sort((a, b) => {
      // First by how many times the query appears
      const aCount = (a.content.toLowerCase().match(new RegExp(lowerQuery, 'g')) || []).length;
      const bCount = (b.content.toLowerCase().match(new RegExp(lowerQuery, 'g')) || []).length;
      
      if (aCount !== bCount) {
        return bCount - aCount;
      }
      
      // Then by timestamp
      return b.timestamp.getTime() - a.timestamp.getTime();
    });

    setResults(searchResults.slice(0, 50)); // Limit to 50 results
    setSelectedIndex(0);
    setIsSearching(false);
  }, [conversations]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((query: string) => performSearch(query), 300),
    [performSearch]
  );

  // Handle query change
  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setQuery(newQuery);
    debouncedSearch(newQuery);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < results.length - 1 ? prev + 1 : prev
        );
        break;
      
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : 0);
        break;
      
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          onResultClick(results[selectedIndex]);
        }
        break;
      
      case 'Escape':
        e.preventDefault();
        onClose?.();
        break;
    }
  };

  // Scroll selected result into view
  useEffect(() => {
    const selectedElement = resultsRef.current?.children[selectedIndex] as HTMLElement;
    if (selectedElement) {
      selectedElement.scrollIntoView({
        block: 'nearest',
        behavior: 'smooth',
      });
    }
  }, [selectedIndex]);

  // Format timestamp
  const formatTimestamp = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  };

  // Truncate content for preview
  const truncateContent = (content: string, maxLength: number = 150): string => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  return (
    <div className="conversation-search">
      <div className="search-header">
        <div className="search-input-container">
          <svg
            className="search-icon"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            className="search-input"
            placeholder={placeholder}
            value={query}
            onChange={handleQueryChange}
            onKeyDown={handleKeyDown}
          />
          {query && (
            <button
              className="clear-button"
              onClick={() => {
                setQuery('');
                setResults([]);
                inputRef.current?.focus();
              }}
              aria-label="Clear search"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
        {onClose && (
          <button
            className="close-button"
            onClick={onClose}
            aria-label="Close search"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      <div className="search-results" ref={resultsRef}>
        {isSearching && (
          <div className="search-status">
            <div className="spinner" />
            Searching...
          </div>
        )}

        {!isSearching && query && results.length === 0 && (
          <div className="search-status no-results">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <p>No results found for "{query}"</p>
            <p className="help-text">Try different keywords</p>
          </div>
        )}

        {!isSearching && !query && (
          <div className="search-status empty">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <p>Search your conversations</p>
            <p className="help-text">
              Use ↑↓ to navigate, Enter to select, Esc to close
            </p>
          </div>
        )}

        {!isSearching && results.length > 0 && (
          <>
            <div className="results-count">
              {results.length} result{results.length !== 1 ? 's' : ''} found
            </div>
            {results.map((result, index) => (
              <div
                key={`${result.conversationId}-${result.messageId}`}
                className={`search-result-item ${index === selectedIndex ? 'selected' : ''}`}
                onClick={() => onResultClick(result)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <div className="result-header">
                  <span className={`result-role ${result.role}`}>
                    {result.role === 'user' ? '👤 You' : '🤖 AI'}
                  </span>
                  <span className="result-timestamp">
                    {formatTimestamp(result.timestamp)}
                  </span>
                </div>
                <div
                  className="result-content"
                  dangerouslySetInnerHTML={{
                    __html: truncateContent(result.highlightedContent || result.content),
                  }}
                />
              </div>
            ))}
          </>
        )}
      </div>

      <div className="search-footer">
        <div className="keyboard-hints">
          <kbd>↑↓</kbd> Navigate
          <kbd>↵</kbd> Select
          <kbd>Esc</kbd> Close
        </div>
      </div>
    </div>
  );
};

export default ConversationSearch;
