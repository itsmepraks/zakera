/**
 * Custom hook for keyboard shortcuts
 */

import { useEffect, useCallback } from 'react';

type KeyboardShortcut = {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean; // Command key on Mac
};

type ShortcutCallback = (event: KeyboardEvent) => void;

export const useKeyboardShortcut = (
  shortcut: KeyboardShortcut,
  callback: ShortcutCallback,
  options: {
    enabled?: boolean;
    preventDefault?: boolean;
    stopPropagation?: boolean;
  } = {}
) => {
  const { enabled = true, preventDefault = true, stopPropagation = false } = options;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      const matchesKey = event.key.toLowerCase() === shortcut.key.toLowerCase();
      const matchesCtrl = shortcut.ctrl === undefined || event.ctrlKey === shortcut.ctrl;
      const matchesShift = shortcut.shift === undefined || event.shiftKey === shortcut.shift;
      const matchesAlt = shortcut.alt === undefined || event.altKey === shortcut.alt;
      const matchesMeta = shortcut.meta === undefined || event.metaKey === shortcut.meta;

      if (matchesKey && matchesCtrl && matchesShift && matchesAlt && matchesMeta) {
        if (preventDefault) {
          event.preventDefault();
        }
        if (stopPropagation) {
          event.stopPropagation();
        }
        callback(event);
      }
    },
    [enabled, shortcut, callback, preventDefault, stopPropagation]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
};

/**
 * Hook for multiple keyboard shortcuts
 */
export const useKeyboardShortcuts = (
  shortcuts: Array<{ shortcut: KeyboardShortcut; callback: ShortcutCallback }>,
  enabled = true
) => {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      shortcuts.forEach(({ shortcut, callback }) => {
        const matchesKey = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const matchesCtrl = shortcut.ctrl === undefined || event.ctrlKey === shortcut.ctrl;
        const matchesShift = shortcut.shift === undefined || event.shiftKey === shortcut.shift;
        const matchesAlt = shortcut.alt === undefined || event.altKey === shortcut.alt;
        const matchesMeta = shortcut.meta === undefined || event.metaKey === shortcut.meta;

        if (matchesKey && matchesCtrl && matchesShift && matchesAlt && matchesMeta) {
          event.preventDefault();
          callback(event);
        }
      });
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts, enabled]);
};
