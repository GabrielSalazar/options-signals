import useSWR from 'swr';
import { api } from '@/services/api'; // Ensure this points to the axios instance
import { Signal } from '@/types/signals';

const fetcher = (url: string) => api.get(url).then(res => res.data.signals);

export function useSignals(active: boolean = true) {
    const { data, error, isLoading, mutate } = useSWR<Signal[]>(
        active ? '/signals?min_confidence=50' : null,
        fetcher,
        {
            refreshInterval: 5000, // Poll every 5s
            revalidateOnFocus: false
        }
    );

    return {
        signals: data,
        isLoading,
        isError: error,
        mutate
    };
}
