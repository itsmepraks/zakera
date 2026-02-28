/**
 * useConversationSearch Hook
 * 
 * Custom hook for managing conversation search with debouncing,
 * caching, and performance optimization.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { SearchFilters } from '../components/ConversationSearch';

interface UseConversationSearchOptions {
  debounceMs?: number;
  cacheResults?: boolean;
}

interface SearchCache {
  [key: string]: number; // key -> result count
}

export const useConversationSearch = (options: UseConversationSearchOptions = {}) => {
  const { debounceMs = 300, cacheResults = true } = options;
  
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const searchCache = useRef<SearchCache>({});
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const abortController = useRef<AbortController | null>(null);

  // Generate cache key from query and filters
  const getCacheKey = useCallback((query: string, filters: SearchFilters): string => {
    return JSON.stringify({ query, filters });
  }, []);

  // Check cache for existing results
  const checkCache = useCallback((key: string): number | null => {
    if (!cacheResults) return null;
    return searchCache.current[key] ?? null;
  }, [cacheResults]);

  // Perform the actual search
  const performSearch = useCallback(async (query: string, filters: SearchFilters) => {
    const cacheKey = getCacheKey(query, filters);
    
    // Check cache first
    const cachedResult = checkCache(cacheKey);
    if (cachedResult !== null) {
      setSearchResults(cachedResult);
      return;
    }

    // Cancel previous request
    if (abortController.current) {
      abortController.current.abort();
    }
    
    abortController.current = new AbortController();
    setIsSearching(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/conversations/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, filters }),
        signal: abortController.current.signal,
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      const resultCount = data.count || 0;
      
      setSearchResults(resultCount);
      
      // Cache the result
      if (cacheResults) {
        searchCache.current[cacheKey] = resultCount;
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Search error:', err);
        setError(err.message || 'Search failed');
        setSearchResults(null);
      }
    } finally {
      setIsSearching(false);
    }
  }, [getCacheKey, checkCache, cacheResults]);

  // Debounced search function
  const debouncedSearch = useCallback((query: string, filters: SearchFilters) => {
    // Clear existing timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // If query is empty and no filters, clear results immediately
    if (!query && Object.keys(filters).length === 0) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }

    // Set debounce timer
    debounceTimer.current = setTimeout(() => {
      performSearch(query, filters);
    }, debounceMs);
  }, [debounceMs, performSearch]);

  // Clear cache function
  const clearCache = useCallback(() => {
    searchCache.current = {};
  }, []);

  // Reset search state
  const reset = useCallback(() => {
    setSearchResults(null);
    setError(null);
    setIsSearching(false);
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    if (abortController.current) {
      abortController.current.abort();
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
      if (abortController.current) {
        abortController.current.abort();
      }
    };
  }, []);

  return {
    isSearching,
    searchResults,
    error,
    debouncedSearch,
    clearCache,
    reset,
  };
};

export default useConversationSearch;
