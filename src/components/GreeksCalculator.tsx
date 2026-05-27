'use client';

import { useState, useMemo, useCallback } from 'react';
import { calcAll, callPrice, putPrice, calcD1, normalCDF, normalPDF } from '@/lib/black-scholes';
import { Slider } from '@/components/ui/slider';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

// ── Greek metadata ──────────────────────────────────────────────────────────

const GREEKS = [
  {
    key: 'delta', symbol: 'Δ', name: 'Delta',
    color: '#185FA5', precision: 4,
    desc: 'Variação do preço da opção por R$1 de variação no ativo. Delta=0.5 → opção sobe R$0,50 se ativo sobe R$1. Também é a probabilidade aproximada de vencer ITM.',
  },
  {
    key: 'gamma', symbol: 'Γ', name: 'Gamma',
    color: '#0F6E56', precision: 5,
    desc: 'Variação do Delta por R$1 de variação no ativo. Gamma alto = Delta muda rápido = re-hedging frequente. Maior para ATM e próximo do vencimento.',
  },
  {
    key: 'theta', symbol: 'Θ', name: 'Theta',
    color: '#993C1D', precision: 4,
    desc: 'Perda de valor por dia que passa (decay temporal). Sempre negativo para comprador de opção. Aumenta dramaticamente próximo do vencimento.',
  },
  {
    key: 'vega', symbol: 'ν', name: 'Vega',
    color: '#534AB7', precision: 4,
    desc: 'Variação do preço por 1% de variação na vol implícita. Vega=0.08 → opção vale R$0,08 a mais se vol sobe de 20% para 21%. Máximo ATM.',
  },
  {
    key: 'vanna', symbol: '∂', name: 'Vanna',
    color: '#854F0B', precision: 4,
    desc: 'Variação do Delta por 1% de variação na vol (ou variação do Vega por R$1 no ativo). Importante para hedging de vol surface — conecta risco direcional e risco de vol.',
  },
  {
    key: 'volga', symbol: '∂²', name: 'Volga',
    color: '#993556', precision: 4,
    desc: 'Variação do Vega por 1% de variação na vol. É o "Gamma da vol". Positivo e alto para opções OTM — elas se beneficiam de explosões de volatilidade (convexidade na vol).',
  },
] as const;

type ChartTab = 'payoff' | 'greeks' | 'comparison';

// ── Component ───────────────────────────────────────────────────────────────

