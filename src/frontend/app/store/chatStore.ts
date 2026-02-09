import { create } from 'zustand'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface ChatStore {
  messages: Message[]
  conversationId: string | null
  addMessage: (message: Message) => void
  clearMessages: () => void
  createConversation: () => Promise<void>
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  conversationId: null,
  
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  
  clearMessages: () => set({ messages: [] }),
  
  createConversation: async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Conversation' })
      })
      
      const data = await response.json()
      set({ conversationId: data.id, messages: [] })
    } catch (error) {
      console.error('Error creating conversation:', error)
    }
  }
}))
