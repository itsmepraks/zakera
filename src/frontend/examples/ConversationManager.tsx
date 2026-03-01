/**
 * ConversationManager - Complete Integration Example
 * 
 * This example demonstrates how to integrate all conversation management
 * features into a complete application.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { ConversationListEnhanced } from '../components/conversation/ConversationListEnhanced';
import { ConversationBranching } from '../components/conversation/ConversationBranching';
import { ConversationTimeline } from '../components/conversation/ConversationTimeline';
import { useConversationStore } from '../store/conversationStore';
import { Conversation, Branch, ConversationFilter, ConversationSort } from '../types/conversation';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

export const ConversationManager: React.FC = () => {
  // Global state
  const {
    conversations,
    currentConversationId,
    setConversations,
    setCurrentConversation,
    addConversation,
    updateConversation,
    deleteConversation,
  } = useConversationStore();

  // Local state
  const [filter, setFilter] = useState<ConversationFilter>({});
  const [showBranches, setShowBranches] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Get current conversation
  const currentConversation = conversations.find(
    c => c.id === currentConversationId
  );

  // Load conversations from API
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/conversations`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      setConversations(response.data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle conversation selection
  const handleSelectConversation = useCallback((conversation: Conversation) => {
    setCurrentConversation(conversation.id);
  }, [setCurrentConversation]);

  // Handle conversation actions
  const handleConversationAction = useCallback(async (
    action: string,
    conversation: Conversation
  ) => {
    try {
      switch (action) {
        case 'create':
          const newConv = await axios.post(
            `${API_BASE}/conversations`,
            { title: 'New Conversation' },
            { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
          );
          addConversation(newConv.data);
          break;

        case 'delete':
          await axios.delete(
            `${API_BASE}/conversations/${conversation.id}`,
            { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
          );
          deleteConversation(conversation.id);
          break;

        case 'archive':
          await axios.patch(
            `${API_BASE}/conversations/${conversation.id}`,
            { status: 'archived' },
            { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
          );
          updateConversation(conversation.id, { status: 'archived' });
          break;

        case 'pin':
          updateConversation(conversation.id, {
            metadata: { ...conversation.metadata, pinned: !conversation.metadata?.pinned },
          });
          break;

        case 'star':
          updateConversation(conversation.id, {
            metadata: { ...conversation.metadata, starred: !conversation.metadata?.starred },
          });
          break;

        default:
          console.log(`Action ${action} not implemented`);
      }
    } catch (error) {
      console.error(`Action ${action} failed:`, error);
    }
  }, [addConversation, updateConversation, deleteConversation]);

  // Branch operations
  const handleBranchCreate = async (params: {
    parentId: string;
    name: string;
    fromMessageId?: string;
  }) => {
    if (!currentConversation) return;

    try {
      const response = await axios.post(
        `${API_BASE}/conversations/${currentConversation.id}/branches`,
        params,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      // Update local state with new branch
      const newBranch = response.data;
      updateConversation(currentConversation.id, {
        branches: [...currentConversation.branches, newBranch],
      });
    } catch (error) {
      console.error('Failed to create branch:', error);
    }
  };

  const handleBranchSwitch = (branchId: string) => {
    if (!currentConversation) return;
    updateConversation(currentConversation.id, { currentBranchId: branchId });
  };

  const handleBranchMerge = async (sourceId: string, targetId: string) => {
    if (!currentConversation) return;

    try {
      await axios.post(
        `${API_BASE}/conversations/${currentConversation.id}/branches/merge`,
        { sourceId, targetId },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      // Reload conversation to get merged state
      await loadConversations();
    } catch (error) {
      console.error('Failed to merge branches:', error);
    }
  };

  const handleBranchDelete = async (branchId: string) => {
    if (!currentConversation) return;

    try {
      await axios.delete(
        `${API_BASE}/conversations/${currentConversation.id}/branches/${branchId}`,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      // Update local state
      updateConversation(currentConversation.id, {
        branches: currentConversation.branches.filter(b => b.id !== branchId),
      });
    } catch (error) {
      console.error('Failed to delete branch:', error);
    }
  };

  const handleBranchRename = async (branchId: string, newName: string) => {
    if (!currentConversation) return;

    try {
      await axios.patch(
        `${API_BASE}/conversations/${currentConversation.id}/branches/${branchId}`,
        { name: newName },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      // Update local state
      updateConversation(currentConversation.id, {
        branches: currentConversation.branches.map(b =>
          b.id === branchId ? { ...b, name: newName } : b
        ),
      });
    } catch (error) {
      console.error('Failed to rename branch:', error);
    }
  };

  return (
    <div className="conversation-manager">
      {/* Left Sidebar - Conversation List */}
      <div className="sidebar">
        <ConversationListEnhanced
          conversations={conversations}
          onConversationSelect={handleSelectConversation}
          onConversationAction={handleConversationAction}
          filter={filter}
          onFilterChange={setFilter}
        />
      </div>

      {/* Main Content - Current Conversation */}
      <div className="main-content">
        {currentConversation ? (
          <>
            {/* Conversation messages would go here */}
            <div className="conversation-view">
              <h2>{currentConversation.title}</h2>
              {/* Message list component */}
            </div>

            {/* Branch Tree (Toggle) */}
            {showBranches && (
              <div className="branch-panel">
                <ConversationBranching
                  conversationId={currentConversation.id}
                  branches={currentConversation.branches}
                  currentBranchId={currentConversation.currentBranchId}
                  onBranchSwitch={handleBranchSwitch}
                  onBranchCreate={handleBranchCreate}
                  onBranchMerge={handleBranchMerge}
                  onBranchDelete={handleBranchDelete}
                  onBranchRename={handleBranchRename}
                />
              </div>
            )}

            {/* Timeline (Toggle) */}
            {showTimeline && (
              <div className="timeline-panel">
                <ConversationTimeline
                  messages={currentConversation.branches.find(
                    b => b.id === currentConversation.currentBranchId
                  )?.messages || []}
                  branches={currentConversation.branches}
                  currentBranchId={currentConversation.currentBranchId}
                  onMessageSelect={(msgId) => console.log('Selected message:', msgId)}
                  onBranchSwitch={handleBranchSwitch}
                />
              </div>
            )}
          </>
        ) : (
          <div className="no-conversation-selected">
            <p>Select a conversation to get started</p>
          </div>
        )}
      </div>

      {/* Floating Action Buttons */}
      <div className="fab-container">
        <button
          onClick={() => setShowBranches(!showBranches)}
          className="fab"
          title="Toggle branches (⌘B)"
          aria-label="Toggle branch tree"
        >
          🌳
        </button>
        <button
          onClick={() => setShowTimeline(!showTimeline)}
          className="fab"
          title="Toggle timeline (⌘T)"
          aria-label="Toggle timeline"
        >
          ⏱️
        </button>
      </div>
    </div>
  );
};
