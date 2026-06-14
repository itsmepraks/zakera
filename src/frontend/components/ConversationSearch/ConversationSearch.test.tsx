/**
 * ConversationSearch.test.tsx
 * ============================
 * Jest + React Testing Library tests for the ConversationSearch component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConversationSearch, { Conversation } from './ConversationSearch';

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const MOCK_CONVERSATIONS: Conversation[] = [
  {
    id: 'conv-1',
    title: 'React hooks deep dive',
    lastMessage: 'Can you explain the rules of hooks in detail?',
    updatedAt: new Date(Date.now() - 3600_000).toISOString(), // 1 hour ago
    model: 'gpt-4o',
  },
  {
    id: 'conv-2',
    title: 'Python async best practices',
    lastMessage: 'What is the difference between asyncio and threading?',
    updatedAt: new Date(Date.now() - 86400_000).toISOString(), // 1 day ago
    model: 'claude-3-sonnet',
  },
  {
    id: 'conv-3',
    title: 'Docker compose networking',
    lastMessage: 'How do I connect two services in the same compose file?',
    updatedAt: new Date(Date.now() - 7200_000).toISOString(), // 2 hours ago
    model: 'gemini-1.5-pro',
  },
  {
    id: 'conv-4',
    title: 'SQL query optimisation',
    lastMessage: 'My JOIN query is slow on 10 million rows, any suggestions?',
    updatedAt: new Date(Date.now() - 600_000).toISOString(), // 10 min ago
    model: 'gpt-4o',
  },
];

const DEFAULT_PROPS = {
  conversations: MOCK_CONVERSATIONS,
  onSelectConversation: jest.fn(),
};

beforeEach(() => jest.clearAllMocks());

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ConversationSearch', () => {
  it('renders the search input', () => {
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    expect(screen.getByRole('searchbox')).toBeInTheDocument();
  });

  it('shows the custom placeholder text', () => {
    render(
      <ConversationSearch {...DEFAULT_PROPS} placeholder="Find a chat…" />
    );
    expect(screen.getByPlaceholderText('Find a chat…')).toBeInTheDocument();
  });

  it('does NOT show the results panel when query is empty', () => {
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    expect(screen.queryByTestId('search-results-panel')).not.toBeInTheDocument();
  });

  it('shows results panel after typing a query (fake timers)', async () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'React' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByTestId('search-results-panel')).toBeInTheDocument()
    );
    jest.useRealTimers();
  });

  it('filters conversations that match the query', async () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'Docker' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByTestId('search-result-conv-3')).toBeInTheDocument()
    );
    // Unrelated conversations should not appear
    expect(screen.queryByTestId('search-result-conv-1')).not.toBeInTheDocument();
    jest.useRealTimers();
  });

  it('shows no-results message when nothing matches', async () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'xyzxyzxyz' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByTestId('search-results-panel')).toBeInTheDocument()
    );
    expect(screen.getByText(/No conversations found/i)).toBeInTheDocument();
    jest.useRealTimers();
  });

  it('calls onSelectConversation with the correct id on click', async () => {
    jest.useFakeTimers();
    const onSelect = jest.fn();
    render(<ConversationSearch {...DEFAULT_PROPS} onSelectConversation={onSelect} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'Python' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByTestId('search-result-conv-2')).toBeInTheDocument()
    );
    fireEvent.click(screen.getByTestId('search-result-conv-2'));
    expect(onSelect).toHaveBeenCalledWith('conv-2');
    jest.useRealTimers();
  });

  it('ArrowDown key moves highlight to the first result', async () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'React' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByTestId('search-results-panel')).toBeInTheDocument()
    );

    fireEvent.keyDown(input, { key: 'ArrowDown' });
    const items = screen.getAllByRole('option');
    expect(items[0]).toHaveAttribute('aria-selected', 'true');
    jest.useRealTimers();
  });

  it('Escape key clears input and closes panel', async () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'SQL' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByTestId('search-results-panel')).toBeInTheDocument()
    );

    fireEvent.keyDown(input, { key: 'Escape' });
    expect(screen.queryByTestId('search-results-panel')).not.toBeInTheDocument();
    expect((input as HTMLInputElement).value).toBe('');
    jest.useRealTimers();
  });

  it('clear button resets input and closes panel', async () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'hooks' } });
    act(() => jest.advanceTimersByTime(300));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole('button', { name: /clear search/i }));
    expect(screen.queryByTestId('search-results-panel')).not.toBeInTheDocument();
    jest.useRealTimers();
  });
});

describe('useDebounce hook (via ConversationSearch)', () => {
  it('does not show results before debounce delay elapses', () => {
    jest.useFakeTimers();
    render(<ConversationSearch {...DEFAULT_PROPS} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'React' } });
    // Only 100ms has passed, debounce is 250ms
    act(() => jest.advanceTimersByTime(100));
    expect(screen.queryByTestId('search-results-panel')).not.toBeInTheDocument();

    jest.useRealTimers();
  });
});
