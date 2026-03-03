/**
 * ConversationExport Component
 * 
 * Provides conversation export functionality with multiple format options.
 * Supports JSON, Markdown, TXT, and CSV exports with progress tracking.
 */

import React, { useState } from 'react';
import './ConversationExport.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  tokens?: number;
}

interface ConversationExportProps {
  conversationId: string;
  messages: Message[];
  title?: string;
  onClose: () => void;
}

type ExportFormat = 'json' | 'markdown' | 'txt' | 'csv';

const ConversationExport: React.FC<ConversationExportProps> = ({
  conversationId,
  messages,
  title = 'Conversation',
  onClose
}) => {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json');
  const [exporting, setExporting] = useState(false);
  const [progress, setProgress] = useState(0);

  const formatJSON = (): string => {
    return JSON.stringify({
      id: conversationId,
      title,
      exportedAt: new Date().toISOString(),
      messageCount: messages.length,
      messages: messages.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp,
        model: msg.model,
        tokens: msg.tokens
      }))
    }, null, 2);
  };

  const formatMarkdown = (): string => {
    let md = `# ${title}\n\n`;
    md += `**Exported:** ${new Date().toLocaleString()}\n`;
    md += `**Messages:** ${messages.length}\n\n---\n\n`;

    messages.forEach((msg, index) => {
      const timestamp = new Date(msg.timestamp).toLocaleString();
      const roleIcon = msg.role === 'user' ? '👤' : '🤖';
      md += `### ${roleIcon} ${msg.role.toUpperCase()} - ${timestamp}\n\n`;
      md += `${msg.content}\n\n`;
      if (msg.model) {
        md += `*Model: ${msg.model}*`;
        if (msg.tokens) md += ` | *Tokens: ${msg.tokens}*`;
        md += `\n\n`;
      }
      md += `---\n\n`;
    });

    return md;
  };

  const formatText = (): string => {
    let txt = `${title}\n`;
    txt += `${'='.repeat(title.length)}\n\n`;
    txt += `Exported: ${new Date().toLocaleString()}\n`;
    txt += `Messages: ${messages.length}\n\n`;
    txt += `${'='.repeat(60)}\n\n`;

    messages.forEach((msg, index) => {
      const timestamp = new Date(msg.timestamp).toLocaleString();
      txt += `[${msg.role.toUpperCase()}] - ${timestamp}\n`;
      txt += `${msg.content}\n`;
      if (msg.model) {
        txt += `(Model: ${msg.model}`;
        if (msg.tokens) txt += `, Tokens: ${msg.tokens}`;
        txt += `)\n`;
      }
      txt += `\n${'-'.repeat(60)}\n\n`;
    });

    return txt;
  };

  const formatCSV = (): string => {
    let csv = 'ID,Role,Content,Timestamp,Model,Tokens\n';
    messages.forEach(msg => {
      const content = msg.content.replace(/"/g, '""'); // Escape quotes
      const timestamp = new Date(msg.timestamp).toISOString();
      csv += `"${msg.id}","${msg.role}","${content}","${timestamp}","${msg.model || ''}","${msg.tokens || ''}"\n`;
    });
    return csv;
  };

  const getExportContent = (): string => {
    switch (selectedFormat) {
      case 'json': return formatJSON();
      case 'markdown': return formatMarkdown();
      case 'txt': return formatText();
      case 'csv': return formatCSV();
      default: return formatJSON();
    }
  };

  const getFileName = (): string => {
    const date = new Date().toISOString().split('T')[0];
    const sanitizedTitle = title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    return `${sanitizedTitle}_${date}.${selectedFormat}`;
  };

  const handleExport = async () => {
    setExporting(true);
    setProgress(0);

    try {
      // Simulate progress for large exports
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 100);

      const content = getExportContent();
      const blob = new Blob([content], { 
        type: getMimeType(selectedFormat) 
      });

      clearInterval(progressInterval);
      setProgress(100);

      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = getFileName();
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setTimeout(() => {
        onClose();
      }, 500);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    } finally {
      setExporting(false);
      setProgress(0);
    }
  };

  const getMimeType = (format: ExportFormat): string => {
    const mimeTypes: Record<ExportFormat, string> = {
      json: 'application/json',
      markdown: 'text/markdown',
      txt: 'text/plain',
      csv: 'text/csv'
    };
    return mimeTypes[format];
  };

  return (
    <div className="export-dialog-overlay" onClick={onClose}>
      <div className="export-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="export-header">
          <h2>Export Conversation</h2>
          <button 
            className="close-button" 
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="export-content">
          <div className="export-info">
            <p><strong>Title:</strong> {title}</p>
            <p><strong>Messages:</strong> {messages.length}</p>
          </div>

          <div className="format-selection">
            <label>Select Format:</label>
            <div className="format-options">
              {['json', 'markdown', 'txt', 'csv'].map((format) => (
                <button
                  key={format}
                  className={`format-button ${selectedFormat === format ? 'selected' : ''}`}
                  onClick={() => setSelectedFormat(format as ExportFormat)}
                  disabled={exporting}
                >
                  <span className="format-icon">{getFormatIcon(format)}</span>
                  <span className="format-name">{format.toUpperCase()}</span>
                </button>
              ))}
            </div>
          </div>

          {exporting && (
            <div className="export-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p>Exporting... {progress}%</p>
            </div>
          )}
        </div>

        <div className="export-footer">
          <button 
            className="cancel-button" 
            onClick={onClose}
            disabled={exporting}
          >
            Cancel
          </button>
          <button 
            className="export-button" 
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>
    </div>
  );
};

const getFormatIcon = (format: string): string => {
  const icons: Record<string, string> = {
    json: '{ }',
    markdown: '#',
    txt: 'T',
    csv: '📊'
  };
  return icons[format] || '📄';
};

export default ConversationExport;
