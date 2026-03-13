/**
 * KeyboardShortcutsModal
 *
 * Displays a categorised reference of all keyboard shortcuts available in
 * the Zakera chat UI.  Toggle it with Ctrl+? / ⌘+? or by clicking the ⌨️
 * icon in the chat toolbar.
 */

import React, { useEffect } from 'react';
import { SHORTCUT_CATALOGUE, ShortcutScope, ShortcutDefinition, MOD_KEY } from '../hooks/useKeyboardShortcuts';

// -------------------------------------------------------------------------
// Types
// -------------------------------------------------------------------------

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// -------------------------------------------------------------------------
// Sub-components
// -------------------------------------------------------------------------

const KbdKey: React.FC<{ label: string }> = ({ label }) => (
  <kbd
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      minWidth: '1.75rem',
      height: '1.75rem',
      padding: '0 0.4rem',
      borderRadius: '0.3rem',
      border: '1px solid #4b5563',
      background: '#1f2937',
      color: '#d1d5db',
      fontSize: '0.75rem',
      fontFamily: 'monospace',
      fontWeight: 600,
      lineHeight: 1,
      userSelect: 'none',
    }}
  >
    {label}
  </kbd>
);

const ShortcutRow: React.FC<{ shortcut: ShortcutDefinition }> = ({ shortcut }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0.5rem 0',
      borderBottom: '1px solid #374151',
    }}
  >
    <span style={{ color: '#e5e7eb', fontSize: '0.875rem' }}>{shortcut.description}</span>
    <span style={{ display: 'flex', gap: '0.25rem', alignItems: 'center', flexShrink: 0, marginLeft: '1rem' }}>
      {shortcut.keys.map((k, i) => (
        <React.Fragment key={k + i}>
          {i > 0 && <span style={{ color: '#6b7280', fontSize: '0.7rem', margin: '0 0.1rem' }}>+</span>}
          <KbdKey label={k} />
        </React.Fragment>
      ))}
    </span>
  </div>
);

// -------------------------------------------------------------------------
// Section helper
// -------------------------------------------------------------------------

const SCOPE_LABELS: Record<ShortcutScope, string> = {
  [ShortcutScope.GLOBAL]: '🌐 Global',
  [ShortcutScope.CHAT]: '💬 Chat',
  [ShortcutScope.MODAL]: '🗔 Modals & Overlays',
};

function groupByScope(shortcuts: ShortcutDefinition[]): Map<ShortcutScope, ShortcutDefinition[]> {
  const map = new Map<ShortcutScope, ShortcutDefinition[]>();
  for (const s of shortcuts) {
    if (!map.has(s.scope)) map.set(s.scope, []);
    map.get(s.scope)!.push(s);
  }
  return map;
}

// -------------------------------------------------------------------------
// Modal
// -------------------------------------------------------------------------

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const grouped = groupByScope(SHORTCUT_CATALOGUE);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.6)',
          zIndex: 1000,
          backdropFilter: 'blur(2px)',
        }}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-modal-title"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1001,
          width: 'min(90vw, 560px)',
          maxHeight: '80vh',
          overflowY: 'auto',
          background: '#111827',
          borderRadius: '0.75rem',
          border: '1px solid #374151',
          boxShadow: '0 25px 50px rgba(0,0,0,0.5)',
          padding: '1.5rem',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.25rem',
          }}
        >
          <h2
            id="shortcuts-modal-title"
            style={{ color: '#f9fafb', fontSize: '1.125rem', fontWeight: 700, margin: 0 }}
          >
            ⌨️ Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            aria-label="Close shortcuts modal"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#9ca3af',
              cursor: 'pointer',
              fontSize: '1.25rem',
              lineHeight: 1,
              padding: '0.25rem',
            }}
          >
            ×
          </button>
        </div>

        {/* Shortcut sections */}
        {Array.from(grouped.entries()).map(([scope, shortcuts]) => (
          <section key={scope} style={{ marginBottom: '1.5rem' }}>
            <h3
              style={{
                color: '#6b7280',
                fontSize: '0.75rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '0.5rem',
              }}
            >
              {SCOPE_LABELS[scope]}
            </h3>
            {shortcuts.map((s) => (
              <ShortcutRow key={s.label} shortcut={s} />
            ))}
          </section>
        ))}

        {/* Footer hint */}
        <p
          style={{
            marginTop: '1rem',
            color: '#4b5563',
            fontSize: '0.75rem',
            textAlign: 'center',
          }}
        >
          Press <KbdKey label={MOD_KEY} /> + <KbdKey label="?" /> to toggle this panel
        </p>
      </div>
    </>
  );
};

export default KeyboardShortcutsModal;
