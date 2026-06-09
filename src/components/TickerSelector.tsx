'use client';

import { useEffect, useId, useState } from 'react';
import { getSupabase } from '@/lib/supabase';

interface Props {
  value: string;
  onChange: (ticker: string) => void;
  placeholder?: string;
}

export function TickerSelector({ value, onChange, placeholder = 'Ex: PETR4' }: Props) {
  const listId = useId();
  const [suggestions, setSuggestions] = useState<string[]>([]);

  useEffect(() => {
    const sb = getSupabase();
    sb.from('signals')
      .select('ticker')
      .order('timestamp', { ascending: false })
      .limit(100)
      .then(({ data }: { data: { ticker: string }[] | null }) => {
        if (!data) return;
        const unique = [...new Set(data.map((r) => r.ticker).filter(Boolean))].slice(0, 20);
        setSuggestions(unique);
      });
  }, []);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        placeholder={placeholder}
        list={listId}
        style={{
          width: 144, borderRadius: 8, padding: '8px 12px', fontSize: 13,
          border: '1.5px solid var(--dw-rule)', background: 'var(--dw-bg-soft)',
          color: 'var(--dw-ink)', outline: 'none', fontFamily: 'var(--font-jetbrains-mono, monospace)',
        }}
      />
      <datalist id={listId}>
        {suggestions.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>
    </div>
  );
}
