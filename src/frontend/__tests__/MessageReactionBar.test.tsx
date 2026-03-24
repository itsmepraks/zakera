/**
 * Tests for MessageReactionBar and useMessageActions.
 */

import React from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import { MessageReactionBar } from '../components/MessageReactionBar';

// ---------------------------------------------------------------------------
// Mock clipboard API
// ---------------------------------------------------------------------------
const mockWriteText = jest.fn().mockResolvedValue(undefined);
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: mockWriteText },
  writable: true,
  configurable: true,
});

beforeEach(() => {
  jest.useFakeTimers();
  mockWriteText.mockClear();
});

afterEach(() => {
  jest.useRealTimers();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultProps = {
  messageId: 'msg-001',
  content: 'Hello from Zakera AI!',
};

const renderBar = (overrides = {}) =>
  render(<MessageReactionBar {...defaultProps} {...overrides} />);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MessageReactionBar', () => {
  it('renders all three action buttons', () => {
    renderBar();
    expect(screen.getByTestId('reaction-like')).toBeInTheDocument();
    expect(screen.getByTestId('reaction-dislike')).toBeInTheDocument();
    expect(screen.getByTestId('copy-button')).toBeInTheDocument();
  });

  it('no reaction is active initially', () => {
    renderBar();
    expect(screen.getByTestId('reaction-like')).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('reaction-dislike')).toHaveAttribute('aria-pressed', 'false');
  });

  describe('Like button', () => {
    it('activates like on first click', () => {
      renderBar();
      fireEvent.click(screen.getByTestId('reaction-like'));
      expect(screen.getByTestId('reaction-like')).toHaveAttribute('aria-pressed', 'true');
    });

    it('deactivates like on second click (toggle off)', () => {
      renderBar();
      fireEvent.click(screen.getByTestId('reaction-like'));
      fireEvent.click(screen.getByTestId('reaction-like'));
      expect(screen.getByTestId('reaction-like')).toHaveAttribute('aria-pressed', 'false');
    });

    it('calls onReaction with "like" then null', () => {
      const onReaction = jest.fn();
      renderBar({ onReaction });
      fireEvent.click(screen.getByTestId('reaction-like'));
      expect(onReaction).toHaveBeenCalledWith('msg-001', 'like');
      fireEvent.click(screen.getByTestId('reaction-like'));
      expect(onReaction).toHaveBeenCalledWith('msg-001', null);
    });
  });

  describe('Dislike button', () => {
    it('activates dislike on click', () => {
      renderBar();
      fireEvent.click(screen.getByTestId('reaction-dislike'));
      expect(screen.getByTestId('reaction-dislike')).toHaveAttribute('aria-pressed', 'true');
    });

    it('calls onReaction with "dislike"', () => {
      const onReaction = jest.fn();
      renderBar({ onReaction });
      fireEvent.click(screen.getByTestId('reaction-dislike'));
      expect(onReaction).toHaveBeenCalledWith('msg-001', 'dislike');
    });
  });

  describe('Mutual exclusivity', () => {
    it('switching from like to dislike deactivates like', () => {
      renderBar();
      fireEvent.click(screen.getByTestId('reaction-like'));
      expect(screen.getByTestId('reaction-like')).toHaveAttribute('aria-pressed', 'true');
      fireEvent.click(screen.getByTestId('reaction-dislike'));
      expect(screen.getByTestId('reaction-dislike')).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByTestId('reaction-like')).toHaveAttribute('aria-pressed', 'false');
    });

    it('switching from dislike to like deactivates dislike', () => {
      renderBar();
      fireEvent.click(screen.getByTestId('reaction-dislike'));
      fireEvent.click(screen.getByTestId('reaction-like'));
      expect(screen.getByTestId('reaction-like')).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByTestId('reaction-dislike')).toHaveAttribute('aria-pressed', 'false');
    });
  });

  describe('Copy button', () => {
    it('copies message content to clipboard', async () => {
      renderBar();
      await act(async () => {
        fireEvent.click(screen.getByTestId('copy-button'));
      });
      expect(mockWriteText).toHaveBeenCalledWith('Hello from Zakera AI!');
    });

    it('shows confirmation (aria-pressed=true) after copy', async () => {
      renderBar();
      await act(async () => {
        fireEvent.click(screen.getByTestId('copy-button'));
      });
      expect(screen.getByTestId('copy-button')).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByTestId('copy-button')).toHaveAttribute('aria-label', 'Copied!');
    });

    it('resets copy confirmation after 2 seconds', async () => {
      renderBar();
      await act(async () => {
        fireEvent.click(screen.getByTestId('copy-button'));
      });
      act(() => {
        jest.advanceTimersByTime(2001);
      });
      await waitFor(() => {
        expect(screen.getByTestId('copy-button')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('copy-button')).toHaveAttribute('aria-label', 'Copy message');
      });
    });

    it('calls onCopy callback with messageId', async () => {
      const onCopy = jest.fn();
      renderBar({ onCopy });
      await act(async () => {
        fireEvent.click(screen.getByTestId('copy-button'));
      });
      expect(onCopy).toHaveBeenCalledWith('msg-001');
    });
  });

  describe('Disabled state', () => {
    it('renders disabled buttons when disabled=true', () => {
      renderBar({ disabled: true });
      expect(screen.getByTestId('reaction-like')).toBeDisabled();
      expect(screen.getByTestId('reaction-dislike')).toBeDisabled();
      expect(screen.getByTestId('copy-button')).toBeDisabled();
    });

    it('does not copy when disabled', async () => {
      renderBar({ disabled: true });
      fireEvent.click(screen.getByTestId('copy-button'));
      expect(mockWriteText).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('container has role=group with an accessible label', () => {
      renderBar();
      expect(screen.getByRole('group', { name: /message actions/i })).toBeInTheDocument();
    });
  });
});
