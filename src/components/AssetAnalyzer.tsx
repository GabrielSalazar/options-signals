'use client';

import { useEffect, useState } from 'react';
import { scoreAsset } from '@/lib/asset-analysis';
import type { AssetAnalysisPayload, AssetVerdict } from '@/lib/types/analytics';

interface Props {
  payload: AssetAnalysisPayload;
  onVerdict?: (v: AssetVerdict) => void;
}

const verdictStyle: Record<AssetVerdict, { label: string; bg: string; color: string; border: string }> = {
  barato: { label: 'Barato', bg: '#D1FAE5', color: '#065F46', border: '#6EE7B7' },
  neutro: { label: 'Neutro', bg: '#FEF3C7', color: '#92400E', border: '#FCD34D' },
  caro:   { label: 'Caro',   bg: '#FEE2E2', color: '#991B1B', border: '#FCA5A5' },
};

const verdictDot: Record<AssetVerdict, string> = {
  barato: '#10B981',
  neutro: '#F59E0B',
  caro:   '#EF4444',
};

function RangeBar({ value, min, max, label }: { value: number; min: number; max: number; label: string }) {
  const range = max - min || 1;
  const pct = Math.max(0, Math.min(100, ((value - min) / range) * 100));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <span>{label}</span>
        <span style={{ color: 'var(--dw-ink)', fontWeight: 600 }}>Atual R$ {value.toFixed(2)}</span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, background: 'var(--dw-rule)' }}>
        <div
          style={{
            position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
            height: 14, width: 14, borderRadius: '50%', background: 'var(--dw-blue)',
            border: '2px solid white', boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
            left: `${pct}%`,
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dw-ink-muted)' }}>
        <span>Mínima R$ {min.toFixed(2)}</span>
        <span>Máxima R$ {max.toFixed(2)}</span>
      </div>
    </div>
  );
}

function OscLabel({ text, tooltip }: { text: string; tooltip: string }) {
  const [hovered, setHovered] = useState(false);
  return (
    <span
      style={{ position: 'relative', cursor: 'help', display: 'inline-block' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {text}
      {hovered && (
        <span style={{
          position: 'absolute', bottom: 'calc(100% + 8px)', left: 0,
          background: '#1a1f3a', color: '#e8eaf6',
          fontSize: 11, lineHeight: 1.5,
          padding: '7px 11px', borderRadius: 8,
          width: 230, display: 'block', textAlign: 'left',
          boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
          pointerEvents: 'none', zIndex: 100,
          whiteSpace: 'normal', fontWeight: 400,
        }}>
          {tooltip}
          <span style={{
            position: 'absolute', top: '100%', left: 16,
            border: '6px solid transparent', borderTopColor: '#1a1f3a', display: 'block',
          }} />
        </span>
      )}
    </span>
  );
}

function RsiGauge({ rsi }: { rsi: number }) {
  const pct = Math.max(0, Math.min(100, rsi));
  const color = rsi < 30 ? 'var(--dw-green)' : rsi > 70 ? 'var(--dw-red)' : 'var(--dw-yellow)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <OscLabel text="RSI 14" tooltip="Índice de Força Relativa: mede a velocidade e magnitude das variações de preço. Abaixo de 30 = sobrevendido (possível reversão de alta); acima de 70 = sobrecomprado (possível reversão de baixa)." />
        <span style={{ fontWeight: 700, color }}>{rsi.toFixed(1)}</span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, overflow: 'hidden', background: 'var(--dw-rule)' }}>
        <div style={{ position: 'absolute', inset: 0, left: 0, width: '30%', background: 'rgba(16,185,129,0.25)' }} />
        <div style={{ position: 'absolute', inset: 0, left: '30%', width: '40%', background: 'rgba(245,158,11,0.20)' }} />
        <div style={{ position: 'absolute', inset: 0, left: '70%', width: '30%', background: 'rgba(239,68,68,0.25)' }} />
        <div
          style={{
            position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
            height: 14, width: 14, borderRadius: '50%', background: 'var(--dw-blue)',
            border: '2px solid white', boxShadow: '0 1px 3px rgba(59,91,219,0.4)',
            left: `${pct}%`,
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dw-ink-muted)' }}>
        <span>Sobrevendido</span><span>Neutro</span><span>Sobrecomprado</span>
      </div>
    </div>
  );
}

function BollingerBar({ pctB }: { pctB: number }) {
  const pct = Math.max(0, Math.min(100, pctB * 100));
  const color = pctB < 0.20 ? 'var(--dw-green)' : pctB > 0.80 ? 'var(--dw-red)' : 'var(--dw-ink-mid)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <OscLabel text="Bollinger %B" tooltip="Posição do preço dentro das Bandas de Bollinger (20 períodos, 2σ). 0% = na banda inferior (sobrevendido), 100% = na banda superior (sobrecomprado). Abaixo de 20% sugere pressão compradora." />
        <span style={{ fontWeight: 700, color }}>{(pctB * 100).toFixed(0)}%</span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, background: 'var(--dw-rule)' }}>
        <div
          style={{
            position: 'absolute', inset: 0, left: 0, borderRadius: 999,
            width: `${pct}%`, background: 'var(--dw-blue)',
          }}
        />
        <div
          style={{
            position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
            height: 14, width: 14, borderRadius: '50%', background: 'var(--dw-blue)',
            border: '2px solid white', boxShadow: '0 1px 3px rgba(59,91,219,0.4)',
            left: `${pct}%`,
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dw-ink-muted)' }}>
        <span>Banda inferior</span><span>Banda superior</span>
      </div>
    </div>
  );
}

