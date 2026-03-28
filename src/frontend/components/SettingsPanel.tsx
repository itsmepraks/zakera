/**
 * SettingsPanel.tsx
 *
 * A slide-in settings drawer for the Zakera AI chat interface.
 * Users can adjust model parameters, theme, memory settings, and
 * provider configuration without navigating away from the chat.
 *
 * Design decisions:
 * - Follows the same CSS-Modules + Tailwind pattern as AgentThinkingPanel
 *   and ConversationPinPanel for visual consistency.
 * - All state is lifted via `onSettingsChange` so the parent can persist
 *   prefs to localStorage or the backend /api/v1/settings endpoint.
 * - Fully accessible: focus-trap, Esc key, ARIA labels, visible focus rings.
 */

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import styles from './SettingsPanel.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Theme = 'light' | 'dark' | 'system';

export interface ModelSettings {
  /** Sampling temperature (0 – 2). Default 0.7 */
  temperature: number;
  /** Maximum tokens to generate. Default 2048 */
  maxTokens: number;
  /** Nucleus sampling top-p (0 – 1). Default 1.0 */
  topP: number;
  /** Enable server-sent streaming. Default true */
  streamingEnabled: boolean;
}

export interface MemorySettings {
  /** Number of recent messages to keep in context window. Default 20 */
  contextWindowSize: number;
  /** Enable FAISS vector similarity search for long-term memory. */
  vectorSearchEnabled: boolean;
  /** Automatically summarise conversations longer than this many messages. */
  autoSummariseThreshold: number;
  /** Include conversation summary in every system prompt. */
  includeSummaryInPrompt: boolean;
}

export interface ZakeraSettings {
  theme: Theme;
  model: ModelSettings;
  memory: MemorySettings;
  /** Identifier of the currently active provider, e.g. "openai" */
  activeProvider: string;
}

export interface SettingsPanelProps {
  /** Whether the panel is visible. */
  isOpen: boolean;
  /** Current settings values. */
  settings: ZakeraSettings;
  /** Called whenever the user changes a setting. */
  onSettingsChange: (updated: ZakeraSettings) => void;
  /** Called when the user requests the panel to close. */
  onClose: () => void;
  /** Called when the user requests a full history wipe. */
  onClearHistory?: () => void;
  /** Called when the user wants to reset all settings to defaults. */
  onResetSettings?: () => void;
  /** Masked API key preview shown in the Provider section (e.g. "sk-...abc"). */
  apiKeyPreview?: string;
}

// ---------------------------------------------------------------------------
// Default values (also exported for use in parent initialisers)
// ---------------------------------------------------------------------------

export const DEFAULT_MODEL_SETTINGS: ModelSettings = {
  temperature: 0.7,
  maxTokens: 2048,
  topP: 1.0,
  streamingEnabled: true,
};

export const DEFAULT_MEMORY_SETTINGS: MemorySettings = {
  contextWindowSize: 20,
  vectorSearchEnabled: false,
  autoSummariseThreshold: 50,
  includeSummaryInPrompt: true,
};

export const DEFAULT_SETTINGS: ZakeraSettings = {
  theme: 'system',
  model: DEFAULT_MODEL_SETTINGS,
  memory: DEFAULT_MEMORY_SETTINGS,
  activeProvider: 'openai',
};

// ---------------------------------------------------------------------------
// Helper sub-components
// ---------------------------------------------------------------------------

interface SliderRowProps {
  id: string;
  label: string;
  description?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  formatValue?: (v: number) => string;
}

const SliderRow: React.FC<SliderRowProps> = ({
  id,
  label,
  description,
  value,
  min,
  max,
  step,
  onChange,
  formatValue,
}) => (
  <div className={styles.settingRow}>
    <div className={styles.settingLabelGroup}>
      <label htmlFor={id} className={styles.settingLabel}>
        {label}
      </label>
      {description && (
        <span className={styles.settingDescription}>{description}</span>
      )}
    </div>
    <div className={styles.sliderGroup}>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className={styles.slider}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-valuetext={formatValue ? formatValue(value) : String(value)}
      />
      <span className={styles.sliderValue}>
        {formatValue ? formatValue(value) : value}
      </span>
    </div>
  </div>
);

