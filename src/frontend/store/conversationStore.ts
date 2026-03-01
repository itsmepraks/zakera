/**
 * Conversation Store
 * 
 * Zustand store for conversation state management.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Conversation, Branch, Message } from '../types/conversation';

interface ConversationState {
  // State
  conversations: Conversation[];
  currentConversationId: string | null;
  currentBranchId: string | null;
  selectedMessageIds: Set<string>;
  isLoading: boolean;
  error: string | null;

  // Actions - Conversations
  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  deleteConversation: (id: string) => void;
  setCurrentConversation: (id: string | null) => void;

  // Actions - Branches
  addBranch: (conversationId: string, branch: Branch) => void;
  updateBranch: (conversationId: string, branchId: string, updates: Partial<Branch>) => void;
  deleteBranch: (conversationId: string, branchId: string) => void;
  setCurrentBranch: (branchId: string | null) => void;
  mergeBranches: (conversationId: string, sourceId: string, targetId: string) => Promise<void>;

  // Actions - Messages
  addMessage: (conversationId: string, branchId: string, message: Message) => void;
  updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => void;
  deleteMessage: (conversationId: string, messageId: string) => void;
  setSelectedMessages: (messageIds: Set<string>) => void;

  // Actions - UI
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useConversationStore = create<ConversationState>()(  
  persist(
    (set, get) => ({
      // Initial state
      conversations: [],
      currentConversationId: null,
      currentBranchId: null,
      selectedMessageIds: new Set(),
      isLoading: false,
      error: null,

      // Conversation actions
      setConversations: (conversations) => set({ conversations }),
      
      addConversation: (conversation) =>
        set((state) => ({
          conversations: [conversation, ...state.conversations],
        })),
      
      updateConversation: (id, updates) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, ...updates } : c
          ),
        })),
      
      deleteConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
          currentConversationId:
            state.currentConversationId === id ? null : state.currentConversationId,
        })),
      
      setCurrentConversation: (id) => set({ currentConversationId: id }),

      // Branch actions
      addBranch: (conversationId, branch) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, branches: [...c.branches, branch] }
              : c
          ),
        })),
      
      updateBranch: (conversationId, branchId, updates) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  branches: c.branches.map((b) =>
                    b.id === branchId ? { ...b, ...updates } : b
                  ),
                }
              : c
          ),
        })),
      
      deleteBranch: (conversationId, branchId) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  branches: c.branches.filter((b) => b.id !== branchId),
                }
              : c
          ),
        })),
      
      setCurrentBranch: (branchId) => set({ currentBranchId: branchId }),
      
      mergeBranches: async (conversationId, sourceId, targetId) => {
        // Implementation would call API
        console.log(`Merging ${sourceId} into ${targetId}`);
      },

      // Message actions
      addMessage: (conversationId, branchId, message) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messageCount: c.messageCount + 1,
                  branches: c.branches.map((b) =>
                    b.id === branchId
                      ? {
                          ...b,
                          messages: [...b.messages, message],
                          messageCount: b.messageCount + 1,
                        }
                      : b
                  ),
                }
              : c
          ),
        })),
      
      updateMessage: (conversationId, messageId, updates) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  branches: c.branches.map((b) => ({
                    ...b,
                    messages: b.messages.map((m) =>
                      m.id === messageId ? { ...m, ...updates } : m
                    ),
                  })),
                }
              : c
          ),
        })),
      
      deleteMessage: (conversationId, messageId) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messageCount: Math.max(0, c.messageCount - 1),
                  branches: c.branches.map((b) => ({
                    ...b,
                    messages: b.messages.filter((m) => m.id !== messageId),
                    messageCount: Math.max(0, b.messageCount - 1),
                  })),
                }
              : c
          ),
        })),
      
      setSelectedMessages: (messageIds) => set({ selectedMessageIds: messageIds }),

      // UI actions
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'zakera-conversation-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist these fields
        currentConversationId: state.currentConversationId,
        currentBranchId: state.currentBranchId,
      }),
    }
  )
);
