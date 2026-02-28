/**
 * ConversationFilters Component
 * 
 * Advanced filtering panel for conversations with date range, model selection,
 * tags, and other criteria.
 */

import React, { useState } from 'react';
import { Calendar, X, Tag, MessageSquare, Paperclip, Sparkles } from 'lucide-react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { SearchFilters } from './ConversationSearch';

interface ConversationFiltersProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
  onClose: () => void;
}

const AVAILABLE_MODELS = [
  { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
  { id: 'claude-3-opus', name: 'Claude 3 Opus', provider: 'Anthropic' },
  { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', provider: 'Anthropic' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google' },
  { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', provider: 'Google' },
  { id: 'sonar', name: 'Sonar', provider: 'Perplexity' },
  { id: 'ollama-llama2', name: 'Llama 2', provider: 'Ollama' },
];

const COMMON_TAGS = [
  'Work', 'Personal', 'Research', 'Code', 'Writing',
  'Ideas', 'Learning', 'Important', 'Draft', 'Archive'
];

export const ConversationFilters: React.FC<ConversationFiltersProps> = ({
  filters,
  onChange,
  onClose,
}) => {
  const [localFilters, setLocalFilters] = useState<SearchFilters>(filters);

  const handleApply = () => {
    onChange(localFilters);
    onClose();
  };

  const handleReset = () => {
    setLocalFilters({});
    onChange({});
  };

  const toggleModel = (modelId: string) => {
    setLocalFilters((prev) => {
      const models = prev.models || [];
      const updated = models.includes(modelId)
        ? models.filter((m) => m !== modelId)
        : [...models, modelId];
      return { ...prev, models: updated.length > 0 ? updated : undefined };
    });
  };

  const toggleTag = (tag: string) => {
    setLocalFilters((prev) => {
      const tags = prev.tags || [];
      const updated = tags.includes(tag)
        ? tags.filter((t) => t !== tag)
        : [...tags, tag];
      return { ...prev, tags: updated.length > 0 ? updated : undefined };
    });
  };

  return (
    <div className="mt-4 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Advanced Filters
        </h3>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-6">
        {/* Date Range Filter */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <Calendar className="w-4 h-4" />
            Date Range
          </label>
          <div className="flex gap-2">
            <DatePicker
              selected={localFilters.dateRange?.start}
              onChange={(date) => {
                if (date) {
                  setLocalFilters((prev) => ({
                    ...prev,
                    dateRange: {
                      start: date,
                      end: prev.dateRange?.end || new Date(),
                    },
                  }));
                }
              }}
              placeholderText="Start date"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              dateFormat="MMM d, yyyy"
            />
            <DatePicker
              selected={localFilters.dateRange?.end}
              onChange={(date) => {
                if (date) {
                  setLocalFilters((prev) => ({
                    ...prev,
                    dateRange: {
                      start: prev.dateRange?.start || new Date(0),
                      end: date,
                    },
                  }));
                }
              }}
              placeholderText="End date"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              dateFormat="MMM d, yyyy"
            />
          </div>
        </div>

        {/* Model Filter */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <Sparkles className="w-4 h-4" />
            Models
          </label>
          <div className="grid grid-cols-2 gap-2">
            {AVAILABLE_MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => toggleModel(model.id)}
                className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                  localFilters.models?.includes(model.id)
                    ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500 text-blue-700 dark:text-blue-300'
                    : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
                }`}
              >
                <div className="font-medium">{model.name}</div>
                <div className="text-xs opacity-70">{model.provider}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Tags Filter */}
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            <Tag className="w-4 h-4" />
            Tags
          </label>
          <div className="flex flex-wrap gap-2">
            {COMMON_TAGS.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                  localFilters.tags?.includes(tag)
                    ? 'bg-purple-50 dark:bg-purple-900/30 border-purple-500 text-purple-700 dark:text-purple-300'
                    : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Additional Filters */}
        <div className="space-y-3">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={localFilters.hasAttachments || false}
              onChange={(e) =>
                setLocalFilters((prev) => ({
                  ...prev,
                  hasAttachments: e.target.checked || undefined,
                }))
              }
              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            />
            <Paperclip className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Has attachments
            </span>
          </label>

          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-gray-500" />
            <label className="text-sm text-gray-700 dark:text-gray-300">
              Minimum messages:
            </label>
            <input
              type="number"
              min="1"
              value={localFilters.minMessages || ''}
              onChange={(e) =>
                setLocalFilters((prev) => ({
                  ...prev,
                  minMessages: e.target.value ? parseInt(e.target.value) : undefined,
                }))
              }
              placeholder="Any"
              className="w-20 px-2 py-1 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleReset}
          className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
        >
          Reset
        </button>
        <button
          onClick={handleApply}
          className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
        >
          Apply Filters
        </button>
      </div>
    </div>
  );
};

export default ConversationFilters;
