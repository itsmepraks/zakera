'use client'

import { useMemo, useState, useRef, useEffect } from 'react'
import { Send, Plus, MessageSquare } from 'lucide-react'
import ChatMessage from './ChatMessage'
import { useChatStore } from '../store/chatStore'
import AgentThinkingPanel from '../../components/AgentThinkingPanel'
import type { AgentThinkingStatus, ThinkingStep } from '../../hooks/useAgentThinking'

export default function ChatInterface() {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  const {
    messages,
    currentConversation,
    isLoading,
    activityEvents,
    createConversation,
    sendMessage,
  } = useChatStore()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!currentConversation) {
      createConversation()
    }
  }, [currentConversation, createConversation])

  const activitySteps = useMemo<ThinkingStep[]>(() => {
    const steps = new Map<string, ThinkingStep>()

    for (const event of activityEvents) {
      if (!event.step_id) continue

      if (event.type === 'agent.step.begin') {
        steps.set(event.step_id, {
          id: event.step_id,
          label: event.label || 'Agent activity',
          detail: event.detail,
          status: 'active',
          startedAt: Date.now(),
          finishedAt: 0,
          tool: event.tool,
        })
      }

      if (event.type === 'agent.step.done' || event.type === 'agent.step.error') {
        const existing = steps.get(event.step_id)
        steps.set(event.step_id, {
          id: event.step_id,
          label: event.label || existing?.label || 'Agent activity',
          detail: event.detail || event.error || existing?.detail,
          status: event.type === 'agent.step.error' ? 'error' : 'done',
          startedAt: existing?.startedAt || Date.now(),
          finishedAt: Date.now(),
          tool: event.tool || existing?.tool,
          tokens: typeof event.usage?.total_tokens === 'number' ? event.usage.total_tokens : existing?.tokens,
        })
      }
    }

    return Array.from(steps.values())
  }, [activityEvents])

  const activityStatus = useMemo<AgentThinkingStatus>(() => {
    if (isLoading) return 'thinking'
    if (activityEvents.some((event) => event.type === 'agent.error')) return 'error'
    if (activityEvents.some((event) => event.type === 'agent.done')) return 'done'
    return activitySteps.length ? 'done' : 'idle'
  }, [activityEvents, activitySteps.length, isLoading])

  const handleSend = async () => {
    if (!input.trim() || !currentConversation) return

    const userMessage = input.trim()
    setInput('')
    await sendMessage(userMessage)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col flex-1 min-w-0 h-screen bg-white overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-6 h-6" />
          <h2 className="text-lg font-semibold">Chat with Zakera</h2>
        </div>
        <button 
          onClick={() => createConversation()}
          className="flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm">New Chat</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <AgentThinkingPanel
          steps={activitySteps}
          status={activityStatus}
          elapsedLabel=""
          activeStepIndex={activitySteps.findIndex((step) => step.status === 'active')}
          defaultExpanded={isLoading}
        />
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Start a conversation with Zakera</p>
              <p className="text-sm mt-2">Ask me anything!</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <ChatMessage key={index} message={message} />
          ))
        )}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-sm font-semibold">
              Z
            </div>
            <div className="typing-indicator flex gap-1 mt-2">
              <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
              <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
              <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 bg-gray-50">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
