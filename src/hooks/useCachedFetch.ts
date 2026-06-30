import { useEffect, useRef, useState } from 'react';

const DEFAULT_CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const MAX_CACHE_SIZE = 50; // LRU limit

interface CacheEntry<T> {
  payload: T;
  fetchedAt: number;
}

class LRUCache<T> {
  private map = new Map<string, CacheEntry<T>>();
  private maxSize: number;

  constructor(maxSize: number) {
    this.maxSize = maxSize;
  }

  get(key: string): CacheEntry<T> | undefined {
    const entry = this.map.get(key);
    if (entry) {
      this.map.delete(key);
      this.map.set(key, entry);
    }
    return entry;
  }

  set(key: string, value: CacheEntry<T>): void {
    if (this.map.has(key)) {
      this.map.delete(key);
    } else if (this.map.size >= this.maxSize) {
      const firstKey = this.map.keys().next().value as string | undefined;
      if (firstKey) {
        this.map.delete(firstKey);
      }
    }
    this.map.set(key, value);
  }

  clear(): void {
    this.map.clear();
  }

  size(): number {
    return this.map.size;
  }
}

// Module-level cache shared across all useCachedFetch calls, keyed by URL.
const cache = new LRUCache<unknown>(MAX_CACHE_SIZE);

export function useCachedFetch<T>(
  url: string | null,
  ttlMs: number = DEFAULT_CACHE_TTL_MS
): {
  data: T | null;
  loading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    if (!url) {
      setData(null);
      setError(null);
      return;
    }

    const cached = cache.get(url) as CacheEntry<T> | undefined;
    if (cached && Date.now() - cached.fetchedAt < ttlMs) {
      setData(cached.payload);
      setLoading(false);
      setError(null);
      return;
    }

    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);

    fetch(url)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => {
            throw new Error(body?.detail ?? `Erro ${res.status}`);
          });
        }
        return res.json() as Promise<T>;
      })
      .then((payload) => {
        if (requestIdRef.current === requestId) {
          cache.set(url, { payload, fetchedAt: Date.now() });
          setData(payload);
        }
      })
      .catch((err: Error) => {
        if (requestIdRef.current === requestId) {
          setError(err.message);
          setData(null);
        }
      })
      .finally(() => {
        if (requestIdRef.current === requestId) {
          setLoading(false);
        }
      });
  }, [url, ttlMs]);

  return { data, loading, error };
}
