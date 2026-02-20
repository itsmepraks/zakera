/**
 * Custom hook for managing typing indicator state
 */
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseTypingIndicatorOptions {
  /** Delay before showing typing indicator (ms) */
  showDelay?: number;
  /** Timeout for hiding typing indicator if no activity (ms) */
  timeout?: number;
}

interface UseTypingIndicatorReturn {
  /** Whether typing indicator is currently shown */
  isTyping: boolean;
  /** Start showing typing indicator */
  startTyping: () => void;
  /** Stop showing typing indicator */
  stopTyping: () => void;
  /** Reset typing state */
  resetTyping: () => void;
}

/**
 * Hook for managing typing indicator with delays and timeouts
 * @param options Configuration options
 * @returns Typing indicator state and controls
 */
export const useTypingIndicator = (
  options: UseTypingIndicatorOptions = {}
): UseTypingIndicatorReturn => {
  const { showDelay = 300, timeout = 30000 } = options;

  const [isTyping, setIsTyping] = useState(false);
  const showTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Clear all timers
  const clearTimers = useCallback(() => {
    if (showTimerRef.current) {
      clearTimeout(showTimerRef.current);
      showTimerRef.current = null;
    }
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }, []);

  // Start typing with delay
  const startTyping = useCallback(() => {
    clearTimers();

    // Show typing indicator after delay
    showTimerRef.current = setTimeout(() => {
      setIsTyping(true);

      // Set timeout to auto-hide
      hideTimerRef.current = setTimeout(() => {
        setIsTyping(false);
      }, timeout);
    }, showDelay);
  }, [showDelay, timeout, clearTimers]);

  // Stop typing immediately
  const stopTyping = useCallback(() => {
    clearTimers();
    setIsTyping(false);
  }, [clearTimers]);

  // Reset typing state
  const resetTyping = useCallback(() => {
    clearTimers();
    setIsTyping(false);
  }, [clearTimers]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  return {
    isTyping,
    startTyping,
    stopTyping,
    resetTyping,
  };
};

export default useTypingIndicator;
