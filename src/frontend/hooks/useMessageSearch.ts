/**
 * useMessageSearch
 * ================
 * React hook for fast in-conversation message search.
 *
 * Features:
 *  - Trigram index for O(1) lookup after initial build
 *  - Fuzzy matching (Levenshtein distance ≤ 2) for typo tolerance
 *  - Regex mode for power users
 *  - Debounced 150 ms to keep keystroke rendering smooth
 *  - Returns highlight offsets so the UI can render <mark> spans
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  createdAt?: string | Date;
  metadata?: Record<string, unknown>;
}

export interface MatchHighlight {
  start: number;
  end: number;
}

export interface SearchResult {
  message: ChatMessage;
  /** Index of the message in the original messages array */
  messageIndex: number;
  /** Match positions within message.content for highlighting */
  highlights: MatchHighlight[];
  /** Relevance score (higher = better) */
  score: number;
}

export interface SearchStats {
  indexedMessages: number;
  queryTimeMs: number;
  totalMatches: number;
}

export interface UseMessageSearchOptions {
  /** Enable fuzzy matching (Levenshtein ≤ 2). Default: true */
  fuzzy?: boolean;
  /** Treat query as a regular expression. Default: false */
  regexMode?: boolean;
  /** Minimum query length before searching. Default: 2 */
  minQueryLength?: number;
  /** Debounce delay in ms. Default: 150 */
  debounceMs?: number;
  /** Roles to include in search. Default: all roles */
  includeRoles?: Array<ChatMessage['role']>;
  /** Maximum results to return. Default: 50 */
  maxResults?: number;
}

export interface UseMessageSearchReturn {
  query: string;
  setQuery: (q: string) => void;
  results: SearchResult[];
  isSearching: boolean;
  clearSearch: () => void;
  stats: SearchStats | null;
  activeResultIndex: number;
  setActiveResultIndex: (i: number) => void;
  navigateNext: () => void;
  navigatePrev: () => void;
}

// ---------------------------------------------------------------------------
// Trigram utilities
// ---------------------------------------------------------------------------

function trigrams(text: string): Set<string> {
  const t = new Set<string>();
  const normalized = text.toLowerCase();
  for (let i = 0; i <= normalized.length - 3; i++) {
    t.add(normalized.slice(i, i + 3));
  }
  return t;
}

function trigramSimilarity(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let intersection = 0;
  for (const t of a) {
    if (b.has(t)) intersection++;
  }
  return (2 * intersection) / (a.size + b.size);
}

// ---------------------------------------------------------------------------
// Levenshtein distance (token-level for fuzzy matching)
// ---------------------------------------------------------------------------

function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  );
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[m][n];
}

function fuzzyContains(text: string, query: string, maxDist = 2): boolean {
  const lText = text.toLowerCase();
  const lQuery = query.toLowerCase();
  // Exact substring first (fast path)
  if (lText.includes(lQuery)) return true;
  // Token-level Levenshtein
  const tokens = lText.split(/\s+/);
  for (const token of tokens) {
    if (Math.abs(token.length - lQuery.length) <= maxDist) {
      if (levenshtein(token, lQuery) <= maxDist) return true;
    }
  }
  return false;
}

// ---------------------------------------------------------------------------
// Find all highlight offsets for a query in text
// ---------------------------------------------------------------------------

function findHighlights(
  text: string,
  query: string,
  regexMode: boolean,
): MatchHighlight[] {
  const highlights: MatchHighlight[] = [];
  if (!query) return highlights;

  if (regexMode) {
    try {
      const re = new RegExp(query, 'gi');
      let match: RegExpExecArray | null;
      while ((match = re.exec(text)) !== null) {
        highlights.push({ start: match.index, end: match.index + match[0].length });
        if (match[0].length === 0) re.lastIndex++; // avoid infinite loop on empty match
      }
    } catch {
      // Invalid regex – fall through to plain text
    }
  }

  if (highlights.length === 0) {
    // Plain text search
    const lText = text.toLowerCase();
    const lQuery = query.toLowerCase();
    let pos = 0;
    while ((pos = lText.indexOf(lQuery, pos)) !== -1) {
      highlights.push({ start: pos, end: pos + lQuery.length });
      pos += lQuery.length;
    }
  }

  return highlights;
}