function MacdBar({ diff }: { diff: number }) {
  const bullish = diff >= 0;
  const color = bullish ? 'var(--dw-green)' : 'var(--dw-red)';
  const label = bullish ? 'Bullish' : 'Bearish';
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
      <OscLabel text="MACD (histograma)" tooltip="Diferença entre a linha MACD (EMA12−EMA26) e sua linha de sinal (EMA9). Positivo (bullish) = momentum de alta crescendo; negativo (bearish) = momentum de baixa. Cruzamento do zero sinaliza mudança de tendência." />
      <span style={{ fontWeight: 700, color }}>
        {diff > 0 ? '+' : ''}{diff.toFixed(3)}{' '}
        <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--dw-ink-muted)' }}>({label})</span>
      </span>
    </div>
  );
}

function StochGauge({ k, d }: { k: number; d: number }) {
  const pctK = Math.max(0, Math.min(100, k));
  const pctD = Math.max(0, Math.min(100, d));
  const colorK = k < 20 ? 'var(--dw-green)' : k > 80 ? 'var(--dw-red)' : 'var(--dw-ink-mid)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <OscLabel text="Stochastic K/D" tooltip="Oscilador de momentum 0–100. K = posição do preço na faixa dos últimos 14 períodos; D = média suavizada de K (3 dias). Abaixo de 20 = sobrevendido; acima de 80 = sobrecomprado." />
        <span style={{ fontWeight: 700, color: colorK }}>K {k.toFixed(0)} / D {d.toFixed(0)}</span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, overflow: 'hidden', background: 'var(--dw-rule)' }}>
        <div style={{ position: 'absolute', inset: 0, left: 0, width: '20%', background: 'rgba(16,185,129,0.25)' }} />
        <div style={{ position: 'absolute', inset: 0, left: '80%', width: '20%', background: 'rgba(239,68,68,0.25)' }} />
        {/* D line marker */}
        <div style={{
          position: 'absolute', top: 0, bottom: 0, width: 2, background: 'rgba(245,158,11,0.7)',
          left: `${pctD}%`, transform: 'translateX(-50%)',
        }} />
        {/* K dot */}
        <div style={{
          position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
          height: 14, width: 14, borderRadius: '50%', background: 'var(--dw-blue)',
          border: '2px solid white', boxShadow: '0 1px 3px rgba(59,91,219,0.4)',
          left: `${pctK}%`,
        }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dw-ink-muted)' }}>
        <span>Sobrevendido</span><span>Neutro</span><span>Sobrecomprado</span>
      </div>
    </div>
  );
}

function AdxBar({ adx }: { adx: number }) {
  const pct = Math.max(0, Math.min(100, adx));
  const color = adx < 25 ? 'var(--dw-ink-muted)' : adx < 50 ? 'var(--dw-blue)' : 'var(--dw-blue)';
  const label = adx < 25 ? 'Lateral' : adx < 50 ? 'Tendência' : 'Tendência forte';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <OscLabel text="ADX 14" tooltip="Força da tendência (não indica direção). Abaixo de 25 = mercado lateral/sem tendência; 25–50 = tendência moderada; acima de 50 = tendência muito forte. Útil para confirmar breakouts." />
        <span style={{ fontWeight: 700, color }}>{adx.toFixed(1)} <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--dw-ink-muted)' }}>({label})</span></span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, overflow: 'hidden', background: 'var(--dw-rule)' }}>
        <div style={{ position: 'absolute', inset: 0, left: 0, width: '25%', background: 'rgba(107,114,128,0.20)' }} />
        <div style={{ position: 'absolute', inset: 0, left: '25%', width: '25%', background: 'rgba(59,91,219,0.18)' }} />
        <div style={{ position: 'absolute', inset: 0, left: '50%', width: '50%', background: 'rgba(59,91,219,0.32)' }} />
        <div style={{
          position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
          height: 14, width: 14, borderRadius: '50%', background: 'var(--dw-blue)',
          border: '2px solid white', boxShadow: '0 1px 3px rgba(59,91,219,0.4)',
          left: `${pct}%`,
        }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--dw-ink-muted)' }}>
        <span>0 Lateral</span><span>25</span><span>50</span><span>100 Forte</span>
      </div>
    </div>
  );
}

