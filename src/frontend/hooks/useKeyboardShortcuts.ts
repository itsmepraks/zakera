/**
 * useKeyboardShortcuts
 *
 * A flexible hook for registering keyboard shortcuts in the Zakera chat UI.
 *
 * Usage
 * -----
 * ```tsx
 * useKeyboardShortcuts([
 *   { key: 'Enter', ctrl: true, callback: handleSubmit, description: 'Send message' },
 *   { key: 'k',     ctrl: true, callback: focusSearch,  description: 'Focus search',  scope: ShortcutScope.GLOBAL },
 * ]);
 * ```
 *
 * All shortcuts are removed when the component unmounts.
 */

import { useEffect, useCallback, useRef } from 'react';

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

export enum ShortcutScope {
  /** Active everywhere in the application */
  GLOBAL = 'global',
  /** Active only inside the chat view */
  CHAT = 'chat',
  /** Active only when a modal is open */
  MODAL = 'modal',
}

export interface KeyboardShortcut {
  /** The key identifier, e.g. 'Enter', 'k', 'Escape', '?' */
  key: string;
  /** Require Ctrl (Windows/Linux) or Cmd (macOS) */
  ctrl?: boolean;
  /** Require Alt / Option */
  alt?: boolean;
  /** Require Shift */
  shift?: boolean;
  /** Callback invoked when the shortcut fires */
  callback: (event: KeyboardEvent) => void;
  /** Human-readable description shown in the shortcuts modal */
  description?: string;
  /** Scope in which this shortcut should be active (default: GLOBAL) */
  scope?: ShortcutScope;
  /** Prevent default browser behaviour (default: true) */
  preventDefault?: boolean;
}

// -------------------------------------------------------------------------
// Normalisation helpers
// -------------------------------------------------------------------------

/** Returns true when the platform meta key (Cmd on macOS, Ctrl elsewhere) is held. */
function isCtrlOrMeta(event: KeyboardEvent, requireCtrl: boolean): boolean {
  if (!requireCtrl) return true;
  return event.ctrlKey || event.metaKey;
}

function shortcutMatches(shortcut: KeyboardShortcut, event: KeyboardEvent): boolean {
  if (event.key.toLowerCase() !== shortcut.key.toLowerCase()) return false;
  if (!isCtrlOrMeta(event, shortcut.ctrl ?? false)) return false;
  if ((shortcut.alt ?? false) !== event.altKey) return false;
  if ((shortcut.shift ?? false) !== event.shiftKey) return false;
  return true;
}

// -------------------------------------------------------------------------
// Hook
// -------------------------------------------------------------------------

/**
 * Register an array of keyboard shortcuts for the lifetime of the component.
 *
 * @param shortcuts  Array of {@link KeyboardShortcut} definitions.
 * @param scope      Restrict which shortcuts are active.  When omitted all
 *                   shortcuts that declare GLOBAL or no scope are honoured.
 * @param enabled    Master switch.  Set to `false` to temporarily suspend all
 *                   shortcuts without unmounting.  Defaults to `true`.
 */
export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  scope: ShortcutScope = ShortcutScope.GLOBAL,
  enabled = true,
): void {
  // Keep a stable ref to the shortcuts list to avoid stale closures when the
  // parent re-renders with an inline array literal.
  const shortcutsRef = useRef<KeyboardShortcut[]>(shortcuts);
  shortcutsRef.current = shortcuts;

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Skip when the user is typing in an editable element (unless the
      // shortcut explicitly targets that context via the ctrl/meta modifier).
      const target = event.target as HTMLElement;
      const isEditable =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      for (const shortcut of shortcutsRef.current) {
        const shortcutScope = shortcut.scope ?? ShortcutScope.GLOBAL;

        // Skip shortcuts that don't belong to the active scope.
        if (scope !== ShortcutScope.GLOBAL && shortcutScope !== scope) continue;

        if (!shortcutMatches(shortcut, event)) continue;

        // Allow shortcuts with Ctrl/Cmd to work inside editable fields;
        // plain key shortcuts are suppressed to avoid interfering with typing.
        if (isEditable && !(shortcut.ctrl ?? false)) continue;

        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }
        shortcut.callback(event);
        break; // first match wins
      }
    },
    [enabled, scope],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

// -------------------------------------------------------------------------
// Pre-defined shortcut catalogue (used by KeyboardShortcutsModal)
// -------------------------------------------------------------------------

export interface ShortcutDefinition {
  label: string;
  keys: string[];
  scope: ShortcutScope;
  description: string;
}

/** Platform-aware modifier label */
export const MOD_KEY =
  typeof navigator !== 'undefined' && /mac/i.test(navigator.platform) ? '⌘' : 'Ctrl';

export const SHORTCUT_CATALOGUE: ShortcutDefinition[] = [
  // --- Chat ---
  {
    label: 'Send message',
    keys: [`${MOD_KEY}`, 'Enter'],
    scope: ShortcutScope.CHAT,
    description: 'Submit the current message in the composer',
  },
  {
    label: 'New conversation',
    keys: [`${MOD_KEY}`, 'N'],
    scope: ShortcutScope.CHAT,
    description: 'Start a fresh conversation',
  },
  {
    label: 'Focus search',
    keys: [`${MOD_KEY}`, 'K'],
    scope: ShortcutScope.GLOBAL,
    description: 'Jump to the conversation search bar',
  },
  {
    label: 'Toggle sidebar',
    keys: [`${MOD_KEY}`, 'B'],
    scope: ShortcutScope.GLOBAL,
    description: 'Show or hide the conversation sidebar',
  },
  {
    label: 'Switch model',
    keys: [`${MOD_KEY}`, 'M'],
    scope: ShortcutScope.CHAT,
    description: 'Open the model-switcher dropdown',
  },
  {
    label: 'Copy last response',
    keys: [`${MOD_KEY}`, 'Shift', 'C'],
    scope: ShortcutScope.CHAT,
    description: "Copy the assistant's most recent message to clipboard",
  },
  {
    label: 'Regenerate response',
    keys: [`${MOD_KEY}`, 'Shift', 'R'],
    scope: ShortcutScope.CHAT,
    description: 'Re-run the last user message with the current model',
  },
  // --- Navigation ---
  {
    label: 'Go to settings',
    keys: [`${MOD_KEY}`, ','],
    scope: ShortcutScope.GLOBAL,
    description: 'Open the settings panel',
  },
  {
    label: 'Show shortcuts',
    keys: [`${MOD_KEY}`, '?'],
    scope: ShortcutScope.GLOBAL,
    description: 'Toggle this shortcuts reference modal',
  },
  // --- Modal ---
  {
    label: 'Close modal / dismiss',
    keys: ['Esc'],
    scope: ShortcutScope.MODAL,
    description: 'Close the currently open modal or overlay',
  },
];
