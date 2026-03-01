/**
 * QuickActionsMenu Component Tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QuickActionsMenu } from '../components/conversation/QuickActionsMenu';

const mockActions = [
  {
    id: 'new-conversation',
    label: 'New Conversation',
    description: 'Start a new chat',
    icon: '➕',
    category: 'Conversations',
    handler: jest.fn(),
    keywords: ['create', 'start'],
  },
  {
    id: 'search',
    label: 'Search',
    description: 'Find conversations',
    icon: '🔍',
    category: 'Navigation',
    shortcut: '⌘F',
    handler: jest.fn(),
    keywords: ['find', 'locate'],
  },
];

describe('QuickActionsMenu', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders when open', () => {
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={true}
        onClose={jest.fn()}
      />
    );
    
    expect(screen.getByPlaceholderText(/Type a command/)).toBeInTheDocument();
    expect(screen.getByText('New Conversation')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
  });

  test('does not render when closed', () => {
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={false}
        onClose={jest.fn()}
      />
    );
    
    expect(screen.queryByPlaceholderText(/Type a command/)).not.toBeInTheDocument();
  });

  test('filters actions by search query', () => {
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={true}
        onClose={jest.fn()}
      />
    );
    
    const input = screen.getByPlaceholderText(/Type a command/);
    fireEvent.change(input, { target: { value: 'search' } });
    
    expect(screen.getByText('Search')).toBeInTheDocument();
    expect(screen.queryByText('New Conversation')).not.toBeInTheDocument();
  });

  test('executes action on click', async () => {
    const handler = jest.fn();
    const actionsWithHandler = [
      { ...mockActions[0], handler },
    ];
    
    const onClose = jest.fn();
    
    render(
      <QuickActionsMenu
        actions={actionsWithHandler}
        isOpen={true}
        onClose={onClose}
      />
    );
    
    fireEvent.click(screen.getByText('New Conversation'));
    
    expect(handler).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  test('navigates with arrow keys', () => {
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={true}
        onClose={jest.fn()}
      />
    );
    
    const menu = screen.getByPlaceholderText(/Type a command/).closest('.quick-actions-menu');
    
    // Arrow down should select next
    fireEvent.keyDown(menu!, { key: 'ArrowDown' });
    // First item should be selected (visual indication)
    
    // Arrow up should select previous
    fireEvent.keyDown(menu!, { key: 'ArrowUp' });
  });

  test('executes selected action on Enter', () => {
    const handler = jest.fn();
    const actionsWithHandler = [
      { ...mockActions[0], handler },
    ];
    
    render(
      <QuickActionsMenu
        actions={actionsWithHandler}
        isOpen={true}
        onClose={jest.fn()}
      />
    );
    
    const menu = screen.getByPlaceholderText(/Type a command/).closest('.quick-actions-menu');
    
    // Press Enter on first item
    fireEvent.keyDown(menu!, { key: 'Enter' });
    
    expect(handler).toHaveBeenCalled();
  });

  test('closes on Escape', () => {
    const onClose = jest.fn();
    
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={true}
        onClose={onClose}
      />
    );
    
    const menu = screen.getByPlaceholderText(/Type a command/).closest('.quick-actions-menu');
    fireEvent.keyDown(menu!, { key: 'Escape' });
    
    expect(onClose).toHaveBeenCalled();
  });

  test('shows shortcuts', () => {
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={true}
        onClose={jest.fn()}
      />
    );
    
    expect(screen.getByText('⌘F')).toBeInTheDocument();
  });

  test('groups actions by category', () => {
    render(
      <QuickActionsMenu
        actions={mockActions}
        isOpen={true}
        onClose={jest.fn()}
      />
    );
    
    expect(screen.getByText('Conversations')).toBeInTheDocument();
    expect(screen.getByText('Navigation')).toBeInTheDocument();
  });
});
