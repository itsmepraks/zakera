/**
 * ConversationBranching Component
 * 
 * Interactive conversation branch visualization and management.
 * Displays branches as a visual tree with full CRUD operations.
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Branch, Message } from '../../types/conversation';
import { useConversationBranching } from '../../hooks/useConversationBranching';
import './ConversationBranching.css';

interface Props {
  conversationId: string;
  branches: Branch[];
  currentBranchId: string;
  onBranchSwitch: (branchId: string) => void;
  onBranchCreate: (params: { parentId: string; name: string; fromMessageId?: string }) => Promise<void>;
  onBranchMerge: (sourceId: string, targetId: string) => Promise<void>;
  onBranchDelete: (branchId: string) => Promise<void>;
  onBranchRename: (branchId: string, newName: string) => Promise<void>;
}

export const ConversationBranching: React.FC<Props> = ({
  conversationId,
  branches,
  currentBranchId,
  onBranchSwitch,
  onBranchCreate,
  onBranchMerge,
  onBranchDelete,
  onBranchRename,
}) => {
  const {
    selectedBranchId,
    setSelectedBranchId,
    branchTree,
    getBranchPath,
    canMergeBranches,
  } = useConversationBranching(branches, currentBranchId);

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');
  const [editingBranchId, setEditingBranchId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const handleCreateBranch = useCallback(async () => {
    if (!newBranchName.trim()) return;
    
    await onBranchCreate({
      parentId: selectedBranchId || currentBranchId,
      name: newBranchName,
    });
    
    setNewBranchName('');
    setShowCreateDialog(false);
  }, [newBranchName, selectedBranchId, currentBranchId, onBranchCreate]);

  const handleRenameBranch = useCallback(async (branchId: string) => {
    if (!editName.trim()) return;
    await onBranchRename(branchId, editName);
    setEditingBranchId(null);
    setEditName('');
  }, [editName, onBranchRename]);

  const renderBranchNode = useCallback((branch: Branch, depth: number = 0) => {
    const isActive = branch.id === currentBranchId;
    const isSelected = branch.id === selectedBranchId;
    const isEditing = branch.id === editingBranchId;
    const path = getBranchPath(branch.id);

    return (
      <div key={branch.id} className="branch-node" style={{ marginLeft: `${depth * 24}px` }}>
        <div
          className={`branch-item ${
            isActive ? 'active' : ''
          } ${isSelected ? 'selected' : ''}`}
          onClick={() => setSelectedBranchId(branch.id)}
          onDoubleClick={() => onBranchSwitch(branch.id)}
        >
          <div className="branch-icon">
            <svg width="16" height="16" viewBox="0 0 16 16">
              <circle cx="8" cy="8" r="4" fill={isActive ? '#3b82f6' : '#6b7280'} />
            </svg>
          </div>

          {isEditing ? (
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => handleRenameBranch(branch.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRenameBranch(branch.id);
                if (e.key === 'Escape') {
                  setEditingBranchId(null);
                  setEditName('');
                }
              }}
              autoFocus
              className="branch-name-input"
            />
          ) : (
            <div className="branch-info">
              <span className="branch-name">{branch.name}</span>
              <span className="branch-meta">
                {branch.messageCount} messages • {new Date(branch.lastActivity).toLocaleDateString()}
              </span>
            </div>
          )}

          <div className="branch-actions">
            {!isEditing && (
              <>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingBranchId(branch.id);
                    setEditName(branch.name);
                  }}
                  title="Rename branch"
                  className="branch-action-btn"
                >
                  ✏️
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete branch "${branch.name}"?`)) {
                      onBranchDelete(branch.id);
                    }
                  }}
                  title="Delete branch"
                  className="branch-action-btn"
                  disabled={branch.id === 'main'}
                >
                  🗑️
                </button>
              </>
            )}
          </div>
        </div>

        {branchTree[branch.id]?.map((childBranch) =>
          renderBranchNode(childBranch, depth + 1)
        )}
      </div>
    );
  }, [currentBranchId, selectedBranchId, editingBranchId, editName, branchTree, getBranchPath, onBranchSwitch, handleRenameBranch, onBranchDelete, setSelectedBranchId]);

  const rootBranches = useMemo(
    () => branches.filter((b) => !b.parentId),
    [branches]
  );

  return (
    <div className="conversation-branching">
      <div className="branching-header">
        <h3>Conversation Branches</h3>
        <div className="header-actions">
          <button
            onClick={() => setShowCreateDialog(true)}
            className="btn btn-primary"
            disabled={!selectedBranchId && !currentBranchId}
          >
            + New Branch
          </button>
          <button
            onClick={() => setShowMergeDialog(true)}
            className="btn btn-secondary"
            disabled={!selectedBranchId || !canMergeBranches(selectedBranchId, currentBranchId)}
          >
            Merge Branch
          </button>
        </div>
      </div>

      <div className="branch-tree">
        {rootBranches.map((branch) => renderBranchNode(branch))}
      </div>

      {/* Create Branch Dialog */}
      {showCreateDialog && (
        <div className="dialog-overlay" onClick={() => setShowCreateDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Create New Branch</h3>
            <input
              type="text"
              value={newBranchName}
              onChange={(e) => setNewBranchName(e.target.value)}
              placeholder="Branch name"
              onKeyDown={(e) => e.key === 'Enter' && handleCreateBranch()}
              autoFocus
            />
            <div className="dialog-actions">
              <button onClick={() => setShowCreateDialog(false)} className="btn">Cancel</button>
              <button onClick={handleCreateBranch} className="btn btn-primary">Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Dialog */}
      {showMergeDialog && selectedBranchId && (
        <div className="dialog-overlay" onClick={() => setShowMergeDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Merge Branch</h3>
            <p>
              Merge <strong>{branches.find(b => b.id === selectedBranchId)?.name}</strong>
              {' '}into <strong>{branches.find(b => b.id === currentBranchId)?.name}</strong>?
            </p>
            <div className="dialog-actions">
              <button onClick={() => setShowMergeDialog(false)} className="btn">Cancel</button>
              <button
                onClick={async () => {
                  await onBranchMerge(selectedBranchId, currentBranchId);
                  setShowMergeDialog(false);
                }}
                className="btn btn-primary"
              >
                Merge
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
