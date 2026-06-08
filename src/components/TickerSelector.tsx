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
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        placeholder={placeholder}
        list={listId}
        className="w-36 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <datalist id={listId}>
        {suggestions.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>
    </div>
  );
}
