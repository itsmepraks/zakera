/**
 * Conversation Search Component
 * Provides real-time search functionality with highlighting
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { debounce } from 'lodash';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
}

interface SearchResult {
  conversationId: string;
  conversationTitle: string;
  messageId: string;
  messageContent: string;
  matchIndex: number;
  matchLength: number;
}

interface ConversationSearchProps {
  conversations: Conversation[];
  onResultClick: (conversationId: string, messageId: string) => void;
  placeholder?: string;
  className?: string;
}

const ConversationSearch: React.FC<ConversationSearchProps> = ({
  conversations,
  onResultClick,
  placeholder = 'Search conversations...',
  className = '',
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Search function
  const performSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    const query = searchQuery.toLowerCase();
    const searchResults: SearchResult[] = [];

    conversations.forEach(conversation => {
      // Search in conversation title
      const titleIndex = conversation.title.toLowerCase().indexOf(query);
      if (titleIndex !== -1) {
        searchResults.push({
          conversationId: conversation.id,
          conversationTitle: conversation.title,
          messageId: '',
          messageContent: conversation.title,
          matchIndex: titleIndex,
          matchLength: query.length,
        });
      }

      // Search in messages
      conversation.messages.forEach(message => {
        const contentIndex = message.content.toLowerCase().indexOf(query);
        if (contentIndex !== -1) {
          searchResults.push({
            conversationId: conversation.id,
            conversationTitle: conversation.title,
            messageId: message.id,
            messageContent: message.content,
            matchIndex: contentIndex,
            matchLength: query.length,
          });
        }
      });
    });

    setResults(searchResults.slice(0, 10)); // Limit to 10 results
    setSelectedIndex(0);
  }, [conversations]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((query: string) => performSearch(query), 300),
    [performSearch]
  );

  useEffect(() => {
    debouncedSearch(query);
    return () => debouncedSearch.cancel();
  }, [query, debouncedSearch]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }

      // Escape to close
      if (e.key === 'Escape') {
        setIsOpen(false);
        inputRef.current?.blur();
      }

      // Arrow keys navigation
      if (isOpen && results.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, results.length - 1));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter') {
          e.preventDefault();
          const result = results[selectedIndex];
          if (result) {
            handleResultClick(result);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, results, selectedIndex]);

  const handleResultClick = (result: SearchResult) => {
    onResultClick(result.conversationId, result.messageId);
    setIsOpen(false);
    setQuery('');
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    inputRef.current?.focus();
  };

  const highlightMatch = (text: string, matchIndex: number, matchLength: number) => {
    const before = text.slice(0, matchIndex);
    const match = text.slice(matchIndex, matchIndex + matchLength);
    const after = text.slice(matchIndex + matchLength);

    return (
      <>
        {before}
        <mark className="bg-yellow-200 dark:bg-yellow-900 text-gray-900 dark:text-gray-100 px-0.5 rounded">
          {match}
        </mark>
        {after}
      </>
    );
  };

  const truncateText = (text: string, matchIndex: number, contextLength: number = 50) => {
    const start = Math.max(0, matchIndex - contextLength);
    const end = Math.min(text.length, matchIndex + contextLength + query.length);
    const truncated = text.slice(start, end);
    
    return (
      <>
        {start > 0 && '...'}
        {truncated}
        {end < text.length && '...'}
      </>
    );
  };

  return (
    <div className={`relative ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className="
            w-full pl-10 pr-10 py-2.5 
            bg-white dark:bg-gray-800
            border border-gray-300 dark:border-gray-700
            rounded-lg
            text-gray-900 dark:text-gray-100
            placeholder-gray-500 dark:placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-primary-500
            transition-colors duration-200
          "
          aria-label="Search conversations"
        />
        {query && (
          <button
            onClick={handleClear}
            className="
              absolute right-3 top-1/2 -translate-y-1/2
              p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
              transition-colors duration-200
            "
            aria-label="Clear search"
          >
            <XMarkIcon className="w-4 h-4 text-gray-400" />
          </button>
        )}
      </div>

      {/* Keyboard Shortcut Hint */}
      {!query && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 pointer-events-none">
          <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">⌘K</kbd>
        </div>
      )}

      {/* Search Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div
          ref={resultsRef}
          className="
            absolute top-full mt-2 w-full
            bg-white dark:bg-gray-800
            border border-gray-200 dark:border-gray-700
            rounded-lg shadow-lg
            max-h-96 overflow-y-auto
            z-50
          "
        >
          {results.map((result, index) => (
            <button
              key={`${result.conversationId}-${result.messageId}-${index}`}
              onClick={() => handleResultClick(result)}
              className={`
                w-full px-4 py-3 text-left
                border-b border-gray-100 dark:border-gray-700 last:border-b-0
                hover:bg-gray-50 dark:hover:bg-gray-750
                transition-colors duration-150
                ${index === selectedIndex ? 'bg-gray-50 dark:bg-gray-750' : ''}
              `}
            >
              {/* Conversation Title */}
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                {result.messageId 
                  ? result.conversationTitle
                  : highlightMatch(result.conversationTitle, result.matchIndex, result.matchLength)
                }
              </div>
              
              {/* Message Content (if applicable) */}
              {result.messageId && (
                <div className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                  {truncateText(result.messageContent, result.matchIndex)}
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* No Results */}
      {isOpen && query && results.length === 0 && (
        <div className="
          absolute top-full mt-2 w-full
          bg-white dark:bg-gray-800
          border border-gray-200 dark:border-gray-700
          rounded-lg shadow-lg
          px-4 py-8 text-center
          z-50
        ">
          <MagnifyingGlassIcon className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-600 dark:text-gray-400">
            No results found for &quot;{query}&quot;
          </p>
        </div>
      )}
    </div>
  );
};

export default ConversationSearch;
