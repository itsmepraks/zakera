/**
 * TypingIndicator
 * ---------------
 * Animated indicator shown while the AI model is generating a response.
 * Features:
 *  - Three-dot pulse animation (CSS-driven, no JS timers).
 *  - Per-provider brand colour and label.
 *  - Optional live tokens-per-second badge.
 *  - Fully accessible: role="status" + aria-live="polite".
 */

import React, { useMemo } from 'react';
import './TypingIndicator.css';

// ---------------------------------------------------------------------------
// Provider branding registry
// ---------------------------------------------------------------------------

type ProviderBrand =
  | 'anthropic'
  | 'openai'
  | 'gemini'
  | 'groq'
  | 'ollama'
  | 'mistral'
  | 'deepseek'
  | 'generic';

interface BrandConfig {
  label: string;
  /** CSS custom property name that holds the brand colour. */
  colorVar: string;
  /** Short emoji/icon used in the badge. */
  icon: string;
}

const BRAND_REGISTRY: Record<ProviderBrand, BrandConfig> = {
  anthropic: {
    label: 'Claude',
    colorVar: '--brand-anthropic',
    icon: '\u{1F9E0}', // brain emoji
  },
  openai: {
    label: 'ChatGPT',
    colorVar: '--brand-openai',
    icon: '\u2728',
  },
  gemini: {
    label: 'Gemini',
    colorVar: '--brand-gemini',
    icon: '\u2B50',
  },
  groq: {
    label: 'Groq',
    colorVar: '--brand-groq',
    icon: '\u26A1',
  },
  ollama: {
    label: 'Ollama',
    colorVar: '--brand-ollama',
    icon: '\uD83D\uDCBB',
  },
  mistral: {
    label: 'Mistral',
    colorVar: '--brand-mistral',
    icon: '\uD83C\uDF2C\uFE0F',
  },
  deepseek: {
    label: 'DeepSeek',
    colorVar: '--brand-deepseek',
    icon: '\uD83D\uDD0D',
  },
  generic: {
    label: 'AI',
    colorVar: '--brand-generic',
    icon: '\uD83E\uDD16',
  },
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface TypingIndicatorProps {
  /** Whether to show the indicator at all. */
  isVisible?: boolean;
  /** Provider brand to apply colour and label from the registry. */
  providerBrand?: ProviderBrand;
  /** Override the display name shown next to the indicator. */
  modelLabel?: string;
  /**
   * Current tokens-per-second rate.  When provided a live badge is shown.
   * Pass `null` to suppress the badge even if streaming is active.
   */
  tokensPerSecond?: number | null;
  /** Number of tokens streamed so far — shown in tooltip. */
  streamedTokens?: number;
  /** Extra CSS class applied to the root element. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isVisible = true,
  providerBrand = 'generic',
  modelLabel,
  tokensPerSecond = null,
  streamedTokens = 0,
  className = '',
}) => {
  const brand = useMemo(
    () => BRAND_REGISTRY[providerBrand] ?? BRAND_REGISTRY.generic,
    [providerBrand],
  );

  const displayLabel = modelLabel ?? brand.label;

  if (!isVisible) return null;

  return (
    <div
      className={`typing-indicator ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-label={`${displayLabel} is typing`}
      style={{ '--brand-color': `var(${brand.colorVar}, #6b7280)` } as React.CSSProperties}
    >
      {/* Brand icon + label */}
      <span className="typing-indicator__brand" aria-hidden="true">
        <span className="typing-indicator__icon">{brand.icon}</span>
        <span className="typing-indicator__label">{displayLabel}</span>
      </span>

      {/* Animated dots */}
      <span className="typing-indicator__dots" aria-hidden="true">
        <span className="typing-indicator__dot" />
        <span className="typing-indicator__dot" />
        <span className="typing-indicator__dot" />
      </span>

      {/* Live token-rate badge */}
      {tokensPerSecond !== null && tokensPerSecond > 0 && (
        <span
          className="typing-indicator__rate-badge"
          title={`${streamedTokens} tokens received`}
          aria-label={`${tokensPerSecond} tokens per second`}
        >
          {tokensPerSecond}
          <span className="typing-indicator__rate-unit">tok/s</span>
        </span>
      )}
    </div>
  );
};

export default TypingIndicator;
