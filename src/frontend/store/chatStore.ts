import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
  reactions: Array<{
    emoji: string;
    count: number;
    userReacted: boolean;
  }>;
  metadata?: {
    model?: string;
    tokensUsed?: number;
    cost?: number;
  };
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

interface ChatState {
  conversations: Map<string, Conversation>;
  activeConversationId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  createConversation: (title: string) => string;
  deleteConversation: (id: string) => void;
  setActiveConversation: (id: string) => void;
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp' | 'reactions'>) => void;
  updateMessage: (messageId: string, content: string) => void;
  deleteMessage: (messageId: string) => void;
  regenerateMessage: (messageId: string) => void;
  editMessage: (messageId: string, content: string) => void;
  toggleReaction: (messageId: string, emoji: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      immer((set, get) => ({
        conversations: new Map(),
        activeConversationId: null,
        isLoading: false,
        error: null,

        createConversation: (title: string) => {
          const id = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          const conversation: Conversation = {
            id,
            title,
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
          };

          set((state) => {
            state.conversations.set(id, conversation);
            state.activeConversationId = id;
          });

          return id;
        },

        deleteConversation: (id: string) => {
          set((state) => {
            state.conversations.delete(id);
            if (state.activeConversationId === id) {
              state.activeConversationId = null;
            }
          });
        },

        setActiveConversation: (id: string) => {
          set({ activeConversationId: id });
        },

        addMessage: (conversationId: string, message) => {
          set((state) => {
            const conversation = state.conversations.get(conversationId);
            if (conversation) {
              const newMessage: Message = {
                ...message,
                id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                timestamp: new Date(),
                reactions: [],
              };
              conversation.messages.push(newMessage);
              conversation.updatedAt = new Date();
            }
          });
        },

        updateMessage: (messageId: string, content: string) => {
          set((state) => {
            for (const conversation of state.conversations.values()) {
              const message = conversation.messages.find(m => m.id === messageId);
              if (message) {
                message.content = content;
                conversation.updatedAt = new Date();
                break;
              }
            }
          });
        },

        deleteMessage: (messageId: string) => {
          set((state) => {
            for (const conversation of state.conversations.values()) {
              const index = conversation.messages.findIndex(m => m.id === messageId);
              if (index !== -1) {
                conversation.messages.splice(index, 1);
                conversation.updatedAt = new Date();
                break;
              }
            }
          });
        },

        regenerateMessage: async (messageId: string) => {
          // Implementation would call API to regenerate
          console.log('Regenerating message:', messageId);
        },

        editMessage: (messageId: string, content: string) => {
          get().updateMessage(messageId, content);
        },

        toggleReaction: (messageId: string, emoji: string) => {
          set((state) => {
            for (const conversation of state.conversations.values()) {
              const message = conversation.messages.find(m => m.id === messageId);
              if (message) {
                const reaction = message.reactions.find(r => r.emoji === emoji);
                if (reaction) {
                  if (reaction.userReacted) {
                    reaction.count--;
                    reaction.userReacted = false;
                    if (reaction.count === 0) {
                      message.reactions = message.reactions.filter(r => r.emoji !== emoji);
                    }
                  } else {
                    reaction.count++;
                    reaction.userReacted = true;
                  }
                } else {
                  message.reactions.push({
                    emoji,
                    count: 1,
                    userReacted: true,
                  });
                }
                break;
              }
            }
          });
        },

        setLoading: (loading: boolean) => {
          set({ isLoading: loading });
        },

        setError: (error: string | null) => {
          set({ error });
        },
      })),
      {
        name: 'chat-storage',
        serialize: (state) => {
          return JSON.stringify({
            ...state,
            state: {
              ...state.state,
              conversations: Array.from(state.state.conversations.entries()),
            },
          });
        },
        deserialize: (str) => {
          const parsed = JSON.parse(str);
          return {
            ...parsed,
            state: {
              ...parsed.state,
              conversations: new Map(parsed.state.conversations),
            },
          };
        },
      }
    )
  )
);

export default useChatStore;
