/**
 * Auto Scroll Hook
 * 
 * Manages automatic scrolling to bottom with user control.
 * 
 * Features:
 * - Auto-scroll on new messages
 * - Detects user scroll position
 * - "Jump to bottom" button when scrolled up
 * - Smooth scroll animations
 * - Customizable behavior
 * 
 * Usage:
 *   const { scrollToBottom, showScrollButton, scrollRef } = useAutoScroll({
 *     messages,
 *     autoScroll: true,
 *   });
 */

import { useEffect, useRef, useState, RefObject } from 'react';

interface UseAutoScrollOptions {
  messages: any[];
  autoScroll?: boolean;
  threshold?: number; // pixels from bottom to trigger auto-scroll
  smoothScroll?: boolean;
}

interface UseAutoScrollReturn {
  scrollRef: RefObject<HTMLDivElement>;
  scrollToBottom: (smooth?: boolean) => void;
  showScrollButton: boolean;
  isNearBottom: boolean;
}

export const useAutoScroll = ({
  messages,
  autoScroll = true,
  threshold = 100,
  smoothScroll = true,
}: UseAutoScrollOptions): UseAutoScrollReturn => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [userHasScrolled, setUserHasScrolled] = useState(false);

  const checkScrollPosition = () => {
    const container = scrollRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const nearBottom = distanceFromBottom <= threshold;

    setIsNearBottom(nearBottom);
    setShowScrollButton(!nearBottom && messages.length > 0);
  };

  const scrollToBottom = (smooth = smoothScroll) => {
    const container = scrollRef.current;
    if (!container) return;

    const scrollOptions: ScrollToOptions = {
      top: container.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    };

    container.scrollTo(scrollOptions);
    setUserHasScrolled(false);
  };

  // Auto-scroll when new messages arrive (if enabled and user hasn't scrolled up)
  useEffect(() => {
    if (autoScroll && !userHasScrolled && isNearBottom) {
      // Small delay to ensure DOM has updated
      const timer = setTimeout(() => {
        scrollToBottom();
      }, 50);

      return () => clearTimeout(timer);
    }
  }, [messages]);

  // Set up scroll listener
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    let scrollTimeout: NodeJS.Timeout;

    const handleScroll = () => {
      // Debounce scroll checks
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        checkScrollPosition();

        // Detect if user manually scrolled up
        const { scrollTop, scrollHeight, clientHeight } = container;
        const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
        if (distanceFromBottom > threshold) {
          setUserHasScrolled(true);
        }
      }, 100);
    };

    container.addEventListener('scroll', handleScroll);
    checkScrollPosition(); // Initial check

    return () => {
      container.removeEventListener('scroll', handleScroll);
      clearTimeout(scrollTimeout);
    };
  }, [threshold]);

  return {
    scrollRef,
    scrollToBottom,
    showScrollButton,
    isNearBottom,
  };
};
