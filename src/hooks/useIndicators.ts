import { useState, useEffect } from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';

const CACHE_TTL_MS = 5 * 60 * 1000;
interface CacheEntry { payload: IndicatorsPayload; fetchedAt: number; }
const cache = new Map<string, CacheEntry>();

export function useIndicators(ticker: string | null): {
  data: IndicatorsPayload | null; loading: boolean; error: string | null;
} {
  const [data, setData] = useState<IndicatorsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) { setData(null); setError(null); return; }
    const key = ticker.toUpperCase();
    const cached = cache.get(key);
    if (cached && Date.now() - cached.fetchedAt < CACHE_TTL_MS) {
      setData(cached.payload); setLoading(false); setError(null); return;
    }
    setLoading(true); setError(null);
    fetch(`/api/market/indicators/${key}`)
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body) => { throw new Error(body?.detail ?? `Erro ${res.status}`); });
        }
        return res.json() as Promise<IndicatorsPayload>;
      })
      .then((payload) => { cache.set(key, { payload, fetchedAt: Date.now() }); setData(payload); })
      .catch((err: Error) => { setError(err.message); setData(null); })
      .finally(() => setLoading(false));
  }, [ticker]);

  return { data, loading, error };
}
