'use client';

export function MaChip({ label, pct }: { label: string; pct: number }) {
  const positive = pct >= 0;
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 6, fontSize: 12, fontWeight: 600,
      background: positive ? '#FEE2E2' : '#D1FAE5',
      color: positive ? '#991B1B' : '#065F46',
    }}>
      {label} {positive ? '+' : ''}{pct.toFixed(1)}%
    </span>
  );
}
