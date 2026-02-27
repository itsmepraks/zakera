/**
 * Typing Indicator Component
 * Shows animated typing indicator when AI or user is typing
 */

import React, { useEffect, useState } from 'react';

interface TypingIndicatorProps {
  userName?: string;
  variant?: 'dots' | 'wave' | 'pulse';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  userName = 'AI',
  variant = 'dots',
  size = 'md',
  className = '',
}) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Fade in animation
    const timer = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const sizeClasses = {
    sm: {
      container: 'px-3 py-2',
      dot: 'w-1.5 h-1.5',
      text: 'text-xs',
    },
    md: {
      container: 'px-4 py-3',
      dot: 'w-2 h-2',
      text: 'text-sm',
    },
    lg: {
      container: 'px-5 py-4',
      dot: 'w-2.5 h-2.5',
      text: 'text-base',
    },
  };

  const sizes = sizeClasses[size];

  const renderDotsVariant = () => (
    <div className="flex items-center space-x-1">
      <div
        className={`${sizes.dot} bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce`}
        style={{ animationDelay: '0ms', animationDuration: '1s' }}
      />
      <div
        className={`${sizes.dot} bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce`}
        style={{ animationDelay: '150ms', animationDuration: '1s' }}
      />
      <div
        className={`${sizes.dot} bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce`}
        style={{ animationDelay: '300ms', animationDuration: '1s' }}
      />
    </div>
  );

  const renderWaveVariant = () => (
    <div className="flex items-center space-x-0.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`w-0.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-pulse`}
          style={{
            height: `${8 + Math.sin(i * 0.5) * 4}px`,
            animationDelay: `${i * 100}ms`,
            animationDuration: '1.5s',
          }}
        />
      ))}
    </div>
  );

  const renderPulseVariant = () => (
    <div className="flex items-center space-x-1.5">
      <div className={`${sizes.dot} bg-primary-500 rounded-full animate-ping`} />
      <div className={`${sizes.dot} bg-primary-500 rounded-full animate-ping`} style={{ animationDelay: '0.2s' }} />
      <div className={`${sizes.dot} bg-primary-500 rounded-full animate-ping`} style={{ animationDelay: '0.4s' }} />
    </div>
  );

  const renderVariant = () => {
    switch (variant) {
      case 'wave':
        return renderWaveVariant();
      case 'pulse':
        return renderPulseVariant();
      case 'dots':
      default:
        return renderDotsVariant();
    }
  };

  return (
    <div
      className={`
        inline-flex items-center gap-3
        ${sizes.container}
        bg-gray-100 dark:bg-gray-800
        rounded-2xl
        transition-all duration-300
        ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
        ${className}
      `}
      role="status"
      aria-live="polite"
      aria-label={`${userName} is typing`}
    >
      {/* User Name */}
      <span className={`${sizes.text} text-gray-600 dark:text-gray-400 font-medium`}>
        {userName} is typing
      </span>

      {/* Animated Indicator */}
      {renderVariant()}
    </div>
  );
};

export default TypingIndicator;

/**
 * Hook for managing typing indicator state
 */
export const useTypingIndicator = (timeoutMs: number = 3000) => {
  const [isTyping, setIsTyping] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  const startTyping = (userId?: string) => {
    if (userId) {
      setTypingUsers(prev => new Set(prev).add(userId));
    }
    setIsTyping(true);

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      if (userId) {
        setTypingUsers(prev => {
          const next = new Set(prev);
          next.delete(userId);
          return next;
        });
      }
    }, timeoutMs);
  };

  const stopTyping = (userId?: string) => {
    if (userId) {
      setTypingUsers(prev => {
        const next = new Set(prev);
        next.delete(userId);
        return next;
      });
    }
    
    if (typingUsers.size === 0 || !userId) {
      setIsTyping(false);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    isTyping,
    typingUsers: Array.from(typingUsers),
    startTyping,
    stopTyping,
  };
};
