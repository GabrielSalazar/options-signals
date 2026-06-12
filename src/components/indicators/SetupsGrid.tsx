'use client';

import React from 'react';
import type { SetupItem } from '@/lib/types/indicators';

const STATUS_STYLE: Record<string, { bg: string; color: string; border: string; label: string }> = {
  ativo:   { bg: '#D1FAE5', color: '#065F46', border: '#6EE7B7', label: 'ativo' },
  armado:  { bg: '#FEF3C7', color: '#92400E', border: '#FCD34D', label: 'armado' },
  inativo: { bg: '#F1F5F9', color: '#64748B', border: '#E2E8F0', label: 'inativo' },
};
const VIES_COLOR: Record<string, string> = { alta: 'var(--dw-green)', baixa: 'var(--dw-red)', neutro: 'var(--dw-ink-muted)' };

export function SetupsGrid({ setups }: { setups: SetupItem[] }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
      {setups.map((s) => {
        const st = STATUS_STYLE[s.status] ?? STATUS_STYLE.inativo;
        const dim = s.status === 'inativo';
        return (
          <div key={s.nome} style={{
            background: 'var(--dw-white)', border: '1px solid var(--dw-rule)', borderRadius: 10,
            padding: 12, opacity: dim ? 0.6 : 1, display: 'flex', flexDirection: 'column', gap: 6,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 700, fontSize: 13, color: VIES_COLOR[s.vies] }}>{s.nome}</span>
              <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: st.bg, color: st.color, border: `1px solid ${st.border}` }}>{st.label}</span>
            </div>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--dw-ink-muted)', lineHeight: 1.4 }}>{s.descricao}</p>
          </div>
        );
      })}
    </div>
  );
}
