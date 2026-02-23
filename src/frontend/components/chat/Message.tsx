import React, { useState, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { MessageReactions } from './MessageReactions';
import { MessageActions } from './MessageActions';
import { useChatStore } from '../../store/chatStore';
import { format } from 'date-fns';

interface MessageProps {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  reactions?: Array<{
    emoji: string;
    count: number;
    userReacted: boolean;
  }>;
  isStreaming?: boolean;
  metadata?: {
    model?: string;
    tokensUsed?: number;
    cost?: number;
  };
}

export const Message: React.FC<MessageProps> = ({
  id,
  content,
  role,
  timestamp,
  reactions = [],
  isStreaming = false,
  metadata,
}) => {
  const [isHovering, setIsHovering] = useState(false);
  const { toggleReaction, regenerateMessage, editMessage, deleteMessage } = useChatStore();

  const isUser = role === 'user';
  const isAssistant = role === 'assistant';

  const handleReactionToggle = useCallback(
    (messageId: string, emoji: string) => {
      toggleReaction(messageId, emoji);
    },
    [toggleReaction]
  );

  const handleRegenerate = useCallback(() => {
    regenerateMessage(id);
  }, [id, regenerateMessage]);

  const handleEdit = useCallback(() => {
    const newContent = prompt('Edit message:', content);
    if (newContent && newContent !== content) {
      editMessage(id, newContent);
    }
  }, [id, content, editMessage]);

  const handleDelete = useCallback(() => {
    deleteMessage(id);
  }, [id, deleteMessage]);

  const formattedTime = useMemo(
    () => format(timestamp, 'HH:mm'),
    [timestamp]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      className={`
        flex gap-3 px-4 py-3 group
        ${isUser ? 'flex-row-reverse' : 'flex-row'}
        ${isHovering ? 'bg-gray-50 dark:bg-gray-900/50' : ''}
        transition-colors duration-150
      `}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Avatar */}
      <div
        className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
          ${isUser 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-300 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
          }
        `}
      >
        {isUser ? 'U' : 'AI'}
      </div>

      {/* Message content */}
      <div className={`flex-1 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {isUser ? 'You' : 'Assistant'}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formattedTime}
          </span>
        </div>

        {/* Content bubble */}
        <div
          className={`
            max-w-[80%] px-4 py-2 rounded-2xl
            ${isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : 'bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm'
            }
          `}
        >
          <p className="text-sm whitespace-pre-wrap break-words">
            {content}
            {isStreaming && (
              <motion.span
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 1, repeat: Infinity }}
                className="inline-block ml-1 w-1 h-4 bg-current"
              />
            )}
          </p>

          {/* Metadata */}
          {metadata && isAssistant && (
            <div className="mt-2 pt-2 border-t border-gray-300 dark:border-gray-700">
              <div className="flex flex-wrap gap-2 text-xs text-gray-600 dark:text-gray-400">
                {metadata.model && (
                  <span className="flex items-center gap-1">
                    <span className="font-medium">Model:</span>
                    {metadata.model}
                  </span>
                )}
                {metadata.tokensUsed && (
                  <span className="flex items-center gap-1">
                    <span className="font-medium">Tokens:</span>
                    {metadata.tokensUsed.toLocaleString()}
                  </span>
                )}
                {metadata.cost !== undefined && (
                  <span className="flex items-center gap-1">
                    <span className="font-medium">Cost:</span>
                    ${metadata.cost.toFixed(6)}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Reactions */}
        {!isStreaming && (
          <MessageReactions
            messageId={id}
            reactions={reactions}
            onReactionToggle={handleReactionToggle}
          />
        )}
      </div>

      {/* Actions */}
      {isHovering && !isStreaming && (
        <motion.div
          initial={{ opacity: 0, x: isUser ? 10 : -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: isUser ? 10 : -10 }}
          transition={{ duration: 0.15 }}
        >
          <MessageActions
            messageId={id}
            content={content}
            onRegenerate={isAssistant ? handleRegenerate : undefined}
            onEdit={handleEdit}
            onDelete={handleDelete}
            canEdit={isUser}
            canDelete={true}
          />
        </motion.div>
      )}
    </motion.div>
  );
};

export default Message;
