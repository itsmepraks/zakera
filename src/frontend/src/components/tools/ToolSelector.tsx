/**
 * ToolSelector Component
 * Allows users to browse and filter available tools
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Search, Filter, Tag, Wrench, ChevronDown, ChevronUp } from 'lucide-react';
import { Tool, ToolCategory, ToolFilters } from '@/types/tools.types';
import { toolService } from '@/services/toolService';
import './ToolSelector.css';

interface ToolSelectorProps {
  onToolSelect: (tool: Tool) => void;
  selectedTool?: Tool | null;
  compact?: boolean;
}

const CATEGORIES: Array<{ value: ToolCategory; label: string }> = [
  { value: 'all', label: 'All Tools' },
  { value: 'builtin', label: 'Built-in' },
  { value: 'custom', label: 'Custom' },
  { value: 'api', label: 'API' },
  { value: 'utility', label: 'Utility' },
];

export const ToolSelector: React.FC<ToolSelectorProps> = ({
  onToolSelect,
  selectedTool,
  compact = false,
}) => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ToolFilters>({
    category: 'all',
    search: '',
    tags: [],
  });
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(!compact);

  useEffect(() => {
    loadTools();
  }, [filters]);

  const loadTools = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await toolService.getTools(filters);
      setTools(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tools');
    } finally {
      setLoading(false);
    }
  };

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    tools.forEach((tool) => {
      tool.tags?.forEach((tag) => tags.add(tag));
    });
    return Array.from(tags).sort();
  }, [tools]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({ ...prev, search: e.target.value }));
  };

  const handleCategoryChange = (category: ToolCategory) => {
    setFilters((prev) => ({ ...prev, category }));
  };

  const toggleTag = (tag: string) => {
    setFilters((prev) => ({
      ...prev,
      tags: prev.tags?.includes(tag)
        ? prev.tags.filter((t) => t !== tag)
        : [...(prev.tags || []), tag],
    }));
  };

  const toggleToolExpand = (toolName: string) => {
    setExpandedTool(expandedTool === toolName ? null : toolName);
  };

  if (loading && tools.length === 0) {
    return (
      <div className="tool-selector loading">
        <div className="loading-spinner" />
        <p>Loading tools...</p>
      </div>
    );
  }

  return (
    <div className={`tool-selector ${compact ? 'compact' : ''}`}>
      <div className="tool-selector-header">
        <h3 className="tool-selector-title">
          <Wrench className="icon" />
          Available Tools
        </h3>
        {compact && (
          <button
            className="filter-toggle"
            onClick={() => setShowFilters(!showFilters)}
            aria-label="Toggle filters"
          >
            <Filter className="icon" />
          </button>
        )}
      </div>

      {showFilters && (
        <div className="tool-filters">
          {/* Search */}
          <div className="filter-search">
            <Search className="search-icon" />
            <input
              type="text"
              placeholder="Search tools..."
              value={filters.search || ''}
              onChange={handleSearchChange}
              className="search-input"
              aria-label="Search tools"
            />
          </div>

          {/* Category Filter */}
          <div className="filter-categories">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                className={`category-btn ${filters.category === cat.value ? 'active' : ''}`}
                onClick={() => handleCategoryChange(cat.value)}
                aria-pressed={filters.category === cat.value}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Tags Filter */}
          {allTags.length > 0 && (
            <div className="filter-tags">
              <label className="tags-label">
                <Tag className="icon" />
                Filter by tags:
              </label>
              <div className="tags-list">
                {allTags.map((tag) => (
                  <button
                    key={tag}
                    className={`tag-btn ${filters.tags?.includes(tag) ? 'active' : ''}`}
                    onClick={() => toggleTag(tag)}
                    aria-pressed={filters.tags?.includes(tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {/* Tools List */}
      <div className="tools-list">
        {tools.length === 0 ? (
          <div className="no-tools">
            <p>No tools found matching your filters.</p>
          </div>
        ) : (
          tools.map((tool) => (
            <div
              key={tool.name}
              className={`tool-card ${selectedTool?.name === tool.name ? 'selected' : ''}`}
            >
              <div
                className="tool-card-header"
                onClick={() => onToolSelect(tool)}
                role="button"
                tabIndex={0}
                onKeyPress={(e) => e.key === 'Enter' && onToolSelect(tool)}
              >
                <div className="tool-info">
                  <h4 className="tool-name">{tool.name}</h4>
                  <p className="tool-description">{tool.description}</p>
                  {tool.tags && tool.tags.length > 0 && (
                    <div className="tool-tags">
                      {tool.tags.map((tag) => (
                        <span key={tag} className="tool-tag">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  className="expand-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleToolExpand(tool.name);
                  }}
                  aria-label={expandedTool === tool.name ? 'Collapse' : 'Expand'}
                >
                  {expandedTool === tool.name ? (
                    <ChevronUp className="icon" />
                  ) : (
                    <ChevronDown className="icon" />
                  )}
                </button>
              </div>

              {expandedTool === tool.name && (
                <div className="tool-card-details">
                  <div className="tool-metadata">
                    {tool.category && (
                      <span className="metadata-item">
                        <strong>Category:</strong> {tool.category}
                      </span>
                    )}
                    {tool.version && (
                      <span className="metadata-item">
                        <strong>Version:</strong> {tool.version}
                      </span>
                    )}
                  </div>
                  <div className="tool-parameters">
                    <strong>Parameters:</strong>
                    {tool.parameters.length === 0 ? (
                      <p className="no-params">No parameters required</p>
                    ) : (
                      <ul className="params-list">
                        {tool.parameters.map((param) => (
                          <li key={param.name} className="param-item">
                            <code>{param.name}</code>
                            <span className="param-type">({param.type})</span>
                            {param.required && <span className="required">*</span>}
                            <p className="param-description">{param.description}</p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
