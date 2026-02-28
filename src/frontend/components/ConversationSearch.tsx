/**
 * ConversationSearch Component
 * 
 * Provides a search interface for filtering conversations with debouncing,
 * keyboard shortcuts, and real-time results.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, X, Filter, Calendar, Tag, Sparkles } from 'lucide-react';
import { useConversationSearch } from '../hooks/useConversationSearch';
import { ConversationFilters } from './ConversationFilters';
import { FilterChips } from './FilterChips';

interface ConversationSearchProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  placeholder?: string;
  className?: string;
}

export interface SearchFilters {
  dateRange?: { start: Date; end: Date };
  models?: string[];
  tags?: string[];
  hasAttachments?: boolean;
  minMessages?: number;
}

export const ConversationSearch: React.FC<ConversationSearchProps> = ({
  onSearch,
  placeholder = 'Search conversations...',
  className = '',
}) => {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({});
  const inputRef = useRef<HTMLInputElement>(null);
  
  const { debouncedSearch, isSearching, searchResults } = useConversationSearch({
    debounceMs: 300,
  });

  // Keyboard shortcut (Cmd/Ctrl + K) to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      
      // Escape to clear search
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        handleClear();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Trigger search when query or filters change
  useEffect(() => {
    if (query || Object.keys(filters).length > 0) {
      debouncedSearch(query, filters);
      onSearch(query, filters);
    }
  }, [query, filters, debouncedSearch, onSearch]);

  const handleClear = useCallback(() => {
    setQuery('');
    setFilters({});
    onSearch('', {});
    inputRef.current?.blur();
  }, [onSearch]);

  const handleFilterChange = useCallback((newFilters: SearchFilters) => {
    setFilters(newFilters);
  }, []);

  const handleRemoveFilter = useCallback((filterKey: keyof SearchFilters) => {
    setFilters((prev) => {
      const updated = { ...prev };
      delete updated[filterKey];
      return updated;
    });
  }, []);

  const activeFilterCount = Object.keys(filters).length;
  const hasActiveSearch = query.length > 0 || activeFilterCount > 0;

  return (
    <div className={`conversation-search ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <div className="flex items-center gap-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
          <Search className="w-5 h-5 text-gray-400 ml-3" />
          
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="flex-1 py-3 px-2 bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400"
            aria-label="Search conversations"
          />

          {isSearching && (
            <div className="flex items-center pr-3">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500" />
            </div>
          )}

          {hasActiveSearch && (
            <button
              onClick={handleClear}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              aria-label="Clear search"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 mr-2 rounded-md transition-colors ${
              activeFilterCount > 0
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400'
            }`}
            aria-label="Toggle filters"
          >
            <Filter className="w-4 h-4" />
            {activeFilterCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Keyboard Shortcut Hint */}
        <div className="absolute right-16 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-1 text-xs text-gray-400 pointer-events-none">
          <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">
            {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}
          </kbd>
          <span>+</span>
          <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">
            K
          </kbd>
        </div>
      </div>

      {/* Active Filter Chips */}
      {activeFilterCount > 0 && (
        <FilterChips filters={filters} onRemove={handleRemoveFilter} />
      )}

      {/* Advanced Filters Panel */}
      {showFilters && (
        <ConversationFilters
          filters={filters}
          onChange={handleFilterChange}
          onClose={() => setShowFilters(false)}
        />
      )}

      {/* Search Results Count */}
      {hasActiveSearch && searchResults !== null && (
        <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          {searchResults === 0 ? (
            <span>No conversations found</span>
          ) : (
            <span>
              Found <strong>{searchResults}</strong> conversation{searchResults !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default ConversationSearch;
