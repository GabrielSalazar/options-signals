'use client';

import React from 'react';

export function ComingSoonPanel({ title, itens }: { title: string; itens: string[] }) {
  return (
    <div style={{ background: 'var(--dw-bg-soft)', border: '1px dashed var(--dw-rule)', borderRadius: 10, padding: 16, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--dw-ink-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>{title}</p>
        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 999, background: '#EEF2FF', color: 'var(--dw-blue)', border: '1px solid #C7D2FE' }}>em breve</span>
      </div>
      <ul style={{ margin: 0, paddingLeft: 16, color: 'var(--dw-ink-muted)', fontSize: 12, lineHeight: 1.7 }}>
        {itens.map((i) => <li key={i}>{i}</li>)}
      </ul>
    </div>
  );
}
