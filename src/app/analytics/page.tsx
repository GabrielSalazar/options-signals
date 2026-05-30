'use client';

import { useState, useMemo, useCallback } from 'react';
import { Search, TrendingUp, BarChart2 } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { fetchSignalHistory, fetchAnalytics } from '@/lib/api';
import { Signal } from '@/types/signals';
import dynamic from 'next/dynamic';

const IVSurface = dynamic(() => import('@/components/IVSurface'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center" style={{ height: 420 }}>
      <span className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin"
        style={{ borderColor: 'var(--dw-rule)', borderTopColor: 'var(--dw-blue)' }} />
    </div>
  ),
});

const VolatilitySkew = dynamic(() => import('@/components/VolatilitySkew'), {
  ssr: false,
});

const GreeksCalculator = dynamic(() => import('@/components/GreeksCalculator'), {
  ssr: false,
  loading: () => (
    <div className="card flex items-center justify-center" style={{ height: 600 }}>
      <span className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin"
        style={{ borderColor: 'var(--dw-rule)', borderTopColor: 'var(--dw-blue)' }} />
    </div>
  ),
});


interface AnalyticsStats {
  ticker: string;
  total: number;
  calls: number;
  puts: number;
  avg_score: number;
}

export default function AnalyticsPage() {
  const [tickerInput, setTickerInput] = useState('PETR4');
  const [ticker, setTicker] = useState('');
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState<AnalyticsStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async () => {
    const t = tickerInput.trim().toUpperCase();
    if (!t) return;
    setLoading(true);
    setError(null);
    setSignals([]);
    setStats(null);
    try {
      const [sigs, statsData] = await Promise.all([
        fetchSignalHistory(200, t),
        fetchAnalytics(t),
      ]);
      setSignals(sigs);
      setStats(statsData);
      setTicker(t);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e?.message || 'Falha ao buscar dados.');
    } finally {
      setLoading(false);
    }
  }, [tickerInput]);

  // ── Volatility Smile data ──────────────────────────────────────────────────
  const smileData = useMemo(() => {
    if (!signals.length) return [];
    const byStrike = new Map<number, { calls: number[]; puts: number[] }>();
    signals.forEach((s) => {
      const key = Math.round(s.strike_ref * 10) / 10;
      if (!byStrike.has(key)) byStrike.set(key, { calls: [], puts: [] });
      const bucket = byStrike.get(key)!;
      if (s.tipo_sinal === 'CALL') bucket.calls.push(s.iv_hist);
      else bucket.puts.push(s.iv_hist);
    });
    const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
    return Array.from(byStrike.entries())
      .sort(([a], [b]) => a - b)
      .map(([strike, { calls, puts }]) => ({
        strike,
        CALL: avg(calls) !== null ? +avg(calls)!.toFixed(1) : null,
        PUT: avg(puts) !== null ? +avg(puts)!.toFixed(1) : null,
      }));
  }, [signals]);

  // ── IV Surface data ────────────────────────────────────────────────────────
  const surfaceData = useMemo(() =>
    signals.map((s) => ({
      strike: s.strike_ref,
      expiry: `${String(s.mes_venc).padStart(2, '0')}/${s.ano_venc}`,
      iv: s.iv_hist,
      tipo: s.tipo_sinal as 'CALL' | 'PUT',
    })),
    [signals],
  );


  return (
    <div className="main-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="label mb-2">Exposição e volatilidade</div>
          <h1 className="font-serif">Analytics & Volatility</h1>
          <p className="mt-2 text-dw-ink-light text-base">
            Superfície de Volatilidade, GEX (Gamma Exposure) e Painel de Gregas.
          </p>
        </div>
      </div>

      {/* Ticker selector */}
      <div className="card mb-6">
        <div className="label mb-3">Selecionar ativo</div>
        <div className="flex gap-3 items-center flex-wrap">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && analyze()}
            placeholder="Ex: PETR4, VALE3, BOVA11"
            className="rounded-lg px-3 py-2.5 text-sm font-mono w-44 focus:outline-none focus:ring-2"
            style={{
              border: '1.5px solid var(--dw-rule)',
              background: 'var(--dw-bg-soft)',
              color: 'var(--dw-ink)',
              '--tw-ring-color': 'var(--dw-blue)',
            } as React.CSSProperties}
          />
          <button
            onClick={analyze}
            disabled={loading}
            className="btn-demo flex items-center gap-2 disabled:opacity-50"
            style={{ background: 'var(--dw-blue)' }}
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Analisar
          </button>

          {stats && (
            <div className="flex items-center gap-4 text-sm ml-2">
              <span className="font-bold font-mono" style={{ color: 'var(--dw-ink)' }}>{stats.ticker}</span>
              <span style={{ color: 'var(--dw-ink-muted)' }}>{stats.total} sinais</span>
              <span className="ct-pill" style={{ background: 'var(--dw-green)20', color: 'var(--dw-green)' }}>
                {stats.calls} CALL
              </span>
              <span className="ct-pill" style={{ background: 'var(--dw-red)20', color: 'var(--dw-red)' }}>
                {stats.puts} PUT
              </span>
              <span style={{ color: 'var(--dw-ink-muted)' }}>Score médio: <strong>{stats.avg_score}</strong></span>
            </div>
          )}
        </div>
        {error && (
          <p className="text-sm mt-3" style={{ color: 'var(--dw-red)' }}>{error}</p>
        )}
      </div>

      {/* Volatility Smile + GEX */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="card lg:col-span-2">
          <div className="label mb-1">Volatility Smile</div>
          <h3 className="font-serif text-lg mb-1">IV Histórica × Strike</h3>
          {ticker && (
            <p className="text-xs mb-4" style={{ color: 'var(--dw-ink-muted)' }}>
              Média de IV histórica por strike — baseado em {signals.length} sinais de {ticker}
            </p>
          )}
          {!ticker && (
            <div className="rounded-xl flex items-center justify-center" style={{ height: 280, background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
              <div className="text-center">
                <TrendingUp className="w-10 h-10 mx-auto mb-2" style={{ color: 'var(--dw-rule)' }} />
                <p className="text-sm" style={{ color: 'var(--dw-ink-muted)' }}>Selecione um ativo acima</p>
              </div>
            </div>
          )}
          {ticker && smileData.length === 0 && (
            <div className="rounded-xl flex items-center justify-center" style={{ height: 280, background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
              <p className="text-sm" style={{ color: 'var(--dw-ink-muted)' }}>Sem sinais suficientes para gerar o smile.</p>
            </div>
          )}
          {smileData.length > 0 && (
            <div style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={smileData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.6} />
                  <XAxis
                    dataKey="strike"
                    stroke="var(--dw-ink-muted)"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `R$${v}`}
                  />
                  <YAxis
                    stroke="var(--dw-ink-muted)"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number | undefined, name: string | undefined) => [`${v?.toFixed(1) ?? '—'}%`, `IV ${name ?? ''}`]}
                    labelFormatter={(l) => `Strike: R$ ${l}`}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="CALL" stroke="var(--dw-blue)" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                  <Line type="monotone" dataKey="PUT" stroke="var(--dw-red)" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* GEX Panel */}
        <div className="card">
          <div className="label mb-1">Market Maker Exposure</div>
          <h3 className="font-serif text-lg mb-2">Gamma Exposure (GEX)</h3>
          <p className="text-sm leading-relaxed mb-6" style={{ color: 'var(--dw-ink-light)' }}>
            Zonas de suporte e resistência magnéticas geradas pelo delta hedge dos formadores de mercado.
          </p>
          {signals.length > 0 ? (
            <div className="flex flex-col gap-3">
              {[
                {
                  label: 'Zero Gamma Level',
                  value: `R$ ${(signals.reduce((a, s) => a + s.preco_acao, 0) / signals.length).toFixed(2)}`,
                  color: 'var(--dw-ink-mid)',
                },
                {
                  label: 'Max Call GEX Strike',
                  value: `R$ ${Math.max(...signals.filter(s => s.tipo_sinal === 'CALL').map(s => s.strike_ref)).toFixed(2)}`,
                  color: 'var(--dw-green)',
                },
                {
                  label: 'Max Put GEX Strike',
                  value: `R$ ${Math.min(...signals.filter(s => s.tipo_sinal === 'PUT').map(s => s.strike_ref)).toFixed(2)}`,
                  color: 'var(--dw-red)',
                },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded-lg p-3" style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
                  <span className="text-xs block mb-1" style={{ color: 'var(--dw-ink-muted)' }}>{label}</span>
                  <span className="text-xl font-mono font-bold" style={{ color }}>{value}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {[
                { label: 'Zero Gamma Level', value: '—', color: 'var(--dw-ink-mid)' },
                { label: 'Max Call GEX Strike', value: '—', color: 'var(--dw-green)' },
                { label: 'Max Put GEX Strike', value: '—', color: 'var(--dw-red)' },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded-lg p-3" style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
                  <span className="text-xs block mb-1" style={{ color: 'var(--dw-ink-muted)' }}>{label}</span>
                  <span className="text-xl font-mono font-bold" style={{ color }}>{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Volatility Skew (IV vs HV) */}
      <VolatilitySkew signals={signals} ticker={ticker} />

      {/* ── Bloco 2: Gregas Interativo ── */}
      <div className="my-6">
        <GreeksCalculator 
           realData={signals.length > 0 ? {
              S: signals[0].preco_acao,
              K: signals[0].strike_ref,
              T: signals[0].dte,
              sigma: signals[0].iv_hist,
              optType: signals[0].tipo_sinal.toLowerCase() as 'call' | 'put'
           } : undefined}
        />
      </div>

      {/* IV Surface */}
      <div className="card">
        <div className="label mb-1">Superfície de Volatilidade</div>
        <h3 className="font-serif text-lg mb-2">IV Surface — Strike × Vencimento</h3>
        {ticker && surfaceData.length > 0 && (
          <p className="text-xs mb-4" style={{ color: 'var(--dw-ink-muted)' }}>
            {surfaceData.length} pontos de {ticker} · CALL em azul · PUT em vermelho
          </p>
        )}
        {!ticker && (
          <div className="rounded-xl flex items-center justify-center" style={{ height: 420, background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
            <div className="text-center">
              <BarChart2 className="w-10 h-10 mx-auto mb-2" style={{ color: 'var(--dw-rule)' }} />
              <p className="text-sm font-medium" style={{ color: 'var(--dw-ink-muted)' }}>Selecione um ativo para gerar a superfície 3D</p>
            </div>
          </div>
        )}
        {ticker && surfaceData.length === 0 && (
          <div className="rounded-xl flex items-center justify-center" style={{ height: 200, background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
            <p className="text-sm" style={{ color: 'var(--dw-ink-muted)' }}>Sem dados suficientes para a superfície.</p>
          </div>
        )}
        {surfaceData.length > 0 && <IVSurface data={surfaceData} />}
      </div>
    </div>
  );
}
