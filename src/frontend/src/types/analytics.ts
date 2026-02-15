/**
 * Analytics Type Definitions
 * 
 * Comprehensive TypeScript types for analytics data structures,
 * API responses, and component props.
 */

export interface DateRangeParams {
  startDate?: Date;
  endDate?: Date;
}

export interface AnalyticsOverview {
  success: boolean;
  data: {
    total_conversations: number;
    total_messages: number;
    active_users: number;
    avg_messages_per_conversation: number;
    success_rate: number;
    model_usage: Record<string, number>;
    period: {
      start: string;
      end: string;
    };
  };
  message?: string;
}

export interface ConversationMetrics {
  success: boolean;
  data: {
    duration_stats: {
      avg_seconds: number;
      max_seconds: number;
      min_seconds: number;
    };
    message_distribution: Record<string, number>;
    daily_counts: Record<string, number>;
    top_conversations: Array<{
      id: number;
      title: string;
      message_count: number;
      duration_seconds: number;
      created_at: string;
    }>;
    filters?: {
      start_date: string;
      end_date: string;
      user_id?: number;
      model?: string;
    };
  };
}

export interface ModelPerformance {
  success: boolean;
  data: {
    models: Record<
      string,
      {
        total_messages: number;
        avg_response_time_ms: number;
        total_tokens: number;
        avg_prompt_tokens: number;
        avg_completion_tokens: number;
        tokens_per_message: number;
      }
    >;
    period: {
      start: string;
      end: string;
    };
  };
}

export interface UserEngagement {
  success: boolean;
  data: {
    top_users: Array<{
      user_id: number;
      conversation_count: number;
      total_messages: number;
      avg_messages_per_conversation: number;
      last_activity: string;
    }>;
    retention: {
      weekly_data: Array<{
        week: number;
        start_date: string;
        end_date: string;
        active_users: number;
        retention_rate?: number;
      }>;
      total_weeks: number;
    };
    period: {
      start: string;
      end: string;
    };
  };
}

export interface CostAnalysis {
  success: boolean;
  data: {
    total_cost_usd: number;
    daily_avg_cost_usd: number;
    monthly_projected_cost_usd: number;
    cost_breakdown: Array<{
      model: string;
      message_count: number;
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      estimated_cost_usd: number;
      cost_per_message: number;
    }>;
    period: {
      start: string;
      end: string;
      days: number;
    };
  };
}

export interface TrendParams {
  metric: 'conversations' | 'messages' | 'users' | 'costs';
  days: number;
}

export interface TrendData {
  success: boolean;
  data: {
    metric: string;
    daily_data: Record<string, number>;
    trend: {
      direction: 'increasing' | 'decreasing' | 'stable';
      percentage_change: number;
    };
    period: {
      days: number;
      start: string;
      end: string;
    };
  };
  message?: string;
}

export interface ExportParams extends DateRangeParams {
  type: 'overview' | 'conversations' | 'models' | 'users' | 'costs';
  format: 'json' | 'csv';
}

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

export interface TimeSeriesDataPoint {
  date: string;
  value: number;
}

export interface MetricCardData {
  title: string;
  value: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease';
  icon?: React.ComponentType;
}
