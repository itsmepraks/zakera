/**
 * Tests for MessageSearch component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MessageSearch from '../../src/frontend/components/MessageSearch';

const mockMessages = [
  { id: '1', role: 'user' as const, content: 'Hello, how are you?' },
  { id: '2', role: 'assistant' as const, content: 'I am doing well, thank you!' },
  { id: '3', role: 'user' as const, content: 'What is the weather like?' },
];

describe('MessageSearch', () => {
  const mockOnResultSelect = jest.fn();

  beforeEach(() => {
    mockOnResultSelect.mockClear();
  });

  it('shows search toggle button initially', () => {
    render(
      <MessageSearch 
        messages={mockMessages} 
        onResultSelect={mockOnResultSelect} 
      />
    );

    expect(screen.getByLabelText(/Open search/)).toBeInTheDocument();
  });

  it('opens search bar when toggle button is clicked', () => {
    render(
      <MessageSearch 
        messages={mockMessages} 
        onResultSelect={mockOnResultSelect} 
      />
    );

    fireEvent.click(screen.getByLabelText(/Open search/));
    expect(screen.getByPlaceholderText(/Search in conversation/)).toBeInTheDocument();
  });

  it('performs search and shows results count', async () => {
    render(
      <MessageSearch 
        messages={mockMessages} 
        onResultSelect={mockOnResultSelect} 
      />
    );

    fireEvent.click(screen.getByLabelText(/Open search/));
    const searchInput = screen.getByPlaceholderText(/Search in conversation/);
    
    fireEvent.change(searchInput, { target: { value: 'hello' } });

    await waitFor(() => {
      expect(screen.getByText(/1 \/ 1/)).toBeInTheDocument();
    }, { timeout: 500 });
  });

  it('shows "No results" when search has no matches', async () => {
    render(
      <MessageSearch 
        messages={mockMessages} 
        onResultSelect={mockOnResultSelect} 
      />
    );

    fireEvent.click(screen.getByLabelText(/Open search/));
    const searchInput = screen.getByPlaceholderText(/Search in conversation/);
    
    fireEvent.change(searchInput, { target: { value: 'xyz123' } });

    await waitFor(() => {
      expect(screen.getByText(/No results/)).toBeInTheDocument();
    }, { timeout: 500 });
  });

  it('clears search when clear button is clicked', async () => {
    render(
      <MessageSearch 
        messages={mockMessages} 
        onResultSelect={mockOnResultSelect} 
      />
    );

    fireEvent.click(screen.getByLabelText(/Open search/));
    const searchInput = screen.getByPlaceholderText(/Search in conversation/) as HTMLInputElement;
    
    fireEvent.change(searchInput, { target: { value: 'hello' } });

    await waitFor(() => {
      expect(searchInput.value).toBe('hello');
    });

    fireEvent.click(screen.getByLabelText(/Clear search/));
    expect(searchInput.value).toBe('');
  });

  it('navigates between search results', async () => {
    const messagesWithMultipleMatches = [
      { id: '1', role: 'user' as const, content: 'test message' },
      { id: '2', role: 'assistant' as const, content: 'another test' },
      { id: '3', role: 'user' as const, content: 'final test' },
    ];

    render(
      <MessageSearch 
        messages={messagesWithMultipleMatches} 
        onResultSelect={mockOnResultSelect} 
      />
    );

    fireEvent.click(screen.getByLabelText(/Open search/));
    const searchInput = screen.getByPlaceholderText(/Search in conversation/);
    
    fireEvent.change(searchInput, { target: { value: 'test' } });

    await waitFor(() => {
      expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
    }, { timeout: 500 });

    // Navigate to next result
    fireEvent.click(screen.getByLabelText(/Next result/));
    
    await waitFor(() => {
      expect(screen.getByText(/2 \/ 3/)).toBeInTheDocument();
    });
  });
});
