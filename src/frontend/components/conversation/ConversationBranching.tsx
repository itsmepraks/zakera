/**
 * ConversationBranching Component
 * 
 * Provides an interactive visual interface for managing conversation branches.
 * Features:
 * - Visual tree representation of conversation branches
 * - Interactive branch creation, merging, and deletion
 * - Branch switching with smooth transitions
 * - Branch comparison and diffing
 * - Drag-and-drop branch reordering
 * - Branch metadata (creation time, message count, last activity)
 * 
 * @component
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './ConversationBranching.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  branchPoint?: boolean;
}

interface Branch {
  id: string;
  name: string;
  parentId: string | null;
  createdAt: string;
  lastActivity: string;
  messageCount: number;
  messages: Message[];
  metadata?: {
    model?: string;
    tags?: string[];
    description?: string;
  };
}

interface ConversationBranchingProps {
  conversationId: string;
  branches: Branch[];
  currentBranchId: string;
  onBranchSwitch: (branchId: string) => void;
  onBranchCreate: (fromBranchId: string, name: string, atMessageId?: string) => void;
  onBranchMerge: (sourceBranchId: string, targetBranchId: string) => void;
  onBranchDelete: (branchId: string) => void;
  onBranchRename: (branchId: string, newName: string) => void;
  className?: string;
}

export const ConversationBranching: React.FC<ConversationBranchingProps> = ({
  conversationId,
  branches,
  currentBranchId,
  onBranchSwitch,
  onBranchCreate,
  onBranchMerge,
  onBranchDelete,
  onBranchRename,
  className = '',
}) => {
  const [viewMode, setViewMode] = useState<'tree' | 'list' | 'timeline'>('tree');
  const [selectedBranchId, setSelectedBranchId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');
  const [mergeSour