function ZScoreBadge({ z }: { z: number }) {
  const color = z < -1 ? 'var(--dw-green)' : z > 0 ? 'var(--dw-red)' : 'var(--dw-yellow)';
  const label = z < -1 ? 'Abaixo da média' : z > 1 ? 'Acima da média' : 'Próximo da média';
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
      <OscLabel text="Z-Score vs MA20" tooltip="Distância do preço atual em relação à média de 20 dias, medida em desvios-padrão. Z < −1 = ativo muito abaixo da média histórica recente; Z > +1 = muito acima. Neutro entre −1 e +1." />
      <span style={{ fontWeight: 700, color }}>
        {z.toFixed(2)}{' '}
        <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--dw-ink-muted)' }}>({label})</span>
      </span>
    </div>
  );
}

export function AssetAnalyzer({ payload, onVerdict }: Props) {
  const { score, verdict, breakdown } = scoreAsset(payload);

  useEffect(() => {
    onVerdict?.(verdict);
  }, [verdict, onVerdict]);

  const vs = verdictStyle[verdict];
  const { preco_atual, ma20, ma50, ma200, faixa_52s_min, faixa_52s_max, rsi14, bollinger_pct_b, z_score_20, macd_diff, stoch_k, stoch_d, adx, preco_graham, preco_dcf } = payload;
  const preco_justo_mas = (ma20 + ma50 + ma200) / 3;

  const maChip = (label: string, ma: number) => {
    const pct = ((preco_atual - ma) / ma) * 100;
    const positive = pct >= 0;
    return (
      <span
        key={label}
        style={{
          padding: '2px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600,
          background: positive ? '#FEE2E2' : '#D1FAE5',
          color: positive ? '#991B1B' : '#065F46',
        }}
      >
        {label} {positive ? '+' : ''}{pct.toFixed(1)}%
      </span>
    );
  };

  const sectionStyle: React.CSSProperties = {
    background: 'var(--dw-bg-soft)',
    border: '1px solid var(--dw-rule-soft)',
    borderRadius: 10,
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  };

  return (
    <div style={{
      background: 'var(--dw-white)',
      border: '1px solid var(--dw-rule)',
      borderRadius: 12,
      padding: 20,
      boxShadow: '0 1px 4px rgba(15,17,23,0.07), 0 1px 2px rgba(15,17,23,0.04)',
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--dw-ink)', margin: 0 }}>{payload.ticker}</h3>
          <p style={{ fontSize: 13, color: 'var(--dw-ink-muted)', margin: 0 }}>R$ {preco_atual.toFixed(2)}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1, marginTop: 2 }}>
            <p style={{ fontSize: 12, color: 'var(--dw-ink-muted)', margin: 0 }}>
              Preço justo (MAs): <span style={{ fontWeight: 600, color: 'var(--dw-ink)' }}>R$ {preco_justo_mas.toFixed(2)}</span>
            </p>
            <p style={{ fontSize: 12, color: 'var(--dw-ink-muted)', margin: 0 }}>
              Preço justo (Graham): <span style={{ fontWeight: 600, color: 'var(--dw-ink)' }}>{preco_graham != null ? `R$ ${preco_graham.toFixed(2)}` : 'N/D'}</span>
            </p>
            <p style={{ fontSize: 12, color: 'var(--dw-ink-muted)', margin: 0 }}>
              Preço justo (DCF): <span style={{ fontWeight: 600, color: 'var(--dw-ink)' }}>{preco_dcf != null ? `R$ ${preco_dcf.toFixed(2)}` : 'N/D'}</span>
            </p>
          </div>
        </div>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', borderRadius: 8,
          background: vs.bg, color: vs.color,
          border: `1px solid ${vs.border}`,
          fontSize: 13, fontWeight: 700,
        }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: verdictDot[verdict], display: 'inline-block' }} />
          {vs.label}
          <span style={{ fontSize: 11, fontWeight: 400, opacity: 0.75 }}>({score}/10)</span>
        </div>
      </div>

      {/* 52-week range */}
      <div style={sectionStyle}>
        <RangeBar value={preco_atual} min={faixa_52s_min} max={faixa_52s_max} label="Posição na faixa 52 semanas" />
      </div>

      {/* Moving averages */}
      <div style={sectionStyle}>
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
          Médias móveis
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {maChip('MA20', ma20)}
          {maChip('MA50', ma50)}
          {maChip('MA200', ma200)}
        </div>
      </div>

      {/* Oscillators */}
      <div style={sectionStyle}>
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>
          Osciladores
        </p>
        <RsiGauge rsi={rsi14} />
        <BollingerBar pctB={bollinger_pct_b} />
        <ZScoreBadge z={z_score_20} />
        <MacdBar diff={macd_diff} />
        <StochGauge k={stoch_k} d={stoch_d} />
        <AdxBar adx={adx} />
      </div>

      {/* Score breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 4, paddingTop: 4, borderTop: '1px solid var(--dw-rule-soft)' }}>
        {(Object.entries(breakdown) as [string, number][]).map(([k, v]) => (
          <div key={k} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: 'var(--dw-ink-muted)', textTransform: 'capitalize' }}>{k}</div>
            <div style={{
              fontSize: 14, fontWeight: 700,
              color: v === 2 ? 'var(--dw-green)' : v === 1 ? 'var(--dw-yellow)' : 'var(--dw-red)',
            }}>{v}/2</div>
          </div>
        ))}
      </div>
    </div>
  );
}
