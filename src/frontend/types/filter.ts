/**
 * Filter and Search Type Definitions
 */

export interface FilterPreset {
  id: string;
  name: string;
  description?: string;
  filter: ConversationFilter;
  sort?: ConversationSort;
  icon?: string;
  isDefault?: boolean;
  createdAt: string;
}

export interface SearchSuggestion {
  type: 'tag' | 'model' | 'recent' | 'command';
  value: string;
  label: string;
  description?: string;
  count?: number;
}

export interface SearchQuery {
  text: string;
  filters: ConversationFilter;
  suggestions: SearchSuggestion[];
  recent: string[];
}

export interface FilterState {
  active: ConversationFilter;
  presets: FilterPreset[];
  history: ConversationFilter[];
  dirty: boolean;
}

import { ConversationFilter, ConversationSort } from './conversation';
