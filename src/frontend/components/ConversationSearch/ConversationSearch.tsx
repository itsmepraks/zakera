/**
 * ConversationSearch.tsx
 * ======================
 * Full-text fuzzy search across loaded conversations.
 *
 * Uses Fuse.js for client-side indexing so results appear instantly
 * without an API call for sessions that are already in the store.
 * Falls back to a server-side search endpoint for older history that
 * hasn't been loaded into memory yet (TODO: implement API call).
 */

import React, {
  forwardRef,
  useCallback,
  useEffect,
  useRef,
  useState,
  KeyboardEvent,
} from 'react';
import Fuse from 'fuse.js';
import styles from './ConversationSearch.module.css';
import { useDebounce } from '../../hooks/useDebounce';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Conversation {
  id: string;
  title: string;
  lastMessage?: string;
  updatedAt: string; // ISO-8601
  model?: string;
}

export interface SearchResult {
  conversation: Conversation;
  /** Fuse.js match score: 0 = perfect, 1 = no match */
  score: number;
  /** Substrings within title that matched, for highlight rendering */
  titleMatches?: readonly Fuse.FuseResultMatch[];
}

export interface ConversationSearchProps {
  /** All conversations available to search */
  conversations: Conversation[];
  /** Called when the user selects a result */
  onSelectConversation: (conversationId: string) => void;
  /** Controlled placeholder text */
  placeholder?: string;
  /** Additional class for the root container */
  className?: string;
  /** Maximum number of results to show */
  maxResults?: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Highlight matched regions in a string by wrapping them in <mark>. */
function highlightMatches(
  text: string,
  matches: readonly Fuse.FuseResultMatch[] | undefined,
): React.ReactNode {
  if (!matches || matches.length === 0) return text;

  // Collect all [start, end] character ranges from all match entries
  const ranges: [number, number][] = [];
  for (const match of matches) {
    if (match.indices) {
      for (const [start, end] of match.indices) {
        ranges.push([start, end]);
      }
    }
  }

  if (ranges.length === 0) return text;

  // Sort ranges and render interleaved plain/highlighted segments
  ranges.sort((a, b) => a[0] - b[0]);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (start > cursor) nodes.push(text.slice(cursor, start));
    nodes.push(
      <mark key={start} className={styles.highlight}>
        {text.slice(start, end + 1)}
      </mark>,
    );
    cursor = end + 1;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return <>{nodes}</>;
}

/** Format an ISO timestamp as a relative label like "2 hours ago". */
function relativeTime(isoString: string): string {
  const ms = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(isoString).toLocaleDateString();
}

// ---------------------------------------------------------------------------
// Fuse.js index configuration
// ---------------------------------------------------------------------------

const FUSE_OPTIONS: Fuse.IFuseOptions<Conversation> = {
  keys: [
    { name: 'title', weight: 0.7 },
    { name: 'lastMessage', weight: 0.3 },
  ],
  threshold: 0.4,       // lower = stricter matching
  includeScore: true,
  includeMatches: true,
  minMatchCharLength: 2,
  ignoreLocation: true, // search anywhere in the string
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ConversationSearch = forwardRef<HTMLInputElement, ConversationSearchProps>(
  (
    {
      conversations,
      onSelectConversation,
      placeholder = 'Search conversations…',
      className,
      maxResults = 8,
    }: ConversationSearchProps,
    ref,
  ) => {
    const [query, setQuery] = useState('');
    const debouncedQuery = useDebounce(query, 250);
    const [results, setResults] = useState<SearchResult[]>([]);
    const [activeIndex, setActiveIndex] = useState<number>(-1);
    const [isOpen, setIsOpen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const fuseRef = useRef<Fuse<Conversation>>(new Fuse(conversations, FUSE_OPTIONS));

    // Rebuild Fuse index whenever the conversation list changes
    useEffect(() => {
      fuseRef.current = new Fuse(conversations, FUSE_OPTIONS);
    }, [conversations]);

    // Run search whenever the debounced query changes
    useEffect(() => {
      if (!debouncedQuery.trim()) {
        setResults([]);
        setIsOpen(false);
        return;
      }

      const raw = fuseRef.current.search(debouncedQuery, { limit: maxResults });
      setResults(
        raw.map((item) => ({
          conversation: item.item,
          score: item.score ?? 1,
          titleMatches: item.matches?.filter((m) => m.key === 'title'),
        })),
      );
      setActiveIndex(-1);
      setIsOpen(true);
    }, [debouncedQuery, maxResults]);

    // Close panel on outside click
    useEffect(() => {
      const handleOutside = (e: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
          setIsOpen(false);
        }
      };
      document.addEventListener('mousedown', handleOutside);
      return () => document.removeEventListener('mousedown', handleOutside);
    }, []);

    const handleSelect = useCallback(
      (id: string) => {
        onSelectConversation(id);
        setQuery('');
        setIsOpen(false);
      },
      [onSelectConversation],
    );

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen || results.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % results.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + results.length) % results.length);
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        handleSelect(results[activeIndex].conversation.id);
      } else if (e.key === 'Escape') {
        setQuery('');
        setIsOpen(false);
      }
    };

    return (
      <div
        ref={containerRef}
        className={`${styles.root}${className ? ` ${className}` : ''}`}
        data-testid="conversation-search"
      >
        {/* Search input */}
        <div className={styles.inputWrapper}>
          <svg
            className={styles.searchIcon}
            aria-hidden="true"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={ref}
            type="search"
            className={styles.input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => debouncedQuery && setIsOpen(true)}
            placeholder={placeholder}
            aria-label="Search conversations"
            aria-autocomplete="list"
            aria-expanded={isOpen}
            aria-controls="conversation-search-results"
            autoComplete="off"
            spellCheck={false}
          />
          {query && (
            <button
              className={styles.clearButton}
              onClick={() => { setQuery(''); setIsOpen(false); }}
              aria-label="Clear search"
              type="button"
            >
              ×
            </button>
          )}
        </div>

        {/* Results panel */}
        {isOpen && (
          <ul
            id="conversation-search-results"
            role="listbox"
            className={styles.results}
            data-testid="search-results-panel"
          >
            {results.length === 0 ? (
              <li className={styles.noResults}>
                <span className={styles.noResultsIcon} aria-hidden="true">🔍</span>
                <span>No conversations found for &ldquo;{debouncedQuery}&rdquo;</span>
              </li>
            ) : (
              results.map((result, idx) => (
                <li
                  key={result.conversation.id}
                  role="option"
                  aria-selected={idx === activeIndex}
                  className={`${styles.resultItem}${
                    idx === activeIndex ? ` ${styles.resultItemActive}` : ''
                  }`}
                  onMouseEnter={() => setActiveIndex(idx)}
                  onClick={() => handleSelect(result.conversation.id)}
                  data-testid={`search-result-${result.conversation.id}`}
                >
                  <div className={styles.resultTitle}>
                    {highlightMatches(
                      result.conversation.title,
                      result.titleMatches,
                    )}
                  </div>
                  {result.conversation.lastMessage && (
                    <div className={styles.resultSnippet}>
                      {result.conversation.lastMessage.slice(0, 80)}
                      {result.conversation.lastMessage.length > 80 ? '…' : ''}
                    </div>
                  )}
                  <div className={styles.resultMeta}>
                    {result.conversation.model && (
                      <span className={styles.modelBadge}>
                        {result.conversation.model}
                      </span>
                    )}
                    <span className={styles.timestamp}>
                      {relativeTime(result.conversation.updatedAt)}
                    </span>
                  </div>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    );
  },
);

ConversationSearch.displayName = 'ConversationSearch';
export default ConversationSearch;
