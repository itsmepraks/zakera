/**
 * Chat Type Definitions
 */

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  response_time_ms?: number;
  created_at: string;
  updated_at?: string;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  model?: string;
  message_count: number;
  duration_seconds?: number;
  created_at: string;
  updated_at?: string;
  last_message_at?: string;
}

export interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
}
