/**
 * Tests for ConversationSearch component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConversationSearch } from '../components/ConversationSearch';

describe('ConversationSearch', () => {
  const mockOnSearch = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders search input', () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    expect(screen.getByPlaceholderText(/search conversations/i)).toBeInTheDocument();
  });

  it('updates query on input change', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText(/search conversations/i) as HTMLInputElement;
    
    await userEvent.type(input, 'test query');
    expect(input.value).toBe('test query');
  });

  it('calls onSearch with debounced query', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText(/search conversations/i);
    
    await userEvent.type(input, 'test');
    
    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith(
        'test',
        expect.any(Object)
      );
    }, { timeout: 500 });
  });

  it('shows clear button when query is present', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText(/search conversations/i);
    
    await userEvent.type(input, 'test');
    
    expect(screen.getByLabelText(/clear search/i)).toBeInTheDocument();
  });

  it('clears query when clear button is clicked', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText(/search conversations/i) as HTMLInputElement;
    
    await userEvent.type(input, 'test');
    expect(input.value).toBe('test');
    
    const clearButton = screen.getByLabelText(/clear search/i);
    await userEvent.click(clearButton);
    
    expect(input.value).toBe('');
    expect(mockOnSearch).toHaveBeenCalledWith('', {});
  });

  it('toggles filters panel when filter button is clicked', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const filterButton = screen.getByLabelText(/toggle filters/i);
    
    await userEvent.click(filterButton);
    expect(screen.getByText(/advanced filters/i)).toBeInTheDocument();
    
    await userEvent.click(filterButton);
    expect(screen.queryByText(/advanced filters/i)).not.toBeInTheDocument();
  });

  it('shows filter count badge when filters are active', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const filterButton = screen.getByLabelText(/toggle filters/i);
    
    await userEvent.click(filterButton);
    
    // Select a model filter
    const gpt4Button = screen.getByText('GPT-4');
    await userEvent.click(gpt4Button);
    
    const applyButton = screen.getByText(/apply filters/i);
    await userEvent.click(applyButton);
    
    // Check for badge (this is a simplified check)
    expect(filterButton).toHaveClass(/bg-blue-100|bg-blue-900/i);
  });

  it('displays keyboard shortcut hint', () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    expect(screen.getByText('K')).toBeInTheDocument();
  });

  it('focuses input on keyboard shortcut', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText(/search conversations/i);
    
    fireEvent.keyDown(document, { key: 'k', metaKey: true });
    
    await waitFor(() => {
      expect(input).toHaveFocus();
    });
  });

  it('clears search on Escape key', async () => {
    render(<ConversationSearch onSearch={mockOnSearch} />);
    const input = screen.getByPlaceholderText(/search conversations/i) as HTMLInputElement;
    
    await userEvent.type(input, 'test');
    expect(input.value).toBe('test');
    
    fireEvent.keyDown(input, { key: 'Escape' });
    
    await waitFor(() => {
      expect(input.value).toBe('');
    });
  });
});
