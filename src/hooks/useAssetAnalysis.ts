import { useState, useEffect } from 'react';
import type { AssetAnalysisPayload } from '@/lib/types/analytics';

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CacheEntry {
  payload: AssetAnalysisPayload;
  fetchedAt: number;
}

const cache = new Map<string, CacheEntry>();

export function useAssetAnalysis(ticker: string | null): {
  data: AssetAnalysisPayload | null;
  loading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<AssetAnalysisPayload | null>(null);
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

    setLoading(true);
    setError(null);

    fetch(`/api/market/analysis/${key}`)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => {
            throw new Error(body?.detail ?? `Erro ${res.status}`);
          });
        }
        return res.json() as Promise<AssetAnalysisPayload>;
      })
      .then((payload) => {
        cache.set(key, { payload, fetchedAt: Date.now() });
        setData(payload);
      })
      .catch((err: Error) => {
        setError(err.message);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [ticker]);

  return { data, loading, error };
}
