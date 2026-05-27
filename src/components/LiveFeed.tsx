'use client';

import React from 'react';
import { useSignals } from '@/hooks/useSignals';
import SignalCard from '@/components/SignalCard';
import { Activity, RefreshCw } from 'lucide-react';

export default function LiveFeed() {
    const { signals, isLoading, isError, mutate } = useSignals(true);

    if (isError) {
        return (
            <div className="p-4 bg-red-50 border border-red-100 rounded-lg text-dw-red text-sm">
                Falha ao carregar sinais ao vivo. Verifique se o backend está rodando.
            </div>
        );
    }

    return (
        <section className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-dw-green opacity-60"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-dw-green"></span>
                    </span>
                    <h2 className="font-serif text-2xl font-bold text-dw-ink">Live Market Feed</h2>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-dw-bg-soft border border-dw-rule rounded text-dw-ink-muted uppercase tracking-wider">
                        Auto-refresh: 5s
                    </span>
                </div>
                <button
                    onClick={() => mutate()}
                    className="btn-secondary flex items-center gap-2 text-sm"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
            </div>

            {isLoading && !signals ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 bg-dw-bg-soft rounded-xl border border-dw-rule animate-pulse" />
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {signals?.slice(0, 6).map((signal, idx) => (
                        <SignalCard key={`${signal.ticker}-${idx}`} signal={signal} />
                    ))}

                    {signals?.length === 0 && (
                        <div className="col-span-full py-16 text-center text-dw-ink-muted bg-dw-bg-soft rounded-xl border border-dashed border-dw-rule">
                            <Activity className="w-12 h-12 mx-auto mb-3 opacity-20" />
                            <p>Aguardando novos sinais do mercado...</p>
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}
