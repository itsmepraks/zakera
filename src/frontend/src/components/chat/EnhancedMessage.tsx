"use client";

import React, { useState, useCallback, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypePrism from 'rehype-prism-plus';
import {
  Copy,
  Check,
  RotateCcw,
  Edit2,
  Share2,
  ThumbsUp,
  ThumbsDown,
  MoreVertical,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Message } from '@/types/chat';
import 'prismjs/themes/prism-tomorrow.css';
import 'katex/dist/katex.min.css';

interface EnhancedMessageProps {
  message: Message;
  onRegenerate?: () => void;
  onEdit?: (content: string) => void;
  onFeedback?: (type: 'positive' | 'negative') => void;
  onShare?: () => void;
  isStreaming?: boolean;
  showActions?: boolean;
  className?: string;
}

export const EnhancedMessage = memo<EnhancedMessageProps>(
  ({
    message,
    onRegenerate,
    onEdit,
    onFeedback,
    onShare,
    isStreaming = false,
    showActions = true,
    className = '',
  }) => {
    const [copied, setCopied] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editedContent, setEditedContent] = useState(message.content);
    const [showMenu, setShowMenu] = useState(false);
    const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);

    const isUser = message.role === 'user';
    const isAssistant = message.role === 'assistant';

    const handleCopy = useCallback(async () => {
      try {
        await navigator.clipboard.writeText(message.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (error) {
        console.error('Failed to copy:', error);
      }
    }, [message.content]);

    const handleEdit = useCallback(() => {
      if (isEditing && editedContent !== message.content) {
        onEdit?.(editedContent);
      }
      setIsEditing(!isEditing);
    }, [isEditing, editedContent, message.content, onEdit]);

    const handleFeedback = useCallback(
      (type: 'positive' | 'negative') => {
        setFeedback(type);
        onFeedback?.(type);
      },
      [onFeedback]
    );

    return (
      <div
        className={`message-container flex gap-4 p-4 group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
          isUser ? 'justify-end' : ''
        } ${className}`}
      >
        {/* Avatar */}
        {!isUser && (
          <div className="flex-shrink-0">
            <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full">
              <span className="text-sm font-medium text-white">AI</span>
            </div>
          </div>
        )}

        {/* Message Content */}
        <div className={`flex-1 space-y-2 ${isUser ? 'max-w-2xl' : 'max-w-3xl'}`}>
          {/* Header */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {isUser ? 'You' : 'Assistant'}
            </span>

            {/* Model Badge */}
            {isAssistant && message.model && (
              <span className="px-2 py-0.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-full dark:bg-gray-700 dark:text-gray-400">
                {message.model}
              </span>
            )}

            {/* Timestamp */}
            <span className="text-xs text-gray-500 dark:text-gray-500">
              {formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}
            </span>

            {/* Streaming Indicator */}
            {isStreaming && (
              <span className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400">
                <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse"></span>
                Generating...
              </span>
            )}
          </div>

          {/* Message Body */}
          <div
            className={`message-body rounded-lg p-4 ${
              isUser
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
            }`}
          >
            {isEditing ? (
              <div className="space-y-2">
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  className="w-full min-h-[100px] p-2 text-sm bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleEdit}
                    className="px-3 py-1 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setEditedContent(message.content);
                    }}
                    className="px-3 py-1 text-sm text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className={`prose prose-sm max-w-none ${
                isUser ? 'prose-invert' : 'dark:prose-invert'
              }`}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex, rehypePrism]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      return !inline && match ? (
                        <div className="relative group/code">
                          <button
                            onClick={handleCopy}
                            className="absolute right-2 top-2 p-1.5 bg-gray-700 hover:bg-gray-600 rounded-md opacity-0 group-hover/code:opacity-100 transition-opacity"
                            title="Copy code"
                          >
                            {copied ? (
                              <Check className="w-4 h-4 text-green-400" />
                            ) : (
                              <Copy className="w-4 h-4 text-gray-300" />
                            )}
                          </button>
                          <code className={className} {...props}>
                            {children}
                          </code>
                        </div>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Token Info */}
          {isAssistant && (message.prompt_tokens || message.completion_tokens) && (
            <div className="flex gap-4 text-xs text-gray-500 dark:text-gray-500">
              {message.prompt_tokens && (
                <span>Prompt: {message.prompt_tokens} tokens</span>
              )}
              {message.completion_tokens && (
                <span>Completion: {message.completion_tokens} tokens</span>
              )}
              {message.response_time_ms && (
                <span>Time: {(message.response_time_ms / 1000).toFixed(2)}s</span>
              )}
            </div>
          )}

          {/* Actions */}
          {showActions && !isEditing && (
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              {/* Copy */}
              <button
                onClick={handleCopy}
                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
                title="Copy message"
                aria-label="Copy message"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>

              {/* Edit (user messages only) */}
              {isUser && onEdit && (
                <button
                  onClick={handleEdit}
                  className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
                  title="Edit message"
                  aria-label="Edit message"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              )}

              {/* Regenerate (assistant messages only) */}
              {isAssistant && onRegenerate && !isStreaming && (
                <button
                  onClick={onRegenerate}
                  className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
                  title="Regenerate response"
                  aria-label="Regenerate response"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}

              {/* Feedback (assistant messages only) */}
              {isAssistant && onFeedback && (
                <>
                  <button
                    onClick={() => handleFeedback('positive')}
                    className={`p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 ${
                      feedback === 'positive'
                        ? 'text-green-600 dark:text-green-500'
                        : 'text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'
                    }`}
                    title="Good response"
                    aria-label="Good response"
                  >
                    <ThumbsUp className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleFeedback('negative')}
                    className={`p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 ${
                      feedback === 'negative'
                        ? 'text-red-600 dark:text-red-500'
                        : 'text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'
                    }`}
                    title="Poor response"
                    aria-label="Poor response"
                  >
                    <ThumbsDown className="w-4 h-4" />
                  </button>
                </>
              )}

              {/* Share */}
              {onShare && (
                <button
                  onClick={onShare}
                  className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
                  title="Share message"
                  aria-label="Share message"
                >
                  <Share2 className="w-4 h-4" />
                </button>
              )}

              <div className="flex-1" />

              {/* More options */}
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700"
                title="More options"
                aria-label="More options"
              >
                <MoreVertical className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* User Avatar */}
        {isUser && (
          <div className="flex-shrink-0">
            <div className="flex items-center justify-center w-8 h-8 bg-gray-300 rounded-full dark:bg-gray-600">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">U</span>
            </div>
          </div>
        )}
      </div>
    );
  }
);

EnhancedMessage.displayName = 'EnhancedMessage';
