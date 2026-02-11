import React, { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import './ChatContainer.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  reactions?: Array<{
    emoji: string;
    count: number;
    userReacted: boolean;
  }>;
}

interface ChatContainerProps {
  messages: Message[];
  isTyping?: boolean;
  onReactionToggle: (messageId: string, emoji: string) => void;
  onMessageEdit?: (messageId: string) => void;
  onMessageDelete?: (messageId: string) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  isTyping = false,
  onReactionToggle,
  onMessageEdit,
  onMessageDelete,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({
      behavior: smooth ? 'smooth' : 'auto',
      block: 'end',
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    setShowScrollButton(!isNearBottom);
  };

  const groupMessagesByDate = (messages: Message[]) => {
    const groups: { [key: string]: Message[] } = {};
    
    messages.forEach((message) => {
      const date = new Date(message.timestamp);
      const dateKey = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      groups[dateKey].push(message);
    });
    
    return groups;
  };

  const messageGroups = groupMessagesByDate(messages);

  return (
    <div className="chat-container" ref={containerRef} onScroll={handleScroll}>
      <div className="messages-wrapper">
        {Object.entries(messageGroups).map(([date, dateMessages]) => (
          <div key={date} className="message-group">
            <div className="date-divider">
              <span className="date-label">{date}</span>
            </div>
            
            {dateMessages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onReactionToggle={onReactionToggle}
                onEdit={onMessageEdit}
                onDelete={onMessageDelete}
              />
            ))}
          </div>
        ))}
        
        {isTyping && <TypingIndicator show={isTyping} userName="AI" />}
        
        <div ref={messagesEndRef} />
      </div>

      {showScrollButton && (
        <button
          className="scroll-to-bottom"
          onClick={() => scrollToBottom(true)}
          aria-label="Scroll to bottom"
        >
          <span className="scroll-icon">↓</span>
          <span className="scroll-text">New messages</span>
        </button>
      )}
    </div>
  );
};

export default ChatContainer;
