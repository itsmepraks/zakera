/**
 * useSettings Hook
 * 
 * Custom hook for managing user settings with local storage persistence,
 * auto-save functionality, and import/export capabilities.
 */

import { useState, useEffect, useCallback } from 'react';
import { UserSettings, defaultSettings } from '@/types/settings';

const SETTINGS_KEY = 'zakera_user_settings';

interface UseSettingsReturn {
  settings: UserSettings;
  updateSettings: (updates: Partial<UserSettings>) => void;
  resetSettings: () => void;
  exportSettings: () => UserSettings;
  importSettings: (settings: Partial<UserSettings>) => void;
  isDirty: boolean;
  save: () => Promise<void>;
}

export function useSettings(): UseSettingsReturn {
  const [settings, setSettings] = useState<UserSettings>(defaultSettings);
  const [initialSettings, setInitialSettings] = useState<UserSettings>(defaultSettings);
  const [isDirty, setIsDirty] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    const loadSettings = () => {
      try {
        const stored = localStorage.getItem(SETTINGS_KEY);
        if (stored) {
          const parsed = JSON.parse(stored) as UserSettings;
          const merged = { ...defaultSettings, ...parsed };
          setSettings(merged);
          setInitialSettings(merged);
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    };

    loadSettings();
  }, []);

  // Apply theme changes
  useEffect(() => {
    const root = document.documentElement;
    
    if (settings.theme === 'dark') {
      root.classList.add('dark');
    } else if (settings.theme === 'light') {
      root.classList.remove('dark');
    } else {
      // System preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  }, [settings.theme]);

  // Check if settings have changed
  useEffect(() => {
    const hasChanged = JSON.stringify(settings) !== JSON.stringify(initialSettings);
    setIsDirty(hasChanged);
  }, [settings, initialSettings]);

  // Auto-save if enabled
  useEffect(() => {
    if (settings.autoSave && isDirty) {
      const timer = setTimeout(() => {
        save();
      }, 1000); // Debounce 1 second

      return () => clearTimeout(timer);
    }
  }, [settings, isDirty]);

  const updateSettings = useCallback((updates: Partial<UserSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  }, []);

  const save = useCallback(async () => {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      setInitialSettings(settings);
      setIsDirty(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
      throw error;
    }
  }, [settings]);

  const resetSettings = useCallback(() => {
    setSettings(defaultSettings);
    setInitialSettings(defaultSettings);
    localStorage.removeItem(SETTINGS_KEY);
    setIsDirty(false);
  }, []);

  const exportSettings = useCallback(() => {
    return settings;
  }, [settings]);

  const importSettings = useCallback((imported: Partial<UserSettings>) => {
    const merged = { ...defaultSettings, ...imported };
    setSettings(merged);
  }, []);

  return {
    settings,
    updateSettings,
    resetSettings,
    exportSettings,
    importSettings,
    isDirty,
    save,
  };
}
