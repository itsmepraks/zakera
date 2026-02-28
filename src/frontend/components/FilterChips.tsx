/**
 * FilterChips Component
 * 
 * Displays active filters as removable chips for easy visualization and management.
 */

import React from 'react';
import { X, Calendar, Sparkles, Tag, Paperclip, MessageSquare } from 'lucide-react';
import { SearchFilters } from './ConversationSearch';

interface FilterChipsProps {
  filters: SearchFilters;
  onRemove: (filterKey: keyof SearchFilters) => void;
}

export const FilterChips: React.FC<FilterChipsProps> = ({ filters, onRemove }) => {
  const formatDateRange = (dateRange: { start: Date; end: Date }) => {
    const format = (date: Date) => date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return `${format(dateRange.start)} - ${format(dateRange.end)}`;
  };

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {/* Date Range Chip */}
      {filters.dateRange && (
        <div className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-sm rounded-full border border-blue-200 dark:border-blue-700">
          <Calendar className="w-3 h-3" />
          <span>{formatDateRange(filters.dateRange)}</span>
          <button
            onClick={() => onRemove('dateRange')}
            className="ml-1 hover:bg-blue-100 dark:hover:bg-blue-800 rounded-full p-0.5 transition-colors"
            aria-label="Remove date filter"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Model Chips */}
      {filters.models?.map((model) => (
        <div
          key={model}
          className="inline-flex items-center gap-1 px-3 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-sm rounded-full border border-purple-200 dark:border-purple-700"
        >
          <Sparkles className="w-3 h-3" />
          <span>{model}</span>
          <button
            onClick={() => {
              // Remove specific model from models array
              const updatedModels = filters.models!.filter((m) => m !== model);
              if (updatedModels.length === 0) {
                onRemove('models');
              }
            }}
            className="ml-1 hover:bg-purple-100 dark:hover:bg-purple-800 rounded-full p-0.5 transition-colors"
            aria-label={`Remove ${model} filter`}
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}

      {/* Tag Chips */}
      {filters.tags?.map((tag) => (
        <div
          key={tag}
          className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-sm rounded-full border border-green-200 dark:border-green-700"
        >
          <Tag className="w-3 h-3" />
          <span>{tag}</span>
          <button
            onClick={() => {
              // Remove specific tag from tags array
              const updatedTags = filters.tags!.filter((t) => t !== tag);
              if (updatedTags.length === 0) {
                onRemove('tags');
              }
            }}
            className="ml-1 hover:bg-green-100 dark:hover:bg-green-800 rounded-full p-0.5 transition-colors"
            aria-label={`Remove ${tag} tag`}
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}

      {/* Has Attachments Chip */}
      {filters.hasAttachments && (
        <div className="inline-flex items-center gap-1 px-3 py-1 bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 text-sm rounded-full border border-orange-200 dark:border-orange-700">
          <Paperclip className="w-3 h-3" />
          <span>Has attachments</span>
          <button
            onClick={() => onRemove('hasAttachments')}
            className="ml-1 hover:bg-orange-100 dark:hover:bg-orange-800 rounded-full p-0.5 transition-colors"
            aria-label="Remove attachments filter"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Min Messages Chip */}
      {filters.minMessages && (
        <div className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-full border border-gray-300 dark:border-gray-600">
          <MessageSquare className="w-3 h-3" />
          <span>≥ {filters.minMessages} messages</span>
          <button
            onClick={() => onRemove('minMessages')}
            className="ml-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-full p-0.5 transition-colors"
            aria-label="Remove minimum messages filter"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
};

export default FilterChips;
