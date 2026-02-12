import React from 'react';
import { User, Bot } from 'lucide-react';
import { MessageContent } from './MessageContent';
import { format } from 'date-fns';
import { clsx } from 'clsx';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  timestamp,
  isStreaming = false,
}) => {
  const isUser = role === 'user';

  return (
    <div
      className={clsx(
        'group relative flex gap-4 px-4 py-6 transition-colors',
        isUser ? 'bg-transparent' : 'bg-gray-50 dark:bg-gray-800/50'
      )}
    >
      {/* Avatar */}
      <div
        className={clsx(
          'flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-purple-600 text-white'
        )}
      >
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {isUser ? 'You' : 'Zakera'}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {format(timestamp, 'h:mm a')}
          </span>
          {isStreaming && (
            <span className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
              <span className="inline-block w-1.5 h-1.5 bg-blue-600 dark:bg-blue-400 rounded-full animate-pulse" />
              Typing...
            </span>
          )}
        </div>

        {/* Message Content */}
        <div className="text-sm text-gray-800 dark:text-gray-200">
          <MessageContent content={content} role={role} />
        </div>
      </div>
    </div>
  );
};
