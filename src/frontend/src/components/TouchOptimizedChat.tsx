import React, { useState, useRef, useEffect, TouchEvent } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface TouchOptimizedChatProps {
  onSendMessage: (message: string) => Promise<void>;
  messages: Message[];
  isLoading?: boolean;
  placeholder?: string;
}

export const TouchOptimizedChat: React.FC<TouchOptimizedChatProps> = ({
  onSendMessage,
  messages,
  isLoading = false,
  placeholder = 'Type a message...',
}) => {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Pull to refresh state
  const [pullDistance, setPullDistance] = useState(0);
  const [isPulling, setIsPulling] = useState(false);
  const touchStartY = useRef(0);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isSending) return;

    setIsSending(true);
    try {
      await onSendMessage(input.trim());
      setInput('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Pull to refresh handlers
  const handleTouchStart = (e: TouchEvent) => {
    if (window.scrollY === 0) {
      touchStartY.current = e.touches[0].clientY;
      setIsPulling(true);
    }
  };

  const handleTouchMove = (e: TouchEvent) => {
    if (!isPulling) return;

    const touchY = e.touches[0].clientY;
    const distance = Math.max(0, touchY - touchStartY.current);
    
    if (distance > 0 && distance < 100) {
      setPullDistance(distance);
    }
  };

  const handleTouchEnd = () => {
    if (pullDistance > 70) {
      // Trigger refresh
      window.location.reload();
    }
    setIsPulling(false);
    setPullDistance(0);
  };

  return (
    <div 
      className="chat-container"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull to refresh indicator */}
      {pullDistance > 0 && (
        <div 
          className="pull-to-refresh"
          style={{
            transform: `translateY(${Math.min(pullDistance, 100)}px)`,
            opacity: pullDistance / 100,
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', marginBottom: '4px' }}>↻</div>
            <div style={{ fontSize: '12px' }}>
              {pullDistance > 70 ? 'Release to refresh' : 'Pull to refresh'}
            </div>
          </div>
        </div>
      )}

      {/* Messages area */}
      <div className="chat-messages">
        <a href="#chat-input" className="skip-to-main">
          Skip to message input
        </a>

        {messages.length === 0 ? (
          <div 
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              padding: '2rem',
              textAlign: 'center',
              color: '#6b7280',
            }}
          >
            <div style={{ fontSize: '48px', marginBottom: '1rem' }}>💬</div>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
              Start a conversation
            </h2>
            <p>Send a message to begin chatting with Zakera</p>
          </div>
        ) : (
          messages.map((message) => (
            <div 
              key={message.id} 
              className="chat-message"
              role="article"
              aria-label={`${message.role === 'user' ? 'Your' : 'Assistant'} message`}
            >
              {/* Avatar */}
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  background: message.role === 'user' ? '#3b82f6' : '#10b981',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  fontSize: '18px',
                }}
              >
                {message.role === 'user' ? '👤' : '🤖'}
              </div>

              {/* Message content */}
              <div
                className="chat-message-content"
                style={{
                  background: message.role === 'user' ? '#eff6ff' : '#f3f4f6',
                }}
              >
                <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                  {message.role === 'user' ? 'You' : 'Zakera'}
                </div>
                <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
                <div 
                  style={{ 
                    fontSize: '0.75rem', 
                    color: '#6b7280', 
                    marginTop: '0.5rem' 
                  }}
                >
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="chat-message" role="status" aria-live="polite">
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: '#10b981',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              🤖
            </div>
            <div
              className="chat-message-content"
              style={{ background: '#f3f4f6' }}
            >
              <div style={{ display: 'flex', gap: '4px' }}>
                <span className="animate" style={{ animation: 'pulse 1.5s ease-in-out infinite' }}>•</span>
                <span className="animate" style={{ animation: 'pulse 1.5s ease-in-out 0.2s infinite' }}>•</span>
                <span className="animate" style={{ animation: 'pulse 1.5s ease-in-out 0.4s infinite' }}>•</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-container" id="chat-input">
        <div className="chat-input">
          <textarea
            ref={textareaRef}
            className="chat-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isSending}
            rows={1}
            aria-label="Message input"
            aria-describedby="send-button"
          />
          <button
            className="chat-send-button"
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            aria-label="Send message"
            id="send-button"
          >
            {isSending ? (
              <span className="animate">⏳</span>
            ) : (
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* CSS for loading animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};