interface ToggleRowProps {
  id: string;
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

const ToggleRow: React.FC<ToggleRowProps> = ({
  id,
  label,
  description,
  checked,
  onChange,
}) => (
  <div className={styles.settingRow}>
    <div className={styles.settingLabelGroup}>
      <label htmlFor={id} className={styles.settingLabel}>
        {label}
      </label>
      {description && (
        <span className={styles.settingDescription}>{description}</span>
      )}
    </div>
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`${styles.toggle} ${checked ? styles.toggleOn : styles.toggleOff}`}
      aria-label={`${label}: ${checked ? 'enabled' : 'disabled'}`}
    >
      <span className={styles.toggleThumb} />
    </button>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  isOpen,
  settings,
  onSettingsChange,
  onClose,
  onClearHistory,
  onResetSettings,
  apiKeyPreview,
}) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const [confirmingReset, setConfirmingReset] = useState(false);

  // ── Focus management ───────────────────────────────────────────────
  useEffect(() => {
    if (isOpen) {
      // Defer so the transition has started
      const id = setTimeout(() => closeButtonRef.current?.focus(), 50);
      return () => clearTimeout(id);
    }
  }, [isOpen]);

  // ── Keyboard handling ──────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        onClose();
      }
      // Focus-trap: keep Tab within the panel
      if (e.key === 'Tab' && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // ── Partial-update helpers ─────────────────────────────────────────
  const updateModel = useCallback(
    (patch: Partial<ModelSettings>) =>
      onSettingsChange({ ...settings, model: { ...settings.model, ...patch } }),
    [settings, onSettingsChange]
  );

  const updateMemory = useCallback(
    (patch: Partial<MemorySettings>) =>
      onSettingsChange({
        ...settings,
        memory: { ...settings.memory, ...patch },
      }),
    [settings, onSettingsChange]
  );

  const handleThemeChange = (theme: Theme) =>
    onSettingsChange({ ...settings, theme });

  // ── Danger-zone actions ────────────────────────────────────────────
  const handleClearHistory = () => {
    if (!confirmingClear) {
      setConfirmingClear(true);
      setTimeout(() => setConfirmingClear(false), 4000);
      return;
    }
    onClearHistory?.();
    setConfirmingClear(false);
  };

  const handleResetSettings = () => {
    if (!confirmingReset) {
      setConfirmingReset(true);
      setTimeout(() => setConfirmingReset(false), 4000);
      return;
    }
    onResetSettings?.();
    setConfirmingReset(false);
  };

  // ── Provider badge colour ──────────────────────────────────────────
  const providerColour: Record<string, string> = {
    openai: styles.badgeGreen,
    anthropic: styles.badgeOrange,
    groq: styles.badgePurple,
    gemini: styles.badgeBlue,
    llama: styles.badgeYellow,
    ollama: styles.badgeGray,
    mistral: styles.badgeTeal,
    cohere: styles.badgePink,
  };
  const badgeClass =
    providerColour[settings.activeProvider] ?? styles.badgeGray;

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className={styles.backdrop}
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Zakera Settings"
        className={`${styles.panel} ${isOpen ? styles.panelOpen : styles.panelClosed}`}
      >
        {/* Header */}
        <div className={styles.header}>
          <h2 className={styles.title}>
            <span className={styles.titleIcon} aria-hidden="true">
              ⚙️
            </span>
            Settings
          </h2>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className={styles.closeButton}
            aria-label="Close settings panel"
          >
            ✕
          </button>
        </div>

        <div className={styles.body}>
          {/* ── Appearance ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Appearance</h3>
            <div className={styles.themeToggleGroup} role="radiogroup" aria-label="Theme">
              {(['light', 'dark', 'system'] as Theme[]).map((t) => (
                <button
                  key={t}
                  role="radio"
                  aria-checked={settings.theme === t}
                  onClick={() => handleThemeChange(t)}
                  className={`${styles.themeButton} ${
                    settings.theme === t ? styles.themeButtonActive : ''
                  }`}
                >
                  {t === 'light' ? '☀️' : t === 'dark' ? '🌙' : '🖥️'}{' '}
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </section>

          {/* ── Model Defaults ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Model Defaults</h3>

            <SliderRow
              id="setting-temperature"
              label="Temperature"
              description="Controls randomness. Lower = more deterministic."
              value={settings.model.temperature}
              min={0}
              max={2}
              step={0.05}
              onChange={(v) => updateModel({ temperature: v })}
              formatValue={(v) => v.toFixed(2)}
            />

            <div className={styles.settingRow}>
              <div className={styles.settingLabelGroup}>
                <label htmlFor="setting-max-tokens" className={styles.settingLabel}>
                  Max Tokens
                </label>
                <span className={styles.settingDescription}>
                  Maximum number of tokens to generate per response.
                </span>
              </div>
              <input
                id="setting-max-tokens"
                type="number"
                min={64}
                max={128000}
                step={64}
                value={settings.model.maxTokens}
                onChange={(e) =>
                  updateModel({ maxTokens: parseInt(e.target.value, 10) || 2048 })
                }
                className={styles.numberInput}
              />
            </div>

            <SliderRow
              id="setting-top-p"
              label="Top-P"
              description="Nucleus sampling — 1.0 disables filtering."
              value={settings.model.topP}
              min={0}
              max={1}
              step={0.01}
              onChange={(v) => updateModel({ topP: v })}
              formatValue={(v) => v.toFixed(2)}
            />

            <ToggleRow
              id="setting-streaming"
              label="Streaming"
              description="Show tokens as they arrive for faster perceived response."
              checked={settings.model.streamingEnabled}
              onChange={(v) => updateModel({ streamingEnabled: v })}
            />
          </section>

          {/* ── Memory & Context ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Memory & Context</h3>

            <SliderRow
              id="setting-context-window"
              label="Context Window Size"
              description="Number of recent messages included in every request."
              value={settings.memory.contextWindowSize}
              min={4}
              max={100}
              step={2}
              onChange={(v) => updateMemory({ contextWindowSize: v })}
              formatValue={(v) => `${v} messages`}
            />

            <ToggleRow
              id="setting-vector-search"
              label="Vector Search"
              description="Use FAISS embeddings for semantic long-term memory retrieval."
              checked={settings.memory.vectorSearchEnabled}
              onChange={(v) => updateMemory({ vectorSearchEnabled: v })}
            />

            <SliderRow
              id="setting-auto-summarise"
              label="Auto-Summarise Threshold"
              description="Summarise conversation when it exceeds this many messages."
              value={settings.memory.autoSummariseThreshold}
              min={10}
              max={200}
              step={5}
              onChange={(v) => updateMemory({ autoSummariseThreshold: v })}
              formatValue={(v) => `${v} messages`}
            />

            <ToggleRow
              id="setting-include-summary"
              label="Include Summary in Prompt"
              description="Prepend conversation summary to every system prompt."
              checked={settings.memory.includeSummaryInPrompt}
              onChange={(v) => updateMemory({ includeSummaryInPrompt: v })}
            />
          </section>

          {/* ── API & Providers ── */}
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>API & Providers</h3>
            <div className={styles.settingRow}>
              <div className={styles.settingLabelGroup}>
                <span className={styles.settingLabel}>Active Provider</span>
                <span className={styles.settingDescription}>
                  Switch providers from the model selector in the chat header.
                </span>
              </div>
              <span className={`${styles.providerBadge} ${badgeClass}`}>
                {settings.activeProvider}
              </span>
            </div>

            {apiKeyPreview && (
              <div className={styles.settingRow}>
                <div className={styles.settingLabelGroup}>
                  <span className={styles.settingLabel}>API Key</span>
                  <span className={styles.settingDescription}>
                    Manage keys in your account settings.
                  </span>
                </div>
                <code className={styles.apiKeyPreview}>{apiKeyPreview}</code>
              </div>
            )}
          </section>

          {/* ── Danger Zone ── */}
          <section className={`${styles.section} ${styles.dangerSection}`}>
            <h3 className={`${styles.sectionTitle} ${styles.dangerTitle}`}>
              Danger Zone
            </h3>

            <div className={styles.dangerRow}>
              <div className={styles.settingLabelGroup}>
                <span className={styles.settingLabel}>Clear Conversation History</span>
                <span className={styles.settingDescription}>
                  Permanently deletes all stored messages and memory.
                </span>
              </div>
              <button
                onClick={handleClearHistory}
                className={`${styles.dangerButton} ${
                  confirmingClear ? styles.dangerButtonConfirm : ''
                }`}
                aria-label="Clear all conversation history"
              >
                {confirmingClear ? '⚠️ Confirm clear' : 'Clear history'}
              </button>
            </div>

            <div className={styles.dangerRow}>
              <div className={styles.settingLabelGroup}>
                <span className={styles.settingLabel}>Reset All Settings</span>
                <span className={styles.settingDescription}>
                  Restore temperature, memory, and theme to defaults.
                </span>
              </div>
              <button
                onClick={handleResetSettings}
                className={`${styles.dangerButton} ${
                  confirmingReset ? styles.dangerButtonConfirm : ''
                }`}
                aria-label="Reset settings to defaults"
              >
                {confirmingReset ? '⚠️ Confirm reset' : 'Reset settings'}
              </button>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <span className={styles.footerNote}>
            Changes are applied instantly and saved to your browser.
          </span>
          <button onClick={onClose} className={styles.doneButton}>
            Done
          </button>
        </div>
      </div>
    </>
  );
};

export default SettingsPanel;
