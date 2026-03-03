/**
 * MessageSearch Component
 * 
 * Provides real-time search within conversation messages with navigation.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import './MessageSearch.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface MessageSearchProps {
  messages: Message[];
  onResultSelect: (messageId: string, resultIndex: number) => void;
  className?: string;
}

const MessageSearch: React.FC<MessageSearchProps> = ({
  messages,
  onResultSelect,
  className = ''
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{messageId: string; indices: number[]}>>([]);
  const [currentResultIndex, setCurrentResultIndex] = useState(0);
  const [isSearchVisible, setIsSearchVisible] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.trim()) {
        performSearch(searchQuery);
      } else {
        setSearchResults([]);
        setCurrentResultIndex(0);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery, messages]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + F to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault();
        setIsSearchVisible(true);
        setTimeout(() => searchInputRef.current?.focus(), 100);
      }
      // Escape to close search
      if (e.key === 'Escape' && isSearchVisible) {
        setIsSearchVisible(false);
        setSearchQuery('');
        setSearchResults([]);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSearchVisible]);

  const performSearch = useCallback((query: string) => {
    const results: Array<{messageId: string; indices: number[]}> = [];
    const lowerQuery = query.toLowerCase();

    messages.forEach(message => {
      const lowerContent = message.content.toLowerCase();
      const indices: number[] = [];
      let startIndex = 0;

      while (true) {
        const index = lowerContent.indexOf(lowerQuery, startIndex);
        if (index === -1) break;
        indices.push(index);
        startIndex = index + 1;
      }

      if (indices.length > 0) {
        results.push({ messageId: message.id, indices });
      }
    });

    setSearchResults(results);
    setCurrentResultIndex(0);

    if (results.length > 0) {
      onResultSelect(results[0].messageId, 0);
    }
  }, [messages, onResultSelect]);

  const handleNext = () => {
    if (searchResults.length === 0) return;

    const totalResults = searchResults.reduce((sum, r) => sum + r.indices.length, 0);
    const nextIndex = (currentResultIndex + 1) % totalResults;
    setCurrentResultIndex(nextIndex);

    // Find which message and which occurrence
    let count = 0;
    for (const result of searchResults) {
      if (count + result.indices.length > nextIndex) {
        const occurrenceIndex = nextIndex - count;
        onResultSelect(result.messageId, occurrenceIndex);
        break;
      }
      count += result.indices.length;
    }
  };

  const handlePrevious = () => {
    if (searchResults.length === 0) return;

    const totalResults = searchResults.reduce((sum, r) => sum + r.indices.length, 0);
    const prevIndex = currentResultIndex === 0 ? totalResults - 1 : currentResultIndex - 1;
    setCurrentResultIndex(prevIndex);

    // Find which message and which occurrence
    let count = 0;
    for (const result of searchResults) {
      if (count + result.indices.length > prevIndex) {
        const occurrenceIndex = prevIndex - count;
        onResultSelect(result.messageId, occurrenceIndex);
        break;
      }
      count += result.indices.length;
    }
  };

  const totalResults = searchResults.reduce((sum, r) => sum + r.indices.length, 0);

  if (!isSearchVisible) {
    return (
      <button
        className="search-toggle-button"
        onClick={() => setIsSearchVisible(true)}
        aria-label="Open search"
        title="Search in conversation (Ctrl+F)"
      >
        🔍
      </button>
    );
  }

  return (
    <div className={`message-search ${className}`}>
      <div className="search-container">
        <div className="search-input-group">
          <svg className="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M11.5 11.5l3 3m-10-6a5 5 0 1010 0 5 5 0 00-10 0z" stroke="currentColor" strokeWidth="1.5" fill="none"/>
          </svg>
          <input
            ref={searchInputRef}
            type="text"
            className="search-input"
            placeholder="Search in conversation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            autoFocus
          />
          {searchQuery && (
            <button
              className="clear-button"
              onClick={() => {
                setSearchQuery('');
                setSearchResults([]);
              }}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        {searchQuery && (
          <div className="search-results-info">
            <span className="result-count">
              {totalResults > 0 
                ? `${currentResultIndex + 1} / ${totalResults}`
                : 'No results'
              }
            </span>
            <div className="navigation-buttons">
              <button
                className="nav-button"
                onClick={handlePrevious}
                disabled={totalResults === 0}
                aria-label="Previous result"
                title="Previous (Shift+Enter)"
              >
                ↑
              </button>
              <button
                className="nav-button"
                onClick={handleNext}
                disabled={totalResults === 0}
                aria-label="Next result"
                title="Next (Enter)"
              >
                ↓
              </button>
            </div>
          </div>
        )}

        <button
          className="close-search-button"
          onClick={() => {
            setIsSearchVisible(false);
            setSearchQuery('');
            setSearchResults([]);
          }}
          aria-label="Close search"
          title="Close (Esc)"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default MessageSearch;
