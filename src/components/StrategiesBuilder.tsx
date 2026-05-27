'use client';

import { useState, useMemo } from 'react';
import { Slider } from '@/components/ui/slider';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import {
  StrategyName,
  StrategyCategory,
  STRATEGY_META,
  // Existing
  getStraddleLegs,
  getStrangleLegs,
  getBullCallSpreadLegs,
  getBearPutSpreadLegs,
  getIronCondorLegs,
  // New — Puras
  getLongCallLegs,
  getShortCallLegs,
  getLongPutLegs,
  getShortPutLegs,
  // New — Com Ação
  getCoveredCallLegs,
  getProtectivePutLegs,
  // New — Spreads de crédito
  getBullPutSpreadLegs,
  getBearCallSpreadLegs,
  // New — Volatilidade vendida
  getShortStraddleLegs,
  getShortStrangleLegs,
  // New — Butterfly
  getButterflyCallLegs,
  // Core
  calculateStrategy,
  calculatePayoffCurve,
} from '@/lib/strategies';
import RiskSimulator from '@/components/RiskSimulator';
import HedgingSimulator from '@/components/HedgingSimulator';
import { fmtCcy } from '@/lib/format';

// Selic e dividend yield são fixados — não há UI para alterá-los hoje
const SELIC_PCT = 14.75;
const DIVIDEND_YIELD_PCT = 0;

// ── Strategy Card Grid Config ─────────────────────────────────────────────────

const CATEGORIES: { key: StrategyCategory; label: string; strategies: StrategyName[] }[] = [
  {
    key: 'puras',
    label: '📌 Posições Puras',
    strategies: ['longCall', 'shortCall', 'longPut', 'shortPut'],
  },
  {
    key: 'acao',
    label: '🏦 Com Ação (Stock)',
    strategies: ['coveredCall', 'protectivePut'],
  },
  {
    key: 'spreads',
    label: '📊 Spreads',
    strategies: ['bullCall', 'bearPut', 'bullPutSpread', 'bearCallSpread'],
  },
  {
    key: 'volatilidade',
    label: '🌊 Volatilidade',
    strategies: ['straddle', 'strangle', 'shortStraddle', 'shortStrangle', 'butterflyCall'],
  },
  {
    key: 'complexas',
    label: '🦅 Complexas',
    strategies: ['ironCondor'],
  },
];

