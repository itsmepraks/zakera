/**
 * MessageTimestamp Component
 * 
 * Displays smart timestamps for messages with relative and absolute time.
 * Updates automatically and shows detailed time on hover.
 */

import React, { useState, useEffect } from 'react';
import './MessageTimestamp.css';

interface MessageTimestampProps {
  timestamp: string | Date;
  format?: 'relative' | 'absolute' | 'both';
  updateInterval?: number; // ms
  className?: string;
}

const MessageTimestamp: React.FC<MessageTimestampProps> = ({
  timestamp,
  format = 'relative',
  updateInterval = 60000, // Update every minute
  className = ''
}) => {
  const [relativeTime, setRelativeTime] = useState<string>('');
  const [absoluteTime, setAbsoluteTime] = useState<string>('');

  useEffect(() => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    
    const updateTimes = () => {
      setRelativeTime(getRelativeTime(date));
      setAbsoluteTime(getAbsoluteTime(date));
    };

    updateTimes();

    // Update relative time periodically
    if (format !== 'absolute') {
      const interval = setInterval(updateTimes, updateInterval);
      return () => clearInterval(interval);
    }
  }, [timestamp, format, updateInterval]);

  const getRelativeTime = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSeconds < 10) return 'just now';
    if (diffSeconds < 60) return `${diffSeconds} seconds ago`;
    if (diffMinutes === 1) return '1 minute ago';
    if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
    if (diffHours === 1) return '1 hour ago';
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  const getAbsoluteTime = (date: Date): string => {
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    };
    return date.toLocaleString('en-US', options);
  };

  const displayTime = () => {
    switch (format) {
      case 'relative':
        return relativeTime;
      case 'absolute':
        return absoluteTime;
      case 'both':
        return `${relativeTime} (${absoluteTime})`;
      default:
        return relativeTime;
    }
  };

  return (
    <span 
      className={`message-timestamp ${className}`}
      title={absoluteTime}
      aria-label={`Message sent ${absoluteTime}`}
    >
      <svg 
        className="timestamp-icon" 
        width="12" 
        height="12" 
        viewBox="0 0 12 12" 
        fill="currentColor"
      >
        <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1" fill="none" />
        <path d="M6 3v3l2 2" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
      {displayTime()}
    </span>
  );
};

export default MessageTimestamp;
