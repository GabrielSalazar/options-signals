'use client';

import React from 'react';
import type { IndicatorsPayload } from '@/lib/types/indicators';
import { volReadLabel } from '@/lib/indicators-narrative';

export function VolReadCard({ p }: { p: IndicatorsPayload }) {
  const [lo, hi] = p.faixa_1sigma;
  return (
    <div style={{ background: 'var(--dw-bg-soft)', border: '1px solid var(--dw-rule-soft)', borderRadius: 10, padding: 16 }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-blue)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: '0 0 10px' }}>
        Leitura para opções
      </p>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
        <span style={{ color: 'var(--dw-ink-muted)' }}>Expected move ({p.dte_proximo_venc}d)</span>
        <span style={{ fontWeight: 700 }}>±R$ {p.expected_move.toFixed(2)} (±{p.expected_move_pct.toFixed(1)}%)</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)', marginBottom: 8 }}>
        <span>Faixa ±1σ</span>
        <span>R$ {lo.toFixed(2)} — R$ {hi.toFixed(2)}</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--dw-ink)', borderTop: '1px solid var(--dw-rule-soft)', paddingTop: 8 }}>
        {volReadLabel(p.vol_read)}
      </div>
    </div>
  );
}
