import { useState, useEffect } from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const MAX_CACHE_SIZE = 50; // LRU limit

interface CacheEntry {
  payload: IndicatorsPayload;
  fetchedAt: number;
}

class LRUCache {
  private map = new Map<string, CacheEntry>();
  private maxSize: number;

  constructor(maxSize: number) {
    this.maxSize = maxSize;
  }

  get(key: string): CacheEntry | undefined {
    const entry = this.map.get(key);
    if (entry) {
      // Move to end (most recently used)
      this.map.delete(key);
      this.map.set(key, entry);
    }
    return entry;
  }

  set(key: string, value: CacheEntry): void {
    if (this.map.has(key)) {
      this.map.delete(key);
    } else if (this.map.size >= this.maxSize) {
      // Remove least recently used (first entry)
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

const cache = new LRUCache(MAX_CACHE_SIZE);

export function useIndicators(ticker: string | null): {
  data: IndicatorsPayload | null; loading: boolean; error: string | null;
} {
  const [data, setData] = useState<IndicatorsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) {
      setData(null);
      setError(null);
      return;
    }

    const key = ticker.toUpperCase();
    const cached = cache.get(key);
    if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
      setData(cached.payload);
      setLoading(false);
      setError(null);
      return;
    }

    let cancel = false;
    setLoading(true);
    setError(null);

    fetch(`/api/market/indicators/${key}`)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => {
            throw new Error(body?.detail ?? `Erro ${res.status}`);
          });
        }
        return res.json() as Promise<IndicatorsPayload>;
      })
      .then((payload) => {
        if (!cancel) {
          cache.set(key, { payload, fetchedAt: Date.now() });
          setData(payload);
        }
      })
      .catch((err: Error) => {
        if (!cancel) {
          setError(err.message);
          setData(null);
        }
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });

    return () => {
      cancel = true;
    };
  }, [ticker]);

  return { data, loading, error };
}
