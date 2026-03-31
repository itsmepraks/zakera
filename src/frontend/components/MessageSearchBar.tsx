/**
 * MessageSearchBar
 * ================
 * Keyboard-activated overlay for searching through chat messages.
 *
 * Usage:
 *   <MessageSearchBar
 *     messages={messages}
 *     onResultSelect={(messageIndex) => scrollToMessage(messageIndex)}
 *   />
 *
 * Keyboard shortcuts:
 *   Ctrl/⌘ + F   : open search
 *   Escape        : close search
 *   Enter / ↓     : next result
 *   ↑             : previous result
 */

'use client';

import React, {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react';
import {
  ChatMessage,
  MatchHighlight,
  SearchResult,
  useMessageSearch,
  UseMessageSearchOptions,
} from '../hooks/useMessageSearch';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MessageSearchBarProps {
  messages: ChatMessage[];
  onResultSelect?: (messageIndex: number, result: SearchResult) => void;
  searchOptions?: UseMessageSearchOptions;
  /** Additional Tailwind classes for the container */
  className?: string;
  /** Placeholder text for the input */
  placeholder?: string;
}

// ---------------------------------------------------------------------------
// Highlight renderer helper
// ---------------------------------------------------------------------------

function HighlightedText({
  text,
  highlights,
  maxLength = 120,
}: {
  text: string;
  highlights: MatchHighlight[];
  maxLength?: number;
}): React.ReactElement {
  // Trim to a window around the first match
  let displayText = text;
  let offset = 0;

  if (text.length > maxLength && highlights.length > 0) {
    const firstMatch = highlights[0];
    const start = Math.max(0, firstMatch.start - 30);
    displayText = (start > 0 ? '…' : '') + text.slice(start, start + maxLength);
    offset = start > 0 ? start - 1 : 0; // account for ellipsis char
  }

  const parts: React.ReactNode[] = [];
  let cursor = 0;

  const adjustedHighlights = highlights
    .map((h) => ({ start: h.start - offset, end: h.end - offset }))
    .filter((h) => h.end > 0 && h.start < displayText.length)
    .map((h) => ({
      start: Math.max(0, h.start),
      end: Math.min(displayText.length, h.end),
    }));

  for (const { start, end } of adjustedHighlights) {
    if (start > cursor) {
      parts.push(
        <span key={`pre-${cursor}`}>{displayText.slice(cursor, start)}</span>,
      );
    }
    parts.push(
      <mark
        key={`mark-${start}`}
        className="bg-yellow-200 dark:bg-yellow-700 text-inherit rounded-sm px-0.5"
      >
        {displayText.slice(start, end)}
      </mark>,
    );
    cursor = end;
  }

  if (cursor < displayText.length) {
    parts.push(
      <span key={`post-${cursor}`}>{displayText.slice(cursor)}</span>,
    );
  }

  return <>{parts}</>;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function MessageSearchBar({
  messages,
  onResultSelect,
  searchOptions,
  className = '',
  placeholder = 'Search messages…',
}: MessageSearchBarProps): React.ReactElement | null {
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const liveRegionId = useId();

  const {
    query,
    setQuery,
    results,
    isSearching,
    clearSearch,
    stats,
    activeResultIndex,
    setActiveResultIndex,
    navigateNext,
    navigatePrev,
  } = useMessageSearch(messages, searchOptions);

  // ---- Open / close handlers ----
  const open = useCallback(() => {
    setIsOpen(true);
    // Focus input after state update
    requestAnimationFrame(() => inputRef.current?.focus());
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    clearSearch();
  }, [clearSearch]);

  // ---- Global keyboard shortcut ----
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        if (isOpen) {
          inputRef.current?.focus();
        } else {
          open();
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, open]);

  // ---- Input keyboard handling ----
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    switch (e.key) {
      case 'Escape':
        close();
        break;
      case 'ArrowDown':
      case 'Enter':
        e.preventDefault();
        if (results.length > 0) {
          if (e.key === 'Enter') {
            selectResult(results[activeResultIndex], activeResultIndex);
          } else {
            navigateNext();
          }
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        navigatePrev();
        break;
    }
  };

  // ---- Scroll active result into view ----
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const activeItem = list.children[activeResultIndex] as HTMLElement | undefined;
    activeItem?.scrollIntoView({ block: 'nearest' });
  }, [activeResultIndex]);

  // ---- Select a result ----
  const selectResult = useCallback(
    (result: SearchResult, idx: number) => {
      setActiveResultIndex(idx);
      onResultSelect?.(result.messageIndex, result);
    },
    [onResultSelect, setActiveResultIndex],
  );

  if (!isOpen) {
    return (
      <button
        onClick={open}
        aria-label="Search messages (Ctrl+F)"
        className={`p-2 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400
          dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700
          transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
        title="Search messages (Ctrl/⌘+F)"
      >
        {/* Magnifying glass icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-5 w-5"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M12.9 14.32a8 8 0 111.414-1.414l4.387 4.387a1 1 0 01-1.414 1.414l-4.387-4.387zM8 14A6 6 0 108 2a6 6 0 000 12z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    );
  }

  return (
    <div
      role="search"
      aria-label="Message search"
      className={`flex flex-col w-full max-w-md bg-white dark:bg-gray-800 border
        border-gray-200 dark:border-gray-600 rounded-xl shadow-xl overflow-hidden
        ${className}`}
    >
      {/* Live region for screen readers */}
      <div
        id={liveRegionId}
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {isSearching && stats
          ? `${stats.totalMatches} result${stats.totalMatches !== 1 ? 's' : ''} found`
          : ''}
      </div>

      {/* Input row */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100 dark:border-gray-700">
        {/* Search icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4 flex-shrink-0 text-gray-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M12.9 14.32a8 8 0 111.414-1.414l4.387 4.387a1 1 0 01-1.414 1.414l-4.387-4.387zM8 14A6 6 0 108 2a6 6 0 000 12z"
            clipRule="evenodd"
          />
        </svg>

        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label={placeholder}
          aria-controls={liveRegionId}
          autoComplete="off"
          spellCheck={false}
          className="flex-1 bg-transparent text-sm text-gray-900 dark:text-gray-100
            placeholder-gray-400 dark:placeholder-gray-500 outline-none"
        />

        {/* Result count badge */}
        {isSearching && stats && (
          <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
            {activeResultIndex + 1} / {stats.totalMatches}
          </span>
        )}

        {/* Navigation arrows */}
        <div className="flex gap-1">
          <button
            onClick={navigatePrev}
            disabled={results.length === 0}
            aria-label="Previous result"
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
              disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
          </button>
          <button
            onClick={navigateNext}
            disabled={results.length === 0}
            aria-label="Next result"
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700
              disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={close}
          aria-label="Close search"
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Results list */}
      {isSearching && (
        <ul
          ref={listRef}
          role="listbox"
          aria-label="Search results"
          className="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700"
        >
          {results.length === 0 ? (
            <li className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 text-center">
              No results found
            </li>
          ) : (
            results.map((result, idx) => (
              <li
                key={result.message.id}
                role="option"
                aria-selected={idx === activeResultIndex}
                onClick={() => selectResult(result, idx)}
                onMouseEnter={() => setActiveResultIndex(idx)}
                className={`px-4 py-2.5 cursor-pointer transition-colors text-sm
                  ${
                    idx === activeResultIndex
                      ? 'bg-blue-50 dark:bg-blue-900/30'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/40'
                  }`}
              >
                {/* Role badge */}
                <span
                  className={`inline-block text-xs font-medium px-1.5 py-0.5 rounded mr-2
                    ${
                      result.message.role === 'user'
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                        : 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300'
                    }`}
                >
                  {result.message.role}
                </span>
                {/* Highlighted snippet */}
                <span className="text-gray-700 dark:text-gray-300">
                  <HighlightedText
                    text={result.message.content}
                    highlights={result.highlights}
                    maxLength={100}
                  />
                </span>
              </li>
            ))
          )}
        </ul>
      )}

      {/* Footer: stats */}
      {isSearching && stats && stats.totalMatches > 0 && (
        <div className="px-4 py-1.5 text-xs text-gray-400 dark:text-gray-500 border-t
          border-gray-100 dark:border-gray-700 flex justify-between">
          <span>{stats.totalMatches} match{stats.totalMatches !== 1 ? 'es' : ''}</span>
          <span>{stats.queryTimeMs.toFixed(1)} ms</span>
        </div>
      )}
    </div>
  );
}

export default MessageSearchBar;
