import { create } from 'zustand'
import api from '../lib/api'

interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  created_at?: string
  tokens_used?: number
}

interface Conversation {
  id: string
  user_id: string
  title: string
  model_name: string
  is_archived: boolean
  is_pinned: boolean
  created_at: string
  updated_at: string
  message_count: number
  messages?: Message[]
}

interface ChatStore {
  conversations: Conversation[]
  currentConversation: Conversation | null
  messages: Message[]
  isLoading: boolean
  error: string | null
  searchQuery: string
  showArchived: boolean
  
  // Actions
  loadConversations: () => Promise<void>
  createConversation: (title?: string) => Promise<Conversation>
  selectConversation: (conversationId: string) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  updateConversation: (conversationId: string, updates: any) => Promise<void>
  deleteConversation: (conversationId: string) => Promise<void>
  searchConversations: (query: string) => void
  toggleArchived: () => void
  clearError: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  error: null,
  searchQuery: '',
  showArchived: false,

  loadConversations: async () => {
    set({ isLoading: true, error: null })
    try {
      const { showArchived, searchQuery } = get()
      const conversations = await api.getConversations(showArchived, searchQuery)
      set({ conversations, isLoading: false })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to load conversations',
        isLoading: false,
      })
    }
  },

  createConversation: async (title: string = 'New Conversation') => {
    set({ isLoading: true, error: null })
    try {
      const conversation = await api.createConversation(title)
      const { conversations } = get()
      set({
        conversations: [conversation, ...conversations],
        currentConversation: conversation,
        messages: [],
        isLoading: false,
      })
      return conversation
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to create conversation',
        isLoading: false,
      })
      throw error
    }
  },

  selectConversation: async (conversationId: string) => {
    set({ isLoading: true, error: null })
    try {
      const conversation = await api.getConversation(conversationId)
      set({
        currentConversation: conversation,
        messages: conversation.messages || [],
        isLoading: false,
      })
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to load conversation',
        isLoading: false,
      })
    }
  },

  sendMessage: async (message: string) => {
    const { currentConversation, messages } = get()
    if (!currentConversation) {
      set({ error: 'No conversation selected' })
      return
    }

    // Optimistically add user message
    const userMessage: Message = {
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    }
    set({ messages: [...messages, userMessage] })

    set({ isLoading: true, error: null })
    try {
      const response = await api.sendMessage(currentConversation.id, message)
      
      // Add assistant message
      const assistantMessage: Message = {
        id: response.message.id,
        role: 'assistant',
        content: response.message.content,
        created_at: response.message.timestamp,
      }
      
      set({
        messages: [...get().messages, assistantMessage],
        isLoading: false,
      })

      // Update conversation list
      get().loadConversations()
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Failed to send message',
        isLoading: false,
      })
    }
  },

  updateConversation: async (conversationId: string, updates: any) => {
    try {
      const updatedConversation = await api.updateConversation(conversationId, updates)
      const { conversations, currentConversation } = get()
      
      set({
        conversations: conversations.map((c) =>
          c.id === conversationId ? { ...c, ...updatedConversation } : c
        ),
        currentConversation:
          currentConversation?.id === conversationId
            ? { ...currentConversation, ...updatedConversation }
            : currentConversation,
      })
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to update conversation' })
    }
  },

  deleteConversation: async (conversationId: string) => {
    try {
      await api.deleteConversation(conversationId)
      const { conversations, currentConversation } = get()
      
      set({
        conversations: conversations.filter((c) => c.id !== conversationId),
        currentConversation:
          currentConversation?.id === conversationId ? null : currentConversation,
        messages: currentConversation?.id === conversationId ? [] : get().messages,
      })
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to delete conversation' })
    }
  },

  searchConversations: (query: string) => {
    set({ searchQuery: query })
    get().loadConversations()
  },

  toggleArchived: () => {
    set({ showArchived: !get().showArchived })
    get().loadConversations()
  },

  clearError: () => set({ error: null }),
}))
