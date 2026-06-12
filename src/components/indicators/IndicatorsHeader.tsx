'use client';

import React from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';
import { tecnicaLabel, resumo } from '@/lib/indicators-narrative';

export function IndicatorsHeader({ p, valuationScore }: { p: IndicatorsPayload; valuationScore: number }) {
  const valLabel = valuationScore >= 7 ? 'descontado' : valuationScore >= 4 ? 'neutro' : 'caro';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: 'var(--dw-ink)' }}>{p.ticker}</h3>
        <span style={{ fontSize: 15, color: 'var(--dw-ink-muted)' }}>R$ {p.preco_atual.toFixed(2)}</span>
        <span style={{ fontSize: 12, color: 'var(--dw-ink-muted)' }}>🕐 {p.hora}</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, padding: '4px 12px', borderRadius: 8, background: '#ECFDF5', color: '#065F46', border: '1px solid #A7F3D0' }}>
          Valuation: {valLabel} {valuationScore}/10
        </span>
        <span style={{ fontSize: 12, fontWeight: 700, padding: '4px 12px', borderRadius: 8, background: '#FFF7ED', color: '#9A3412', border: '1px solid #FED7AA' }}>
          Técnica: {tecnicaLabel(p)}
        </span>
      </div>
      <p style={{ margin: 0, fontSize: 14, color: 'var(--dw-ink-light)' }}>{resumo(p)}</p>
    </div>
  );
}
