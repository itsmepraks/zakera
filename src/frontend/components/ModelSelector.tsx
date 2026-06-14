/**
 * ModelSelector.tsx
 *
 * A two-level dropdown component that lets users pick a provider and model
 * for the Zakera AI chat agent.  It renders provider groups with nested
 * model options and shows capability badges (streaming, vision, tools, code)
 * alongside context-length and cost-tier metadata.
 *
 * Usage:
 *   <ModelSelector
 *     value={{ provider: 'openai', model: 'gpt-4o' }}
 *     onChange={(selection) => console.log(selection)}
 *   />
 */

import React, {
  FC,
  KeyboardEvent,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CostTier = 'free' | 'low' | 'medium' | 'high';

export interface ModelCapabilities {
  streaming: boolean;
  vision: boolean;
  functionCalling: boolean;
  codeGeneration: boolean;
}

export interface ModelInfo {
  id: string;
  label: string;
  contextLength: number;  // in tokens
  costTier: CostTier;
  capabilities: ModelCapabilities;
  isDefault?: boolean;
  isBeta?: boolean;
}

export interface ProviderInfo {
  id: string;
  label: string;
  logoEmoji: string;
  models: ModelInfo[];
  requiresApiKey: boolean;
  localOnly?: boolean;
}

export interface ModelSelection {
  provider: string;
  model: string;
}

export interface ModelSelectorProps {
  value: ModelSelection;
  onChange: (selection: ModelSelection) => void;
  disabled?: boolean;
  className?: string;
  showCapabilityBadges?: boolean;
  showCostTier?: boolean;
  placeholder?: string;
}

// ---------------------------------------------------------------------------
// Provider / model catalogue
// ---------------------------------------------------------------------------

const ALL_PROVIDERS: ProviderInfo[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    logoEmoji: '🤖',
    requiresApiKey: true,
    models: [
      {
        id: 'gpt-4o',
        label: 'GPT-4o',
        contextLength: 128_000,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'gpt-4o-mini',
        label: 'GPT-4o mini',
        contextLength: 128_000,
        costTier: 'low',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
      {
        id: 'gpt-4-turbo',
        label: 'GPT-4 Turbo',
        contextLength: 128_000,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
      {
        id: 'gpt-3.5-turbo',
        label: 'GPT-3.5 Turbo',
        contextLength: 16_385,
        costTier: 'low',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
      },
    ],
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    logoEmoji: 'OR',
    requiresApiKey: true,
    models: [
      {
        id: '~openai/gpt-latest',
        label: 'GPT Latest',
        contextLength: 128_000,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'openrouter/auto',
        label: 'Auto Router',
        contextLength: 200_000,
        costTier: 'medium',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
      {
        id: 'openrouter/free',
        label: 'Free Router',
        contextLength: 128_000,
        costTier: 'free',
        capabilities: { streaming: true, vision: false, functionCalling: false, codeGeneration: true },
      },
      {
        id: 'anthropic/claude-sonnet-4.5',
        label: 'Claude Sonnet 4.5',
        contextLength: 200_000,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
      {
        id: 'google/gemini-2.5-flash',
        label: 'Gemini 2.5 Flash',
        contextLength: 1_000_000,
        costTier: 'low',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
    ],
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    logoEmoji: '🧠',
    requiresApiKey: true,
    models: [
      {
        id: 'claude-3-5-sonnet-20241022',
        label: 'Claude 3.5 Sonnet',
        contextLength: 200_000,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'claude-3-5-haiku-20241022',
        label: 'Claude 3.5 Haiku',
        contextLength: 200_000,
        costTier: 'medium',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
      {
        id: 'claude-3-opus-20240229',
        label: 'Claude 3 Opus',
        contextLength: 200_000,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
    ],
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    logoEmoji: '✨',
    requiresApiKey: true,
    models: [
      {
        id: 'gemini-2.0-flash',
        label: 'Gemini 2.0 Flash',
        contextLength: 1_000_000,
        costTier: 'low',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'gemini-1.5-pro',
        label: 'Gemini 1.5 Pro',
        contextLength: 2_000_000,
        costTier: 'medium',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
      },
    ],
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    logoEmoji: '🔍',
    requiresApiKey: true,
    models: [
      {
        id: 'deepseek-chat',
        label: 'DeepSeek Chat',
        contextLength: 64_000,
        costTier: 'low',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'deepseek-reasoner',
        label: 'DeepSeek Reasoner (R1)',
        contextLength: 64_000,
        costTier: 'medium',
        capabilities: { streaming: true, vision: false, functionCalling: false, codeGeneration: true },
        isBeta: true,
      },
    ],
  },
  {
    id: 'groq',
    label: 'Groq',
    logoEmoji: '⚡',
    requiresApiKey: true,
    models: [
      {
        id: 'llama-3.3-70b-versatile',
        label: 'Llama 3.3 70B',
        contextLength: 128_000,
        costTier: 'low',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'mixtral-8x7b-32768',
        label: 'Mixtral 8x7B',
        contextLength: 32_768,
        costTier: 'free',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
      },
    ],
  },
  {
    id: 'ollama',
    label: 'Ollama (local)',
    logoEmoji: '🦙',
    requiresApiKey: false,
    localOnly: true,
    models: [
      {
        id: 'llama3.2',
        label: 'Llama 3.2',
        contextLength: 128_000,
        costTier: 'free',
        capabilities: { streaming: true, vision: false, functionCalling: false, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'mistral',
        label: 'Mistral 7B',
        contextLength: 32_768,
        costTier: 'free',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
      },
      {
        id: 'codellama',
        label: 'Code Llama',
        contextLength: 16_384,
        costTier: 'free',
        capabilities: { streaming: true, vision: false, functionCalling: false, codeGeneration: true },
      },
    ],
  },
  {
    id: 'mistral',
    label: 'Mistral AI',
    logoEmoji: '🌬️',
    requiresApiKey: true,
    models: [
      {
        id: 'mistral-large-latest',
        label: 'Mistral Large',
        contextLength: 131_072,
        costTier: 'high',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
      {
        id: 'codestral-latest',
        label: 'Codestral',
        contextLength: 262_144,
        costTier: 'medium',
        capabilities: { streaming: true, vision: false, functionCalling: true, codeGeneration: true },
      },
    ],
  },
  {
    id: 'xai',
    label: 'xAI Grok',
    logoEmoji: '𝕏',
    requiresApiKey: true,
    models: [
      {
        id: 'grok-2',
        label: 'Grok 2',
        contextLength: 131_072,
        costTier: 'high',
        capabilities: { streaming: true, vision: true, functionCalling: true, codeGeneration: true },
        isDefault: true,
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatContextLength(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M ctx`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K ctx`;
  return `${tokens} ctx`;
}

const COST_TIER_LABELS: Record<CostTier, string> = {
  free: '🆓 Free',
  low: '💚 Low',
  medium: '🟡 Mid',
  high: '🔴 High',
};

const COST_TIER_CLASSES: Record<CostTier, string> = {
  free: 'bg-green-100 text-green-800',
  low: 'bg-teal-100 text-teal-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface CapabilityBadgeProps {
  active: boolean;
  label: string;
  icon: string;
}

const CapabilityBadge: FC<CapabilityBadgeProps> = ({ active, label, icon }) => (
  <span
    title={label}
    className={`inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-xs font-medium ${
      active
        ? 'bg-indigo-100 text-indigo-700'
        : 'bg-gray-100 text-gray-400 line-through'
    }`}
    aria-label={`${label}: ${active ? 'supported' : 'not supported'}`}
  >
    {icon}
  </span>
);

interface ModelOptionProps {
  model: ModelInfo;
  isSelected: boolean;
  showCapabilities: boolean;
  showCost: boolean;
  onSelect: (modelId: string) => void;
}

const ModelOption: FC<ModelOptionProps> = ({
  model,
  isSelected,
  showCapabilities,
  showCost,
  onSelect,
}) => (
  <button
    role="option"
    aria-selected={isSelected}
    onClick={() => onSelect(model.id)}
    className={`w-full text-left px-3 py-2 text-sm rounded-md flex flex-col gap-1 transition-colors ${
      isSelected
        ? 'bg-indigo-600 text-white'
        : 'hover:bg-gray-100 text-gray-900'
    }`}
  >
    <span className="flex items-center gap-2">
      <span className="font-medium">{model.label}</span>
      {model.isDefault && (
        <span className="text-xs opacity-70">(default)</span>
      )}
      {model.isBeta && (
        <span className="rounded bg-purple-200 px-1 text-xs text-purple-700">beta</span>
      )}
    </span>

    <span className="flex flex-wrap items-center gap-1">
      <span
        className={`rounded px-1 py-0.5 text-xs ${
          isSelected ? 'bg-white/20 text-white' : 'bg-gray-200 text-gray-600'
        }`}
      >
        {formatContextLength(model.contextLength)}
      </span>

      {showCost && (
        <span
          className={`rounded px-1 py-0.5 text-xs ${
            isSelected ? 'bg-white/20 text-white' : COST_TIER_CLASSES[model.costTier]
          }`}
        >
          {COST_TIER_LABELS[model.costTier]}
        </span>
      )}

      {showCapabilities && (
        <>
          <CapabilityBadge active={model.capabilities.streaming} label="Streaming" icon="▶" />
          <CapabilityBadge active={model.capabilities.vision} label="Vision" icon="👁" />
          <CapabilityBadge active={model.capabilities.functionCalling} label="Tool calling" icon="🔧" />
          <CapabilityBadge active={model.capabilities.codeGeneration} label="Code" icon="</>"/>
        </>
      )}
    </span>
  </button>
);

// ---------------------------------------------------------------------------
// useModelSelector hook (headless)
// ---------------------------------------------------------------------------

export function useModelSelector(initialSelection: ModelSelection) {
  const [selection, setSelection] = useState<ModelSelection>(initialSelection);
  const [isOpen, setIsOpen] = useState(false);

  const selectedProvider = useMemo(
    () => ALL_PROVIDERS.find((p) => p.id === selection.provider) ?? ALL_PROVIDERS[0],
    [selection.provider]
  );

  const selectedModel = useMemo(
    () => selectedProvider.models.find((m) => m.id === selection.model) ?? selectedProvider.models[0],
    [selectedProvider, selection.model]
  );

  const selectModel = useCallback(
    (providerId: string, modelId: string) => {
      setSelection({ provider: providerId, model: modelId });
      setIsOpen(false);
    },
    []
  );

  return { selection, isOpen, setIsOpen, selectedProvider, selectedModel, selectModel, providers: ALL_PROVIDERS };
}

// ---------------------------------------------------------------------------
// ModelSelector (main component)
// ---------------------------------------------------------------------------

export const ModelSelector: FC<ModelSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  className = '',
  showCapabilityBadges = true,
  showCostTier = true,
  placeholder = 'Select a model…',
}) => {
  const triggerId = useId();
  const listboxId = useId();
  const [isOpen, setIsOpen] = useState(false);
  const [activeProvider, setActiveProvider] = useState<string>(
    value.provider || ALL_PROVIDERS[0].id
  );
  const panelRef = useRef<HTMLDivElement>(null);

  const selectedProvider = ALL_PROVIDERS.find((p) => p.id === value.provider) ?? ALL_PROVIDERS[0];
  const selectedModel = selectedProvider.models.find((m) => m.id === value.model) ?? selectedProvider.models[0];

  // Close panel on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [isOpen]);

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'Escape') setIsOpen(false);
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsOpen((prev) => !prev);
    }
  };

  const handleModelSelect = (modelId: string) => {
    onChange({ provider: activeProvider, model: modelId });
    setIsOpen(false);
  };

  return (
    <div ref={panelRef} className={`relative inline-block ${className}`}>
      {/* Trigger button */}
      <button
        id={triggerId}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-label="Select AI model"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium shadow-sm transition-colors ${
          disabled
            ? 'cursor-not-allowed bg-gray-100 text-gray-400'
            : 'cursor-pointer bg-white text-gray-900 hover:bg-gray-50 border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500'
        }`}
      >
        <span className="text-base">{selectedProvider.logoEmoji}</span>
        <span>
          {selectedProvider.label} / {selectedModel.label}
        </span>
        {selectedModel.isBeta && (
          <span className="rounded bg-purple-200 px-1 text-xs text-purple-700">beta</span>
        )}
        <svg
          className={`ml-1 h-4 w-4 text-gray-500 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          aria-labelledby={triggerId}
          className="absolute left-0 z-50 mt-2 flex w-[520px] max-h-[480px] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
        >
          {/* Provider sidebar */}
          <div className="w-40 shrink-0 overflow-y-auto border-r border-gray-100 bg-gray-50 p-2">
            <p className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
              Provider
            </p>
            {ALL_PROVIDERS.map((provider) => (
              <button
                key={provider.id}
                onClick={() => setActiveProvider(provider.id)}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${
                  activeProvider === provider.id
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <span>{provider.logoEmoji}</span>
                <span className="truncate">{provider.label}</span>
                {provider.localOnly && (
                  <span className="ml-auto text-xs opacity-60">local</span>
                )}
              </button>
            ))}
          </div>

          {/* Model list */}
          <div className="flex-1 overflow-y-auto p-2">
            {(() => {
              const prov = ALL_PROVIDERS.find((p) => p.id === activeProvider);
              if (!prov) return null;
              return (
                <>
                  <p className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
                    {prov.label} models
                  </p>
                  <div className="flex flex-col gap-1" role="group" aria-label={`${prov.label} models`}>
                    {prov.models.map((model) => (
                      <ModelOption
                        key={model.id}
                        model={model}
                        isSelected={value.provider === activeProvider && value.model === model.id}
                        showCapabilities={showCapabilityBadges}
                        showCost={showCostTier}
                        onSelect={handleModelSelect}
                      />
                    ))}
                  </div>

                  {prov.requiresApiKey && (
                    <p className="mt-2 px-1 text-xs text-gray-400">
                      🔑 API key required — set in Settings → Providers
                    </p>
                  )}
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelSelector;
