'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import ConversationSidebar from '../components/ConversationSidebar'
import ChatInterface from '../components/ChatInterface'
import AgentRunDrawer from '../components/AgentRunDrawer'
import { Loader2 } from 'lucide-react'

export default function ChatPage() {
  const { isAuthenticated, isLoading: authLoading, checkAuth } = useAuthStore()
  const {
    activeRun,
    agentRuns,
    approveAgentAction,
    loadConversations,
    rejectAgentAction,
    selectAgentRun,
  } = useChatStore()
  const router = useRouter()

  useEffect(() => {
    checkAuth()
  }, [])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    } else if (isAuthenticated) {
      loadConversations()
    }
  }, [isAuthenticated, authLoading, router, loadConversations])

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <ConversationSidebar />
      <ChatInterface />
      <AgentRunDrawer
        runs={agentRuns}
        activeRun={activeRun}
        onSelectRun={selectAgentRun}
        onApprove={approveAgentAction}
        onReject={rejectAgentAction}
      />
    </div>
  )
}
