/**
 * Conversation Template Selector Component
 * 
 * A comprehensive widget for browsing, filtering, and selecting conversation templates
 */

import React, { useState, useMemo } from 'react';
import {
  ConversationTemplate,
  TemplateCategory,
  TemplateDifficulty,
  CATEGORY_LABELS,
  CATEGORY_ICONS,
  DIFFICULTY_COLORS,
} from '../../types/templates';
import { useTemplates } from '../../hooks/useTemplates';
import './TemplateSelector.css';

interface TemplateSelectorProps {
  onSelectTemplate: (template: ConversationTemplate) => void;
  onClose: () => void;
  isOpen: boolean;
  defaultCategory?: TemplateCategory;
}

export const TemplateSelector: React.FC<TemplateSelectorProps> = ({
  onSelectTemplate,
  onClose,
  isOpen,
  defaultCategory,
}) => {
  const {
    templates,
    loading,
    error,
    total,
    fetchTemplates,
    fetchPopular,
    logTemplateUsage,
  } = useTemplates();

  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>(
    defaultCategory || 'all'
  );
  const [selectedDifficulty, setSelectedDifficulty] = useState<TemplateDifficulty | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showPopular, setShowPopular] = useState(false);
  const [expandedTemplate, setExpandedTemplate] = useState<number | null>(null);

  // Filter templates
  const filteredTemplates = useMemo(() => {
    let filtered = templates;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter((t) => t.category === selectedCategory);
    }

    if (selectedDifficulty !== 'all') {
      filtered = filtered.filter((t) => t.difficulty === selectedDifficulty);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.title.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    return filtered;
  }, [templates, selectedCategory, selectedDifficulty, searchQuery]);

  // Handle category selection
  const handleCategoryChange = (category: TemplateCategory | 'all') => {
    setSelectedCategory(category);
    if (category === 'all') {
      fetchTemplates({ sort_by: 'usage_count', sort_order: 'desc' });
    } else {
      fetchTemplates({ category, sort_by: 'usage_count', sort_order: 'desc' });
    }
  };

  // Handle template selection
  const handleSelectTemplate = async (template: ConversationTemplate) => {
    await logTemplateUsage(template.id);
    onSelectTemplate(template);
    onClose();
  };

  // Toggle popular view
  const handleTogglePopular = () => {
    setShowPopular(!showPopular);
    if (!showPopular) {
      fetchPopular(12);
    } else {
      fetchTemplates();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="template-selector-overlay" onClick={onClose}>
      <div className="template-selector-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="template-selector-header">
          <div className="header-title">
            <h2>📚 Choose a Conversation Template</h2>
            <p>Start your conversation with expert-designed prompts and guidance</p>
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        {/* Controls */}
        <div className="template-selector-controls">
          {/* Search */}
          <div className="search-box">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            {searchQuery && (
              <button
                className="clear-search"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
              >
                ✕
              </button>
            )}
          </div>

          {/* View mode and popular toggle */}
          <div className="control-buttons">
            <button
              className={`control-button ${showPopular ? 'active' : ''}`}
              onClick={handleTogglePopular}
              title="Show popular templates"
            >
              ⭐ Popular
            </button>
            <button
              className={`control-button ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
              title="Grid view"
            >
              ⊞
            </button>
            <button
              className={`control-button ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
              title="List view"
            >
              ☰
            </button>
          </div>
        </div>

        {/* Category filters */}
        <div className="category-filters">
          <button
            className={`category-chip ${selectedCategory === 'all' ? 'active' : ''}`}
            onClick={() => handleCategoryChange('all')}
          >
            All Templates
          </button>
          {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
            <button
              key={key}
              className={`category-chip ${selectedCategory === key ? 'active' : ''}`}
              onClick={() => handleCategoryChange(key as TemplateCategory)}
            >
              {CATEGORY_ICONS[key as TemplateCategory]} {label}
            </button>
          ))}
        </div>

        {/* Difficulty filters */}
        <div className="difficulty-filters">
          <span className="filter-label">Difficulty:</span>
          <button
            className={`difficulty-chip ${selectedDifficulty === 'all' ? 'active' : ''}`}
            onClick={() => setSelectedDifficulty('all')}
          >
            All Levels
          </button>
          {(['beginner', 'intermediate', 'advanced', 'expert'] as TemplateDifficulty[]).map(
            (level) => (
              <button
                key={level}
                className={`difficulty-chip ${selectedDifficulty === level ? 'active' : ''}`}
                style={{
                  borderColor: DIFFICULTY_COLORS[level],
                  color: selectedDifficulty === level ? '#fff' : DIFFICULTY_COLORS[level],
                  backgroundColor:
                    selectedDifficulty === level ? DIFFICULTY_COLORS[level] : 'transparent',
                }}
                onClick={() => setSelectedDifficulty(level)}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            )
          )}
        </div>

        {/* Results count */}
        <div className="results-info">
          <span>
            Showing {filteredTemplates.length} of {total} templates
          </span>
        </div>

        {/* Template grid/list */}
        <div className={`template-${viewMode}`}>
          {loading && (
            <div className="loading-state">
              <div className="spinner" />
              <p>Loading templates...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p>❌ {error}</p>
              <button onClick={() => fetchTemplates()}>Retry</button>
            </div>
          )}

          {!loading && !error && filteredTemplates.length === 0 && (
            <div className="empty-state">
              <p>😔 No templates found</p>
              <p>Try adjusting your filters or search query</p>
            </div>
          )}

          {!loading &&
            !error &&
            filteredTemplates.map((template) => (
              <div
                key={template.id}
                className={`template-card ${expandedTemplate === template.id ? 'expanded' : ''}`}
              >
                <div className="template-card-header">
                  <div className="template-icon">
                    {CATEGORY_ICONS[template.category]}
                  </div>
                  <div className="template-title-area">
                    <h3>{template.title}</h3>
                    <div className="template-meta">
                      <span
                        className="difficulty-badge"
                        style={{ backgroundColor: DIFFICULTY_COLORS[template.difficulty] }}
                      >
                        {template.difficulty}
                      </span>
                      <span className="usage-count">👥 {template.usage_count} uses</span>
                    </div>
                  </div>
                </div>

                <p className="template-description">{template.description}</p>

                {expandedTemplate === template.id && (
                  <div className="template-details">
                    {template.suggested_questions.length > 0 && (
                      <div className="suggested-questions">
                        <h4>💡 Suggested Questions:</h4>
                        <ul>
                          {template.suggested_questions.slice(0, 3).map((q, idx) => (
                            <li key={idx}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {template.tags.length > 0 && (
                      <div className="template-tags">
                        {template.tags.map((tag) => (
                          <span key={tag} className="tag">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}

                    {template.model_recommendations.length > 0 && (
                      <div className="model-recommendations">
                        <strong>🤖 Recommended models:</strong>
                        <span>{template.model_recommendations.join(', ')}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="template-card-actions">
                  <button
                    className="action-button secondary"
                    onClick={() =>
                      setExpandedTemplate(expandedTemplate === template.id ? null : template.id)
                    }
                  >
                    {expandedTemplate === template.id ? 'Show Less' : 'View Details'}
                  </button>
                  <button
                    className="action-button primary"
                    onClick={() => handleSelectTemplate(template)}
                  >
                    Use Template
                  </button>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default TemplateSelector;
