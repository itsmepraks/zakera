/**
 * useConversationBulkSelect Hook
 * 
 * Manages multi-select state for bulk operations.
 */

import { useCallback, useMemo } from 'react';
import { Conversation } from '../types/conversation';

export const useConversationBulkSelect = (
  conversations: Conversation[],
  selectedIds: Set<string>,
  onSelectionChange: (selectedIds: Set<string>) => void
) => {
  const selectAll = useCallback(() => {
    const allIds = new Set(conversations.map(c => c.id));
    onSelectionChange(allIds);
  }, [conversations, onSelectionChange]);

  const deselectAll = useCallback(() => {
    onSelectionChange(new Set());
  }, [onSelectionChange]);

  const toggleSelection = useCallback((id: string) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    onSelectionChange(newSelection);
  }, [selectedIds, onSelectionChange]);

  const selectRange = useCallback((fromIndex: number, toIndex: number) => {
    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);
    
    const rangeIds = conversations
      .slice(start, end + 1)
      .map(c => c.id);
    
    const newSelection = new Set([...selectedIds, ...rangeIds]);
    onSelectionChange(newSelection);
  }, [conversations, selectedIds, onSelectionChange]);

  const toggleRange = useCallback((fromIndex: number, toIndex: number) => {
    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);
    
    const rangeIds = new Set(
      conversations.slice(start, end + 1).map(c => c.id)
    );

    const newSelection = new Set(selectedIds);
    const allSelected = Array.from(rangeIds).every(id => newSelection.has(id));

    if (allSelected) {
      rangeIds.forEach(id => newSelection.delete(id));
    } else {
      rangeIds.forEach(id => newSelection.add(id));
    }

    onSelectionChange(newSelection);
  }, [conversations, selectedIds, onSelectionChange]);

  const isAllSelected = useMemo(
    () => conversations.length > 0 && selectedIds.size === conversations.length,
    [conversations.length, selectedIds.size]
  );

  const hasSelection = useMemo(
    () => selectedIds.size > 0,
    [selectedIds.size]
  );

  const isSomeSelected = useMemo(
    () => selectedIds.size > 0 && selectedIds.size < conversations.length,
    [selectedIds.size, conversations.length]
  );

  return {
    selectAll,
    deselectAll,
    toggleSelection,
    selectRange,
    toggleRange,
    isAllSelected,
    hasSelection,
    isSomeSelected,
  };
};
