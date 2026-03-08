/**
 * Custom React hook for auto-saving draft messages
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface DraftData {
  content: string;
  conversationId: string;
  timestamp: number;
}

interface UseDraftAutosaveOptions {
  conversationId: string;
  autosaveDelay?: number; // milliseconds
  storageKey?: string;
  onSave?: (draft: string) => void;
  onRestore?: (draft: string) => void;
}

interface UseDraftAutosaveResult {
  draft: string;
  setDraft: (content: string) => void;
  clearDraft: () => void;
  saveDraft: () => void;
  restoreDraft: () => string | null;
  hasDraft: boolean;
  lastSaved: Date | null;
  isSaving: boolean;
}

export const useDraftAutosave = ({
  conversationId,
  autosaveDelay = 2000,
  storageKey = 'zakera_message_drafts',
  onSave,
  onRestore,
}: UseDraftAutosaveOptions): UseDraftAutosaveResult => {
  const [draft, setDraftState] = useState('');
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);
  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isInitialMount = useRef(true);

  // Get storage key for this conversation
  const getStorageKey = useCallback(() => {
    return `${storageKey}_${conversationId}`;
  }, [storageKey, conversationId]);

  // Save draft to localStorage
  const saveDraftToStorage = useCallback(
    (content: string) => {
      try {
        const draftData: DraftData = {
          content,
          conversationId,
          timestamp: Date.now(),
        };
        localStorage.setItem(getStorageKey(), JSON.stringify(draftData));
        setLastSaved(new Date());
        setHasDraft(content.length > 0);
        onSave?.(content);
      } catch (error) {
        console.error('Error saving draft:', error);
      }
    },
    [conversationId, getStorageKey, onSave]
  );

  // Restore draft from localStorage
  const restoreDraft = useCallback((): string | null => {
    try {
      const stored = localStorage.getItem(getStorageKey());
      if (!stored) return null;

      const draftData: DraftData = JSON.parse(stored);

      // Check if draft is for current conversation
      if (draftData.conversationId !== conversationId) {
        return null;
      }

      // Check if draft is not too old (24 hours)
      const ageInHours = (Date.now() - draftData.timestamp) / (1000 * 60 * 60);
      if (ageInHours > 24) {
        localStorage.removeItem(getStorageKey());
        return null;
      }

      setDraftState(draftData.content);
      setHasDraft(true);
      setLastSaved(new Date(draftData.timestamp));
      onRestore?.(draftData.content);

      return draftData.content;
    } catch (error) {
      console.error('Error restoring draft:', error);
      return null;
    }
  }, [conversationId, getStorageKey, onRestore]);

  // Clear draft from localStorage
  const clearDraft = useCallback(() => {
    try {
      localStorage.removeItem(getStorageKey());
      setDraftState('');
      setHasDraft(false);
      setLastSaved(null);

      // Clear autosave timer
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    } catch (error) {
      console.error('Error clearing draft:', error);
    }
  }, [getStorageKey]);

  // Manual save
  const saveDraft = useCallback(() => {
    if (draft.trim()) {
      setIsSaving(true);
      saveDraftToStorage(draft);
      setTimeout(() => setIsSaving(false), 300);
    }
  }, [draft, saveDraftToStorage]);

  // Set draft with autosave
  const setDraft = useCallback(
    (content: string) => {
      setDraftState(content);

      // Clear existing timer
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }

      // Set new autosave timer
      if (content.trim()) {
        autosaveTimerRef.current = setTimeout(() => {
          setIsSaving(true);
          saveDraftToStorage(content);
          setTimeout(() => setIsSaving(false), 300);
        }, autosaveDelay);
      } else {
        // Clear draft if content is empty
        clearDraft();
      }
    },
    [autosaveDelay, saveDraftToStorage, clearDraft]
  );

  // Restore draft on mount
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      restoreDraft();
    }
  }, [restoreDraft]);

  // Clear draft when conversation changes
  useEffect(() => {
    if (!isInitialMount.current) {
      clearDraft();
    }
  }, [conversationId, clearDraft]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
  }, []);

  // Save before page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (draft.trim()) {
        saveDraftToStorage(draft);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [draft, saveDraftToStorage]);

  return {
    draft,
    setDraft,
    clearDraft,
    saveDraft,
    restoreDraft,
    hasDraft,
    lastSaved,
    isSaving,
  };
};

export default useDraftAutosave;
