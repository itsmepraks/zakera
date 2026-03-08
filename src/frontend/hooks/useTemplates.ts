/**
 * Custom React hook for managing conversation templates
 */

import { useState, useEffect, useCallback } from 'react';
import {
  ConversationTemplate,
  TemplateListResponse,
  TemplateFilters,
  TemplateStats,
} from '../types/templates';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

interface UseTemplatesResult {
  templates: ConversationTemplate[];
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  hasMore: boolean;
  fetchTemplates: (filters?: TemplateFilters, page?: number) => Promise<void>;
  fetchPopular: (limit?: number, category?: string) => Promise<void>;
  getTemplate: (id: number) => Promise<ConversationTemplate | null>;
  getTemplateStats: (id: number) => Promise<TemplateStats | null>;
  logTemplateUsage: (id: number, conversationId?: number, modelUsed?: string) => Promise<void>;
  refreshTemplates: () => Promise<void>;
}

export const useTemplates = (): UseTemplatesResult => {
  const [templates, setTemplates] = useState<ConversationTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [currentFilters, setCurrentFilters] = useState<TemplateFilters>({});

  const fetchTemplates = useCallback(
    async (filters: TemplateFilters = {}, pageNum: number = 1) => {
      setLoading(true);
      setError(null);
      setCurrentFilters(filters);
      setPage(pageNum);

      try {
        const params = new URLSearchParams();
        params.append('skip', String((pageNum - 1) * 20));
        params.append('limit', '20');

        if (filters.category) params.append('category', filters.category);
        if (filters.difficulty) params.append('difficulty', filters.difficulty);
        if (filters.search) params.append('search', filters.search);
        if (filters.is_public !== undefined)
          params.append('is_public', String(filters.is_public));
        if (filters.is_active !== undefined)
          params.append('is_active', String(filters.is_active));
        if (filters.sort_by) params.append('sort_by', filters.sort_by);
        if (filters.sort_order) params.append('sort_order', filters.sort_order);
        if (filters.tags) {
          filters.tags.forEach((tag) => params.append('tags', tag));
        }

        const response = await fetch(
          `${API_BASE}/conversation-templates/?${params.toString()}`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch templates: ${response.statusText}`);
        }

        const data: TemplateListResponse = await response.json();
        setTemplates(data.templates);
        setTotal(data.total);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(errorMessage);
        console.error('Error fetching templates:', err);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const fetchPopular = useCallback(async (limit: number = 10, category?: string) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('limit', String(limit));
      if (category) params.append('category', category);

      const response = await fetch(
        `${API_BASE}/conversation-templates/popular/top?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch popular templates: ${response.statusText}`);
      }

      const data: ConversationTemplate[] = await response.json();
      setTemplates(data);
      setTotal(data.length);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching popular templates:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const getTemplate = useCallback(async (id: number): Promise<ConversationTemplate | null> => {
    try {
      const response = await fetch(`${API_BASE}/conversation-templates/${id}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch template: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      console.error('Error fetching template:', err);
      return null;
    }
  }, []);

  const getTemplateStats = useCallback(async (id: number): Promise<TemplateStats | null> => {
    try {
      const response = await fetch(`${API_BASE}/conversation-templates/${id}/stats`);

      if (!response.ok) {
        throw new Error(`Failed to fetch template stats: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      console.error('Error fetching template stats:', err);
      return null;
    }
  }, []);

  const logTemplateUsage = useCallback(
    async (id: number, conversationId?: number, modelUsed?: string): Promise<void> => {
      try {
        const params = new URLSearchParams();
        if (conversationId) params.append('conversation_id', String(conversationId));
        if (modelUsed) params.append('model_used', modelUsed);

        const response = await fetch(
          `${API_BASE}/conversation-templates/${id}/use?${params.toString()}`,
          { method: 'POST' }
        );

        if (!response.ok) {
          console.warn('Failed to log template usage:', response.statusText);
        }
      } catch (err) {
        console.warn('Error logging template usage:', err);
        // Don't throw - usage logging shouldn't block functionality
      }
    },
    []
  );

  const refreshTemplates = useCallback(async () => {
    await fetchTemplates(currentFilters, page);
  }, [currentFilters, page, fetchTemplates]);

  // Initial fetch on mount
  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const hasMore = templates.length < total;

  return {
    templates,
    loading,
    error,
    total,
    page,
    hasMore,
    fetchTemplates,
    fetchPopular,
    getTemplate,
    getTemplateStats,
    logTemplateUsage,
    refreshTemplates,
  };
};

export default useTemplates;
