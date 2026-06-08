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
  StrategyId,
  StrategyCategory,
  STRATEGY_DEFS,
  instantiateLegs,
  defaultStrikes,
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

const CATEGORIES: { key: StrategyCategory; label: string; strategies: StrategyId[] }[] = [
  { key: 'puras', label: '📌 Posições Puras', strategies: ['longCall', 'shortCall', 'longPut', 'shortPut'] },
  { key: 'acao', label: '🏦 Com Ação (Stock)', strategies: ['coveredCall', 'protectivePut'] },
  { key: 'spreads', label: '📊 Spreads', strategies: ['bullCall', 'bearPut', 'bullPutSpread', 'bearCallSpread'] },
  { key: 'volatilidade', label: '🌊 Volatilidade', strategies: ['straddle', 'strangle', 'shortStraddle', 'shortStrangle', 'butterflyCall'] },
  { key: 'complexas', label: '🦅 Complexas', strategies: ['ironCondor'] },
  { key: 'razao', label: '⚖️ Razão / Backspread', strategies: ['callRatioBackspread', 'putRatioBackspread', 'callFrontRatioSpread', 'putFrontRatioSpread'] },
  { key: 'borboletasAvancadas', label: '🦋 Borboletas & Condores Avançados', strategies: ['ironButterfly', 'longCondor', 'brokenWingButterfly'] },
  { key: 'creditoHibridas', label: '🦎 Crédito Híbridas', strategies: ['jadeLizard', 'collar', 'seagull', 'riskReversal'] },
  { key: 'direcionalVol', label: '🎯 Direcionais (Vol)', strategies: ['strap', 'strip'] },
  { key: 'sinteticas', label: '🔁 Sintéticas / Arbitragem', strategies: ['boxSpread', 'conversion', 'reversal', 'syntheticLong', 'syntheticShort'] },
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
  const [strategy, setStrategy] = useState<StrategyId>('straddle');

  // Market parameters
  const [S, setS]         = useState(100);
  const [sigma, setSigma] = useState(25);
  const [T, setT]         = useState(30);
  const r = SELIC_PCT;
  const q = DIVIDEND_YIELD_PCT;

  // Strikes da estrutura — array dimensionado pela estratégia selecionada
  const [strikes, setStrikes] = useState<number[]>(() => defaultStrikes(STRATEGY_DEFS.straddle, 100));

  function selectStrategy(id: StrategyId) {
    setStrategy(id);
    setStrikes(defaultStrikes(STRATEGY_DEFS[id], S));
  }
  function setStrike(i: number, v: number) {
    setStrikes((prev) => prev.map((s, j) => (j === i ? v : s)));
  }

  const def        = STRATEGY_DEFS[strategy];
  const stockUnits = def.stockUnits;
  const numLegs    = def.legs.length + (stockUnits !== 0 ? 1 : 0);
  const hasStock   = stockUnits !== 0;

  const legs = useMemo(() => {
    const d = STRATEGY_DEFS[strategy];
    // guarda o render transitório logo após trocar de estratégia
    const s = strikes.length === d.strikeOffsets.length ? strikes : defaultStrikes(d, S);
    return instantiateLegs(d, s);
  }, [strategy, strikes, S]);

  const result = useMemo(
    () => calculateStrategy(legs, S, T / 365, sigma / 100, r / 100, q / 100, stockUnits),
    [legs, S, T, sigma, r, q, stockUnits],
  );

  const chartData = useMemo(
    () => calculatePayoffCurve(legs, S, T / 365, sigma / 100, r / 100, q / 100, 0.4, 150, stockUnits),
    [legs, S, T, sigma, r, q, stockUnits],
  );

  const profileStyle = PROFILE_STYLE[def.profile] ?? PROFILE_STYLE.neutro;

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
                const m          = STRATEGY_DEFS[strat];
                const isSelected = strategy === strat;
                const ps         = PROFILE_STYLE[m.profile];
                return (
                  <button
                    key={strat}
                    onClick={() => selectStrategy(strat)}
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
        <div className="text-3xl leading-none">{def.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="font-bold text-dw-ink text-sm">
            {def.label}
            <span className="text-dw-ink-muted font-normal ml-2">· {def.labelPT}</span>
          </div>
          <div className="text-xs text-dw-ink-muted mt-0.5">{def.description}</div>
        </div>
        <div className="flex flex-wrap gap-1.5 items-center">
          <span
            className="text-[10px] font-bold uppercase px-2 py-1 rounded-full border"
            style={{ color: profileStyle.color, background: 'white', borderColor: profileStyle.border }}
          >
            {def.profile}
          </span>
          <span className="text-[10px] text-dw-ink-muted border border-dw-rule-soft rounded-full px-2 py-1 bg-white">
            {numLegs} perna{numLegs !== 1 ? 's' : ''}
          </span>
          {def.unlimitedLoss && (
            <span className="text-[10px] font-bold text-red-700 bg-red-50 border border-red-300 rounded-full px-2 py-1">
              ⚠️ Risco Ilimitado
            </span>
          )}
          {hasStock && (
            <span className="text-[10px] text-purple-700 bg-purple-50 border border-purple-200 rounded-full px-2 py-1">
              🏦 Inclui posição em ação
            </span>
          )}
          {def.locked && (
            <span className="text-[10px] text-slate-700 bg-slate-100 border border-slate-300 rounded-full px-2 py-1">
              🔒 Payoff travado
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

            {def.strikeLabels.length === 0 ? (
              <p className="text-xs text-dw-ink-muted">Sem strikes (estrutura personalizada).</p>
            ) : (
              def.strikeLabels.map((label, i) => (
                <div key={`${strategy}-${i}`}>
                  {i > 0 && <div className="my-3" />}
                  <SliderControl
                    label={label}
                    value={strikes[i] ?? defaultStrikes(def, S)[i]}
                    min={50} max={200} step={1}
                    onChange={(v) => setStrike(i, v)}
                    suffix=" R$"
                  />
                </div>
              ))
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
              label={`Max Loss${def.unlimitedLoss ? ' ⚠️' : ''}`}
              value={typeof result.maxLoss === 'number' ? fmtCcy(Math.abs(result.maxLoss)) : result.maxLoss}
              color={def.unlimitedLoss ? '#B91C1C' : 'var(--dw-red)'}
              highlight={def.unlimitedLoss}
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
      <RiskSimulator legs={legs} S0={S} T={T} sigma={sigma} r={r} q={q} stockUnits={stockUnits} />

      {/* Delta Hedging e Gamma Scalping */}
      <HedgingSimulator legs={legs} S0={S} T={T} sigma={sigma} r={r} q={q} stockUnits={stockUnits} />
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
