'use client'

import { useState } from 'react'
import { useChatStore } from '../store/chatStore'
import { useAuthStore } from '../store/authStore'
import {
  Plus,
  MessageSquare,
  Search,
  Archive,
  Pin,
  Trash2,
  Edit2,
  LogOut,
  User,
} from 'lucide-react'

export default function ConversationSidebar() {
  const {
    conversations,
    currentConversation,
    createConversation,
    selectConversation,
    updateConversation,
    deleteConversation,
    searchConversations,
    toggleArchived,
    showArchived,
    searchQuery,
  } = useChatStore()
  const { user, logout } = useAuthStore()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const handleCreateConversation = async () => {
    await createConversation('New Conversation')
  }

  const handleEditTitle = async (conversationId: string) => {
    if (editTitle.trim()) {
      await updateConversation(conversationId, { title: editTitle })
    }
    setEditingId(null)
  }

  const startEdit = (conversation: any) => {
    setEditingId(conversation.id)
    setEditTitle(conversation.title)
  }

  const handleTogglePin = async (conversationId: string, isPinned: boolean) => {
    await updateConversation(conversationId, { is_pinned: !isPinned })
  }

  const handleArchive = async (conversationId: string, isArchived: boolean) => {
    await updateConversation(conversationId, { is_archived: !isArchived })
  }

  const handleDelete = async (conversationId: string) => {
    if (confirm('Are you sure you want to delete this conversation?')) {
      await deleteConversation(conversationId)
    }
  }

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">Zakera AI</h2>
          <button
            onClick={handleCreateConversation}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            title="New conversation"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => searchConversations(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
        </div>

        {/* Toggle archived */}
        <button
          onClick={toggleArchived}
          className={`mt-2 w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
            showArchived
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <Archive className="w-4 h-4" />
          {showArchived ? 'Hide Archived' : 'Show Archived'}
        </button>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No conversations yet</p>
            <p className="text-sm mt-1">Create one to get started</p>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`group mb-2 p-3 rounded-lg cursor-pointer transition-colors ${
                  currentConversation?.id === conversation.id
                    ? 'bg-blue-50 border border-blue-200'
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
                onClick={() => selectConversation(conversation.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  {editingId === conversation.id ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => handleEditTitle(conversation.id)}
                      onKeyPress={(e) => e.key === 'Enter' && handleEditTitle(conversation.id)}
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        {conversation.is_pinned && <Pin className="w-3 h-3 text-blue-600" />}
                        <h3 className="font-medium text-sm truncate">{conversation.title}</h3>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {conversation.message_count} messages
                      </p>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        startEdit(conversation)
                      }}
                      className="p-1 hover:bg-gray-200 rounded"
                      title="Edit"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleTogglePin(conversation.id, conversation.is_pinned)
                      }}
                      className="p-1 hover:bg-gray-200 rounded"
                      title={conversation.is_pinned ? 'Unpin' : 'Pin'}
                    >
                      <Pin className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleArchive(conversation.id, conversation.is_archived)
                      }}
                      className="p-1 hover:bg-gray-200 rounded"
                      title={conversation.is_archived ? 'Unarchive' : 'Archive'}
                    >
                      <Archive className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(conversation.id)
                      }}
                      className="p-1 hover:bg-red-100 hover:text-red-600 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* User info */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold">
              {user?.username.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{user?.username}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
