import type { IndicatorsPayload } from '@/lib/types/indicators';
import { useCachedFetch } from './useCachedFetch';

export function useIndicators(ticker: string | null): {
  data: IndicatorsPayload | null;
  loading: boolean;
  error: string | null;
} {
  const url = ticker ? `/api/market/indicators/${ticker.toUpperCase()}` : null;
  return useCachedFetch<IndicatorsPayload>(url);
}
