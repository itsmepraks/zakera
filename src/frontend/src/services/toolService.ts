/**
 * API service for tool operations
 */

import axios from 'axios';
import {
  Tool,
  ToolExecutionResult,
  ToolExecutionHistory,
  ToolStatistics,
  ToolChainExecution,
  ToolFilters,
} from '@/types/tools.types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const toolApi = axios.create({
  baseURL: `${API_BASE_URL}/api/tools`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token interceptor
toolApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const toolService = {
  /**
   * Get list of all available tools
   */
  async getTools(filters?: ToolFilters): Promise<Tool[]> {
    const params = new URLSearchParams();
    if (filters?.category && filters.category !== 'all') {
      params.append('category', filters.category);
    }
    if (filters?.search) {
      params.append('search', filters.search);
    }
    if (filters?.tags && filters.tags.length > 0) {
      params.append('tags', filters.tags.join(','));
    }

    const response = await toolApi.get(`/?${params.toString()}`);
    return response.data.tools || response.data;
  },

  /**
   * Get details of a specific tool
   */
  async getToolInfo(toolName: string): Promise<Tool> {
    const response = await toolApi.get(`/${toolName}`);
    return response.data;
  },

  /**
   * Execute a single tool
   */
  async executeTool(
    toolName: string,
    parameters: Record<string, any>
  ): Promise<ToolExecutionResult> {
    const response = await toolApi.post('/execute', {
      tool_name: toolName,
      parameters,
    });
    return response.data;
  },

  /**
   * Execute multiple tools in parallel
   */
  async executeParallel(
    executions: Array<{ tool_name: string; parameters: Record<string, any> }>
  ): Promise<ToolExecutionResult[]> {
    const response = await toolApi.post('/execute/parallel', {
      executions,
    });
    return response.data.results || response.data;
  },

  /**
   * Execute tools in a chain (output of one feeds into next)
   */
  async executeChain(chain: ToolChainExecution): Promise<ToolExecutionResult[]> {
    const response = await toolApi.post('/execute/chain', chain);
    return response.data.results || response.data;
  },

  /**
   * Get execution history
   */
  async getHistory(
    limit: number = 50,
    offset: number = 0
  ): Promise<ToolExecutionHistory[]> {
    const response = await toolApi.get('/history', {
      params: { limit, offset },
    });
    return response.data.history || response.data;
  },

  /**
   * Get tool usage statistics
   */
  async getStatistics(): Promise<ToolStatistics> {
    const response = await toolApi.get('/statistics');
    return response.data;
  },

  /**
   * Clear tool cache
   */
  async clearCache(): Promise<void> {
    await toolApi.delete('/cache');
  },

  /**
   * Get OpenAI function calling schema for tools
   */
  async getFunctionSchemas(): Promise<any[]> {
    const response = await toolApi.get('/schemas/openai');
    return response.data.functions || response.data;
  },
};