export default function GreeksCalculator() {
  // State
  const [S, setS] = useState(100);
  const [K, setK] = useState(100);
  const [sigma, setSigma] = useState(25);
  const [T, setT] = useState(30);
  const [r, setR] = useState(14.75);
  const [q, setQ] = useState(0);
  const [optionType, setOptionType] = useState<'call' | 'put'>('call');
  const [chartTab, setChartTab] = useState<ChartTab>('payoff');

  // Core calculation (recalculates on any input change)
  const bs = useMemo(
    () => calcAll(S, K, T / 365, sigma / 100, r / 100, q / 100, optionType),
    [S, K, T, sigma, r, q, optionType],
  );

  // Chart data — computed for all tabs
  const chartData = useMemo(() => {
    const sigDec = sigma / 100;
    const tYr = T / 365;
    const rDec = r / 100;
    const qDec = q / 100;
    if (tYr <= 0 || sigDec <= 0) return [];

    const sqT = Math.sqrt(tYr);
    const range = 50;
    const points: Record<string, number | null>[] = [];

    for (let i = K - range; i <= K + range; i += 2) {
      if (i <= 0) continue;
      const d1i = calcD1(i, K, tYr, sigDec, rDec, qDec);
      const eqT = Math.exp(-qDec * tYr);

      const callP = callPrice(i, K, tYr, sigDec, rDec, qDec);
      const putP = putPrice(i, K, tYr, sigDec, rDec, qDec);

      const deltaCall = eqT * normalCDF(d1i);
      const deltaPut = eqT * (normalCDF(d1i) - 1);
      const gammaVal = (normalPDF(d1i) * eqT) / (i * sigDec * sqT);

      points.push({
        S: i,
        Call: +callP.toFixed(4),
        Put: +putP.toFixed(4),
        'Call Delta': +deltaCall.toFixed(4),
        'Put Delta': +deltaPut.toFixed(4),
        'Call Gamma': +gammaVal.toFixed(5),
      });
    }
    return points;
  }, [K, T, sigma, r, q]);

  const handleToggle = useCallback((type: 'call' | 'put') => setOptionType(type), []);

  // Greek values as an array aligned with GREEKS metadata
  const greekValues = [bs.delta, bs.gamma, bs.theta, bs.vega, bs.vanna, bs.volga];

  return (
    <div className="greeks-calculator">
      {/* ── Title ── */}
      <h3 className="font-serif text-2xl mb-1" style={{ color: 'var(--dw-ink)' }}>
        Gregas e Risco
      </h3>
      <p className="text-sm mb-6" style={{ color: 'var(--dw-ink-light)' }}>
        Calculadora interativa Black-Scholes com gregas de 1ª e 2ª ordem
      </p>

      {/* ── Toggle Call / Put ── */}
      <div className="greeks-toggle-group mb-5">
        <button
          className={`greeks-toggle-btn${optionType === 'call' ? ' active' : ''}`}
          onClick={() => handleToggle('call')}
        >
          CALL
        </button>
        <button
          className={`greeks-toggle-btn${optionType === 'put' ? ' active' : ''}`}
          onClick={() => handleToggle('put')}
        >
          PUT
        </button>
      </div>

      {/* ── Asset Parameters ── */}
      <div className="greeks-section mb-4">
        <div className="greeks-section-title">Parâmetros do Ativo</div>
        <div className="greeks-controls">
          <SliderControl label="S — Preço do ativo" value={S} suffix=" R$"
            min={50} max={200} step={1} onChange={setS} />
          <SliderControl label="K — Strike" value={K} suffix=" R$"
            min={50} max={200} step={1} onChange={setK} />
          <SliderControl label="σ — Volatilidade" value={sigma} suffix="%"
            min={5} max={100} step={1} onChange={setSigma} />
          <SliderControl label="T — Dias até vencimento" value={T} suffix=" dias"
            min={1} max={365} step={1} onChange={setT} />
        </div>
      </div>

      {/* ── Market Parameters ── */}
      <div className="greeks-section mb-5">
        <div className="greeks-section-title">Parâmetros de Mercado</div>
        <div className="greeks-controls">
          <SliderControl label="r — Taxa de juros (Selic)" value={r} suffix="%"
            min={0} max={20} step={0.25} onChange={setR} />
          <SliderControl label="q — Dividend yield" value={q} suffix="%"
            min={0} max={15} step={0.5} onChange={setQ} />
        </div>
      </div>

      {/* ── Summary Cards (Price, Moneyness, d1, d2) ── */}
      <div className="greeks-summary-grid mb-5">
        <SummaryCard
          label={`Preço da ${optionType === 'call' ? 'Call' : 'Put'}`}
          value={`R$ ${bs.price.toFixed(2)}`}
          color="var(--dw-green)"
        />
        <SummaryCard label="Moneyness" value={bs.moneyness} />
        <SummaryCard label="d₁" value={bs.d1.toFixed(3)} />
        <SummaryCard label="d₂" value={bs.d2.toFixed(3)} />
      </div>

      {/* ── Greek Cards (2 rows × 3) ── */}
      <div className="greeks-cards-grid mb-5">
        {GREEKS.map((g, i) => (
          <div key={g.key} className="greek-card" style={{ borderLeftColor: g.color }}>
            <div className="greek-card-header">
              <span className="greek-symbol" style={{ color: g.color }}>{g.symbol}</span>
              <div className="greek-info">
                <span className="greek-name">
                  {g.name} = <span style={{ color: g.color, fontWeight: 600 }}>
                    {greekValues[i].toFixed(g.precision)}
                  </span>
                </span>
              </div>
            </div>
            <p className="greek-desc">{g.desc}</p>
          </div>
        ))}
      </div>

      {/* ── Sensitivity ── */}
      <div className="greeks-section mb-5">
        <div className="greeks-section-title">Sensibilidade</div>
        <div className="greeks-sensitivity">
          <SensRow label="Se S subir R$1:" value={`R$ ${Math.abs(bs.delta).toFixed(4)}`} color="#185FA5" />
          <SensRow label="Se σ subir 1%:" value={`R$ ${Math.abs(bs.vega).toFixed(4)}`} color="#534AB7" />
          <SensRow label="Se passar 1 dia:" value={`R$ ${Math.abs(bs.theta).toFixed(4)}`} color="#993C1D" />
          <SensRow label="Probabilidade de vencer ITM:" value={`${(bs.probITM * 100).toFixed(1)}%`} color="#0F6E56" />
        </div>
      </div>

      {/* ── Charts ── */}
      <div className="greeks-section">
        <div className="greeks-section-title">Análises Gráficas</div>
        <div className="greeks-tab-buttons mb-3">
          {([
            ['payoff', 'Payoff'],
            ['greeks', 'Gregas vs Preço'],
            ['comparison', 'Call vs Put'],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              className={`greeks-tab-btn${chartTab === key ? ' active' : ''}`}
              onClick={() => setChartTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <div style={{ height: 300 }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              {chartTab === 'payoff' ? (
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.6} />
                  <XAxis dataKey="S" stroke="var(--dw-ink-muted)" fontSize={11} tickLine={false}
                    axisLine={false} tickFormatter={(v) => `R$${v}`} />
                  <YAxis stroke="var(--dw-ink-muted)" fontSize={11} tickLine={false} axisLine={false}
                    tickFormatter={(v) => `R$${v}`} />
                  <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number | string | undefined) => [typeof v === 'number' ? `R$ ${v.toFixed(2)}` : (v ?? '—'), undefined]}
                    labelFormatter={(l) => `Preço do Ativo: R$ ${l}`} />
                  <Legend />
                  <Line type="monotone" dataKey="Call" stroke="#185FA5" strokeWidth={2}
                    dot={false} />
                  <Line type="monotone" dataKey="Put" stroke="#0F6E56" strokeWidth={2}
                    dot={false} />
                </LineChart>
              ) : chartTab === 'greeks' ? (
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.6} />
                  <XAxis dataKey="S" stroke="var(--dw-ink-muted)" fontSize={11} tickLine={false}
                    axisLine={false} tickFormatter={(v) => `R$${v}`} />
                  <YAxis yAxisId="left" stroke="#185FA5" fontSize={11} tickLine={false}
                    axisLine={false} />
                  <YAxis yAxisId="right" orientation="right" stroke="#0F6E56" fontSize={11}
                    tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 12 }}
                    labelFormatter={(l) => `Preço do Ativo: R$ ${l}`} />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="Call Delta" stroke="#185FA5"
                    strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="Call Gamma" stroke="#0F6E56"
                    strokeWidth={2} dot={false} />
                </LineChart>
              ) : (
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--dw-rule)" opacity={0.6} />
                  <XAxis dataKey="S" stroke="var(--dw-ink-muted)" fontSize={11} tickLine={false}
                    axisLine={false} tickFormatter={(v) => `R$${v}`} />
                  <YAxis stroke="var(--dw-ink-muted)" fontSize={11} tickLine={false}
                    axisLine={false} />
                  <Tooltip contentStyle={{ background: 'white', border: '1px solid var(--dw-rule)', borderRadius: 8, fontSize: 12 }}
                    labelFormatter={(l) => `Preço do Ativo: R$ ${l}`} />
                  <Legend />
                  <Line type="monotone" dataKey="Call Delta" stroke="#185FA5"
                    strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Put Delta" stroke="#993C1D"
                    strokeWidth={2} dot={false} />
                </LineChart>
              )}
            </ResponsiveContainer>
          ) : (
            <div className="rounded-xl flex items-center justify-center h-full"
              style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule)' }}>
              <p className="text-sm" style={{ color: 'var(--dw-ink-muted)' }}>
                Ajuste os parâmetros acima para visualizar.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Footer note ── */}
      <p className="text-xs mt-4" style={{ color: 'var(--dw-ink-muted)' }}>
        Use os sliders para ver as gregas mudando em tempo real com B-S (taxa Selic ~{r}%).
        Todos os cálculos são client-side e funcionam offline.
      </p>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function SliderControl({
  label, value, suffix, min, max, step, onChange,
}: {
  label: string; value: number; suffix: string;
  min: number; max: number; step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="greeks-control-group">
      <div className="greeks-control-label">
        {label}: <span className="greeks-control-value">{value}{suffix}</span>
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

function SummaryCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="greeks-summary-card">
      <div className="greeks-summary-label">{label}</div>
      <div className="greeks-summary-value" style={color ? { color } : undefined}>{value}</div>
    </div>
  );
}

function SensRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="greeks-sens-row">
      <strong>{label}</strong>{' '}
      <span style={{ color, fontWeight: 600 }}>{value}</span>
    </div>
  );
}
