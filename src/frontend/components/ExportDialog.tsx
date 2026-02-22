/**
 * Export Dialog Component
 * 
 * Modal for exporting conversations with format selection and progress tracking.
 */

import React, { useState } from 'react';
import { ProgressBar } from './LoadingStates';
import { useToast } from '../hooks/useToast';

interface ExportDialogProps {
  conversationId: string;
  isOpen: boolean;
  onClose: () => void;
}

type ExportFormat = 'json' | 'markdown' | 'txt' | 'csv';

export const ExportDialog: React.FC<ExportDialogProps> = ({
  conversationId,
  isOpen,
  onClose,
}) => {
  const [format, setFormat] = useState<ExportFormat>('markdown');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const { showToast } = useToast();

  const handleExport = async () => {
    setIsExporting(true);
    setProgress(0);

    try {
      const response = await fetch(
        `/api/v1/conversations/${conversationId}/export?format=${format}`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      if (!response.ok) throw new Error('Export failed');

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      let receivedLength = 0;
      const chunks: Uint8Array[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        chunks.push(value);
        receivedLength += value.length;

        // Update progress (estimate based on received data)
        const estimatedProgress = Math.min((receivedLength / 1024) * 10, 90);
        setProgress(estimatedProgress);
      }

      // Combine chunks
      const blob = new Blob(chunks, { type: 'text/plain' });
      const url = URL.createObjectURL(blob);

      // Download file
      const link = document.createElement('a');
      link.href = url;
      link.download = `conversation-${conversationId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setProgress(100);
      showToast({
        type: 'success',
        message: 'Conversation exported successfully',
      });

      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (error) {
      console.error('Export error:', error);
      showToast({
        type: 'error',
        message: 'Failed to export conversation',
      });
    } finally {
      setIsExporting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog-content" onClick={(e) => e.stopPropagation()}>
        <div className="dialog-header">
          <h2>Export Conversation</h2>
          <button className="dialog-close" onClick={onClose} aria-label="Close">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M6 6l12 12M6 18L18 6" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
        </div>

        <div className="dialog-body">
          <div className="form-group">
            <label htmlFor="format">Export Format</label>
            <select
              id="format"
              value={format}
              onChange={(e) => setFormat(e.target.value as ExportFormat)}
              disabled={isExporting}
            >
              <option value="markdown">Markdown (.md)</option>
              <option value="json">JSON (.json)</option>
              <option value="txt">Plain Text (.txt)</option>
              <option value="csv">CSV (.csv)</option>
            </select>
          </div>

          <div className="form-group">
            <label>
              <input
                type="checkbox"
                checked={includeMetadata}
                onChange={(e) => setIncludeMetadata(e.target.checked)}
                disabled={isExporting}
              />
              Include metadata (timestamps, model info, etc.)
            </label>
          </div>

          {isExporting && (
            <div className="export-progress">
              <ProgressBar progress={progress} label="Exporting conversation..." />
            </div>
          )}
        </div>

        <div className="dialog-footer">
          <button className="btn-secondary" onClick={onClose} disabled={isExporting}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleExport} disabled={isExporting}>
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExportDialog;
