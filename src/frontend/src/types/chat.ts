/**
 * Type definitions for enhanced chat functionality
 */
import { Reaction } from './reactions';

export type MessageStatus = 'sending' | 'sent' | 'delivered' | 'error';

export interface ChatMessage {
  /** Unique message ID */
  id: number;
  /** Conversation ID */
  conversationId: number;
  /** Message role (user, assistant, system) */
  role: 'user' | 'assistant' | 'system';
  /** Message content */
  content: string;
  /** Message timestamp */
  timestamp: Date;
  /** Delivery status */
  status?: MessageStatus;
  /** Token count (if available) */
  tokens?: number;
  /** Model used to generate response (if applicable) */
  model?: string;
  /** Cost in dollars (if available) */
  cost?: number;
  /** Message reactions */
  reactions?: Reaction[];
  /** Whether message is being edited */
  isEditing?: boolean;
  /** Temporary client-side ID for optimistic updates */
  tempId?: string;
}

export interface TypingStatus {
  /** Whether someone is typing */
  isTyping: boolean;
  /** Who is typing */
  entity: string;
  /** Conversation ID */
  conversationId: number;
}

export interface MessageUpdate {
  /** Message ID */
  messageId: number;
  /** New status */
  status?: MessageStatus;
  /** New content (for edits) */
  content?: string;
  /** Updated reactions */
  reactions?: Reaction[];
}
