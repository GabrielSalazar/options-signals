'use client';

import React from 'react';
import { useSignals } from '@/hooks/useSignals';
import SignalCard from '@/components/SignalCard';
import { Activity, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function LiveFeed() {
    const { signals, isLoading, isError, mutate } = useSignals(true);

    if (isError) return <div className="text-red-400 p-4">Falha ao carregar sinais ao vivo. verifique se o backend está rodando.</div>;

    return (
        <section className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                    </span>
                    <h2 className="text-2xl font-bold text-white">Live Market Feed</h2>
                    <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700">
                        Auto-refresh: 5s
                    </span>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => mutate()}
                    className="text-slate-400 hover:text-white"
                >
                    <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            {isLoading && !signals ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 bg-slate-900/50 rounded-lg animate-pulse border border-slate-800"></div>
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {signals?.slice(0, 6).map((signal, idx) => ( // Show top 6
                        <SignalCard key={`${signal.ticker}-${idx}`} signal={signal} />
                    ))}

                    {signals?.length === 0 && (
                        <div className="col-span-full py-12 text-center text-slate-500 bg-slate-900/30 rounded-lg border border-slate-800 border-dashed">
                            <Activity className="w-12 h-12 mx-auto mb-3 opacity-20" />
                            <p>Aguardando novos sinais do mercado...</p>
                        </div>
                    )}
                </div>
            )}
        </section>
    );
}
