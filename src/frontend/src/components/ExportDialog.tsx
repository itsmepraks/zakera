/**
 * Export Dialog Component
 * Provides UI for exporting conversations in various formats
 */

import React, { useState, useEffect } from 'react';
import {
  ArrowDownTrayIcon,
  XMarkIcon,
  DocumentTextIcon,
  CodeBracketIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline';

export type ExportFormat = 'json' | 'markdown' | 'text' | 'csv';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  conversation: Conversation;
  onExport: (format: ExportFormat) => Promise<void>;
  className?: string;
}

const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  conversation,
  onExport,
  className = '',
}) => {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json');
  const [preview, setPreview] = useState<string>('');
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);

  const formats = [
    {
      id: 'json' as ExportFormat,
      name: 'JSON',
      icon: CodeBracketIcon,
      description: 'Machine-readable format with full data',
      extension: '.json',
    },
    {
      id: 'markdown' as ExportFormat,
      name: 'Markdown',
      icon: DocumentTextIcon,
      description: 'Human-readable format with formatting',
      extension: '.md',
    },
    {
      id: 'text' as ExportFormat,
      name: 'Plain Text',
      icon: DocumentTextIcon,
      description: 'Simple text format',
      extension: '.txt',
    },
    {
      id: 'csv' as ExportFormat,
      name: 'CSV',
      icon: TableCellsIcon,
      description: 'Spreadsheet-compatible format',
      extension: '.csv',
    },
  ];

  // Generate preview based on selected format
  useEffect(() => {
    if (!conversation) return;

    const generatePreview = () => {
      switch (selectedFormat) {
        case 'json':
          return JSON.stringify(
            {
              title: conversation.title,
              messages: conversation.messages.slice(0, 3),
              // ... truncated for preview
            },
            null,
            2
          );

        case 'markdown':
          const mdLines = [
            `# ${conversation.title}`,
            '',
            `**Created:** ${new Date(conversation.createdAt).toLocaleString()}`,
            `**Messages:** ${conversation.messages.length}`,
            '',
            '---',
            '',
          ];

          conversation.messages.slice(0, 3).forEach((msg) => {
            mdLines.push(`### ${msg.role === 'user' ? 'User' : 'Assistant'}`);
            mdLines.push('');
            mdLines.push(msg.content);
            mdLines.push('');
          });

          if (conversation.messages.length > 3) {
            mdLines.push('... (truncated for preview)');
          }

          return mdLines.join('\n');

        case 'text':
          const txtLines = [
            conversation.title,
            '='.repeat(conversation.title.length),
            '',
          ];

          conversation.messages.slice(0, 3).forEach((msg) => {
            txtLines.push(`[${msg.role.toUpperCase()}]`);
            txtLines.push(msg.content);
            txtLines.push('');
          });

          if (conversation.messages.length > 3) {
            txtLines.push('... (truncated for preview)');
          }

          return txtLines.join('\n');

        case 'csv':
          const csvLines = ['Timestamp,Role,Content'];

          conversation.messages.slice(0, 3).forEach((msg) => {
            const content = msg.content.replace(/"/g, '""'); // Escape quotes
            csvLines.push(`"${msg.timestamp}","${msg.role}","${content}"`);
          });

          if (conversation.messages.length > 3) {
            csvLines.push('... (truncated for preview)');
          }

          return csvLines.join('\n');

        default:
          return '';
      }
    };

    setPreview(generatePreview());
  }, [conversation, selectedFormat]);

  const handleExport = async () => {
    setIsExporting(true);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 100);

      await onExport(selectedFormat);

      clearInterval(progressInterval);
      setProgress(100);

      // Close dialog after successful export
      setTimeout(() => {
        onClose();
        setIsExporting(false);
        setProgress(0);
      }, 500);
    } catch (error) {
      console.error('Export failed:', error);
      setIsExporting(false);
      setProgress(0);
    }
  };

  const handleDownload = () => {
    const format = formats.find((f) => f.id === selectedFormat);
    if (!format) return;

    const blob = new Blob([preview], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${conversation.title}${format.extension}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="export-dialog-title" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" 
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className={`
          relative w-full max-w-4xl
          bg-white dark:bg-gray-900
          rounded-xl shadow-2xl
          transform transition-all
          ${className}
        `}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 id="export-dialog-title" className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Export Conversation
            </h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              aria-label="Close dialog"
            >
              <XMarkIcon className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {/* Format Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Select Export Format
              </label>
              <div className="grid grid-cols-2 gap-3">
                {formats.map((format) => {
                  const Icon = format.icon;
                  return (
                    <button
                      key={format.id}
                      onClick={() => setSelectedFormat(format.id)}
                      className={`
                        flex items-start p-4 rounded-lg border-2 transition-all
                        ${selectedFormat === format.id
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }
                      `}
                    >
                      <Icon className={`w-6 h-6 mr-3 flex-shrink-0 ${selectedFormat === format.id ? 'text-primary-500' : 'text-gray-400'}`} />
                      <div className="text-left">
                        <div className="font-medium text-gray-900 dark:text-gray-100">
                          {format.name}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          {format.description}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Preview */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Preview
                </label>
                <button
                  onClick={handleDownload}
                  className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
                >
                  Download Preview
                </button>
              </div>
              <div className="
                bg-gray-50 dark:bg-gray-800
                border border-gray-200 dark:border-gray-700
                rounded-lg p-4
                max-h-96 overflow-y-auto
                font-mono text-sm
              ">
                <pre className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap break-words">
                  {preview}
                </pre>
              </div>
            </div>

            {/* Progress Bar */}
            {isExporting && (
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Exporting...
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {progress}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onClose}
              disabled={isExporting}
              className="
                px-4 py-2 rounded-lg
                text-gray-700 dark:text-gray-300
                hover:bg-gray-100 dark:hover:bg-gray-800
                transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="
                flex items-center gap-2 px-4 py-2 rounded-lg
                bg-primary-600 hover:bg-primary-700
                text-white font-medium
                transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {isExporting ? (
                <>
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Exporting...
                </>
              ) : (
                <>
                  <ArrowDownTrayIcon className="w-5 h-5" />
                  Export
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExportDialog;
