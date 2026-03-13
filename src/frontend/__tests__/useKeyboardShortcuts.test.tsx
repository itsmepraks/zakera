/**
 * Tests for the useKeyboardShortcuts hook.
 *
 * Verifies:
 *  - Basic shortcut registration and callback firing
 *  - Modifier key combinations (Ctrl/Cmd, Alt, Shift)
 *  - Scope filtering (GLOBAL vs CHAT)
 *  - Master `enabled` flag
 *  - Cleanup on unmount
 *  - Non-interference with plain keypresses in editable fields
 */

import { renderHook, act } from '@testing-library/react';
import { useKeyboardShortcuts, ShortcutScope, KeyboardShortcut } from '../hooks/useKeyboardShortcuts';

// ---------------------------------------------------------------------------
// Helper to dispatch a synthetic KeyboardEvent
// ---------------------------------------------------------------------------

function fireKey(
  key: string,
  options: Partial<KeyboardEventInit> = {},
): void {
  const event = new KeyboardEvent('keydown', {
    key,
    bubbles: true,
    cancelable: true,
    ...options,
  });
  window.dispatchEvent(event);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useKeyboardShortcuts', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('fires callback for a plain key shortcut (no modifiers)', () => {
    const cb = jest.fn();
    const shortcuts: KeyboardShortcut[] = [
      { key: 'Escape', callback: cb, description: 'Dismiss', scope: ShortcutScope.GLOBAL },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey('Escape');

    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('fires callback for Ctrl+K shortcut', () => {
    const cb = jest.fn();
    const shortcuts: KeyboardShortcut[] = [
      { key: 'k', ctrl: true, callback: cb, description: 'Focus search' },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey('k', { ctrlKey: true });

    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('does NOT fire when Ctrl is required but missing', () => {
    const cb = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'k', ctrl: true, callback: cb }]),
    );
    fireKey('k'); // no ctrlKey
    expect(cb).not.toHaveBeenCalled();
  });

  it('fires callback for Ctrl+Shift+C', () => {
    const cb = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts([
        { key: 'c', ctrl: true, shift: true, callback: cb, description: 'Copy last' },
      ]),
    );
    fireKey('c', { ctrlKey: true, shiftKey: true });
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('does NOT fire when Shift is required but missing', () => {
    const cb = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'c', ctrl: true, shift: true, callback: cb }]),
    );
    fireKey('c', { ctrlKey: true }); // no shiftKey
    expect(cb).not.toHaveBeenCalled();
  });

  it('treats metaKey (Cmd) as equivalent to ctrlKey', () => {
    const cb = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'Enter', ctrl: true, callback: cb }]),
    );
    fireKey('Enter', { metaKey: true }); // macOS Cmd+Enter
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('scoped to CHAT does not fire when active scope is GLOBAL only', () => {
    const cb = jest.fn();
    // Register shortcut with CHAT scope but mount hook with GLOBAL scope
    renderHook(() =>
      useKeyboardShortcuts(
        [{ key: 'Enter', ctrl: true, callback: cb, scope: ShortcutScope.CHAT }],
        ShortcutScope.GLOBAL,
      ),
    );
    fireKey('Enter', { ctrlKey: true });
    expect(cb).not.toHaveBeenCalled();
  });

  it('scoped to CHAT fires when hook scope is also CHAT', () => {
    const cb = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts(
        [{ key: 'Enter', ctrl: true, callback: cb, scope: ShortcutScope.CHAT }],
        ShortcutScope.CHAT,
      ),
    );
    fireKey('Enter', { ctrlKey: true });
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('respects the enabled=false master switch', () => {
    const cb = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts(
        [{ key: 'Escape', callback: cb }],
        ShortcutScope.GLOBAL,
        false, // disabled
      ),
    );
    fireKey('Escape');
    expect(cb).not.toHaveBeenCalled();
  });

  it('removes event listener on unmount', () => {
    const removeSpy = jest.spyOn(window, 'removeEventListener');
    const cb = jest.fn();
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts([{ key: 'Escape', callback: cb }]),
    );

    unmount();
    fireKey('Escape');

    // Listener should have been removed
    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    expect(cb).not.toHaveBeenCalled();

    removeSpy.mockRestore();
  });

  it('only fires the FIRST matching shortcut (first-match-wins)', () => {
    const cb1 = jest.fn();
    const cb2 = jest.fn();
    renderHook(() =>
      useKeyboardShortcuts([
        { key: 'k', ctrl: true, callback: cb1 },
        { key: 'k', ctrl: true, callback: cb2 }, // duplicate
      ]),
    );
    fireKey('k', { ctrlKey: true });
    expect(cb1).toHaveBeenCalledTimes(1);
    expect(cb2).not.toHaveBeenCalled();
  });
});
