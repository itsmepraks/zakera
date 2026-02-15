/**
 * Settings Type Definitions
 */

export interface UserSettings {
  // General
  language: string;
  autoSave: boolean;
  notifications: boolean;
  soundEffects: boolean;

  // Model
  defaultModel: string;
  temperature: number;
  maxTokens: number;
  streaming: boolean;

  // Appearance
  theme: 'light' | 'dark' | 'system';
  fontSize: 'small' | 'medium' | 'large';
  codeTheme: 'github' | 'dracula' | 'nord' | 'monokai';
  compactMode: boolean;

  // Privacy
  saveHistory: boolean;
  analytics: boolean;
  shareToImprove: boolean;
}

export const defaultSettings: UserSettings = {
  language: 'en',
  autoSave: true,
  notifications: true,
  soundEffects: false,
  defaultModel: 'gpt-3.5-turbo',
  temperature: 0.7,
  maxTokens: 2048,
  streaming: true,
  theme: 'system',
  fontSize: 'medium',
  codeTheme: 'github',
  compactMode: false,
  saveHistory: true,
  analytics: true,
  shareToImprove: false,
};
