'use client';

import { scoreAsset } from '@/lib/asset-analysis';
import type { AssetAnalysisPayload, AssetVerdict } from '@/lib/types/analytics';

interface Props {
  payload: AssetAnalysisPayload;
  onVerdict?: (v: AssetVerdict) => void;
}

const verdictStyle: Record<AssetVerdict, { label: string; class: string }> = {
  barato: { label: '🟢 Barato', class: 'bg-emerald-900/40 text-emerald-300 border-emerald-700' },
  neutro: { label: '🟡 Neutro', class: 'bg-yellow-900/40 text-yellow-300 border-yellow-700' },
  caro:   { label: '🔴 Caro',   class: 'bg-red-900/40 text-red-300 border-red-700' },
};

function RangeBar({ value, min, max, label }: { value: number; min: number; max: number; label: string }) {
  const range = max - min || 1;
  const pct = Math.max(0, Math.min(100, ((value - min) / range) * 100));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>{label}</span>
        <span>R$ {value.toFixed(2)}</span>
      </div>
      <div className="relative h-2 w-full rounded-full bg-zinc-700">
        <div className="absolute inset-y-0 left-0 rounded-full bg-zinc-500" style={{ width: `${pct}%` }} />
        <div
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-blue-400 border-2 border-white shadow"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-zinc-500">
        <span>R$ {min.toFixed(2)}</span>
        <span>R$ {max.toFixed(2)}</span>
      </div>
    </div>
  );
}

function RsiGauge({ rsi }: { rsi: number }) {
  const pct = Math.max(0, Math.min(100, rsi));
  const color = rsi < 30 ? 'text-emerald-400' : rsi > 70 ? 'text-red-400' : 'text-yellow-400';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>RSI 14</span>
        <span className={`font-semibold ${color}`}>{rsi.toFixed(1)}</span>
      </div>
      <div className="relative h-2 w-full rounded-full bg-zinc-700">
        <div className="absolute inset-y-0 left-0 w-[30%] rounded-l-full bg-emerald-800/50" />
        <div className="absolute inset-y-0 left-[30%] w-[40%] bg-yellow-800/50" />
        <div className="absolute inset-y-0 left-[70%] w-[30%] rounded-r-full bg-red-800/50" />
        <div
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-white border-2 border-zinc-400 shadow"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-zinc-500">
        <span>Sobrevendido</span><span>Neutro</span><span>Sobrecomprado</span>
      </div>
    </div>
  );
}

function BollingerBar({ pctB }: { pctB: number }) {
  const pct = Math.max(0, Math.min(100, pctB * 100));
  const color = pctB < 0.20 ? 'text-emerald-400' : pctB > 0.80 ? 'text-red-400' : 'text-zinc-300';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>Bollinger %B</span>
        <span className={`font-semibold ${color}`}>{(pctB * 100).toFixed(0)}%</span>
      </div>
      <div className="relative h-2 w-full rounded-full bg-zinc-700">
        <div className="absolute inset-y-0 left-0 rounded-full bg-blue-500/60" style={{ width: `${pct}%` }} />
      </div>
      <div className="flex justify-between text-xs text-zinc-500">
        <span>Banda inferior</span><span>Banda superior</span>
      </div>
    </div>
  );
}

function ZScoreBadge({ z }: { z: number }) {
  const color = z < -1 ? 'text-emerald-400' : z > 0 ? 'text-red-400' : 'text-yellow-400';
  const label = z < -1 ? 'Abaixo da média' : z > 1 ? 'Acima da média' : 'Próximo da média';
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-zinc-400 text-xs">Z-Score vs MA20</span>
      <span className={`font-semibold ${color}`}>{z.toFixed(2)} <span className="text-xs font-normal text-zinc-400">({label})</span></span>
    </div>
  );
}

export function AssetAnalyzer({ payload, onVerdict }: Props) {
  const { score, verdict, breakdown } = scoreAsset(payload);

  // Notify parent on mount / change
  if (onVerdict) onVerdict(verdict);

  const { label, class: cls } = verdictStyle[verdict];
  const { preco_atual, ma20, ma50, ma200, faixa_52s_min, faixa_52s_max, rsi14, bollinger_pct_b, z_score_20 } = payload;

  const maChip = (label: string, ma: number) => {
    const pct = ((preco_atual - ma) / ma) * 100;
    const positive = pct >= 0;
    return (
      <span
        key={label}
        className={`px-2 py-0.5 rounded text-xs font-medium ${positive ? 'bg-red-900/40 text-red-300' : 'bg-emerald-900/40 text-emerald-300'}`}
      >
        {label} {positive ? '+' : ''}{pct.toFixed(1)}%
      </span>
    );
  };

  return (
    <div className="rounded-xl border border-zinc-700 bg-zinc-800/60 p-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">{payload.ticker}</h3>
          <p className="text-xs text-zinc-400">R$ {preco_atual.toFixed(2)}</p>
        </div>
        <div className={`px-3 py-1.5 rounded-lg border text-sm font-semibold ${cls}`}>
          {label}
          <span className="ml-2 text-xs font-normal opacity-70">({score}/10)</span>
        </div>
      </div>

      <RangeBar value={preco_atual} min={faixa_52s_min} max={faixa_52s_max} label="Posição na faixa 52 semanas" />

      <div className="space-y-1">
        <p className="text-xs text-zinc-400">Médias móveis</p>
        <div className="flex flex-wrap gap-1.5">
          {maChip('MA20', ma20)}
          {maChip('MA50', ma50)}
          {maChip('MA200', ma200)}
        </div>
      </div>

      <RsiGauge rsi={rsi14} />
      <BollingerBar pctB={bollinger_pct_b} />
      <ZScoreBadge z={z_score_20} />

      <div className="grid grid-cols-5 gap-1 pt-1 border-t border-zinc-700">
        {(Object.entries(breakdown) as [string, number][]).map(([k, v]) => (
          <div key={k} className="text-center">
            <div className="text-xs text-zinc-500 capitalize">{k}</div>
            <div className={`text-sm font-bold ${v === 2 ? 'text-emerald-400' : v === 1 ? 'text-yellow-400' : 'text-red-400'}`}>{v}/2</div>
          </div>
        ))}
      </div>
    </div>
  );
}
