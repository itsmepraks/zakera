import React, { useState, useEffect } from 'react';
import { MessageSquare, Search, Trash2, Clock, Cpu } from 'lucide-react';

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

interface ConversationHistoryProps {
  conversations: Conversation[];
  currentConversationId?: string;
  onSelectConversation: (conversation: Conversation) => void;
  onDeleteConversation: (conversationId: string) => void;
  onNewConversation: () => void;
}

const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredConversations, setFilteredConversations] = useState<Conversation[]>(conversations);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredConversations(conversations);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = conversations.filter((conv) => {
      // Search in title
      if (conv.title.toLowerCase().includes(query)) return true;
      
      // Search in messages
      return conv.messages.some((msg) =>
        msg.content.toLowerCase().includes(query)
      );
    });

    setFilteredConversations(filtered);
  }, [searchQuery, conversations]);

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const handleDelete = (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      onDeleteConversation(conversationId);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={onNewConversation}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 font-medium"
        >
          <MessageSquare size={18} />
          New Conversation
        </button>
      </div>

      {/* Search */}
      <div className="p-4">
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
            size={18}
          />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2">
        {filteredConversations.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            {searchQuery ? 'No conversations found' : 'No conversations yet'}
          </div>
        ) : (
          filteredConversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelectConversation(conv)}
              className={`
                group relative p-3 mb-2 rounded-lg cursor-pointer transition-colors
                ${currentConversationId === conv.id
                  ? 'bg-blue-100 dark:bg-blue-900 border-l-4 border-blue-600'
                  : 'bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700'
                }
              `}
            >
              {/* Title */}
              <div className="font-medium text-gray-900 dark:text-gray-100 mb-1 pr-8 truncate">
                {conv.title}
              </div>

              {/* Metadata */}
              <div className="flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                <div className="flex items-center gap-1">
                  <Clock size={12} />
                  {formatDate(conv.updated_at)}
                </div>
                <div className="flex items-center gap-1">
                  <Cpu size={12} />
                  {conv.model}
                </div>
                {conv.total_tokens && (
                  <div>{conv.total_tokens} tokens</div>
                )}
              </div>

              {/* Preview */}
              {conv.messages.length > 0 && (
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                  {conv.messages[conv.messages.length - 1].content}
                </div>
              )}

              {/* Delete button */}
              <button
                onClick={(e) => handleDelete(e, conv.id)}
                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-100 dark:hover:bg-red-900 text-red-600 dark:text-red-400"
                title="Delete conversation"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Stats Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
        <div className="flex justify-between">
          <span>{filteredConversations.length} conversations</span>
          <span>
            {conversations.reduce((sum, conv) => sum + conv.messages.length, 0)} messages
          </span>
        </div>
      </div>
    </div>
  );
};

export default ConversationHistory;
