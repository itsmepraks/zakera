/**
 * TypeScript type definitions for the Tool System
 */

export interface ToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
  default?: any;
  enum?: string[];
  min?: number;
  max?: number;
  pattern?: string;
}

export interface Tool {
  name: string;
  description: string;
  category: string;
  parameters: ToolParameter[];
  version?: string;
  author?: string;
  tags?: string[];
  examples?: ToolExample[];
}

export interface ToolExample {
  description: string;
  parameters: Record<string, any>;
  expected_output?: string;
}

export interface ToolExecutionResult {
  success: boolean;
  result?: any;
  error?: string;
  execution_time?: number;
  timestamp: string;
  tool_name: string;
  parameters: Record<string, any>;
}

export interface ToolExecutionHistory {
  id: string;
  tool_name: string;
  parameters: Record<string, any>;
  result: ToolExecutionResult;
  timestamp: string;
  user_id?: string;
}

export interface ToolStatistics {
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_execution_time: number;
  cache_hits: number;
  cache_misses: number;
  most_used_tools: Array<{
    name: string;
    count: number;
  }>;
}

export interface ToolChainExecution {
  tools: Array<{
    name: string;
    parameters: Record<string, any>;
  }>;
  results?: ToolExecutionResult[];
}

export type ToolCategory = 'builtin' | 'custom' | 'api' | 'utility' | 'all';

export interface ToolFilters {
  category?: ToolCategory;
  search?: string;
  tags?: string[];
}
