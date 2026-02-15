/**
 * Analytics Service
 * 
 * Type-safe API client for interacting with the analytics backend.
 * Handles all analytics-related API calls with proper error handling,
 * caching, and data transformation.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { 
  AnalyticsOverview,
  ConversationMetrics,
  ModelPerformance,
  UserEngagement,
  CostAnalysis,
  DateRangeParams,
  ExportParams,
  TrendParams,
  TrendData,
} from '@/types/analytics';

class AnalyticsService {
  private client: AxiosInstance;
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private cacheTTL = 5 * 60 * 1000; // 5 minutes

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private getCacheKey(endpoint: string, params?: any): string {
    return `${endpoint}:${JSON.stringify(params || {})}`;
  }

  private getFromCache<T>(key: string): T | null {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.cacheTTL) {
      return cached.data as T;
    }
    this.cache.delete(key);
    return null;
  }

  private setCache(key: string, data: any): void {
    this.cache.set(key, { data, timestamp: Date.now() });
  }

  private handleError(error: AxiosError): Error {
    if (error.response) {
      const message = (error.response.data as any)?.detail || error.message;
      return new Error(`API Error: ${message}`);
    } else if (error.request) {
      return new Error('No response from server. Please check your connection.');
    }
    return new Error(error.message);
  }

  /**
   * Get overview metrics
   */
  async getOverviewMetrics(params?: DateRangeParams): Promise<AnalyticsOverview> {
    const cacheKey = this.getCacheKey('/api/v1/analytics/overview', params);
    const cached = this.getFromCache<AnalyticsOverview>(cacheKey);
    if (cached) return cached;

    const response = await this.client.get<AnalyticsOverview>('/api/v1/analytics/overview', {
      params: this.formatDateParams(params),
    });

    this.setCache(cacheKey, response.data);
    return response.data;
  }

  /**
   * Get conversation metrics
   */
  async getConversationMetrics(params?: DateRangeParams & {
    userId?: number;
    model?: string;
  }): Promise<ConversationMetrics> {
    const cacheKey = this.getCacheKey('/api/v1/analytics/conversations', params);
    const cached = this.getFromCache<ConversationMetrics>(cacheKey);
    if (cached) return cached;

    const response = await this.client.get<ConversationMetrics>(
      '/api/v1/analytics/conversations',
      { params: this.formatDateParams(params) }
    );

    this.setCache(cacheKey, response.data);
    return response.data;
  }

  /**
   * Get model performance metrics
   */
  async getModelPerformance(params?: DateRangeParams): Promise<ModelPerformance> {
    const cacheKey = this.getCacheKey('/api/v1/analytics/models', params);
    const cached = this.getFromCache<ModelPerformance>(cacheKey);
    if (cached) return cached;

    const response = await this.client.get<ModelPerformance>('/api/v1/analytics/models', {
      params: this.formatDateParams(params),
    });

    this.setCache(cacheKey, response.data);
    return response.data;
  }

  /**
   * Get user engagement metrics
   */
  async getUserEngagement(params?: DateRangeParams & { topN?: number }): Promise<UserEngagement> {
    const cacheKey = this.getCacheKey('/api/v1/analytics/users', params);
    const cached = this.getFromCache<UserEngagement>(cacheKey);
    if (cached) return cached;

    const response = await this.client.get<UserEngagement>('/api/v1/analytics/users', {
      params: this.formatDateParams(params),
    });

    this.setCache(cacheKey, response.data);
    return response.data;
  }

  /**
   * Get cost analysis
   */
  async getCostAnalysis(params?: DateRangeParams): Promise<CostAnalysis> {
    const cacheKey = this.getCacheKey('/api/v1/analytics/costs', params);
    const cached = this.getFromCache<CostAnalysis>(cacheKey);
    if (cached) return cached;

    const response = await this.client.get<CostAnalysis>('/api/v1/analytics/costs', {
      params: this.formatDateParams(params),
    });

    this.setCache(cacheKey, response.data);
    return response.data;
  }

  /**
   * Get trend analysis
   */
  async getTrends(params: TrendParams): Promise<TrendData> {
    const response = await this.client.get<TrendData>('/api/v1/analytics/trends', {
      params,
    });
    return response.data;
  }

  /**
   * Export analytics data
   */
  async exportData(params: ExportParams): Promise<any> {
    const response = await this.client.get('/api/v1/analytics/export', {
      params: {
        ...this.formatDateParams(params),
        format: params.format,
        metric_type: params.type,
      },
      responseType: params.format === 'json' ? 'json' : 'blob',
    });
    return response.data;
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Clear specific cache entry
   */
  clearCacheEntry(endpoint: string, params?: any): void {
    const key = this.getCacheKey(endpoint, params);
    this.cache.delete(key);
  }

  /**
   * Format date parameters for API
   */
  private formatDateParams(params?: DateRangeParams & any): any {
    if (!params) return {};

    const { startDate, endDate, ...rest } = params;
    return {
      ...rest,
      start_date: startDate ? startDate.toISOString() : undefined,
      end_date: endDate ? endDate.toISOString() : undefined,
    };
  }
}

export const analyticsService = new AnalyticsService();
