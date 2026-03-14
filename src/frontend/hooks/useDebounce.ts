/**
 * useDebounce.ts
 * ==============
 * Generic debounce hook.  Returns a debounced copy of `value` that only
 * updates after `delay` milliseconds have elapsed since the last change.
 *
 * @example
 *   const debouncedQuery = useDebounce(searchQuery, 300);
 */

import { useEffect, useState } from 'react';

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    if (delay <= 0) {
      setDebouncedValue(value);
      return;
    }

    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Cancel the timer if value or delay changes before it fires,
    // or when the component that uses this hook unmounts.
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

export default useDebounce;
