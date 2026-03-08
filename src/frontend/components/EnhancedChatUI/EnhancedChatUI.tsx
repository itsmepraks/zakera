/**
 * Enhanced Chat UI - Main Integration Component
 * 
 * Brings together all enhanced chat features:
 * - Template selector
 * - Message reactions
 * - Conversation summary
 * - Enhanced composer
 */

import React, { useState, useEffect, useRef } from 'react';
import { TemplateSelector } from '../TemplateSelector/TemplateSelector';
import { MessageReactions } from '../MessageReactions/MessageReactions';
import { ConversationSummary } from '../ConversationSummary/ConversationSummary';
import { MessageComposer } from '../MessageComposer/MessageComposer';
import { ConversationTemplate } from '../../types/templates';
import { ReactionType, ReactionCount } from '../../types/reactions';
import './EnhancedChatUI.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  reactions?: ReactionCount[];
}

interface EnhancedChatUIProps {
  conversationId: string;
  messages: Message[];
  onSendMessage: (message: string, systemPrompt?: string) => void;
  onReact: (messageId: string, reactionType: ReactionType) => void;
  onFeedback: (messageId: string, feedbackType: 'positive' | 'negative', text?: string) => void;
  currentModel?: string;
  disabled?: boolean;
}

export const EnhancedChatUI: React.FC<EnhancedChatUIProps> = ({
  conversationId,
  messages,
  onSendMessage,
  onReact,
  onFeedback,
  currentModel = 'gpt-4-turbo',
  disabled = false,
}) => {
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<ConversationTemplate | null>(null);
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle template selection
  const handleSelectTemplate = (template: ConversationTemplate) => {
    setSelectedTemplate(template);
    setSystemPrompt(template.system_prompt);
    setShowTemplateSelector(false);

    // If template has a starter message, show it
    if (template.starter_message) {
      // You might want to display this as a system message
      console.log('Template starter:', template.starter_message);
    }
  };

  // Handle sending message
  const handleSendMessage = (message: string) => {
    onSendMessage(message, systemPrompt || undefined);
  };

  // Format timestamp
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="enhanced-chat-ui">
      {/* Header with template info and actions */}
      <div className="chat-header">
        <div className="header-left">
          <h2 className="chat-title">💬 Zakera AI Assistant</h2>
          {selectedTemplate && (
            <div className="active-template-badge">
              <span className="template-icon">📚</span>
              <span className="template-name">{selectedTemplate.title}</span>
              <button
                className="clear-template-btn"
                onClick={() => {
                  setSelectedTemplate(null);
                  setSystemPrompt('');
                }}
                title="Clear template"
              >
                ✕
              </button>
            </div>
          )}
        </div>

        <div className="header-actions">
          <button
            className="header-action-btn"
            onClick={() => setShowTemplateSelector(true)}
            title="Choose template"
          >
            📚 Templates
          </button>
          <button
            className="header-action-btn"
            onClick={() => setShowSummary(!showSummary)}
            title="View summary"
            disabled={messages.length === 0}
          >
            📝 Summary
          </button>
        </div>
      </div>

      {/* Summary panel */}
      {showSummary && (
        <div className="summary-panel">
          <ConversationSummary
            messages={messages}
            conversationId={conversationId}
            onClose={() => setShowSummary(false)}
          />
        </div>
      )}

      {/* Messages area */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat-state">
            <div className="welcome-message">
              <h3>👋 Welcome to Zakera!</h3>
              <p>Start a conversation or choose a template to get started.</p>
              <button
                className="cta-button"
                onClick={() => setShowTemplateSelector(true)}
              >
                📚 Browse Templates
              </button>
            </div>

            {/* Suggested templates */}
            <div className="quick-templates">
              <h4>Quick Start:</h4>
              <div className="quick-template-chips">
                <button className="quick-chip" onClick={() => setShowTemplateSelector(true)}>
                  🔍 Code Review
                </button>
                <button className="quick-chip" onClick={() => setShowTemplateSelector(true)}>
                  🧩 Problem Solving
                </button>
                <button className="quick-chip" onClick={() => setShowTemplateSelector(true)}>
                  📚 Learn Something
                </button>
                <button className="quick-chip" onClick={() => setShowTemplateSelector(true)}>
                  💡 Brainstorm Ideas
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message-wrapper ${message.role}`}
              >
                <div className="message-bubble">
                  <div className="message-header">
                    <span className="message-author">
                      {message.role === 'user' ? '👤 You' : '🤖 AI Assistant'}
                    </span>
                    <span className="message-time">{formatTime(message.timestamp)}</span>
                  </div>

                  <div className="message-content">{message.content}</div>

                  {/* Reactions for AI messages */}
                  {message.role === 'assistant' && (
                    <MessageReactions
                      messageId={message.id}
                      reactions={message.reactions || []}
                      onReact={onReact}
                      onFeedback={onFeedback}
                      disabled={disabled}
                    />
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Enhanced composer */}
      <div className="composer-container">
        <MessageComposer
          conversationId={conversationId}
          onSendMessage={handleSendMessage}
          onOpenTemplates={() => setShowTemplateSelector(true)}
          disabled={disabled}
          showTemplateButton={true}
        />
      </div>

      {/* Template selector modal */}
      <TemplateSelector
        isOpen={showTemplateSelector}
        onClose={() => setShowTemplateSelector(false)}
        onSelectTemplate={handleSelectTemplate}
      />
    </div>
  );
};

export default EnhancedChatUI;
