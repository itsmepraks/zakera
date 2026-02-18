import React, { useState } from 'react';
import { Download, Upload, FileText, FileJson, File } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  model?: string;
  tokens?: number;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
  model: string;
  total_tokens?: number;
  metadata?: Record<string, any>;
}

interface ConversationExporterProps {
  conversation: Conversation;
  onImport: (conversation: Conversation) => void;
}

export type ExportFormat = 'json' | 'markdown' | 'text';

const ConversationExporter: React.FC<ConversationExporterProps> = ({
  conversation,
  onImport,
}) => {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const exportToJSON = (conv: Conversation): string => {
    return JSON.stringify(conv, null, 2);
  };

  const exportToMarkdown = (conv: Conversation): string => {
    let markdown = `# ${conv.title}\n\n`;
    markdown += `**Created:** ${new Date(conv.created_at).toLocaleString()}\n`;
    markdown += `**Model:** ${conv.model}\n`;
    if (conv.total_tokens) {
      markdown += `**Total Tokens:** ${conv.total_tokens}\n`;
    }
    markdown += `\n---\n\n`;

    conv.messages.forEach((msg, idx) => {
      const role = msg.role === 'user' ? '👤 User' : '🤖 Assistant';
      markdown += `## ${role}\n\n`;
      markdown += `*${new Date(msg.timestamp).toLocaleString()}*\n\n`;
      markdown += `${msg.content}\n\n`;
      if (msg.tokens) {
        markdown += `*Tokens: ${msg.tokens}*\n\n`;
      }
      markdown += `---\n\n`;
    });

    return markdown;
  };

  const exportToText = (conv: Conversation): string => {
    let text = `${conv.title}\n`;
    text += `${'='.repeat(conv.title.length)}\n\n`;
    text += `Created: ${new Date(conv.created_at).toLocaleString()}\n`;
    text += `Model: ${conv.model}\n`;
    if (conv.total_tokens) {
      text += `Total Tokens: ${conv.total_tokens}\n`;
    }
    text += `\n`;

    conv.messages.forEach((msg, idx) => {
      const role = msg.role === 'user' ? 'USER' : 'ASSISTANT';
      text += `[${role}] ${new Date(msg.timestamp).toLocaleString()}\n`;
      text += `${msg.content}\n`;
      if (msg.tokens) {
        text += `(${msg.tokens} tokens)\n`;
      }
      text += `\n${'─'.repeat(60)}\n\n`;
    });

    return text;
  };

  const handleExport = (format: ExportFormat) => {
    let content: string;
    let filename: string;
    let mimeType: string;

    switch (format) {
      case 'json':
        content = exportToJSON(conversation);
        filename = `conversation_${conversation.id}.json`;
        mimeType = 'application/json';
        break;
      case 'markdown':
        content = exportToMarkdown(conversation);
        filename = `conversation_${conversation.id}.md`;
        mimeType = 'text/markdown';
        break;
      case 'text':
        content = exportToText(conversation);
        filename = `conversation_${conversation.id}.txt`;
        mimeType = 'text/plain';
        break;
      default:
        return;
    }

    // Create download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setShowExportMenu(false);
  };

  const validateImportedConversation = (data: any): Conversation | null => {
    // Basic validation
    if (!data.id || !data.title || !Array.isArray(data.messages)) {
      return null;
    }

    // Validate messages structure
    for (const msg of data.messages) {
      if (!msg.id || !msg.role || !msg.content || !msg.timestamp) {
        return null;
      }
      if (msg.role !== 'user' && msg.role !== 'assistant') {
        return null;
      }
    }

    return data as Conversation;
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportError(null);

    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      const validatedConversation = validateImportedConversation(data);
      
      if (!validatedConversation) {
        setImportError('Invalid conversation format. Please check the file structure.');
        return;
      }

      onImport(validatedConversation);
      alert(`Successfully imported conversation: ${validatedConversation.title}`);
    } catch (error) {
      setImportError(
        error instanceof Error
          ? `Import failed: ${error.message}`
          : 'Unknown error during import'
      );
    }

    // Reset input
    event.target.value = '';
  };

  return (
    <div className="flex items-center gap-2 relative">
      {/* Export Button */}
      <div className="relative">
        <button
          onClick={() => setShowExportMenu(!showExportMenu)}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          title="Export conversation"
        >
          <Download size={18} />
          <span className="text-sm font-medium">Export</span>
        </button>

        {/* Export Menu */}
        {showExportMenu && (
          <div className="absolute top-full mt-2 right-0 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 min-w-[180px]">
            <button
              onClick={() => handleExport('json')}
              className="flex items-center gap-2 w-full px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-left transition-colors"
            >
              <FileJson size={16} />
              <span className="text-sm">JSON Format</span>
            </button>
            <button
              onClick={() => handleExport('markdown')}
              className="flex items-center gap-2 w-full px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-left transition-colors"
            >
              <FileText size={16} />
              <span className="text-sm">Markdown</span>
            </button>
            <button
              onClick={() => handleExport('text')}
              className="flex items-center gap-2 w-full px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 text-left transition-colors rounded-b-lg"
            >
              <File size={16} />
              <span className="text-sm">Plain Text</span>
            </button>
          </div>
        )}
      </div>

      {/* Import Button */}
      <label
        className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors cursor-pointer"
        title="Import conversation"
      >
        <Upload size={18} />
        <span className="text-sm font-medium">Import</span>
        <input
          type="file"
          accept=".json"
          onChange={handleImport}
          className="hidden"
        />
      </label>

      {/* Import Error */}
      {importError && (
        <div className="absolute top-full mt-2 right-0 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 text-red-800 dark:text-red-200 px-4 py-2 rounded-lg text-sm max-w-md z-10">
          {importError}
          <button
            onClick={() => setImportError(null)}
            className="ml-2 font-bold"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
};

export default ConversationExporter;
