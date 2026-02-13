/**
 * ToolHistory Component
 * Displays past tool executions with filtering and details
 */

import React, { useState, useEffect } from 'react';
import {
  History,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Filter,
} from 'lucide-react';
import { ToolExecutionHistory } from '@/types/tools.types';
import { toolService } from '@/services/toolService';
import { format } from 'date-fns';
import './ToolHistory.css';

interface ToolHistoryProps {
  limit?: number;
  autoRefresh?: boolean;
  onReExecute?: (toolName: string, parameters: Record<string, any>) => void;
}

export const ToolHistory: React.FC<ToolHistoryProps> = ({
  limit = 50,
  autoRefresh = false,
  onReExecute,
}) => {
  const [history, setHistory] = useState<ToolExecutionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterSuccess, setFilterSuccess] = useState<'all' | 'success' | 'failed'>('all');
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    loadHistory();

    if (autoRefresh) {
      const interval = setInterval(loadHistory, 10000); // Refresh every 10s
      return () => clearInterval(interval);
    }
  }, [offset, limit, autoRefresh]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await toolService.getHistory(limit, offset);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const handleRefresh = () => {
    setOffset(0);
    loadHistory();
  };

  const handleLoadMore = () => {
    setOffset((prev) => prev + limit);
  };

  const filteredHistory = history.filter((item) => {
    if (filterSuccess === 'all') return true;
    if (filterSuccess === 'success') return item.result.success;
    if (filterSuccess === 'failed') return !item.result.success;
    return true;
  });

  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'MMM d, yyyy HH:mm:ss');
    } catch {
      return timestamp;
    }
  };

  if (loading && history.length === 0) {
    return (
      <div className="tool-history loading">
        <div className="loading-spinner" />
        <p>Loading history...</p>
      </div>
    );
  }

  return (
    <div className="tool-history">
      <div className="history-header">
        <h3 className="history-title">
          <History className="icon" />
          Tool Execution History
        </h3>
        <div className="header-actions">
          <button
            onClick={handleRefresh}
            className="refresh-btn"
            disabled={loading}
            aria-label="Refresh history"
          >
            <RefreshCw className={`icon ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="history-filters">
        <div className="filter-group">
          <Filter className="icon" />
          <button
            className={`filter-btn ${filterSuccess === 'all' ? 'active' : ''}`}
            onClick={() => setFilterSuccess('all')}
          >
            All
          </button>
          <button
            className={`filter-btn ${filterSuccess === 'success' ? 'active' : ''}`}
            onClick={() => setFilterSuccess('success')}
          >
            Success
          </button>
          <button
            className={`filter-btn ${filterSuccess === 'failed' ? 'active' : ''}`}
            onClick={() => setFilterSuccess('failed')}
          >
            Failed
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {/* History List */}
      <div className="history-list">
        {filteredHistory.length === 0 ? (
          <div className="no-history">
            <History className="icon-large" />
            <p>No execution history found.</p>
          </div>
        ) : (
          filteredHistory.map((item) => (
            <div key={item.id} className="history-item">
              <div
                className="item-header"
                onClick={() => toggleExpand(item.id)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => e.key === 'Enter' && toggleExpand(item.id)}
              >
                <div className="item-info">
                  <div className="item-status">
                    {item.result.success ? (
                      <CheckCircle className="icon success" />
                    ) : (
                      <XCircle className="icon error" />
                    )}
                  </div>
                  <div className="item-details">
                    <h4 className="item-tool-name">{item.tool_name}</h4>
                    <p className="item-timestamp">{formatTimestamp(item.timestamp)}</p>
                  </div>
                </div>
                <div className="item-actions">
                  {item.result.execution_time && (
                    <span className="execution-time">
                      <Clock className="icon" />
                      {item.result.execution_time.toFixed(2)}s
                    </span>
                  )}
                  <button
                    className="expand-btn"
                    aria-label={expandedId === item.id ? 'Collapse' : 'Expand'}
                  >
                    {expandedId === item.id ? (
                      <ChevronUp className="icon" />
                    ) : (
                      <ChevronDown className="icon" />
                    )}
                  </button>
                </div>
              </div>

              {expandedId === item.id && (
                <div className="item-expanded">
                  {/* Parameters */}
                  <div className="expanded-section">
                    <h5 className="section-title">Parameters</h5>
                    <pre className="code-block">
                      {JSON.stringify(item.parameters, null, 2)}
                    </pre>
                  </div>

                  {/* Result */}
                  <div className="expanded-section">
                    <h5 className="section-title">
                      {item.result.success ? 'Result' : 'Error'}
                    </h5>
                    {item.result.error ? (
                      <div className="error-display">{item.result.error}</div>
                    ) : (
                      <pre className="code-block">
                        {JSON.stringify(item.result.result, null, 2)}
                      </pre>
                    )}
                  </div>

                  {/* Re-execute button */}
                  {onReExecute && (
                    <div className="expanded-actions">
                      <button
                        onClick={() => onReExecute(item.tool_name, item.parameters)}
                        className="reexecute-btn"
                      >
                        <RefreshCw className="icon" />
                        Re-execute
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Load More */}
      {filteredHistory.length >= limit && (
        <div className="history-footer">
          <button onClick={handleLoadMore} className="load-more-btn" disabled={loading}>
            {loading ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
};
