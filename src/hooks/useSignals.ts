import { useEffect, useState, useCallback } from 'react';
import { getSupabase } from '@/lib/supabase';
import { Signal } from '@/types/signals';

// Número de sinais mantidos no feed ao vivo (consulta inicial + janela do realtime).
const LIVE_FEED_LIMIT = 100;

function isB3MarketOpen(): boolean {
    const now = new Date();
    const fmt = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/Sao_Paulo',
        weekday: 'short',
        hour: 'numeric',
        minute: 'numeric',
        hour12: false,
    });
    const parts = Object.fromEntries(fmt.formatToParts(now).map(p => [p.type, p.value]));
    const day = parts.weekday; // 'Sun', 'Sat', etc.
    if (day === 'Sun' || day === 'Sat') return false;
    const brtMin = parseInt(parts.hour) * 60 + parseInt(parts.minute);
    return brtMin >= 600 && brtMin <= 1080; // 10:00–18:00 BRT (DST-safe)
}

export function useSignals(active: boolean = true) {
    const [signals, setSignals] = useState<Signal[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isError, setIsError] = useState(false);

    const fetchInitial = useCallback(async () => {
        try {
            const sb = getSupabase();
            const { data, error } = await sb
                .from('signals')
                .select('*')
                .order('timestamp', { ascending: false })
                .limit(LIVE_FEED_LIMIT);

            if (error) {
                setIsError(true);
            } else {
                setSignals(data ?? []);
            }
        } catch {
            setIsError(true);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!active) {
            setIsLoading(false);
            return;
        }

        fetchInitial();

        // Realtime subscription — only subscribe during market hours to spare Render
        if (!isB3MarketOpen()) return;

        let sb: ReturnType<typeof getSupabase>;
        let channel: ReturnType<typeof sb.channel>;

        try {
            sb = getSupabase();
            channel = sb
                .channel('signals-live')
                .on(
                    'postgres_changes',
                    { event: 'INSERT', schema: 'public', table: 'signals' },
                    (payload: { new: Signal }) => {
                        setSignals((prev) => [payload.new, ...prev].slice(0, LIVE_FEED_LIMIT));
                    }
                )
                .subscribe();
        } catch {
            // Realtime not available — initial fetch is enough
        }

        return () => {
            try { sb?.removeChannel(channel); } catch { /* ignore */ }
        };
    }, [active, fetchInitial]);

    const mutate = useCallback(() => { fetchInitial(); }, [fetchInitial]);

    return { signals, isLoading, isError, mutate };
}
