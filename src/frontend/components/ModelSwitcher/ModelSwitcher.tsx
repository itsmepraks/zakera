import React, { useState, useRef, useEffect, useCallback } from 'react';
import './ModelSwitcher.css';

export interface ModelOption {
  provider: string;
  model: string;
  label: string;
  contextWindow: number;
  recommended?: boolean;
  description?: string;
}

interface ProviderGroup {
  name: string;
  color: string;
  models: ModelOption[];
}

const PROVIDER_GROUPS: ProviderGroup[] = [
  {
    name: 'OpenAI',
    color: '#10a37f',
    models: [
      {
        provider: 'openai',
        model: 'gpt-4-turbo-preview',
        label: 'GPT-4 Turbo',
        contextWindow: 128000,
        recommended: true,
        description: 'Most capable GPT-4 model with vision',
      },
      {
        provider: 'openai',
        model: 'gpt-4o',
        label: 'GPT-4o',
        contextWindow: 128000,
        description: 'Omni model — text, vision & audio',
      },
      {
        provider: 'openai',
        model: 'gpt-3.5-turbo',
        label: 'GPT-3.5 Turbo',
        contextWindow: 16385,
        description: 'Fast and cost-effective',
      },
    ],
  },
  {
    name: 'Anthropic',
    color: '#d4a373',
    models: [
      {
        provider: 'anthropic',
        model: 'claude-3-5-sonnet-20241022',
        label: 'Claude 3.5 Sonnet',
        contextWindow: 200000,
        recommended: true,
        description: 'Best balance of intelligence and speed',
      },
      {
        provider: 'anthropic',
        model: 'claude-3-opus-20240229',
        label: 'Claude 3 Opus',
        contextWindow: 200000,
        description: 'Highest capability model',
      },
      {
        provider: 'anthropic',
        model: 'claude-3-haiku-20240307',
        label: 'Claude 3 Haiku',
        contextWindow: 200000,
        description: 'Fastest Claude model',
      },
    ],
  },
  {
    name: 'Google',
    color: '#4285f4',
    models: [
      {
        provider: 'gemini',
        model: 'gemini-1.5-pro',
        label: 'Gemini 1.5 Pro',
        contextWindow: 1000000,
        recommended: true,
        description: 'Long context, multimodal',
      },
      {
        provider: 'gemini',
        model: 'gemini-1.5-flash',
        label: 'Gemini 1.5 Flash',
        contextWindow: 1000000,
        description: 'Fast and efficient',
      },
    ],
  },
  {
    name: 'Groq',
    color: '#f97316',
    models: [
      {
        provider: 'groq',
        model: 'llama3-70b-8192',
        label: 'LLaMA 3 70B',
        contextWindow: 8192,
        recommended: true,
        description: 'Ultra-fast inference on Groq hardware',
      },
      {
        provider: 'groq',
        model: 'mixtral-8x7b-32768',
        label: 'Mixtral 8x7B',
        contextWindow: 32768,
        description: 'Mixture-of-experts model',
      },
    ],
  },
  {
    name: 'Mistral',
    color: '#7c3aed',
    models: [
      {
        provider: 'mistral',
        model: 'mistral-large-latest',
        label: 'Mistral Large',
        contextWindow: 32000,
        recommended: true,
        description: 'Most capable Mistral model',
      },
      {
        provider: 'mistral',
        model: 'mistral-small-latest',
        label: 'Mistral Small',
        contextWindow: 32000,
        description: 'Efficient for straightforward tasks',
      },
    ],
  },
  {
    name: 'Local',
    color: '#6b7280',
    models: [
      {
        provider: 'ollama',
        model: 'llama3',
        label: 'LLaMA 3 (Ollama)',
        contextWindow: 8192,
        description: 'Run locally via Ollama',
      },
      {
        provider: 'ollama',
        model: 'mistral',
        label: 'Mistral 7B (Ollama)',
        contextWindow: 8192,
        description: 'Mistral 7B running locally',
      },
    ],
  },
];

function formatContextWindow(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(0)}M ctx`;
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}K ctx`;
  return `${tokens} ctx`;
}

interface ModelSwitcherProps {
  /** Currently active model identifier, e.g. "gpt-4-turbo-preview" */
  currentModel?: string;
  /** Currently active provider identifier, e.g. "openai" */
  currentProvider?: string;
  /** Called when the user picks a different model */
  onModelChange: (provider: string, model: string) => void;
  /** Disable the switcher (e.g. while a response is streaming) */
  disabled?: boolean;
  className?: string;
}

export const ModelSwitcher: React.FC<ModelSwitcherProps> = ({
  currentModel = 'gpt-4-turbo-preview',
  currentProvider = 'openai',
  onModelChange,
  disabled = false,
  className = '',
}) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Find the display label for the currently selected model
  const currentLabel = PROVIDER_GROUPS
    .flatMap(g => g.models)
    .find(m => m.model === currentModel && m.provider === currentProvider)
    ?.label ?? currentModel;

  const handleSelect = useCallback(
    (provider: string, model: string) => {
      onModelChange(provider, model);
      setOpen(false);
    },
    [onModelChange],
  );

  // Close on outside click or Escape key
  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div
      ref={containerRef}
      className={`model-switcher ${className} ${disabled ? 'model-switcher--disabled' : ''}`}
    >
      <button
        className="model-switcher__trigger"
        onClick={() => !disabled && setOpen(prev => !prev)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Current model: ${currentLabel}. Click to change.`}
        disabled={disabled}
        type="button"
      >
        <span className="model-switcher__icon">✨</span>
        <span className="model-switcher__label">{currentLabel}</span>
        <span className={`model-switcher__chevron ${open ? 'model-switcher__chevron--up' : ''}`}>
          ▾
        </span>
      </button>

      {open && (
        <div className="model-switcher__panel" role="listbox" aria-label="Available models">
          {PROVIDER_GROUPS.map(group => (
            <div key={group.name} className="model-switcher__group">
              <div
                className="model-switcher__group-header"
                style={{ borderLeftColor: group.color }}
              >
                <span
                  className="model-switcher__provider-badge"
                  style={{ backgroundColor: group.color }}
                >
                  {group.name}
                </span>
              </div>

              <ul className="model-switcher__model-list">
                {group.models.map(option => {
                  const isActive =
                    option.model === currentModel && option.provider === currentProvider;

                  return (
                    <li
                      key={`${option.provider}-${option.model}`}
                      className={`model-switcher__model-item ${
                        isActive ? 'model-switcher__model-item--active' : ''
                      }`}
                      role="option"
                      aria-selected={isActive}
                      onClick={() => handleSelect(option.provider, option.model)}
                    >
                      <div className="model-switcher__model-info">
                        <span className="model-switcher__model-name">
                          {option.label}
                          {option.recommended && (
                            <span
                              className="model-switcher__recommended"
                              title="Recommended for this provider"
                            >
                              ★
                            </span>
                          )}
                        </span>
                        {option.description && (
                          <span className="model-switcher__model-desc">{option.description}</span>
                        )}
                      </div>
                      <span className="model-switcher__ctx-badge">
                        {formatContextWindow(option.contextWindow)}
                      </span>
                      {isActive && (
                        <span className="model-switcher__checkmark" aria-hidden="true">
                          ✓
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ModelSwitcher;
export { PROVIDER_GROUPS };
