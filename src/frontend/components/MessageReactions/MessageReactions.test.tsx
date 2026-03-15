import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MessageReactions } from './MessageReactions';
import type { ReactionMap } from '../../types/reactions';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const BASE_REACTIONS: ReactionMap = {
  '\u{1F44D}': { count: 3, userReacted: false }, // 👍
  '\u2764\uFE0F': { count: 1, userReacted: true }, // ❤️
};

const noop = () => {};

function renderComponent(
  overrides: Partial<React.ComponentProps<typeof MessageReactions>> = {},
) {
  const defaultProps = {
    messageId: 'msg-1',
    reactions: BASE_REACTIONS,
    onReactionToggle: noop,
    onAddReaction: noop,
    disabled: false,
  };
  return render(<MessageReactions {...defaultProps} {...overrides} />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MessageReactions', () => {
  test('renders reaction chips from props', () => {
    renderComponent();
    // 2 emoji reactions + add button
    expect(screen.getByTestId('reaction-chip-\u{1F44D}')).toBeInTheDocument();
    expect(screen.getByTestId('reaction-chip-\u2764\uFE0F')).toBeInTheDocument();
  });

  test('renders count badge for each reaction', () => {
    renderComponent();
    // counts are inside chips — check by accessible label
    expect(
      screen.getByLabelText(/React with.*3 reactions/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/React with.*1 reaction[^s]/i),
    ).toBeInTheDocument();
  });

  test('calls onReactionToggle when chip clicked', () => {
    const onReactionToggle = jest.fn();
    renderComponent({ onReactionToggle });
    fireEvent.click(screen.getByTestId('reaction-chip-\u{1F44D}'));
    expect(onReactionToggle).toHaveBeenCalledTimes(1);
    expect(onReactionToggle).toHaveBeenCalledWith('msg-1', '\u{1F44D}');
  });

  test('marks chip as active when userReacted is true', () => {
    renderComponent();
    const heartChip = screen.getByTestId('reaction-chip-\u2764\uFE0F');
    expect(heartChip).toHaveAttribute('aria-pressed', 'true');
  });

  test('shows add button when not disabled', () => {
    renderComponent();
    expect(screen.getByTestId('add-reaction-button')).toBeInTheDocument();
  });

  test('hides add button when disabled prop is true', () => {
    renderComponent({ disabled: true });
    expect(screen.queryByTestId('add-reaction-button')).not.toBeInTheDocument();
  });

  test('opens emoji picker on add button click', () => {
    renderComponent();
    fireEvent.click(screen.getByTestId('add-reaction-button'));
    expect(screen.getByTestId('emoji-picker')).toBeInTheDocument();
  });

  test('closes picker on Escape key', () => {
    renderComponent();
    fireEvent.click(screen.getByTestId('add-reaction-button'));
    expect(screen.getByTestId('emoji-picker')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByTestId('emoji-picker')).not.toBeInTheDocument();
  });

  test('calls onAddReaction when emoji selected from picker', () => {
    const onAddReaction = jest.fn();
    renderComponent({ onAddReaction });
    fireEvent.click(screen.getByTestId('add-reaction-button'));
    // Pick the fire emoji 🔥
    fireEvent.click(screen.getByTestId('emoji-option-\u{1F525}'));
    expect(onAddReaction).toHaveBeenCalledWith('msg-1', '\u{1F525}');
  });

  test('closes picker after emoji is selected', () => {
    renderComponent();
    fireEvent.click(screen.getByTestId('add-reaction-button'));
    fireEvent.click(screen.getByTestId('emoji-option-\u{1F525}'));
    expect(screen.queryByTestId('emoji-picker')).not.toBeInTheDocument();
  });

  test('does not call onReactionToggle when disabled', () => {
    const onReactionToggle = jest.fn();
    renderComponent({ disabled: true, onReactionToggle });
    // chips are still rendered but disabled
    const chip = screen.getByTestId('reaction-chip-\u{1F44D}');
    expect(chip).toBeDisabled();
    fireEvent.click(chip);
    expect(onReactionToggle).not.toHaveBeenCalled();
  });

  test('chip has correct aria-label format', () => {
    renderComponent();
    const thumbsUpChip = screen.getByTestId('reaction-chip-\u{1F44D}');
    expect(thumbsUpChip).toHaveAttribute(
      'aria-label',
      expect.stringContaining('3 reactions'),
    );
  });

  test('chips are keyboard-accessible via Enter key', () => {
    const onReactionToggle = jest.fn();
    renderComponent({ onReactionToggle });
    const chip = screen.getByTestId('reaction-chip-\u{1F44D}');
    fireEvent.keyDown(chip, { key: 'Enter' });
    expect(onReactionToggle).toHaveBeenCalledWith('msg-1', '\u{1F44D}');
  });

  test('reaction tray renders without crashing for empty reactions', () => {
    renderComponent({ reactions: {} });
    expect(screen.getByTestId('reaction-tray')).toBeInTheDocument();
  });
});
