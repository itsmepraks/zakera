/**
 * useKeyboardShortcuts Hook
 * 
 * Manages keyboard shortcuts for conversation management.
 */

import { useEffect, useCallback } from 'react';
import { KeyboardShortcut } from '../types/ui';

export const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[]) => {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const matchingShortcut = shortcuts.find(shortcut => {
      if (!shortcut.enabled) return false;

      const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase();
      const ctrlMatches = !shortcut.ctrlKey || event.ctrlKey;
      const shiftMatches = !shortcut.shiftKey || event.shiftKey;
      const altMatches = !shortcut.altKey || event.altKey;
      const metaMatches = !shortcut.metaKey || event.metaKey;

      return keyMatches && ctrlMatches && shiftMatches && altMatches && metaMatches;
    });

    if (matchingShortcut) {
      event.preventDefault();
      matchingShortcut.handler();
    }
  }, [shortcuts]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const getShortcutLabel = useCallback((shortcut: KeyboardShortcut): string => {
    const parts: string[] = [];
    
    if (shortcut.metaKey) parts.push('⌘'); // Command
    if (shortcut.ctrlKey) parts.push('Ctrl');
    if (shortcut.altKey) parts.push('Alt');
    if (shortcut.shiftKey) parts.push('⇧'); // Shift
    parts.push(shortcut.key.toUpperCase());

    return parts.join('+');
  }, []);

  return {
    getShortcutLabel,
  };
};
