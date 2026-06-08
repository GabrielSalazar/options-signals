'use client';

import { useState, useMemo, type ReactNode } from 'react';
import { runMonteCarlo, MonteCarloParams } from '@/lib/monte-carlo';
import { Leg } from '@/lib/strategies';
import { Slider } from '@/components/ui/slider';
import { fmtCcy } from '@/lib/format';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, ReferenceLine, Cell
} from 'recharts';

type PathPoint = { day: number } & Record<string, number>;

interface Props {
  legs: Leg[];
  S0: number;
  T: number;
  sigma: number;
  r: number;
  q: number;
  stockUnits: number;
}

export default function RiskSimulator({ legs, S0, T, sigma, r, q, stockUnits }: Props) {
  const [numPaths, setNumPaths] = useState(10000);
  const [mu, setMu] = useState(10); // Drift (annualized return expectation)

  const mcParams: MonteCarloParams = useMemo(() => ({
    S0,
    mu: mu / 100,
    sigma: sigma / 100,
    T: T / 365,
    steps: T, // 1 step per day
    numPaths,
    legs,
    r: r / 100,
    q: q / 100,
    stockUnits,
  }), [S0, mu, sigma, T, numPaths, legs, r, q, stockUnits]);

  // Run calculation (could be heavy on main thread if numPaths is very large, but 10k is fast)
  const result = useMemo(() => {
    if (legs.length === 0 || T <= 0) return null;
    return runMonteCarlo(mcParams);
  }, [mcParams, T, legs.length]);

  // Memoizado: evita recomputar T+1 pontos × N paths em cada render do parent (tooltip hover, etc.)
  const pathsData: PathPoint[] = useMemo(() => {
    if (!result) return [];
    const data: PathPoint[] = [];
    for (let t = 0; t <= T; t++) {
      const point: PathPoint = { day: t };
      result.paths.forEach((path, i) => {
        point[`path${i}`] = path[t];
      });
      data.push(point);
    }
    return data;
  }, [result, T]);

  // Memoizado + reduce em vez de Math.min/max(...arr) — evita stack overflow com 50k paths
  const histogramData = useMemo(() => {
    if (!result || result.pnlDistribution.length === 0) return [];
    let minPnl = Infinity, maxPnl = -Infinity;
    for (const v of result.pnlDistribution) {
      if (v < minPnl) minPnl = v;
      if (v > maxPnl) maxPnl = v;
    }
    const bins = 50;
    const binWidth = (maxPnl - minPnl) / bins;
    if (binWidth === 0) return [];

    const histogramMap = new Map<number, number>();
    for (const pnl of result.pnlDistribution) {
      const binIndex = Math.floor((pnl - minPnl) / binWidth);
      const binCenter = minPnl + (binIndex + 0.5) * binWidth;
      const key = Math.round(binCenter * 100) / 100;
      histogramMap.set(key, (histogramMap.get(key) || 0) + 1);
    }
    return Array.from(histogramMap.entries())
      .map(([pnl, count]) => ({ pnl, count }))
      .sort((a, b) => a.pnl - b.pnl);
  }, [result]);

  if (!result) return null;

  return (
    <div className="risk-simulator mt-8 bg-white border border-dw-rule rounded-xl p-6 shadow-sm">
      <div className="mb-6 border-b-2 border-dw-ink pb-2">
        <h2 className="text-xl font-serif text-dw-ink mb-1">Risk Management & Monte Carlo</h2>
        <p className="text-sm text-dw-ink-muted">
          Simulação com {numPaths.toLocaleString()} caminhos via Movimento Browniano Geométrico.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
        <div className="p-4 bg-dw-bg-soft border border-dw-rule-soft rounded-xl">
          <label className="block text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">Parâmetros Simulação</label>
          <div className="flex flex-col gap-2">
            <div className="text-xs font-medium text-dw-ink-mid flex justify-between">
              <span>Caminhos (N)</span>
              <span className="font-mono font-bold text-dw-blue">{numPaths.toLocaleString()}</span>
            </div>
            <Slider value={[numPaths]} min={1000} max={50000} step={1000} onValueChange={([v]) => setNumPaths(v)} />
          </div>
          <div className="my-4"></div>
          <div className="flex flex-col gap-2">
            <div className="text-xs font-medium text-dw-ink-mid flex justify-between">
              <span>Drift Esperado (μ)</span>
              <span className="font-mono font-bold text-dw-blue">{mu}% a.a.</span>
            </div>
            <Slider value={[mu]} min={-50} max={50} step={1} onValueChange={([v]) => setMu(v)} />
          </div>
        </div>

        <div className="lg:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Win Rate" value={`${(result.winRate * 100).toFixed(1)}%`} color={result.winRate > 0.5 ? 'var(--dw-green)' : 'var(--dw-ink)'} />
          <StatCard label="PnL Médio Estimado" value={fmtCcy(result.meanPnl)} color={result.meanPnl > 0 ? 'var(--dw-green)' : 'var(--dw-red)'} />
          <StatCard label="VaR (95%)" value={fmtCcy(result.var95)} color="var(--dw-red)" desc="Pior caso (5%)" />
          <StatCard label="CVaR (95%)" value={fmtCcy(result.cvar95)} color="var(--dw-red)" desc="Média do 5% pior" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4" style={{ height: 350 }}>
          <h3 className="text-xs font-bold text-dw-blue uppercase tracking-widest mb-2">Simulação de Caminhos do Ativo</h3>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={pathsData} margin={{ top: 10, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
              <XAxis dataKey="day" fontSize={10} tickFormatter={(v) => `D+${v}`} />
              <YAxis domain={['auto', 'auto']} fontSize={10} tickFormatter={(v) => `R$${v}`} />
              <Tooltip formatter={fmtCcy} labelFormatter={(l) => `Dia ${l}`} contentStyle={{ fontSize: 11 }} />
              {result.paths.map((_, i) => (
                <Line key={i} type="monotone" dataKey={`path${i}`} stroke={`rgba(24, 95, 165, ${Math.max(0.05, 5 / result.paths.length)})`} strokeWidth={1} dot={false} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4" style={{ height: 350 }}>
          <h3 className="text-xs font-bold text-dw-blue uppercase tracking-widest mb-2">Distribuição de P&L no Vencimento</h3>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={histogramData} margin={{ top: 10, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.4} />
              <XAxis dataKey="pnl" fontSize={10} tickFormatter={(v) => `R$${Math.round(v)}`} />
              <YAxis fontSize={10} />
              <Tooltip cursor={{ fill: 'rgba(0,0,0,0.05)' }} formatter={(val: number | string | undefined) => [val ?? '—', 'Frequência'] as [number | string, string]} labelFormatter={(l: ReactNode) => `PnL: R$ ${Number(l).toFixed(2)}`} contentStyle={{ fontSize: 11 }} />
              <ReferenceLine x={0} stroke="var(--dw-ink)" strokeDasharray="3 3" />
              <ReferenceLine x={result.var95} stroke="var(--dw-red)" strokeDasharray="3 3" label={{ position: 'top', value: 'VaR 95%', fill: 'var(--dw-red)', fontSize: 10 }} />
              <Bar dataKey="count">
                {histogramData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? 'var(--dw-green)' : 'var(--dw-red)'} fillOpacity={0.7} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color, desc }: { label: string; value: string; color: string; desc?: string }) {
  return (
    <div className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4 flex flex-col justify-center text-center">
      <div className="text-[11px] text-dw-ink-muted mb-1 uppercase font-bold tracking-widest">{label}</div>
      <div className="text-xl font-mono font-bold" style={{ color }}>{value}</div>
      {desc && <div className="text-[10px] text-dw-ink-light mt-1">{desc}</div>}
    </div>
  );
}
