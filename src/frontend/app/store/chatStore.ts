import { create } from 'zustand'
import api, { AgentRun, AgentStreamEvent } from '../lib/api'

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
  agentRuns: AgentRun[]
  activeRun: AgentRun | null
  activityEvents: AgentStreamEvent[]
  isLoading: boolean
  error: string | null
  searchQuery: string
  showArchived: boolean
  
  // Actions
  loadConversations: () => Promise<void>
  createConversation: (title?: string) => Promise<Conversation>
  selectConversation: (conversationId: string) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  loadAgentRuns: (conversationId?: string) => Promise<void>
  selectAgentRun: (runId: string) => Promise<void>
  approveAgentAction: (runId: string, approvalId: string) => Promise<void>
  rejectAgentAction: (runId: string, approvalId: string) => Promise<void>
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
  agentRuns: [],
  activeRun: null,
  activityEvents: [],
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
        agentRuns: [],
        activeRun: null,
        activityEvents: [],
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
        activityEvents: [],
        isLoading: false,
      })
      get().loadAgentRuns(conversation.id)
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
      let assistantContent = ''
      let activeRunId: string | undefined
      set({ activityEvents: [] })

      await api.streamMessage(currentConversation.id, message, {
        toolsEnabled: true,
        onEvent: (event) => {
          if (event.run_id) activeRunId = event.run_id
          if (event.type.startsWith('agent.')) {
            set({ activityEvents: [...get().activityEvents, event] })
          }
          if (event.type === 'agent.response.chunk') {
            assistantContent += event.chunk || ''
          }
        },
      })
      
      if (!assistantContent) {
        const approval = get().activityEvents.find((event) => event.type === 'agent.approval.required')
        const error = get().activityEvents.find((event) => event.type === 'agent.error')
        assistantContent = approval
          ? 'Approval required before Zakera can continue this run.'
          : error?.error
            ? `Zakera hit an error: ${error.error}`
            : 'Zakera finished without returning a message.'
      }
      
      set({
        messages: [
          ...get().messages,
          {
            role: 'assistant',
            content: assistantContent,
            created_at: new Date().toISOString(),
          },
        ],
        isLoading: false,
      })

      // Update conversation list
      get().loadConversations()
      if (activeRunId) {
        await get().selectAgentRun(activeRunId)
      }
      await get().loadAgentRuns(currentConversation.id)
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || error.message || 'Failed to send message',
        isLoading: false,
      })
    }
  },

  loadAgentRuns: async (conversationId?: string) => {
    const id = conversationId || get().currentConversation?.id
    if (!id) return
    try {
      const agentRuns = await api.getAgentRuns(id)
      set({ agentRuns })
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to load agent runs' })
    }
  },

  selectAgentRun: async (runId: string) => {
    try {
      const activeRun = await api.getAgentRun(runId)
      set({ activeRun })
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to load agent run' })
    }
  },

  approveAgentAction: async (runId: string, approvalId: string) => {
    try {
      const result = await api.approveAgentAction(runId, approvalId)
      set({ activeRun: result.run })
      if (result.content) {
        set({
          messages: [
            ...get().messages,
            {
              role: 'assistant',
              content: result.content,
              created_at: new Date().toISOString(),
            },
          ],
        })
      }
      await get().loadAgentRuns(result.run.conversation_id)
      get().loadConversations()
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to approve action' })
    }
  },

  rejectAgentAction: async (runId: string, approvalId: string) => {
    try {
      const result = await api.rejectAgentAction(runId, approvalId)
      set({ activeRun: result.run })
      await get().loadAgentRuns(result.run.conversation_id)
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to reject action' })
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
        agentRuns: currentConversation?.id === conversationId ? [] : get().agentRuns,
        activeRun: currentConversation?.id === conversationId ? null : get().activeRun,
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
