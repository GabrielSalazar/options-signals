import type { AssetAnalysisPayload } from '@/lib/types/analytics';
import { useCachedFetch } from './useCachedFetch';

export function useAssetAnalysis(ticker: string | null): {
  data: AssetAnalysisPayload | null;
  loading: boolean;
  error: string | null;
} {
  const url = ticker ? `/api/market/analysis/${ticker.toUpperCase()}` : null;
  return useCachedFetch<AssetAnalysisPayload>(url);
}
