/**
 * useConversationBranching Hook
 * 
 * Manages conversation branch state and operations.
 */

import { useState, useMemo, useCallback } from 'react';
import { Branch } from '../types/conversation';

export const useConversationBranching = (
  branches: Branch[],
  currentBranchId: string
) => {
  const [selectedBranchId, setSelectedBranchId] = useState<string | null>(null);

  // Build branch tree structure
  const branchTree = useMemo(() => {
    const tree: Record<string, Branch[]> = {};
    
    branches.forEach(branch => {
      const parentId = branch.parentId || 'root';
      if (!tree[parentId]) {
        tree[parentId] = [];
      }
      tree[parentId].push(branch);
    });

    // Sort children by creation date
    Object.keys(tree).forEach(parentId => {
      tree[parentId].sort((a, b) => 
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
      );
    });

    return tree;
  }, [branches]);

  // Get path from root to a branch
  const getBranchPath = useCallback((branchId: string): Branch[] => {
    const path: Branch[] = [];
    let currentId: string | null = branchId;

    while (currentId) {
      const branch = branches.find(b => b.id === currentId);
      if (!branch) break;
      
      path.unshift(branch);
      currentId = branch.parentId;
    }

    return path;
  }, [branches]);

  // Check if two branches can be merged
  const canMergeBranches = useCallback((sourceId: string, targetId: string): boolean => {
    if (sourceId === targetId) return false;

    const sourcePath = getBranchPath(sourceId);
    const targetPath = getBranchPath(targetId);

    // Can't merge if source is ancestor of target
    if (sourcePath.some(b => b.id === targetId)) return false;

    // Can't merge if target is ancestor of source  
    if (targetPath.some(b => b.id === sourceId)) return false;

    return true;
  }, [getBranchPath]);

  // Get common ancestor of two branches
  const getCommonAncestor = useCallback((branchId1: string, branchId2: string): Branch | null => {
    const path1 = getBranchPath(branchId1);
    const path2 = getBranchPath(branchId2);

    for (let i = Math.min(path1.length, path2.length) - 1; i >= 0; i--) {
      if (path1[i]?.id === path2[i]?.id) {
        return path1[i];
      }
    }

    return null;
  }, [getBranchPath]);

  // Get branch depth in tree
  const getBranchDepth = useCallback((branchId: string): number => {
    return getBranchPath(branchId).length - 1;
  }, [getBranchPath]);

  // Get all descendant branches
  const getDescendants = useCallback((branchId: string): Branch[] => {
    const descendants: Branch[] = [];
    const queue = [branchId];

    while (queue.length > 0) {
      const currentId = queue.shift()!;
      const children = branchTree[currentId] || [];
      
      descendants.push(...children);
      queue.push(...children.map(b => b.id));
    }

    return descendants;
  }, [branchTree]);

  return {
    selectedBranchId,
    setSelectedBranchId,
    branchTree,
    getBranchPath,
    canMergeBranches,
    getCommonAncestor,
    getBranchDepth,
    getDescendants,
  };
};
