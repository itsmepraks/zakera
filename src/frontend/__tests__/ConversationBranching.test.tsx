/**
 * ConversationBranching Component Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationBranching } from '../components/conversation/ConversationBranching';
import { Branch } from '../types/conversation';

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
    name: 'Experiment',
    parentId: 'main',
    createdAt: '2026-02-15T00:00:00Z',
    lastActivity: '2026-02-20T00:00:00Z',
    messageCount: 5,
    messages: [],
  },
];

describe('ConversationBranching', () => {
  const defaultProps = {
    conversationId: 'conv-1',
    branches: mockBranches,
    currentBranchId: 'main',
    onBranchSwitch: jest.fn(),
    onBranchCreate: jest.fn(),
    onBranchMerge: jest.fn(),
    onBranchDelete: jest.fn(),
    onBranchRename: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders branch tree', () => {
    render(<ConversationBranching {...defaultProps} />);
    
    expect(screen.getByText('Main')).toBeInTheDocument();
    expect(screen.getByText('Experiment')).toBeInTheDocument();
  });

  test('shows create branch dialog', async () => {
    render(<ConversationBranching {...defaultProps} />);
    
    fireEvent.click(screen.getByText('+ New Branch'));
    
    await waitFor(() => {
      expect(screen.getByText('Create New Branch')).toBeInTheDocument();
    });
  });

  test('creates new branch', async () => {
    const onCreate = jest.fn().mockResolvedValue(undefined);
    render(<ConversationBranching {...defaultProps} onBranchCreate={onCreate} />);
    
    // Open dialog
    fireEvent.click(screen.getByText('+ New Branch'));
    
    // Enter name
    const input = screen.getByPlaceholderText('Branch name');
    fireEvent.change(input, { target: { value: 'New Branch' } });
    
    // Create
    fireEvent.click(screen.getByText('Create'));
    
    await waitFor(() => {
      expect(onCreate).toHaveBeenCalledWith({
        parentId: 'main',
        name: 'New Branch',
      });
    });
  });

  test('renames branch', async () => {
    const onRename = jest.fn().mockResolvedValue(undefined);
    render(<ConversationBranching {...defaultProps} onBranchRename={onRename} />);
    
    // Click edit button
    const editButtons = screen.getAllByTitle('Rename branch');
    fireEvent.click(editButtons[0]);
    
    // Change name
    const input = screen.getByDisplayValue('Main');
    fireEvent.change(input, { target: { value: 'Main Branch' } });
    fireEvent.blur(input);
    
    await waitFor(() => {
      expect(onRename).toHaveBeenCalledWith('main', 'Main Branch');
    });
  });

  test('deletes branch with confirmation', async () => {
    window.confirm = jest.fn(() => true);
    const onDelete = jest.fn().mockResolvedValue(undefined);
    
    render(<ConversationBranching {...defaultProps} onBranchDelete={onDelete} />);
    
    const deleteButtons = screen.getAllByTitle('Delete branch');
    fireEvent.click(deleteButtons[1]); // Delete child branch
    
    expect(window.confirm).toHaveBeenCalled();
    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith('branch-1');
    });
  });

  test('switches branch on double-click', () => {
    const onSwitch = jest.fn();
    render(<ConversationBranching {...defaultProps} onBranchSwitch={onSwitch} />);
    
    const branchItem = screen.getByText('Experiment').closest('.branch-item');
    fireEvent.doubleClick(branchItem!);
    
    expect(onSwitch).toHaveBeenCalledWith('branch-1');
  });

  test('disables delete for main branch', () => {
    render(<ConversationBranching {...defaultProps} />);
    
    const deleteButtons = screen.getAllByTitle('Delete branch');
    expect(deleteButtons[0]).toBeDisabled(); // Main branch
    expect(deleteButtons[1]).not.toBeDisabled(); // Child branch
  });

  test('shows branch metadata', () => {
    render(<ConversationBranching {...defaultProps} />);
    
    expect(screen.getByText(/10 messages/)).toBeInTheDocument();
    expect(screen.getByText(/5 messages/)).toBeInTheDocument();
  });
});
