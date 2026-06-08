'use client';

import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, CartesianGrid,
} from 'recharts';
import { impliedVol } from '@/lib/black-scholes';
import type { AssetAnalysisPayload } from '@/lib/types/analytics';

const R = 0.1075;

interface Props {
  payload: AssetAnalysisPayload;
  selectedIV?: number;
}

export function VolatilityPanel({ payload, selectedIV }: Props) {
  const hvData = [
    { name: 'HV 20d', valor: parseFloat((payload.hv_20 * 100).toFixed(1)) },
    { name: 'HV 60d', valor: parseFloat((payload.hv_60 * 100).toFixed(1)) },
  ];

  const skewData = useMemo(() => {
    const calls: { strike: number; iv: number }[] = [];
    const puts:  { strike: number; iv: number }[] = [];

    for (const item of payload.chain) {
      if (item.negocios <= 0 || item.preco <= 0) continue;
      const T = 30 / 365; // fallback — será substituído por DTE real quando disponível
      const iv = impliedVol(item.preco, payload.preco_atual, item.strike, T, R, item.tipo);
      if (isNaN(iv) || iv <= 0 || iv > 3) continue;
      const point = { strike: item.strike, iv: parseFloat((iv * 100).toFixed(1)) };
      if (item.tipo === 'call') calls.push(point);
      else puts.push(point);
    }

    return { calls, puts };
  }, [payload]);

  const hasSkew = skewData.calls.length > 0 || skewData.puts.length > 0;

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800/60 p-5 space-y-6">
      <h3 className="text-base font-semibold text-white">Volatilidade Histórica vs Implícita</h3>

      {/* HV bars */}
      <div>
        <p className="text-xs text-zinc-400 mb-3">Volatilidade Histórica</p>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={hvData} margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#a1a1aa', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} unit="%" />
            <Tooltip
              contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8 }}
              formatter={(v: number | undefined) => [`${v ?? 0}%`, 'HV']}
            />
            <Bar dataKey="valor" fill="#3b82f6" radius={[4, 4, 0, 0]} name="HV (%)" />
            {selectedIV !== undefined && (
              <Bar dataKey={() => parseFloat((selectedIV * 100).toFixed(1))} fill="#f59e0b" radius={[4, 4, 0, 0]} name="IV selecionada (%)" />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Skew scatter */}
      {hasSkew && (
        <div>
          <p className="text-xs text-zinc-400 mb-3">Curva de Skew (IV por strike)</p>
          <ResponsiveContainer width="100%" height={180}>
            <ScatterChart margin={{ top: 0, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
              <XAxis
                dataKey="strike" type="number" name="Strike"
                tick={{ fill: '#a1a1aa', fontSize: 11 }}
                tickFormatter={(v) => `R$${v}`}
                domain={['auto', 'auto']}
              />
              <YAxis dataKey="iv" type="number" name="IV" unit="%" tick={{ fill: '#a1a1aa', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8 }}
                formatter={(v: number | undefined, name: string | undefined) => [`${v ?? 0}%`, name ?? '']}
                labelFormatter={() => ''}
              />
              <Legend wrapperStyle={{ color: '#a1a1aa', fontSize: 12 }} />
              {skewData.calls.length > 0 && (
                <Scatter name="Calls" data={skewData.calls} fill="#34d399" opacity={0.8} />
              )}
              {skewData.puts.length > 0 && (
                <Scatter name="Puts" data={skewData.puts} fill="#f87171" opacity={0.8} />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {!hasSkew && (
        <p className="text-sm text-zinc-500">Nenhuma opção com volume disponível para calcular o skew.</p>
      )}
    </div>
  );
}
