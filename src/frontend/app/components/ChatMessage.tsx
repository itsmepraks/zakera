'use client'

import { useState } from 'react'
import { format } from 'date-fns'
import { User, Bot, Copy, Check } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  created_at?: string
}

interface ChatMessageProps {
  message: Message
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch (error) {
      console.error('Failed to copy message:', error)
    }
  }
  
  return (
    <div className={`chat-message flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-semibold flex-shrink-0 ${
        isUser 
          ? 'bg-gradient-to-br from-green-500 to-teal-500' 
          : 'bg-gradient-to-br from-blue-500 to-purple-500'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      
      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`group relative px-4 py-3 pr-10 rounded-2xl ${
          isUser 
            ? 'bg-gradient-to-br from-green-500 to-teal-500 text-white rounded-br-sm' 
            : 'bg-gray-100 text-gray-900 rounded-bl-sm'
        }`}>
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Copy message"
            title="Copy message"
            className={`absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center rounded-md transition-opacity hover:bg-black/10 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              isUser ? 'text-white/80 hover:text-white focus:ring-white/70' : 'text-gray-500 hover:text-gray-700 focus:ring-gray-400'
            }`}
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </button>
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <span className="text-xs text-gray-400 mt-1 px-2">
          {format(new Date(message.timestamp || message.created_at || Date.now()), 'HH:mm')}
        </span>
      </div>
    </div>
  )
}