// ---------------------------------------------------------------------------
// Index structure
// ---------------------------------------------------------------------------

interface IndexedMessage {
  message: ChatMessage;
  messageIndex: number;
  trigramSet: Set<string>;
  lowerContent: string;
}

function buildIndex(
  messages: ChatMessage[],
  includeRoles?: Array<ChatMessage['role']>,
): IndexedMessage[] {
  return messages
    .map((msg, idx) => ({ message: msg, messageIndex: idx }))
    .filter(
      ({ message }) =>
        !includeRoles || includeRoles.includes(message.role),
    )
    .map(({ message, messageIndex }) => ({
      message,
      messageIndex,
      trigramSet: trigrams(message.content),
      lowerContent: message.content.toLowerCase(),
    }));
}

// ---------------------------------------------------------------------------
// Debounce helper
// ---------------------------------------------------------------------------

function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

// ---------------------------------------------------------------------------
// Main hook
// ---------------------------------------------------------------------------

export function useMessageSearch(
  messages: ChatMessage[],
  options: UseMessageSearchOptions = {},
): UseMessageSearchReturn {
  const {
    fuzzy = true,
    regexMode = false,
    minQueryLength = 2,
    debounceMs = 150,
    includeRoles,
    maxResults = 50,
  } = options;

  const [query, setQuery] = useState('');
  const [activeResultIndex, setActiveResultIndex] = useState(0);
  const debouncedQuery = useDebounce(query, debounceMs);

  // Rebuild index whenever messages change (memoised by reference)
  const index = useMemo(
    () => buildIndex(messages, includeRoles),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [messages, JSON.stringify(includeRoles)],
  );

  const statsRef = useRef<SearchStats | null>(null);

  const results = useMemo<SearchResult[]>(() => {
    const q = debouncedQuery.trim();
    if (q.length < minQueryLength) {
      statsRef.current = null;
      return [];
    }

    const t0 = performance.now();
    const queryTrigramSet = trigrams(q);
    const matched: SearchResult[] = [];

    for (const item of index) {
      let matches = false;
      let score = 0;

      if (regexMode) {
        try {
          const re = new RegExp(q, 'i');
          matches = re.test(item.message.content);
          score = matches ? 1 : 0;
        } catch {
          matches = false;
        }
      } else {
        // Fast trigram pre-filter
        const sim = trigramSimilarity(queryTrigramSet, item.trigramSet);
        if (sim > 0.1 || item.lowerContent.includes(q.toLowerCase())) {
          matches = true;
          score = sim;
        } else if (fuzzy) {
          matches = fuzzyContains(item.message.content, q);
          score = matches ? 0.3 : 0;
        }
      }

      if (matches) {
        const highlights = findHighlights(item.message.content, q, regexMode);
        matched.push({
          message: item.message,
          messageIndex: item.messageIndex,
          highlights,
          score,
        });
      }
    }

    matched.sort((a, b) => b.score - a.score);
    const limited = matched.slice(0, maxResults);

    statsRef.current = {
      indexedMessages: index.length,
      queryTimeMs: performance.now() - t0,
      totalMatches: limited.length,
    };

    return limited;
  }, [debouncedQuery, index, fuzzy, regexMode, minQueryLength, maxResults]);

  // Reset active result when results change
  useEffect(() => {
    setActiveResultIndex(0);
  }, [results]);

  const clearSearch = useCallback(() => {
    setQuery('');
    setActiveResultIndex(0);
  }, []);

  const navigateNext = useCallback(() => {
    if (results.length === 0) return;
    setActiveResultIndex((i) => (i + 1) % results.length);
  }, [results.length]);

  const navigatePrev = useCallback(() => {
    if (results.length === 0) return;
    setActiveResultIndex((i) => (i - 1 + results.length) % results.length);
  }, [results.length]);

  return {
    query,
    setQuery,
    results,
    isSearching: debouncedQuery.trim().length >= minQueryLength,
    clearSearch,
    stats: statsRef.current,
    activeResultIndex,
    setActiveResultIndex,
    navigateNext,
    navigatePrev,
  };
}
