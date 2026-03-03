/**
 * Tests for MessageTimestamp component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import MessageTimestamp from '../../src/frontend/components/MessageTimestamp';

describe('MessageTimestamp', () => {
  it('renders relative time for recent messages', () => {
    const now = new Date();
    const twoMinutesAgo = new Date(now.getTime() - 2 * 60 * 1000);

    render(<MessageTimestamp timestamp={twoMinutesAgo} format="relative" />);
    expect(screen.getByText(/2 minutes ago/)).toBeInTheDocument();
  });

  it('renders "just now" for very recent messages', () => {
    const now = new Date();
    const fiveSecondsAgo = new Date(now.getTime() - 5 * 1000);

    render(<MessageTimestamp timestamp={fiveSecondsAgo} format="relative" />);
    expect(screen.getByText(/just now/)).toBeInTheDocument();
  });

  it('renders absolute time when format is absolute', () => {
    const date = new Date('2024-03-02T10:30:00');

    render(<MessageTimestamp timestamp={date} format="absolute" />);
    const timestampElement = screen.getByText(/Mar 2, 2024/);
    expect(timestampElement).toBeInTheDocument();
  });

  it('includes absolute time in title attribute', () => {
    const date = new Date('2024-03-02T10:30:00');

    const { container } = render(<MessageTimestamp timestamp={date} />);
    const timestampSpan = container.querySelector('.message-timestamp');
    expect(timestampSpan).toHaveAttribute('title');
  });

  it('accepts string timestamp', () => {
    const timestampString = '2024-03-02T10:30:00Z';

    render(<MessageTimestamp timestamp={timestampString} format="relative" />);
    expect(screen.getByRole('generic')).toBeInTheDocument();
  });
});
