import { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';

interface TypingEvent {
  conversationId: string;
  isTyping: boolean;
  userName?: string;
}

export const useTypingIndicator = (conversationId: string) => {
  const [isTyping, setIsTyping] = useState(false);
  const [typingUser, setTypingUser] = useState<string>('AI');
  const { socket, isConnected } = useWebSocket();

  useEffect(() => {
    if (!socket || !isConnected) return;

    const handleTypingStart = (event: TypingEvent) => {
      if (event.conversationId === conversationId) {
        setIsTyping(true);
        setTypingUser(event.userName || 'AI');
      }
    };

    const handleTypingStop = (event: TypingEvent) => {
      if (event.conversationId === conversationId) {
        setIsTyping(false);
      }
    };

    socket.on('typing_start', handleTypingStart);
    socket.on('typing_stop', handleTypingStop);

    return () => {
      socket.off('typing_start', handleTypingStart);
      socket.off('typing_stop', handleTypingStop);
    };
  }, [socket, isConnected, conversationId]);

  const startTyping = useCallback(() => {
    if (socket && isConnected) {
      socket.emit('typing_start', { conversationId });
    }
  }, [socket, isConnected, conversationId]);

  const stopTyping = useCallback(() => {
    if (socket && isConnected) {
      socket.emit('typing_stop', { conversationId });
    }
  }, [socket, isConnected, conversationId]);

  return {
    isTyping,
    typingUser,
    startTyping,
    stopTyping,
  };
};

export default useTypingIndicator;
