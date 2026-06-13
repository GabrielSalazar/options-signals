'use client';

import React from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';
import { ZoneGauge, StatRow } from './Gauges';
import { MaChip } from '@/components/shared/MaChip';

const sectionStyle: React.CSSProperties = {
  background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule-soft)',
  borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
};
const titleStyle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase',
  letterSpacing: '0.1em', margin: 0,
};

export function MomentoPanel({ p }: { p: IndicatorsPayload }) {
  const rsiColor = p.rsi14 < 30 ? 'var(--dw-green)' : p.rsi14 > 70 ? 'var(--dw-red)' : 'var(--dw-yellow)';
  return (
    <div style={sectionStyle}>
      <p style={titleStyle}>Momento</p>
      <ZoneGauge label="RSI 14" value={p.rsi14} display={p.rsi14.toFixed(1)} color={rsiColor} />
      <ZoneGauge label="Stochastic K/D" value={p.stoch_k} display={`K ${p.stoch_k.toFixed(0)} / D ${p.stoch_d.toFixed(0)}`} lowPct={20} highPct={80} />
      <StatRow label="Volume rel. 20d" value={`${p.vol_ratio.toFixed(1)}×`} color={p.vol_ratio >= 1.5 ? 'var(--dw-green)' : undefined} />
    </div>
  );
}

export function TendenciaPanel({ p }: { p: IndicatorsPayload }) {
  const maPct = (ma: number) => ((p.preco_atual - ma) / ma) * 100;
  const adxColor = p.adx >= 25 ? 'var(--dw-blue)' : 'var(--dw-ink-muted)';
  const adxLabel = p.adx < 25 ? 'lateral' : p.adx < 50 ? 'tendência' : 'tendência forte';
  return (
    <div style={sectionStyle}>
      <p style={titleStyle}>Tendência</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        <MaChip label="MA20" pct={maPct(p.ma20)} />
        <MaChip label="MA50" pct={maPct(p.ma50)} />
        <MaChip label="MA200" pct={maPct(p.ma200)} />
      </div>
      <StatRow label="ADX 14" value={`${p.adx.toFixed(1)} — ${adxLabel}`} color={adxColor} />
      <StatRow label="MACD (hist.)" value={`${p.macd_diff > 0 ? '+' : ''}${p.macd_diff.toFixed(3)}`} color={p.macd_diff >= 0 ? 'var(--dw-green)' : 'var(--dw-red)'} />
    </div>
  );
}

export function ReversaoPanel({ p }: { p: IndicatorsPayload }) {
  const zColor = p.z_score_20 < -1 ? 'var(--dw-green)' : p.z_score_20 > 1 ? 'var(--dw-red)' : 'var(--dw-yellow)';
  return (
    <div style={sectionStyle}>
      <p style={titleStyle}>Reversão</p>
      <ZoneGauge label="Bollinger %B" value={p.bollinger_pct_b * 100} display={`${(p.bollinger_pct_b * 100).toFixed(0)}%`} lowPct={20} highPct={80} />
      <StatRow label="Z-Score vs MA20" value={p.z_score_20.toFixed(2)} color={zColor} />
      <StatRow label="ATR 14" value={`R$ ${p.atr14.toFixed(2)} (${(p.atr14 / p.preco_atual * 100).toFixed(1)}%)`} />
      <StatRow label="Distância do VWAP" value={`${p.vwap_dist_pct > 0 ? '+' : ''}${p.vwap_dist_pct.toFixed(1)}%`} color={p.vwap_dist_pct >= 0 ? 'var(--dw-green)' : 'var(--dw-red)'} />
    </div>
  );
}

export function VolatilidadePanel({ p }: { p: IndicatorsPayload }) {
  const ivTxt = p.iv_atm != null ? `${(p.iv_atm * 100).toFixed(0)}%` : '—';
  const ratioTxt = p.iv_hv_ratio != null ? `${p.iv_hv_ratio.toFixed(2)}×` : 'indisponível';
  return (
    <div style={{ ...sectionStyle, border: '1.5px solid var(--dw-blue)' }}>
      <p style={titleStyle}>Volatilidade</p>
      <StatRow label="IV ATM × HV20" value={`${ivTxt} vs ${(p.hv_20 * 100).toFixed(0)}%`} />
      <StatRow label="IV / HV" value={ratioTxt} color="var(--dw-blue)" />
      <StatRow label="σ20 anualizada" value={`${(p.sigma_20 * 100).toFixed(0)}%`} />
    </div>
  );
}