const PROFILE_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  alta:   { color: '#0F6E56', bg: '#ECFDF5', border: '#A7F3D0' },
  baixa:  { color: '#B91C1C', bg: '#FEF2F2', border: '#FECACA' },
  neutro: { color: '#1D4ED8', bg: '#EFF6FF', border: '#BFDBFE' },
  renda:  { color: '#B45309', bg: '#FFFBEB', border: '#FDE68A' },
  hedge:  { color: '#6D28D9', bg: '#F5F3FF', border: '#DDD6FE' },
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function StrategiesBuilder() {
  const [strategy, setStrategy] = useState<StrategyName>('straddle');

  // Market parameters
  const [S, setS]         = useState(100);
  const [sigma, setSigma] = useState(25);
  const [T, setT]         = useState(30);
  const r = SELIC_PCT;
  const q = DIVIDEND_YIELD_PCT;

  // Strike states (K1–K5 shared across strategies)
  // K1 — single-strike strategies (Long/Short Call/Put, Straddles, Covered Call, Protective Put)
  //       and Butterfly center
  // K2 — lower strike for dual-strike strategies / Iron Condor put short
  // K3 — upper strike for dual-strike strategies / Iron Condor call short
  // K4 — Butterfly left wing / Iron Condor put long
  // K5 — Butterfly right wing / Iron Condor call long
  const [K1, setK1] = useState(100);
  const [K2, setK2] = useState(95);
  const [K3, setK3] = useState(105);
  const [K4, setK4] = useState(90);
  const [K5, setK5] = useState(110);

  const meta        = STRATEGY_META[strategy];
  const stockOffset = meta.hasStockComponent;

  const legs = useMemo(() => {
    switch (strategy) {
      // Posições Puras
      case 'longCall':      return getLongCallLegs(K1);
      case 'shortCall':     return getShortCallLegs(K1);
      case 'longPut':       return getLongPutLegs(K1);
      case 'shortPut':      return getShortPutLegs(K1);
      // Com Ação
      case 'coveredCall':   return getCoveredCallLegs(K1);
      case 'protectivePut': return getProtectivePutLegs(K1);
      // Straddle / Short Straddle — single strike
      case 'straddle':      return getStraddleLegs(K1);
      case 'shortStraddle': return getShortStraddleLegs(K1);
      // Dual-strike
      case 'strangle':      return getStrangleLegs(K2, K3);
      case 'shortStrangle': return getShortStrangleLegs(K2, K3);
      case 'bullCall':      return getBullCallSpreadLegs(K2, K3);
      case 'bearPut':       return getBearPutSpreadLegs(K2, K3);
      case 'bullPutSpread': return getBullPutSpreadLegs(K2, K3);
      case 'bearCallSpread':return getBearCallSpreadLegs(K2, K3);
      // Butterfly: left=K4, center=K1, right=K5
      case 'butterflyCall': return getButterflyCallLegs(K4, K1, K5);
      // Iron Condor: put_long=K4, put_short=K2, call_short=K3, call_long=K5
      case 'ironCondor':    return getIronCondorLegs(K4, K2, K3, K5);
      default:              return [];
    }
  }, [strategy, K1, K2, K3, K4, K5]);

  const result = useMemo(
    () => calculateStrategy(legs, S, T / 365, sigma / 100, r / 100, q / 100, stockOffset),
    [legs, S, T, sigma, r, q, stockOffset],
  );

  const chartData = useMemo(
    () => calculatePayoffCurve(legs, S, T / 365, sigma / 100, r / 100, q / 100, 0.4, 150, stockOffset),
    [legs, S, T, sigma, r, q, stockOffset],
  );

  const profileStyle = PROFILE_STYLE[meta.profile] ?? PROFILE_STYLE.neutro;

  // ── Strike panel helpers ───────────────────────────────────────────────────

  const isSingleStrike = ['longCall','shortCall','longPut','shortPut',
    'straddle','shortStraddle','coveredCall','protectivePut'].includes(strategy);

  const isDualStrike = ['strangle','shortStrangle','bullCall','bearPut',
    'bullPutSpread','bearCallSpread'].includes(strategy);

  const isButterfly   = strategy === 'butterflyCall';
  const isIronCondor  = strategy === 'ironCondor';

  const dualStrikeLabels: Record<string, [string, string]> = {
    strangle:       ['Strike Put (K₁)',              'Strike Call (K₂)'],
    shortStrangle:  ['Strike Put (K₁)',              'Strike Call (K₂)'],
    bullCall:       ['Strike Call Longa (K₁)',        'Strike Call Curta (K₂)'],
    bearPut:        ['Strike Put Longa (K₁)',         'Strike Put Curta (K₂)'],
    bullPutSpread:  ['Strike Put Longa — inferior (K₁)', 'Strike Put Curta — superior (K₂)'],
    bearCallSpread: ['Strike Call Curta — inferior (K₁)','Strike Call Longa — superior (K₂)'],
  };

  return (
    <div className="strategies-builder bg-white border border-dw-rule rounded-xl p-6 shadow-sm mb-6">
      <div className="mb-6 border-b-2 border-dw-ink pb-2">
        <h2 className="text-2xl font-serif text-dw-ink mb-1">Construtor de Estratégias</h2>
        <p className="text-sm text-dw-ink-muted">
          Simule e compare o payoff de operações estruturadas com múltiplas pernas.
        </p>
      </div>

      {/* ── Strategy Card Grid Selector ──────────────────────────────────── */}
      <div className="mb-6 space-y-4">
        {CATEGORIES.map((cat) => (
          <div key={cat.key}>
            <div className="text-[10px] font-bold text-dw-ink-muted uppercase tracking-widest mb-2">
              {cat.label}
            </div>
            <div className="flex flex-wrap gap-2">
              {cat.strategies.map((strat) => {
                const m          = STRATEGY_META[strat];
                const isSelected = strategy === strat;
                const ps         = PROFILE_STYLE[m.profile];
                return (
                  <button
                    key={strat}
                    onClick={() => setStrategy(strat)}
                    className={[
                      'flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all',
                      isSelected
                        ? 'border-dw-blue bg-dw-blue text-white shadow-md scale-[1.02]'
                        : 'border-dw-rule bg-white hover:border-dw-blue hover:bg-blue-50 text-dw-ink',
                    ].join(' ')}
                  >
                    <span className="text-lg leading-none">{m.icon}</span>
                    <div className="min-w-0">
                      <div className="text-xs font-bold leading-tight truncate">{m.label}</div>
                      <div className={`text-[10px] leading-tight truncate ${isSelected ? 'text-blue-100' : 'text-dw-ink-muted'}`}>
                        {m.labelPT}
                      </div>
                    </div>
                    {/* Profile badge — hidden when selected for contrast */}
                    {!isSelected && (
                      <span
                        className="text-[9px] font-bold rounded px-1.5 py-0.5 ml-1 whitespace-nowrap"
                        style={{ color: ps.color, background: ps.bg, border: `1px solid ${ps.border}` }}
                      >
                        {m.profile}
                      </span>
                    )}
                    {/* Unlimited loss warning */}
                    {m.unlimitedLoss && (
                      <span className="text-[9px] font-bold text-red-600 bg-red-50 border border-red-300 rounded px-1 py-0.5 ml-0.5">
                        ⚠️
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* ── Selected Strategy Info Banner ─────────────────────────────────── */}
      <div className="flex flex-wrap items-start gap-3 mb-6 p-4 rounded-xl border"
        style={{ background: profileStyle.bg, borderColor: profileStyle.border }}>
        <div className="text-3xl leading-none">{meta.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-dw-ink text-sm">
            {meta.label}
            <span className="text-dw-ink-muted font-normal ml-2">· {meta.labelPT}</span>
          </div>
          <div className="text-xs text-dw-ink-muted mt-0.5">{meta.description}</div>
        </div>
        <div className="flex flex-wrap gap-1.5 items-center">
          <span
            className="text-[10px] font-bold uppercase px-2 py-1 rounded-full border"
            style={{ color: profileStyle.color, background: 'white', borderColor: profileStyle.border }}
          >
            {meta.profile}
          </span>
          <span className="text-[10px] text-dw-ink-muted border border-dw-rule-soft rounded-full px-2 py-1 bg-white">
            {meta.numLegs} perna{meta.numLegs !== 1 ? 's' : ''}
          </span>
          {meta.unlimitedLoss && (
            <span className="text-[10px] font-bold text-red-700 bg-red-50 border border-red-300 rounded-full px-2 py-1">
              ⚠️ Risco Ilimitado
            </span>
          )}
          {meta.hasStockComponent && (
            <span className="text-[10px] text-purple-700 bg-purple-50 border border-purple-200 rounded-full px-2 py-1">
              🏦 Inclui posição em ação
            </span>
          )}
        </div>
      </div>

      {/* ── Main Grid: Controls + Chart ───────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left Column: Sliders */}
        <div className="lg:col-span-1 flex flex-col gap-6">

          {/* Strike Controls */}
          <div className="p-4 bg-dw-bg-soft border border-dw-rule-soft rounded-xl">
            <label className="block text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">
              Strikes da Estrutura
            </label>

            {/* Single-strike strategies */}
            {isSingleStrike && (
              <SliderControl
                label={
                  strategy === 'coveredCall'   ? 'Strike da Call Vendida (K)' :
                  strategy === 'protectivePut' ? 'Strike da Put Protetora (K)' :
                  'Strike (K)'
                }
                value={K1} min={50} max={200} step={1} onChange={setK1} suffix=" R$"
              />
            )}

            {/* Dual-strike strategies */}
            {isDualStrike && (() => {
              const [label2, label3] = dualStrikeLabels[strategy] ?? ['Strike 1 (K₁)', 'Strike 2 (K₂)'];
              return (
                <>
                  <SliderControl label={label2} value={K2} min={50} max={200} step={1} onChange={setK2} suffix=" R$" />
                  <div className="my-3" />
                  <SliderControl label={label3} value={K3} min={50} max={200} step={1} onChange={setK3} suffix=" R$" />
                </>
              );
            })()}

            {/* Butterfly: left (K4) · center (K1) · right (K5) */}
            {isButterfly && (
              <>
                <SliderControl label="Asa Esquerda (K₁)" value={K4} min={50} max={200} step={1} onChange={setK4} suffix=" R$" />
                <div className="my-3" />
                <SliderControl label="Strike Central (K₂ — pico)" value={K1} min={50} max={200} step={1} onChange={setK1} suffix=" R$" />
                <div className="my-3" />
                <SliderControl label="Asa Direita (K₃)" value={K5} min={50} max={200} step={1} onChange={setK5} suffix=" R$" />
              </>
            )}

            {/* Iron Condor: K4 · K2 · K3 · K5 */}
            {isIronCondor && (
              <>
                <SliderControl label="Put Longa — Asa inf. (K₁)" value={K4} min={50} max={200} step={1} onChange={setK4} suffix=" R$" />
                <div className="my-3" />
                <SliderControl label="Put Curta (K₂)"             value={K2} min={50} max={200} step={1} onChange={setK2} suffix=" R$" />
                <div className="my-3" />
                <SliderControl label="Call Curta (K₃)"            value={K3} min={50} max={200} step={1} onChange={setK3} suffix=" R$" />
                <div className="my-3" />
                <SliderControl label="Call Longa — Asa sup. (K₄)" value={K5} min={50} max={200} step={1} onChange={setK5} suffix=" R$" />
              </>
            )}
          </div>

          {/* Market Parameters */}
          <div className="p-4 bg-dw-bg-soft border border-dw-rule-soft rounded-xl">
            <label className="block text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">Mercado</label>
            <SliderControl label="Preço do Ativo (S)" value={S} min={50} max={200} step={1} onChange={setS} suffix=" R$" />
            <div className="my-3" />
            <SliderControl label="Volatilidade (σ)" value={sigma} min={5} max={100} step={1} onChange={setSigma} suffix="%" />
            <div className="my-3" />
            <SliderControl label="Vencimento (T)" value={T} min={1} max={365} step={1} onChange={setT} suffix=" dias" />
          </div>
        </div>

        {/* Right Column: Results + Chart */}
        <div className="lg:col-span-2 flex flex-col gap-6">

          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <SummaryCard
              label={result.totalCost > 0 ? 'Custo (Débito)' : 'Crédito Recebido'}
              value={fmtCcy(Math.abs(result.totalCost))}
              color={result.totalCost > 0 ? 'var(--dw-red)' : 'var(--dw-green)'}
            />
            <SummaryCard
              label="Max Profit"
              value={typeof result.maxProfit === 'number' ? fmtCcy(result.maxProfit) : result.maxProfit}
              color="var(--dw-green)"
            />
            <SummaryCard
              label={`Max Loss${meta.unlimitedLoss ? ' ⚠️' : ''}`}
              value={typeof result.maxLoss === 'number' ? fmtCcy(Math.abs(result.maxLoss)) : result.maxLoss}
              color={meta.unlimitedLoss ? '#B91C1C' : 'var(--dw-red)'}
              highlight={meta.unlimitedLoss}
            />
            <SummaryCard
              label="Breakevens"
              value={
                result.breakevens.length > 0
                  ? result.breakevens.map((b) => b.toFixed(2)).join(' | ')
                  : 'N/A'
              }
              mono
            />
          </div>

          {/* Greeks Row */}
          <div className="grid grid-cols-4 gap-3">
            <GreekMiniCard symbol="Δ" name="Delta" value={result.greeks.delta} color="#185FA5" />
            <GreekMiniCard symbol="Γ" name="Gamma" value={result.greeks.gamma} color="#0F6E56" />
            <GreekMiniCard symbol="Θ" name="Theta" value={result.greeks.theta} color="#993C1D" />
            <GreekMiniCard symbol="ν" name="Vega"  value={result.greeks.vega}  color="#534AB7" />
          </div>

          {/* Payoff Chart */}
          <div
            className="bg-dw-bg-soft border border-dw-rule-soft rounded-xl p-4 flex-grow"
            style={{ minHeight: '360px' }}
          >
            <h3 className="text-xs font-bold text-dw-blue uppercase tracking-widest mb-4">
              Gráfico de Payoff (P&amp;L)
            </h3>
            <ResponsiveContainer width="100%" height="90%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.6} />
                <XAxis
                  dataKey="S"
                  stroke="var(--dw-ink-muted)" fontSize={11}
                  tickLine={false} axisLine={false}
                  tickFormatter={(v) => `R$${Number(v).toFixed(0)}`}
                />
                <YAxis
                  stroke="var(--dw-ink-muted)" fontSize={11}
                  tickLine={false} axisLine={false}
                  tickFormatter={(v) => `R$${v}`}
                />
                <Tooltip
                  contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number | string | undefined) => [
                    typeof v === 'number' ? `R$ ${v.toFixed(2)}` : (v ?? '—'),
                    undefined,
                  ]}
                  labelFormatter={(l) => `Preço do Ativo: R$ ${Number(l).toFixed(2)}`}
                />
                <Legend />
                <ReferenceLine y={0} stroke="var(--dw-ink-muted)" strokeDasharray="3 3" />
                <ReferenceLine
                  x={S}
                  stroke="var(--dw-blue)"
                  strokeDasharray="3 3"
                  label={{ position: 'top', value: 'Preço Atual', fill: 'var(--dw-blue)', fontSize: 10 }}
                />
                <Line
                  type="monotone" dataKey="payoffExpiration"
                  name="P&L no Vencimento"
                  stroke="#185FA5" strokeWidth={3} dot={false}
                />
                <Line
                  type="monotone" dataKey="payoffToday"
                  name="P&L Hoje (T+0)"
                  stroke="#0F6E56" strokeWidth={2} strokeDasharray="5 5" dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Risco e Simulação Monte Carlo */}
      <RiskSimulator legs={legs} S0={S} T={T} sigma={sigma} r={r} q={q} />

      {/* Delta Hedging e Gamma Scalping */}
      <HedgingSimulator legs={legs} S0={S} T={T} sigma={sigma} r={r} q={q} />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SliderControl({
  label, value, suffix, min, max, step, onChange,
}: {
  label: string; value: number; suffix: string;
  min: number; max: number; step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs font-medium text-dw-ink-mid flex justify-between">
        <span>{label}</span>
        <span className="font-mono font-bold text-dw-blue">{value}{suffix}</span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([v]) => onChange(v)}
      />
    </div>
  );
}

function SummaryCard({
  label, value, color, mono = false, highlight = false,
}: {
  label: string; value: string; color?: string; mono?: boolean; highlight?: boolean;
}) {
  return (
    <div
      className={`border rounded-xl p-3 text-center ${
        highlight ? 'bg-red-50 border-red-200' : 'bg-dw-bg-soft border-dw-rule-soft'
      }`}
    >
      <div className="text-[11px] text-dw-ink-muted mb-1">{label}</div>
      <div
        className={`font-bold ${mono ? 'text-sm font-mono text-dw-ink mt-1' : 'text-lg font-mono'}`}
        style={color ? { color } : undefined}
      >
        {value}
      </div>
    </div>
  );
}

function GreekMiniCard({
  symbol, name, value, color,
}: { symbol: string; name: string; value: number; color: string }) {
  return (
    <div
      className="bg-white border border-dw-rule-soft rounded-lg p-3 flex items-center justify-between"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div>
        <div className="text-[10px] uppercase font-bold text-dw-ink-muted mb-1">{name}</div>
        <div className="text-sm font-mono font-bold" style={{ color: 'var(--dw-ink)' }}>
          {value.toFixed(4)}
        </div>
      </div>
      <div className="text-xl font-light" style={{ color }}>{symbol}</div>
    </div>
  );
}
