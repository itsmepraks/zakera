"use client";

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  TrendingDown,
  Users,
  MessageSquare,
  DollarSign,
  Activity,
  Download,
  RefreshCw,
  Calendar,
} from 'lucide-react';
import { analyticsService } from '@/services/analytics';
import { OverviewMetrics } from './OverviewMetrics';
import { ConversationChart } from './ConversationChart';
import { ModelPerformanceChart } from './ModelPerformanceChart';
import { UserEngagementChart } from './UserEngagementChart';
import { CostAnalysisChart } from './CostAnalysisChart';
import { DateRangePicker } from './DateRangePicker';
import { formatNumber, formatCurrency, formatPercentage } from '@/lib/utils';

interface AnalyticsDashboardProps {
  className?: string;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ className = '' }) => {
  const [dateRange, setDateRange] = useState<{ start: Date; end: Date }>({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date(),
  });
  const [activeTab, setActiveTab] = useState<'overview' | 'conversations' | 'models' | 'users' | 'costs'>('overview');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch overview metrics
  const {
    data: overviewData,
    isLoading: overviewLoading,
    error: overviewError,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ['analytics', 'overview', dateRange.start, dateRange.end],
    queryFn: () =>
      analyticsService.getOverviewMetrics({
        startDate: dateRange.start,
        endDate: dateRange.end,
      }),
  });

  // Fetch conversation metrics
  const {
    data: conversationData,
    isLoading: conversationLoading,
    refetch: refetchConversations,
  } = useQuery({
    queryKey: ['analytics', 'conversations', dateRange.start, dateRange.end],
    queryFn: () =>
      analyticsService.getConversationMetrics({
        startDate: dateRange.start,
        endDate: dateRange.end,
      }),
    enabled: activeTab === 'conversations',
  });

  // Fetch model performance
  const {
    data: modelData,
    isLoading: modelLoading,
    refetch: refetchModels,
  } = useQuery({
    queryKey: ['analytics', 'models', dateRange.start, dateRange.end],
    queryFn: () =>
      analyticsService.getModelPerformance({
        startDate: dateRange.start,
        endDate: dateRange.end,
      }),
    enabled: activeTab === 'models',
  });

  // Fetch user engagement
  const {
    data: userData,
    isLoading: userLoading,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ['analytics', 'users', dateRange.start, dateRange.end],
    queryFn: () =>
      analyticsService.getUserEngagement({
        startDate: dateRange.start,
        endDate: dateRange.end,
        topN: 20,
      }),
    enabled: activeTab === 'users',
  });

  // Fetch cost analysis
  const {
    data: costData,
    isLoading: costLoading,
    refetch: refetchCosts,
  } = useQuery({
    queryKey: ['analytics', 'costs', dateRange.start, dateRange.end],
    queryFn: () =>
      analyticsService.getCostAnalysis({
        startDate: dateRange.start,
        endDate: dateRange.end,
      }),
    enabled: activeTab === 'costs',
  });

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([
      refetchOverview(),
      refetchConversations(),
      refetchModels(),
      refetchUsers(),
      refetchCosts(),
    ]);
    setIsRefreshing(false);
  };

  const handleExport = async () => {
    const data = await analyticsService.exportData({
      type: activeTab,
      format: 'json',
      startDate: dateRange.start,
      endDate: dateRange.end,
    });

    // Create download link
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `zakera-analytics-${activeTab}-${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'conversations', label: 'Conversations', icon: MessageSquare },
    { id: 'models', label: 'Models', icon: Activity },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'costs', label: 'Costs', icon: DollarSign },
  ] as const;

  return (
    <div className={`analytics-dashboard ${className}`}>
      {/* Header */}
      <div className="flex flex-col gap-4 mb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analytics</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Insights into conversations, models, and user engagement
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <DateRangePicker value={dateRange} onChange={setDateRange} />

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Refresh analytics data"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <button
            onClick={handleExport}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Export analytics data"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto border-b border-gray-200 dark:border-gray-700">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 whitespace-nowrap ${
              activeTab === id
                ? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
                : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
            }`}
            aria-selected={activeTab === id}
            role="tab"
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-6">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {overviewLoading ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, i) => (
                  <div
                    key={i}
                    className="h-32 bg-gray-200 rounded-lg animate-pulse dark:bg-gray-700"
                  />
                ))}
              </div>
            ) : overviewError ? (
              <div className="p-4 text-red-800 bg-red-100 border border-red-300 rounded-lg dark:bg-red-900/20 dark:text-red-400">
                Error loading overview data. Please try again.
              </div>
            ) : overviewData ? (
              <>
                {/* Metric Cards */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <MetricCard
                    title="Total Conversations"
                    value={formatNumber(overviewData.data.total_conversations)}
                    icon={MessageSquare}
                    trend={{
                      value: 12.5,
                      direction: 'up',
                    }}
                  />
                  <MetricCard
                    title="Total Messages"
                    value={formatNumber(overviewData.data.total_messages)}
                    icon={Activity}
                    trend={{
                      value: 8.3,
                      direction: 'up',
                    }}
                  />
                  <MetricCard
                    title="Active Users"
                    value={formatNumber(overviewData.data.active_users)}
                    icon={Users}
                    trend={{
                      value: 5.7,
                      direction: 'up',
                    }}
                  />
                  <MetricCard
                    title="Success Rate"
                    value={formatPercentage(overviewData.data.success_rate)}
                    icon={TrendingUp}
                    trend={{
                      value: 2.1,
                      direction: 'up',
                    }}
                  />
                </div>

                {/* Additional Overview Content */}
                <OverviewMetrics data={overviewData.data} />
              </>
            ) : null}
          </div>
        )}

        {/* Conversations Tab */}
        {activeTab === 'conversations' && (
          <div className="space-y-6">
            {conversationLoading ? (
              <div className="h-64 bg-gray-200 rounded-lg animate-pulse dark:bg-gray-700" />
            ) : conversationData ? (
              <ConversationChart data={conversationData.data} />
            ) : null}
          </div>
        )}

        {/* Models Tab */}
        {activeTab === 'models' && (
          <div className="space-y-6">
            {modelLoading ? (
              <div className="h-64 bg-gray-200 rounded-lg animate-pulse dark:bg-gray-700" />
            ) : modelData ? (
              <ModelPerformanceChart data={modelData.data} />
            ) : null}
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            {userLoading ? (
              <div className="h-64 bg-gray-200 rounded-lg animate-pulse dark:bg-gray-700" />
            ) : userData ? (
              <UserEngagementChart data={userData.data} />
            ) : null}
          </div>
        )}

        {/* Costs Tab */}
        {activeTab === 'costs' && (
          <div className="space-y-6">
            {costLoading ? (
              <div className="h-64 bg-gray-200 rounded-lg animate-pulse dark:bg-gray-700" />
            ) : costData ? (
              <CostAnalysisChart data={costData.data} />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

// Metric Card Component
interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ElementType;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, icon: Icon, trend }) => {
  return (
    <div className="p-6 bg-white border border-gray-200 rounded-lg shadow-sm dark:bg-gray-800 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</span>
        <div className="p-2 bg-blue-100 rounded-lg dark:bg-blue-900/20">
          <Icon className="w-5 h-5 text-blue-600 dark:text-blue-500" />
        </div>
      </div>
      <div className="flex items-end justify-between">
        <span className="text-3xl font-bold text-gray-900 dark:text-white">{value}</span>
        {trend && (
          <div
            className={`flex items-center gap-1 text-sm font-medium ${
              trend.direction === 'up'
                ? 'text-green-600 dark:text-green-500'
                : 'text-red-600 dark:text-red-500'
            }`}
          >
            {trend.direction === 'up' ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            {formatPercentage(trend.value)}
          </div>
        )}
      </div>
    </div>
  );
};
