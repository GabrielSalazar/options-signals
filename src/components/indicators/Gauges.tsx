'use client';

import React from 'react';
import { MaChip } from '@/components/shared/MaChip';

const GREEN = 'var(--dw-green)';
const RED = 'var(--dw-red)';
const BLUE = 'var(--dw-blue)';

/** Gauge 0–100 com 3 zonas (verde/amarelo/vermelho) e marcador. */
export function ZoneGauge({
  label, value, display, lowPct = 30, highPct = 70, color,
}: { label: string; value: number; display: string; lowPct?: number; highPct?: number; color?: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--dw-ink-muted)' }}>
        <span>{label}</span>
        <span style={{ fontWeight: 700, color: color ?? 'var(--dw-ink)' }}>{display}</span>
      </div>
      <div style={{ position: 'relative', height: 6, width: '100%', borderRadius: 999, overflow: 'hidden', background: 'var(--dw-rule)' }}>
        <div style={{ position: 'absolute', inset: 0, left: 0, width: `${lowPct}%`, background: 'rgba(16,185,129,0.25)' }} />
        <div style={{ position: 'absolute', inset: 0, left: `${lowPct}%`, width: `${highPct - lowPct}%`, background: 'rgba(245,158,11,0.20)' }} />
        <div style={{ position: 'absolute', inset: 0, left: `${highPct}%`, width: `${100 - highPct}%`, background: 'rgba(239,68,68,0.25)' }} />
        <div style={{
          position: 'absolute', top: '50%', transform: 'translateX(-50%) translateY(-50%)',
          height: 14, width: 14, borderRadius: '50%', background: BLUE,
          border: '2px solid white', boxShadow: '0 1px 3px rgba(59,91,219,0.4)', left: `${pct}%`,
        }} />
      </div>
    </div>
  );
}

/** Linha rótulo→valor simples. */
export function StatRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
      <span style={{ color: 'var(--dw-ink-muted)', fontSize: 12 }}>{label}</span>
      <span style={{ fontWeight: 700, color: color ?? 'var(--dw-ink)' }}>{value}</span>
    </div>
  );
}

export { GREEN, RED, BLUE };
