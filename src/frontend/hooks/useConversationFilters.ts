import { useState, useMemo, useCallback } from 'react';
import { debounce } from 'lodash';
import { isAfter, isBefore, parseISO } from 'date-fns';

interface Conversation {
  id: string;
  title: string;
  messages: Array<{ role: string; content: string }>;
  model: string;
  provider: string;
  createdAt: string;
  tags: string[];
  starred: boolean;
}

interface FilterState {
  searchQuery: string;
  selectedModel: string;
  selectedProvider: string;
  selectedTags: string[];
  dateRange: { start: string; end: string };
  showStarredOnly: boolean;
}

export const useConversationFilters = (conversations: Conversation[]) => {
  const [filters, setFilters] = useState<FilterState>({
    searchQuery: '',
    selectedModel: 'all',
    selectedProvider: 'all',
    selectedTags: [],
    dateRange: { start: '', end: '' },
    showStarredOnly: false,
  });

  // Fuzzy search implementation
  const fuzzyMatch = useCallback((text: string, query: string): boolean => {
    const lowerText = text.toLowerCase();
    const lowerQuery = query.toLowerCase();
    
    if (lowerText.includes(lowerQuery)) {
      return true;
    }

    let queryIndex = 0;
    for (let i = 0; i < lowerText.length && queryIndex < lowerQuery.length; i++) {
      if (lowerText[i] === lowerQuery[queryIndex]) {
        queryIndex++;
      }
    }
    return queryIndex === lowerQuery.length;
  }, []);

  // Filter conversations
  const filteredConversations = useMemo(() => {
    return conversations.filter((conv) => {
      // Search filter
      if (filters.searchQuery) {
        const searchMatch =
          fuzzyMatch(conv.title, filters.searchQuery) ||
          conv.messages.some((msg) => fuzzyMatch(msg.content, filters.searchQuery));
        if (!searchMatch) return false;
      }

      // Model filter
      if (filters.selectedModel !== 'all' && conv.model !== filters.selectedModel) {
        return false;
      }

      // Provider filter
      if (filters.selectedProvider !== 'all' && conv.provider !== filters.selectedProvider) {
        return false;
      }

      // Tag filter
      if (filters.selectedTags.length > 0) {
        const hasTag = filters.selectedTags.some((tag) => conv.tags.includes(tag));
        if (!hasTag) return false;
      }

      // Date range filter
      if (filters.dateRange.start) {
        const startDate = parseISO(filters.dateRange.start);
        if (isBefore(parseISO(conv.createdAt), startDate)) {
          return false;
        }
      }
      if (filters.dateRange.end) {
        const endDate = parseISO(filters.dateRange.end);
        if (isAfter(parseISO(conv.createdAt), endDate)) {
          return false;
        }
      }

      // Starred filter
      if (filters.showStarredOnly && !conv.starred) {
        return false;
      }

      return true;
    });
  }, [conversations, filters, fuzzyMatch]);

  // Debounced search update
  const debouncedSetSearch = useMemo(
    () =>
      debounce((query: string) => {
        setFilters((prev) => ({ ...prev, searchQuery: query }));
      }, 300),
    []
  );

  const updateFilter = useCallback(
    (key: keyof FilterState, value: any) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const clearFilters = useCallback(() => {
    setFilters({
      searchQuery: '',
      selectedModel: 'all',
      selectedProvider: 'all',
      selectedTags: [],
      dateRange: { start: '', end: '' },
      showStarredOnly: false,
    });
  }, []);

  // Extract unique filter options
  const availableOptions = useMemo(
    () => ({
      models: Array.from(new Set(conversations.map((c) => c.model))),
      providers: Array.from(new Set(conversations.map((c) => c.provider))),
      tags: Array.from(new Set(conversations.flatMap((c) => c.tags))),
    }),
    [conversations]
  );

  return {
    filters,
    filteredConversations,
    availableOptions,
    updateFilter,
    clearFilters,
    debouncedSetSearch,
  };
};
