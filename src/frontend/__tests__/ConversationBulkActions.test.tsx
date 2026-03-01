/**
 * ConversationBulkActions Component Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConversationBulkActions } from '../components/conversation/ConversationBulkActions';
import { Conversation } from '../types/conversation';

const mockConversations: Conversation[] = [
  {
    id: 'conv-1',
    title: 'Test Conversation 1',
    userId: 'user-1',
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-02-28T00:00:00Z',
    messageCount: 10,
    currentBranchId: 'main',
    branches: [],
    tags: ['test'],
    status: 'active',
  },
  {
    id: 'conv-2',
    title: 'Test Conversation 2',
    userId: 'user-1',
    createdAt: '2026-02-01T00:00:00Z',
    updatedAt: '2026-02-28T00:00:00Z',
    messageCount: 5,
    currentBranchId: 'main',
    branches: [],
    tags: [],
    status: 'active',
  },
];

describe('ConversationBulkActions', () => {
  const defaultProps = {
    conversations: mockConversations,
    selectedIds: new Set(['conv-1']),
    onSelectionChange: jest.fn(),
    onBulkDelete: jest.fn().mockResolvedValue(undefined),
    onBulkArchive: jest.fn().mockResolvedValue(undefined),
    onBulkExport: jest.fn().mockResolvedValue(undefined),
    onBulkTag: jest.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders when items selected', () => {
    render(<ConversationBulkActions {...defaultProps} />);
    expect(screen.getByText('1 selected')).toBeInTheDocument();
  });

  test('does not render when no items selected', () => {
    render(
      <ConversationBulkActions
        {...defaultProps}
        selectedIds={new Set()}
      />
    );
    expect(screen.queryByText('selected')).not.toBeInTheDocument();
  });

  test('bulk delete with confirmation', async () => {
    window.confirm = jest.fn(() => true);
    const onDelete = jest.fn().mockResolvedValue(undefined);
    
    render(
      <ConversationBulkActions {...defaultProps} onBulkDelete={onDelete} />
    );
    
    fireEvent.click(screen.getByText(/Delete/));
    
    expect(window.confirm).toHaveBeenCalledWith('Delete 1 conversation(s)?');
    
    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith(['conv-1']);
    });
  });

  test('bulk archive', async () => {
    const onArchive = jest.fn().mockResolvedValue(undefined);
    
    render(
      <ConversationBulkActions {...defaultProps} onBulkArchive={onArchive} />
    );
    
    fireEvent.click(screen.getByText(/Archive/));
    
    await waitFor(() => {
      expect(onArchive).toHaveBeenCalledWith(['conv-1']);
    });
  });

  test('bulk export with format selection', async () => {
    const onExport = jest.fn().mockResolvedValue(undefined);
    
    render(
      <ConversationBulkActions {...defaultProps} onBulkExport={onExport} />
    );
    
    // Open export menu
    fireEvent.click(screen.getByText(/Export/));
    
    // Select JSON format
    fireEvent.click(screen.getByText('Export as JSON'));
    
    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith(['conv-1'], 'json');
    });
  });

  test('bulk tag with dialog', async () => {
    const onTag = jest.fn().mockResolvedValue(undefined);
    
    render(
      <ConversationBulkActions {...defaultProps} onBulkTag={onTag} />
    );
    
    // Open tag dialog
    fireEvent.click(screen.getByText(/Tag/));
    
    // Enter tags
    const input = screen.getByPlaceholderText(/Enter tags/);
    fireEvent.change(input, { target: { value: 'important, work' } });
    
    // Submit
    fireEvent.click(screen.getByText('Add Tags'));
    
    await waitFor(() => {
      expect(onTag).toHaveBeenCalledWith(['conv-1'], ['important', 'work']);
    });
  });

  test('clears selection', () => {
    const onChange = jest.fn();
    
    render(
      <ConversationBulkActions {...defaultProps} onSelectionChange={onChange} />
    );
    
    const clearButton = screen.getByTitle('Clear selection');
    fireEvent.click(clearButton);
    
    expect(onChange).toHaveBeenCalledWith(new Set());
  });

  test('shows processing state', async () => {
    const onDelete = jest.fn(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );
    
    window.confirm = jest.fn(() => true);
    
    render(
      <ConversationBulkActions {...defaultProps} onBulkDelete={onDelete} />
    );
    
    fireEvent.click(screen.getByText(/Delete/));
    
    await waitFor(() => {
      expect(screen.getByText(/Processing/)).toBeInTheDocument();
    });
  });

  test('disables actions during processing', async () => {
    const onDelete = jest.fn(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );
    
    window.confirm = jest.fn(() => true);
    
    render(
      <ConversationBulkActions {...defaultProps} onBulkDelete={onDelete} />
    );
    
    const deleteBtn = screen.getByText(/Delete/);
    fireEvent.click(deleteBtn);
    
    // Button should be disabled during operation
    expect(deleteBtn).toBeDisabled();
  });
});
