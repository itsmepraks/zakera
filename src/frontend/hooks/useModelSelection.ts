import { useState, useCallback, useEffect } from 'react';
import { PROVIDER_GROUPS, ModelOption } from '../components/ModelSwitcher/ModelSwitcher';

const STORAGE_KEY = 'zakera_model_preference';

interface ModelPreference {
  provider: string;
  model: string;
}

const DEFAULT_PREFERENCE: ModelPreference = {
  provider: 'openai',
  model: 'gpt-4-turbo-preview',
};

function readStoredPreference(): ModelPreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFERENCE;
    const parsed = JSON.parse(raw) as Partial<ModelPreference>;
    if (parsed.provider && parsed.model) {
      return { provider: parsed.provider, model: parsed.model };
    }
  } catch {
    // localStorage not available or JSON parse error — fall back to default
  }
  return DEFAULT_PREFERENCE;
}

function writeStoredPreference(pref: ModelPreference): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pref));
  } catch {
    // Storage quota exceeded or unavailable — ignore silently
  }
}

/** All model options flattened from PROVIDER_GROUPS */
const ALL_MODELS: ModelOption[] = PROVIDER_GROUPS.flatMap(g => g.models);

interface UseModelSelectionReturn {
  /** Currently selected provider id, e.g. "openai" */
  provider: string;
  /** Currently selected model id, e.g. "gpt-4-turbo-preview" */
  model: string;
  /** Display label for the current model */
  modelLabel: string;
  /** Set both provider and model, persists to localStorage */
  setModel: (provider: string, model: string) => void;
  /** All available model options (flat list) */
  availableModels: ModelOption[];
  /** Models filtered to the currently selected provider */
  modelsForCurrentProvider: ModelOption[];
}

/**
 * Manages the selected AI provider & model.
 *
 * Reads the last selection from localStorage on mount so the user's
 * preference persists across page reloads. Updates are written back
 * synchronously after every change.
 *
 * @example
 * ```tsx
 * const { provider, model, setModel } = useModelSelection();
 *
 * return (
 *   <ModelSwitcher
 *     currentProvider={provider}
 *     currentModel={model}
 *     onModelChange={setModel}
 *   />
 * );
 * ```
 */
export function useModelSelection(): UseModelSelectionReturn {
  const [preference, setPreference] = useState<ModelPreference>(DEFAULT_PREFERENCE);

  // Hydrate from localStorage after first render (avoids SSR mismatch)
  useEffect(() => {
    setPreference(readStoredPreference());
  }, []);

  const setModel = useCallback((provider: string, model: string) => {
    const next: ModelPreference = { provider, model };
    setPreference(next);
    writeStoredPreference(next);
  }, []);

  const modelLabel =
    ALL_MODELS.find(m => m.model === preference.model && m.provider === preference.provider)
      ?.label ?? preference.model;

  const modelsForCurrentProvider = ALL_MODELS.filter(
    m => m.provider === preference.provider,
  );

  return {
    provider: preference.provider,
    model: preference.model,
    modelLabel,
    setModel,
    availableModels: ALL_MODELS,
    modelsForCurrentProvider,
  };
}
