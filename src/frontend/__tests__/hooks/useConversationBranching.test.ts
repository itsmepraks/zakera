/**
 * useConversationBranching Hook Tests
 */

import { renderHook, act } from '@testing-library/react-hooks';
import { useConversationBranching } from '../../hooks/useConversationBranching';
import { Branch } from '../../types/conversation';

const mockBranches: Branch[] = [
  {
    id: 'main',
    conversationId: 'conv-1',
    name: 'Main',
    parentId: null,
    createdAt: '2026-01-01T00:00:00Z',
    lastActivity: '2026-02-28T00:00:00Z',
    messageCount: 10,
    messages: [],
  },
  {
    id: 'branch-1',
    conversationId: 'conv-1',
    name: 'Branch 1',
    parentId: 'main',
    createdAt: '2026-02-15T00:00:00Z',
    lastActivity: '2026-02-20T00:00:00Z',
    messageCount: 5,
    messages: [],
  },
  {
    id: 'branch-2',
    conversationId: 'conv-1',
    name: 'Branch 2',
    parentId: 'branch-1',
    createdAt: '2026-02-20T00:00:00Z',
    lastActivity: '2026-02-25T00:00:00Z',
    messageCount: 3,
    messages: [],
  },
];

describe('useConversationBranching', () => {
  test('builds branch tree correctly', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    expect(result.current.branchTree).toHaveProperty('root');
    expect(result.current.branchTree).toHaveProperty('main');
    expect(result.current.branchTree.root).toHaveLength(1);
    expect(result.current.branchTree.main).toHaveLength(1);
  });

  test('gets branch path correctly', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    const path = result.current.getBranchPath('branch-2');
    
    expect(path).toHaveLength(3);
    expect(path[0].id).toBe('main');
    expect(path[1].id).toBe('branch-1');
    expect(path[2].id).toBe('branch-2');
  });

  test('calculates branch depth correctly', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    expect(result.current.getBranchDepth('main')).toBe(0);
    expect(result.current.getBranchDepth('branch-1')).toBe(1);
    expect(result.current.getBranchDepth('branch-2')).toBe(2);
  });

  test('checks if branches can merge', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    // Can merge siblings
    expect(result.current.canMergeBranches('branch-1', 'main')).toBe(true);
    
    // Cannot merge branch with itself
    expect(result.current.canMergeBranches('main', 'main')).toBe(false);
    
    // Cannot merge parent into child
    expect(result.current.canMergeBranches('main', 'branch-1')).toBe(false);
  });

  test('finds common ancestor', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    const ancestor = result.current.getCommonAncestor('branch-1', 'branch-2');
    
    expect(ancestor?.id).toBe('branch-1');
  });

  test('gets all descendants', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    const descendants = result.current.getDescendants('main');
    
    expect(descendants).toHaveLength(2);
    expect(descendants.map(b => b.id)).toContain('branch-1');
    expect(descendants.map(b => b.id)).toContain('branch-2');
  });

  test('updates selected branch', () => {
    const { result } = renderHook(() =>
      useConversationBranching(mockBranches, 'main')
    );

    expect(result.current.selectedBranchId).toBeNull();

    act(() => {
      result.current.setSelectedBranchId('branch-1');
    });

    expect(result.current.selectedBranchId).toBe('branch-1');
  });
});
