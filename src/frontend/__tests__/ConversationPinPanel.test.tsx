/**
 * Tests for ConversationPinPanel component and usePinnedMessages hook.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderHook, act as hookAct } from '@testing-library/react-hooks';

import ConversationPinPanel from '../components/ConversationPinPanel';
import {
  usePinnedMessages,
  MAX_PINS,
  Message,
} from '../hooks/usePinnedMessages';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const CONV_ID = 'conv-abc-123';

const MESSAGES: Message[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'What is the capital of France?',
    timestamp: '2026-03-24T20:00:00.000Z',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'The capital of France is Paris.',
    timestamp: '2026-03-24T20:00:05.000Z',
  },
  {
    id: 'msg-3',
    role: 'assistant',
    content:
      "Paris is also the largest city in France and serves as the country's " +
      'major economic, cultural, and political centre.',
    timestamp: '2026-03-24T20:00:10.000Z',
  },
];

const defaultProps = (
  overrides: Partial<React.ComponentProps<typeof ConversationPinPanel>> = {},
) => ({
  conversationId: CONV_ID,
  pinnedMessages: [MESSAGES[1]],
  onUnpin: jest.fn(),
  onClearAll: jest.fn(),
  onScrollToMessage: jest.fn(),
  ...overrides,
});

// ---------------------------------------------------------------------------
// ConversationPinPanel – rendering
// ---------------------------------------------------------------------------

describe('ConversationPinPanel – rendering', () => {
  it('renders with the default open state (aria-expanded=true)', () => {
    render(<ConversationPinPanel {...defaultProps()} />);
    const toggle = screen.getByRole('button', { name: /pinned messages/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('renders closed when defaultOpen=false', () => {
    render(<ConversationPinPanel {...defaultProps({ defaultOpen: false })} />);
    const toggle = screen.getByRole('button', { name: /pinned messages/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('displays the correct pin count badge', () => {
    render(
      <ConversationPinPanel
        {...defaultProps({ pinnedMessages: [MESSAGES[0], MESSAGES[1]] })}
      />,
    );
    expect(screen.getByLabelText('2 pinned')).toBeInTheDocument();
  });

  it('shows pinned message role chip and preview text', () => {
    render(<ConversationPinPanel {...defaultProps()} />);
    expect(screen.getByText('AI')).toBeInTheDocument();
    expect(
      screen.getByText('The capital of France is Paris.'),
    ).toBeInTheDocument();
  });

  it('shows a "You" chip for user-role messages', () => {
    render(
      <ConversationPinPanel
        {...defaultProps({ pinnedMessages: [MESSAGES[0]] })}
      />,
    );
    expect(screen.getByText('You')).toBeInTheDocument();
  });

  it('renders the empty state when no messages are pinned', () => {
    render(<ConversationPinPanel {...defaultProps({ pinnedMessages: [] })} />);
    expect(screen.getByText(/no pinned messages yet/i)).toBeInTheDocument();
  });

  it('does not render Clear-all when list is empty', () => {
    render(<ConversationPinPanel {...defaultProps({ pinnedMessages: [] })} />);
    expect(
      screen.queryByRole('button', { name: /clear all pins/i }),
    ).not.toBeInTheDocument();
  });

  it('renders Clear-all button when messages are pinned', () => {
    render(<ConversationPinPanel {...defaultProps()} />);
    expect(
      screen.getByRole('button', { name: /clear all pins/i }),
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ConversationPinPanel – interactions
// ---------------------------------------------------------------------------

describe('ConversationPinPanel – interactions', () => {
  it('toggles open/closed state on header button click', async () => {
    render(<ConversationPinPanel {...defaultProps()} />);
    const toggle = screen.getByRole('button', { name: /pinned messages/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('calls onUnpin with the correct message id', async () => {
    const onUnpin = jest.fn();
    render(<ConversationPinPanel {...defaultProps({ onUnpin })} />);
    const unpinBtn = screen.getByRole('button', { name: /unpin this message/i });
    await userEvent.click(unpinBtn);
    expect(onUnpin).toHaveBeenCalledTimes(1);
    expect(onUnpin).toHaveBeenCalledWith('msg-2');
  });

  it('calls onScrollToMessage when a pin card is activated', async () => {
    const onScrollToMessage = jest.fn();
    render(<ConversationPinPanel {...defaultProps({ onScrollToMessage })} />);
    const card = screen.getByRole('button', {
      name: /go to pinned AI message/i,
    });
    await userEvent.click(card);
    expect(onScrollToMessage).toHaveBeenCalledTimes(1);
    expect(onScrollToMessage).toHaveBeenCalledWith('msg-2');
  });

  it('requires a second click to confirm Clear-all', async () => {
    const onClearAll = jest.fn();
    render(<ConversationPinPanel {...defaultProps({ onClearAll })} />);
    const clearBtn = screen.getByRole('button', { name: /clear all pins/i });
    // First click: show confirmation prompt
    await userEvent.click(clearBtn);
    expect(onClearAll).not.toHaveBeenCalled();
    const confirmBtn = await screen.findByRole('button', {
      name: /confirm clear all pins/i,
    });
    // Second click: actually clears
    await userEvent.click(confirmBtn);
    expect(onClearAll).toHaveBeenCalledTimes(1);
  });

  it('unpin click does not propagate to the navigate handler', async () => {
    const onScrollToMessage = jest.fn();
    const onUnpin = jest.fn();
    render(
      <ConversationPinPanel
        {...defaultProps({ onScrollToMessage, onUnpin })}
      />,
    );
    await userEvent.click(
      screen.getByRole('button', { name: /unpin this message/i }),
    );
    expect(onUnpin).toHaveBeenCalledTimes(1);
    expect(onScrollToMessage).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// usePinnedMessages hook
// ---------------------------------------------------------------------------

describe('usePinnedMessages', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts with an empty pin set', () => {
    const { result } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    expect(result.current.pinnedIds.size).toBe(0);
    expect(result.current.pinnedMessages).toHaveLength(0);
  });

  it('pinMessage adds a message and exposes it via pinnedMessages', () => {
    const { result } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    hookAct(() => { result.current.pinMessage('msg-1'); });
    expect(result.current.isPinned('msg-1')).toBe(true);
    expect(result.current.pinnedMessages).toHaveLength(1);
    expect(result.current.pinnedMessages[0].id).toBe('msg-1');
  });

  it('unpinMessage removes the pin', () => {
    const { result } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    hookAct(() => { result.current.pinMessage('msg-1'); });
    hookAct(() => { result.current.unpinMessage('msg-1'); });
    expect(result.current.isPinned('msg-1')).toBe(false);
    expect(result.current.pinnedMessages).toHaveLength(0);
  });

  it('togglePin alternately pins and unpins', () => {
    const { result } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    hookAct(() => { result.current.togglePin('msg-2'); });
    expect(result.current.isPinned('msg-2')).toBe(true);
    hookAct(() => { result.current.togglePin('msg-2'); });
    expect(result.current.isPinned('msg-2')).toBe(false);
  });

  it('clearAllPins empties the pin set', () => {
    const { result } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    hookAct(() => {
      result.current.pinMessage('msg-1');
      result.current.pinMessage('msg-2');
      result.current.pinMessage('msg-3');
    });
    hookAct(() => { result.current.clearAllPins(); });
    expect(result.current.pinnedMessages).toHaveLength(0);
  });

  it('persists pins to localStorage and reloads on remount', () => {
    const { result, unmount } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    hookAct(() => { result.current.pinMessage('msg-3'); });
    unmount();

    const { result: r2 } = renderHook(() =>
      usePinnedMessages(CONV_ID, MESSAGES),
    );
    expect(r2.current.isPinned('msg-3')).toBe(true);
  });

  it('keeps pin state independent per conversationId', () => {
    const { result: rA } = renderHook(() =>
      usePinnedMessages('conv-A', MESSAGES),
    );
    const { result: rB } = renderHook(() =>
      usePinnedMessages('conv-B', MESSAGES),
    );
    hookAct(() => { rA.current.pinMessage('msg-1'); });
    expect(rA.current.isPinned('msg-1')).toBe(true);
    expect(rB.current.isPinned('msg-1')).toBe(false);
  });

  it(`caps pins at MAX_PINS (${MAX_PINS})`, () => {
    const manyMessages: Message[] = Array.from(
      { length: MAX_PINS + 5 },
      (_, i) => ({ id: `m${i}`, role: 'assistant' as const, content: `Msg ${i}` }),
    );
    const { result } = renderHook(() =>
      usePinnedMessages(CONV_ID, manyMessages),
    );
    hookAct(() => {
      manyMessages.forEach((m) => result.current.pinMessage(m.id));
    });
    expect(result.current.pinnedMessages).toHaveLength(MAX_PINS);
  });
});
