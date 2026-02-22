/**
 * Message Retry Component
 * 
 * Displays a retry button for failed messages with automatic retry logic.
 * 
 * Features:
 * - One-click retry
 * - Automatic retry with exponential backoff
 * - Visual loading state
 * - Error reason display
 * - Retry count limit
 * - Toast notifications
 * 
 * Usage:
 *   <MessageRetry
 *     messageId="msg_123"
 *     error="Network error"
 *     onRetry={handleRetry}
 *   />
 */

import React, { useState } from 'react';
import { useToast } from '../hooks/useToast';

interface MessageRetryProps {
  messageId: string;
  error: string;
  retryCount?: number;
  maxRetries?: number;
  onRetry: (messageId: string) => Promise<void>;
  autoRetry?: boolean;
  autoRetryDelay?: number; // milliseconds
}

export const MessageRetry: React.FC<MessageRetryProps> = ({
  messageId,
  error,
  retryCount = 0,
  maxRetries = 3,
  onRetry,
  autoRetry = false,
  autoRetryDelay = 2000,
}) => {
  const [isRetrying, setIsRetrying] = useState(false);
  const [localRetryCount, setLocalRetryCount] = useState(retryCount);
  const { showToast } = useToast();

  const handleRetry = async () => {
    if (localRetryCount >= maxRetries) {
      showToast({
        type: 'error',
        message: `Maximum retry attempts (${maxRetries}) reached`,
      });
      return;
    }

    setIsRetrying(true);
    setLocalRetryCount(prev => prev + 1);

    try {
      await onRetry(messageId);
      showToast({
        type: 'success',
        message: 'Message sent successfully',
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      showToast({
        type: 'error',
        message: errorMessage,
      });

      // Automatic retry with exponential backoff
      if (autoRetry && localRetryCount < maxRetries - 1) {
        const delay = autoRetryDelay * Math.pow(2, localRetryCount);
        showToast({
          type: 'info',
          message: `Retrying in ${delay / 1000}s...`,
        });

        setTimeout(() => {
          handleRetry();
        }, delay);
      }
    } finally {
      setIsRetrying(false);
    }
  };

  const canRetry = localRetryCount < maxRetries;

  return (
    <div className="message-retry">
      <div className="message-retry-content">
        <div className="message-retry-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="#ef4444" strokeWidth="2" />
            <path d="M12 8v4" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="16" r="0.5" fill="#ef4444" />
          </svg>
        </div>

        <div className="message-retry-info">
          <div className="message-retry-error">
            <strong>Failed to send:</strong> {error}
          </div>
          {localRetryCount > 0 && (
            <div className="message-retry-count">
              Retry attempt {localRetryCount} of {maxRetries}
            </div>
          )}
        </div>
      </div>

      <div className="message-retry-actions">
        {canRetry ? (
          <button
            className="btn-retry"
            onClick={handleRetry}
            disabled={isRetrying}
            aria-label="Retry sending message"
          >
            {isRetrying ? (
              <>
                <span className="spinner" />
                Retrying...
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M21 12a9 9 0 11-9-9c2.52 0 4.93 1 6.74 2.74L21 8"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path d="M21 3v5h-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
                Retry
              </>
            )}
          </button>
        ) : (
          <div className="message-retry-limit">
            Max retries reached. Please try again later.
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageRetry;
