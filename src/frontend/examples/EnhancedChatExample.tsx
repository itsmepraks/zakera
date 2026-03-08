/**
 * Complete Example: Enhanced Chat UI Integration
 * 
 * Demonstrates how to use all enhanced chat features together
 */

import React, { useState, useEffect } from 'react';
import { EnhancedChatUI } from '../components/EnhancedChatUI/EnhancedChatUI';
import { ReactionType, ReactionCount } from '../types/reactions';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  reactions?: ReactionCount[];
}

export const EnhancedChatExample: React.FC = () => {
  const [conversationId] = useState('demo-conversation-123');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // Simulate initial messages
  useEffect(() => {
    const initialMessages: Message[] = [
      {
        id: 'msg-1',
        role: 'assistant',
        content: 'Hello! I\'m Zakera, your AI assistant. How can I help you today?',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        reactions: [
          { type: 'thumbs_up', count: 1, user_reacted: false },
          { type: 'heart', count: 1, user_reacted: false },
        ],
      },
    ];
    setMessages(initialMessages);
  }, []);

  /**
   * Handle sending a message
   */
  const handleSendMessage = async (message: string, systemPrompt?: string) => {
    // Add user message immediately
    const userMessage: Message = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsProcessing(true);

    try {
      // Call your API endpoint
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          system_prompt: systemPrompt,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      // Add AI response
      const aiMessage: Message = {
        id: data.id || `msg-ai-${Date.now()}`,
        role: 'assistant',
        content: data.content || data.message,
        timestamp: new Date().toISOString(),
        reactions: [],
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error sending message:', error);

      // Add error message
      const errorMessage: Message = {
        id: `msg-error-${Date.now()}`,
        role: 'assistant',
        content: '❌ Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        reactions: [],
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * Handle message reactions
   */
  const handleReact = async (messageId: string, reactionType: ReactionType) => {
    // Optimistic update
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== messageId) return msg;

        const reactions = msg.reactions || [];
        const existingReaction = reactions.find((r) => r.type === reactionType);

        let newReactions: ReactionCount[];

        if (existingReaction) {
          // Toggle off if user already reacted
          if (existingReaction.user_reacted) {
            newReactions = reactions.map((r) =>
              r.type === reactionType
                ? { ...r, count: r.count - 1, user_reacted: false }
                : r
            ).filter((r) => r.count > 0);
          } else {
            // Add user reaction
            newReactions = reactions.map((r) =>
              r.type === reactionType
                ? { ...r, count: r.count + 1, user_reacted: true }
                : r
            );
          }
        } else {
          // New reaction
          newReactions = [
            ...reactions,
            { type: reactionType, count: 1, user_reacted: true },
          ];
        }

        return { ...msg, reactions: newReactions };
      })
    );

    // Call API to persist
    try {
      await fetch(`/api/v1/messages/${messageId}/react`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reaction_type: reactionType }),
      });
    } catch (error) {
      console.error('Error saving reaction:', error);
      // Optionally revert optimistic update
    }
  };

  /**
   * Handle message feedback
   */
  const handleFeedback = async (
    messageId: string,
    feedbackType: 'positive' | 'negative',
    feedbackText?: string
  ) => {
    console.log('Feedback received:', { messageId, feedbackType, feedbackText });

    try {
      await fetch(`/api/v1/messages/${messageId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedback_type: feedbackType,
          feedback_text: feedbackText,
        }),
      });

      // Show success notification (optional)
      console.log('✅ Feedback saved successfully');
    } catch (error) {
      console.error('Error saving feedback:', error);
    }
  };

  return (
    <div style={{ height: '100vh' }}>
      <EnhancedChatUI
        conversationId={conversationId}
        messages={messages}
        onSendMessage={handleSendMessage}
        onReact={handleReact}
        onFeedback={handleFeedback}
        currentModel="gpt-4-turbo"
        disabled={isProcessing}
      />
    </div>
  );
};

export default EnhancedChatExample;

/**
 * EXAMPLE OUTPUT:
 * 
 * This creates a complete chat interface with:
 * - Template selector button in header
 * - Message composer with formatting tools
 * - Auto-save draft functionality
 * - Reactions on AI messages
 * - Feedback collection
 * - Summary generation button
 * - Beautiful gradient design
 * - Responsive layout
 * - Dark mode support
 * 
 * USAGE:
 * 
 * 1. User clicks "Templates" → browses and selects template
 * 2. Template applied → system prompt set
 * 3. User types message → auto-saved as draft
 * 4. User formats text → toolbar or shortcuts
 * 5. User sends message → draft cleared
 * 6. AI responds → message appears
 * 7. User reacts → thumbs up/down or custom
 * 8. User provides feedback → optional text
 * 9. User clicks "Summary" → AI generates summary
 * 10. User copies/exports summary
 * 
 * All features work seamlessly together!
 */
