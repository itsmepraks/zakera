/**
 * TypeScript type definitions for conversation templates
 */

export type TemplateCategory =
  | 'code_review'
  | 'technical'
  | 'creative'
  | 'problem_solving'
  | 'learning'
  | 'brainstorming'
  | 'analysis'
  | 'general';

export type TemplateDifficulty = 'beginner' | 'intermediate' | 'advanced' | 'expert';

export interface ConversationTemplate {
  id: number;
  title: string;
  description: string;
  category: TemplateCategory;
  difficulty: TemplateDifficulty;
  system_prompt: string;
  starter_message: string | null;
  suggested_questions: string[];
  tags: string[];
  model_recommendations: string[];
  is_public: boolean;
  is_active: boolean;
  usage_count: number;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  total: number;
  page: number;
  page_size: number;
  templates: ConversationTemplate[];
}

export interface TemplateFilters {
  category?: TemplateCategory;
  difficulty?: TemplateDifficulty;
  tags?: string[];
  search?: string;
  is_public?: boolean;
  is_active?: boolean;
  sort_by?: 'created_at' | 'updated_at' | 'usage_count' | 'title';
  sort_order?: 'asc' | 'desc';
}

export interface TemplateStats {
  template_id: number;
  title: string;
  total_uses: number;
  unique_users: number;
  last_used: string | null;
  model_distribution: Record<string, number>;
  created_at: string;
  is_public: boolean;
  is_active: boolean;
}

export const CATEGORY_LABELS: Record<TemplateCategory, string> = {
  code_review: 'Code Review',
  technical: 'Technical Discussion',
  creative: 'Creative Writing',
  problem_solving: 'Problem Solving',
  learning: 'Learning & Education',
  brainstorming: 'Brainstorming',
  analysis: 'Analysis & Optimization',
  general: 'General Purpose',
};

export const CATEGORY_ICONS: Record<TemplateCategory, string> = {
  code_review: '🔍',
  technical: '⚙️',
  creative: '✨',
  problem_solving: '🧩',
  learning: '📚',
  brainstorming: '💡',
  analysis: '📊',
  general: '💬',
};

export const DIFFICULTY_COLORS: Record<TemplateDifficulty, string> = {
  beginner: '#4ade80',
  intermediate: '#fbbf24',
  advanced: '#f97316',
  expert: '#ef4444',
};
